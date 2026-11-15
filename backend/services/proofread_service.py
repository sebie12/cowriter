import asyncio
import json
import re
from typing import Any
from uuid import uuid4

from backend.llm.contracts import ChatRequest, LLMError, ToolDefinition
from backend.prompts import SystemPrompts
from backend.services.chat_service import MAX_TOOL_ROUNDS, ChatService


ISSUE_TYPES = {"spelling", "grammar", "claim", "style"}
MAX_TEXT_LENGTH = 60_000
MAX_ISSUES = 200
UNREADABLE_REVIEW = "The model returned an unreadable review; try again or a larger model."


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
    ) -> list[dict[str, Any]]:
        if not text.strip():
            return []
        if len(text) > MAX_TEXT_LENGTH:
            raise LLMError(f"The draft must be {MAX_TEXT_LENGTH} characters or fewer to review.", 413)

        llm, config = self.chat_service.resolve_provider(
            connection_id=connection_id,
            requested_provider=provider,
        )
        request = ChatRequest(
            connection_id=connection_id,
            provider=provider,
            model=model,
            message=f"Review this draft:\n<<<\n{text}\n>>>",
            system_prompt=SystemPrompts.proofread(
                description=description,
                references=references or [],
                can_read_project_files=project_path is not None,
            ),
        )

        if project_path is None:
            content = llm.chat(request, config).message
        else:
            content = self._run(self._review_with_tools(request, llm, config, project_path))

        valid_reference_ids = {reference["id"] for reference in references or []}
        return locate_issues(text, parse_review(content), valid_reference_ids)

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

    async def _review_with_tools(self, request, llm, config, project_path) -> str:
        try:
            async with self.chat_service.mcp_client_factory(project_path) as client:
                tools = tuple(
                    ToolDefinition(
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=tool.input_schema,
                    )
                    for tool in await client.list_tools()
                )
                if not tools:
                    return llm.chat(request, config).message

                messages: list[dict[str, Any]] = [
                    {"role": "system", "content": request.system_prompt},
                    *request.model_messages(),
                ]
                for _ in range(MAX_TOOL_ROUNDS):
                    turn = llm.complete_chat(request, config, messages, tools)
                    if not turn.tool_calls:
                        return turn.content
                    messages.append(ChatService._assistant_tool_message(turn))
                    for call in turn.tool_calls:
                        result = await client.call_tool(call.name, call.arguments)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "tool_name": call.name,
                            "content": ChatService._serialize_mcp_result(result),
                        })
        except LLMError:
            raise
        except Exception as error:
            raise LLMError("Could not communicate with the project tools.", 502) from error
        raise LLMError("The review needed too many file lookups. Try again.", 502)


def parse_review(content: str) -> list[dict[str, Any]]:
    """Extract the issues array from the model's (hopefully JSON) reply."""
    if not isinstance(content, str):
        raise LLMError(UNREADABLE_REVIEW, 502)
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end < start:
        raise LLMError(UNREADABLE_REVIEW, 502)
    try:
        payload = json.loads(content[start:end + 1])
    except ValueError as error:
        raise LLMError(UNREADABLE_REVIEW, 502) from error
    issues = payload.get("issues") if isinstance(payload, dict) else None
    if not isinstance(issues, list):
        raise LLMError(UNREADABLE_REVIEW, 502)
    return [issue for issue in issues if isinstance(issue, dict)]


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
        suggestion = suggestion if isinstance(suggestion, str) and suggestion != quote else None
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
