import asyncio
import difflib
import json
import logging
import re
from typing import Any
from uuid import uuid4

from backend.llm.contracts import ChatRequest, LLMError
from backend.prompts import SystemPrompts
from backend.services.chat_service import CONTEXT_FULL_MESSAGE, MAX_TOOL_ROUNDS, ChatService
from backend.services.essay_context import load_essay


ISSUE_TYPES = {"spelling", "grammar", "claim", "style"}
MAX_TEXT_LENGTH = 60_000
MAX_ISSUES = 200
UNREADABLE_REVIEW = "The model returned an unreadable review; try again or a larger model."
FINALIZE_INSTRUCTION = (
    "Now give your final review of the draft as a single JSON object in the required shape "
    '({"issues": [...]}), with no other text.'
)
FINALIZE_WITH_TOPIC_INSTRUCTION = (
    "Now give your final review of the draft as a single JSON object in the required shape "
    '({"topic": {...}, "issues": [...]}), with no other text.'
)
REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": sorted(ISSUE_TYPES)},
                    "quote": {"type": "string"},
                    "explanation": {"type": "string"},
                    "suggestion": {"type": ["string", "null"]},
                    "reference_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["type", "quote", "explanation", "suggestion", "reference_ids"],
            },
        },
    },
    "required": ["issues"],
}
# With an essay, the model also says whether the draft is about the essay's topic at all.
TOPIC_REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "topic": {
            "type": "object",
            "properties": {
                "on_topic": {"type": "boolean"},
                "explanation": {"type": "string"},
            },
            "required": ["on_topic", "explanation"],
        },
        **REVIEW_SCHEMA["properties"],
    },
    "required": ["topic", "issues"],
}

# Room for the model's answer on top of the prompt, and bounds for the requested context window.
ANSWER_TOKENS = 2048
MIN_CONTEXT_TOKENS = 4096
MAX_CONTEXT_TOKENS = 32768

logger = logging.getLogger(__name__)


def context_tokens_for(*texts: str) -> int:
    """Rough window size for a prompt (about 3 characters per token for mixed-language text)."""
    estimate = sum(len(text) for text in texts) // 3 + ANSWER_TOKENS
    rounded = -(-estimate // 1024) * 1024
    return max(MIN_CONTEXT_TOKENS, min(MAX_CONTEXT_TOKENS, rounded))


class ProofreadService:
    """Asks the selected model to review a draft and maps its findings onto the text."""

    def __init__(self, chat_service: ChatService):
        self.chat_service = chat_service

    def review(
        self,
        *,
        connection_id: int,
        provider: str,
        model: str,
        text: str,
        description: str | None = None,
        references: list[dict[str, Any]] | None = None,
        project_path: str | None = None,
    ) -> dict[str, Any]:
        """Return {"issues": [...], "topic": {...} | None, "essay_file": str | None, "essay_truncated": bool}.

        "topic" says whether the draft is about the essay's topic; it is None without an essay.
        """
        if not text.strip():
            return {"issues": [], "topic": None, "essay_file": None, "essay_truncated": False}
        if len(text) > MAX_TEXT_LENGTH:
            raise LLMError(f"The draft must be {MAX_TEXT_LENGTH} characters or fewer to review.", 413)

        llm, config = self.chat_service.resolve_provider(
            connection_id=connection_id,
            requested_provider=provider,
        )
        essay = None
        if project_path is not None:
            try:
                essay = load_essay(project_path)
            except OSError:
                logger.warning("Could not read the essay in %s", project_path, exc_info=True)

        system_prompt = SystemPrompts.proofread(
            description=description,
            references=references or [],
            can_read_project_files=project_path is not None,
            essay=essay is not None,
        )
        message = SystemPrompts.proofread_message(
            text, (essay.relative_path, essay.text, essay.truncated) if essay else None
        )
        request = ChatRequest(
            connection_id=connection_id,
            provider=provider,
            model=model,
            message=message,
            system_prompt=system_prompt,
            # Constrain the answer to valid JSON; small local models otherwise break it now and then.
            json_schema=TOPIC_REVIEW_SCHEMA if essay else REVIEW_SCHEMA,
            # Local models default to small windows and silently drop the start of longer prompts.
            context_tokens=context_tokens_for(system_prompt, message),
        )

        if project_path is None:
            payload = parse_review_payload(llm.chat(request, config).message)
        else:
            payload = self._run(self._review_with_tools(request, llm, config, project_path))

        valid_reference_ids = {reference["id"] for reference in references or []}
        return {
            "issues": locate_issues(text, payload["issues"], valid_reference_ids),
            "topic": parse_topic(payload) if essay else None,
            "essay_file": essay.relative_path if essay else None,
            "essay_truncated": essay.truncated if essay else False,
        }

    @staticmethod
    def _run(coroutine):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coroutine)
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                loop.close()

    async def _review_with_tools(self, request, llm, config, project_path) -> dict[str, Any]:
        """Let the model read project files, then make sure the final answer is valid JSON.

        Structured output and tool calls can't be combined, so tool rounds run unconstrained.
        If the model's last answer isn't readable JSON (or it keeps calling tools), one more
        turn without tools asks for the final review under the JSON constraint.
        """
        try:
            async with self.chat_service.mcp_client_factory(project_path) as client:
                tools = ChatService.tool_definitions(await client.list_tools())
                if not tools:
                    return parse_review_payload(llm.chat(request, config).message)

                messages: list[dict[str, Any]] = [
                    {"role": "system", "content": request.system_prompt},
                    *request.model_messages(),
                ]
                # Ollama reports its default window, but this request asks for a larger one.
                context_window = max(
                    ChatService.context_window(llm, config, request.model),
                    request.context_tokens or 0,
                )
                for _ in range(MAX_TOOL_ROUNDS):
                    turn = llm.complete_chat(request, config, messages, tools)
                    if not turn.tool_calls:
                        try:
                            return parse_review_payload(turn.content)
                        except LLMError:
                            messages.append({"role": "assistant", "content": turn.content})
                            break
                    messages.append(ChatService._assistant_tool_message(turn))
                    for call in turn.tool_calls:
                        arguments = ChatService.budget_tool_arguments(
                            call, messages, tools, context_window
                        )
                        if arguments is None:
                            content = CONTEXT_FULL_MESSAGE
                        else:
                            result = await client.call_tool(call.name, arguments)
                            content = ChatService._serialize_mcp_result(result)
                        messages.append(ChatService._tool_message(call, content))
        except LLMError:
            raise
        except Exception as error:
            raise LLMError("Could not communicate with the project tools.", 502) from error

        finalize = (
            FINALIZE_WITH_TOPIC_INSTRUCTION
            if request.json_schema is TOPIC_REVIEW_SCHEMA
            else FINALIZE_INSTRUCTION
        )
        messages.append({"role": "user", "content": finalize})
        final_turn = llm.complete_chat(request, config, messages, ())
        return parse_review_payload(final_turn.content)


def parse_review(content: str) -> list[dict[str, Any]]:
    """Extract the issues array from the model's (hopefully JSON) reply."""
    return parse_review_payload(content)["issues"]


def parse_review_payload(content: str) -> dict[str, Any]:
    """Parse the model's (hopefully JSON) reply; the issues list is required, the rest is kept as is."""
    if not isinstance(content, str):
        raise LLMError(UNREADABLE_REVIEW, 502)
    start = content.find("{")
    end = content.rfind("}")
    payload = None
    if 0 <= start < end:
        try:
            payload = json.loads(content[start:end + 1])
        except ValueError:
            payload = None
    issues = payload.get("issues") if isinstance(payload, dict) else None
    if not isinstance(issues, list):
        logger.warning("Unreadable proofreading reply: %r", content[:2000])
        raise LLMError(UNREADABLE_REVIEW, 502)
    return {**payload, "issues": [issue for issue in issues if isinstance(issue, dict)]}


def parse_topic(payload: dict[str, Any]) -> dict[str, Any] | None:
    """The model's verdict on whether the draft is about the essay's topic, or None if it gave none.

    A missing or malformed verdict doesn't fail the review; the issues are still useful.
    """
    topic = payload.get("topic")
    if not isinstance(topic, dict) or not isinstance(topic.get("on_topic"), bool):
        return None
    return {
        "on_topic": topic["on_topic"],
        "explanation": _clean_text(topic.get("explanation"), 1000) or "",
    }


def _clean_text(value: Any, max_length: int) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()[:max_length]


def _find_quote(text: str, quote: str, search_from: int) -> tuple[int, int] | None:
    index = text.find(quote, search_from)
    if index >= 0:
        return index, index + len(quote)
    # Models often normalise whitespace or line breaks; fall back to a tolerant match.
    words = quote.split()
    if not words:
        return None
    pattern = re.compile(r"\s+".join(re.escape(word) for word in words))
    match = pattern.search(text, search_from)
    if match is None:
        return None
    return match.start(), match.end()


def _narrow_spelling_span(
    text: str, start: int, end: int, suggestion: str | None
) -> tuple[int, int]:
    """Models often quote a phrase but suggest only the corrected word; shrink to that word."""
    if not suggestion or any(character.isspace() for character in suggestion):
        return start, end
    words = list(re.finditer(r"\S+", text[start:end]))
    if len(words) < 2:
        return start, end
    best = max(
        words,
        key=lambda word: difflib.SequenceMatcher(None, word.group(0).lower(), suggestion.lower()).ratio(),
    )
    return start + best.start(), start + best.end()


def locate_issues(
    text: str,
    issues: list[dict[str, Any]],
    valid_reference_ids: set[int],
) -> list[dict[str, Any]]:
    located: list[dict[str, Any]] = []
    next_search_by_quote: dict[str, int] = {}

    for issue in issues[:MAX_ISSUES]:
        issue_type = issue.get("type")
        quote = issue.get("quote")
        explanation = _clean_text(issue.get("explanation"), 1000)
        if issue_type not in ISSUE_TYPES or not isinstance(quote, str) or not quote.strip():
            continue
        quote = quote.strip()

        span = _find_quote(text, quote, next_search_by_quote.get(quote, 0))
        if span is None:
            continue
        start, end = span
        next_search_by_quote[quote] = end

        suggestion = issue.get("suggestion")
        suggestion = suggestion.strip() if isinstance(suggestion, str) else None
        if issue_type == "spelling":
            start, end = _narrow_spelling_span(text, start, end, suggestion)
        if suggestion is not None and suggestion == text[start:end]:
            suggestion = None
        reference_ids = [
            reference_id
            for reference_id in issue.get("reference_ids") or ()
            if isinstance(reference_id, int) and reference_id in valid_reference_ids
        ]
        located.append({
            "id": f"issue-{uuid4()}",
            "type": issue_type,
            "start": start,
            "end": end,
            "quote": text[start:end],
            "explanation": explanation or "",
            "suggestion": suggestion,
            "reference_ids": reference_ids,
        })

    located.sort(key=lambda issue: (issue["start"], issue["end"]))
    return located
