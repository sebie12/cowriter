import asyncio
import unittest
from types import SimpleNamespace

from backend.llm import ChatRequest, ChatResult, LLMError, ModelTurn, ToolCall
from backend.llm.contracts import ToolDefinition
from backend.services import ChatService
from backend.services.chat_service import LocalTool


class FakeCredentialStore:
    def __init__(self, credentials=None):
        self.credentials = credentials or {}
        self.call = None

    def get_many(self, provider, account_id, fields):
        self.call = (provider, account_id, fields)
        return {
            field: self.credentials[field]
            for field in fields
            if field in self.credentials
        }


class FakeProvider:
    provider_ids = {"openai"}
    credential_fields = ("api_key",)

    def __init__(self):
        self.chat_call = None
        self.stream_chat_call = None
        self.models_config = None
        self.complete_chat_calls = []
        self.turns = []

    def chat(self, request, config):
        self.chat_call = (request, config)
        return ChatResult(message="answer")

    def stream_chat(self, request, config):
        self.stream_chat_call = (request, config)
        return iter(["streamed ", "answer"])

    def complete_chat(self, request, config, messages, tools):
        self.complete_chat_calls.append((request, config, list(messages), tools))
        return self.turns.pop(0)

    def list_models(self, config):
        self.models_config = config
        return ["gpt-test"]


class FakeOllamaProvider(FakeProvider):
    provider_ids = {"ollama"}
    credential_fields = ()


class FakeMCPClient:
    def __init__(self):
        self.calls = []
        self.context_task = None

    async def __aenter__(self):
        self.context_task = asyncio.current_task()
        return self

    async def __aexit__(self, _exception_type, _exception, _traceback):
        if asyncio.current_task() is not self.context_task:
            raise RuntimeError("MCP context exited in a different task.")
        return False

    async def list_tools(self):
        return [SimpleNamespace(
            name="read_file",
            description="Read a project file.",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        )]

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return SimpleNamespace(
            structured_content={"content": "project text"},
            content=[],
            is_error=False,
        )


class PagedMCPClient(FakeMCPClient):
    async def list_tools(self):
        return [SimpleNamespace(
            name="read_file",
            description="Read a project file.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "offset": {"type": "integer"},
                    "max_chars": {"type": "integer"},
                },
                "required": ["path"],
            },
        )]


class FailingMCPClient(FakeMCPClient):
    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        raise RuntimeError("Tool process stopped.")


class FakeToolCallService:
    def __init__(self):
        self.started = []
        self.completed = []
        self.failed = []

    def start_tool_call(self, **values):
        self.started.append(values)
        record = FakeToolCallRecord(len(self.started), **values)
        return record

    def mark_tool_call_running(self, tool_call_id):
        record = FakeToolCallRecord.records[tool_call_id]
        record.status = "running"
        return record

    def complete_tool_call(self, tool_call_id, **values):
        self.completed.append((tool_call_id, values))
        record = FakeToolCallRecord.records[tool_call_id]
        record.status = "failed" if values.get("is_error") else "completed"
        record.output_data = values["output_data"]
        record.error = values.get("error")
        record.completed_at = "2026-09-19T10:00:01Z"
        return record

    def fail_tool_call(self, tool_call_id, error):
        self.failed.append((tool_call_id, str(error)))
        record = FakeToolCallRecord.records[tool_call_id]
        record.status = "failed"
        record.error = str(error)
        record.completed_at = "2026-09-19T10:00:01Z"
        return record


class FakeToolCallRecord:
    records = {}

    def __init__(self, record_id, **values):
        self.id = record_id
        self.conversation_id = values["conversation_id"]
        self.provider_call_id = values["provider_call_id"]
        self.tool_name = values["tool_name"]
        self.input_data = values["input_data"]
        self.output_data = None
        self.status = "pending"
        self.error = None
        self.created_at = "2026-09-19T10:00:00Z"
        self.completed_at = None
        self.records[self.id] = self

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "provider_call_id": self.provider_call_id,
            "tool_name": self.tool_name,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "status": self.status,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class ChatServiceTests(unittest.TestCase):
    def setUp(self):
        FakeToolCallRecord.records = {}
        self.connection = SimpleNamespace(
            provider="openai",
            account_id="account-1",
            endpoint_url=None,
            status="connected",
        )
        self.provider = FakeProvider()
        self.credentials = FakeCredentialStore({"api_key": "secret"})
        self.service = ChatService(
            connection_lookup=lambda connection_id: self.connection if connection_id == 7 else None,
            credential_store=self.credentials,
            providers=[self.provider, FakeOllamaProvider()],
        )

    def test_selects_provider_and_passes_normalized_configuration(self):
        request = ChatRequest(7, "OpenAI", "gpt-test", "Hello")

        result = self.service.chat(request)

        self.assertEqual(result.message, "answer")
        self.assertEqual(self.provider.chat_call[0], request)
        self.assertEqual(self.provider.chat_call[1].credentials, {"api_key": "secret"})
        self.assertEqual(self.credentials.call, ("openai", "account-1", ("api_key",)))

    def test_lists_models_through_selected_provider(self):
        provider_id, models = self.service.list_models(7)

        self.assertEqual(provider_id, "openai")
        self.assertEqual(models, ["gpt-test"])
        self.assertEqual(self.provider.models_config.credentials, {"api_key": "secret"})

    def test_streams_chat_through_selected_provider(self):
        request = ChatRequest(7, "OpenAI", "gpt-test", "Hello")

        chunks = list(self.service.stream_chat(request))

        self.assertEqual([event["type"] for event in chunks], [
            "assistant_start",
            "assistant_delta",
            "assistant_delta",
            "assistant_end",
        ])
        self.assertEqual(
            [event["content"] for event in chunks if event["type"] == "assistant_delta"],
            ["streamed ", "answer"],
        )
        self.assertEqual(self.provider.stream_chat_call[0], request)
        self.assertEqual(self.provider.stream_chat_call[1].credentials, {"api_key": "secret"})

    def test_feeds_mcp_tools_and_results_to_provider(self):
        mcp_client = FakeMCPClient()
        tool_call_service = FakeToolCallService()
        self.provider.turns = [
            ModelTurn("", (ToolCall("call-1", "read_file", {"path": "draft.txt"}),)),
            ModelTurn("Answer from the project file."),
        ]
        service = ChatService(
            connection_lookup=lambda _connection_id: self.connection,
            credential_store=self.credentials,
            providers=[self.provider],
            project_lookup=lambda _project_id: SimpleNamespace(path="/tmp/project"),
            mcp_client_factory=lambda _project_path: mcp_client,
            conversation_resolver=lambda _project_id: SimpleNamespace(id=12),
            tool_call_service=tool_call_service,
        )

        chunks = list(service.stream_chat(
            ChatRequest(7, "openai", "gpt-test", "Read it", project_id=3)
        ))

        self.assertEqual(
            [event["type"] for event in chunks],
            [
                "tool_call",
                "tool_call",
                "tool_call",
                "assistant_start",
                "assistant_delta",
                "assistant_end",
            ],
        )
        self.assertEqual(
            [event["tool_call"]["status"] for event in chunks if event["type"] == "tool_call"],
            ["pending", "running", "completed"],
        )
        self.assertEqual(len(mcp_client.calls), 1)
        self.assertEqual(mcp_client.calls[0][0], "read_file")
        self.assertEqual(mcp_client.calls[0][1]["path"], "draft.txt")
        self.assertGreater(mcp_client.calls[0][1]["max_chars"], 0)
        self.assertEqual(self.provider.complete_chat_calls[0][3][0].name, "read_file")
        self.assertEqual(self.provider.complete_chat_calls[1][2][-1], {
            "role": "tool",
            "tool_call_id": "call-1",
            "tool_name": "read_file",
            "content": '{"content": "project text"}',
        })
        self.assertEqual(tool_call_service.started, [{
            "conversation_id": 12,
            "provider_call_id": "call-1",
            "tool_name": "read_file",
            "input_data": {"path": "draft.txt"},
        }])
        self.assertEqual(tool_call_service.completed, [(1, {
            "output_data": {"content": "project text"},
            "is_error": False,
            "error": None,
        })])
        self.assertEqual(tool_call_service.failed, [])

    def test_records_tool_execution_exception(self):
        mcp_client = FailingMCPClient()
        tool_call_service = FakeToolCallService()
        self.provider.turns = [
            ModelTurn("", (ToolCall("call-2", "read_file", {"path": "draft.txt"}),)),
        ]
        service = ChatService(
            connection_lookup=lambda _connection_id: self.connection,
            credential_store=self.credentials,
            providers=[self.provider],
            project_lookup=lambda _project_id: SimpleNamespace(path="/tmp/project"),
            mcp_client_factory=lambda _project_path: mcp_client,
            conversation_resolver=lambda _project_id: SimpleNamespace(id=13),
            tool_call_service=tool_call_service,
        )

        events = iter(service.stream_chat(
            ChatRequest(7, "openai", "gpt-test", "Read it", project_id=3)
        ))
        self.assertEqual(next(events)["tool_call"]["status"], "pending")
        self.assertEqual(next(events)["tool_call"]["status"], "running")
        self.assertEqual(next(events)["tool_call"]["status"], "failed")
        with self.assertRaisesRegex(LLMError, "project tools"):
            next(events)

        self.assertEqual(tool_call_service.failed, [(1, "Tool process stopped.")])
        self.assertEqual(tool_call_service.completed, [])

    def test_emits_multiple_tool_calls_in_execution_order(self):
        mcp_client = FakeMCPClient()
        tool_call_service = FakeToolCallService()
        self.provider.turns = [
            ModelTurn("", (
                ToolCall("call-1", "read_file", {"path": "first.txt"}),
                ToolCall("call-2", "read_file", {"path": "second.txt"}),
            )),
            ModelTurn("Both files were read."),
        ]
        service = ChatService(
            connection_lookup=lambda _connection_id: self.connection,
            credential_store=self.credentials,
            providers=[self.provider],
            project_lookup=lambda _project_id: SimpleNamespace(path="/tmp/project"),
            mcp_client_factory=lambda _project_path: mcp_client,
            conversation_resolver=lambda _project_id: SimpleNamespace(id=14),
            tool_call_service=tool_call_service,
        )

        events = list(service.stream_chat(
            ChatRequest(7, "openai", "gpt-test", "Read both", project_id=3)
        ))
        tool_events = [event["tool_call"] for event in events if event["type"] == "tool_call"]

        self.assertEqual(
            [(event["provider_call_id"], event["status"]) for event in tool_events],
            [
                ("call-1", "pending"),
                ("call-1", "running"),
                ("call-1", "completed"),
                ("call-2", "pending"),
                ("call-2", "running"),
                ("call-2", "completed"),
            ],
        )

    def test_rejects_connection_provider_mismatch(self):
        request = ChatRequest(7, "ollama", "model", "Hello")

        with self.assertRaisesRegex(LLMError, "does not match"):
            self.service.chat(request)

    def test_reports_supported_providers(self):
        self.assertTrue(self.service.supports_provider("OpenAI"))
        self.assertTrue(self.service.supports_provider("ollama"))
        self.assertFalse(self.service.supports_provider("gemini"))

    def test_rejects_missing_credentials(self):
        self.credentials.credentials = {}

        with self.assertRaisesRegex(LLMError, "credentials are not configured") as raised:
            self.service.chat(ChatRequest(7, "openai", "model", "Hello"))

        self.assertEqual(raised.exception.status_code, 409)

    def test_rejects_missing_connection(self):
        with self.assertRaisesRegex(LLMError, "not found") as raised:
            self.service.chat(ChatRequest(99, "openai", "model", "Hello"))

        self.assertEqual(raised.exception.status_code, 404)


    def make_tool_service(self, mcp_client, tool_call_service):
        return ChatService(
            connection_lookup=lambda _connection_id: self.connection,
            credential_store=self.credentials,
            providers=[self.provider],
            project_lookup=lambda _project_id: SimpleNamespace(path="/tmp/project"),
            mcp_client_factory=lambda _project_path: mcp_client,
            conversation_resolver=lambda _project_id: SimpleNamespace(id=15),
            tool_call_service=tool_call_service,
        )

    def test_read_file_is_limited_to_the_remaining_context(self):
        mcp_client = PagedMCPClient()
        self.provider.context_window = lambda _config, _model: 3000
        self.provider.turns = [
            ModelTurn("", (ToolCall("call-1", "read_file", {"path": "draft.tex"}),)),
            ModelTurn("Done."),
        ]
        service = self.make_tool_service(mcp_client, FakeToolCallService())

        list(service.stream_chat(ChatRequest(7, "openai", "gpt-test", "Read it", project_id=3)))

        max_chars = mcp_client.calls[0][1]["max_chars"]
        self.assertGreater(max_chars, 0)
        self.assertLess(max_chars, (3000 - 1024) * 4)
        schema = self.provider.complete_chat_calls[0][3][0].input_schema
        self.assertNotIn("max_chars", schema["properties"])
        self.assertIn("offset", schema["properties"])
        self.assertEqual(schema["required"], ["path"])

    def test_model_cannot_raise_its_own_read_limit(self):
        mcp_client = PagedMCPClient()
        self.provider.context_window = lambda _config, _model: 3000
        self.provider.turns = [
            ModelTurn("", (ToolCall("call-1", "read_file", {"path": "a", "max_chars": 10**9}),)),
            ModelTurn("Done."),
        ]
        service = self.make_tool_service(mcp_client, FakeToolCallService())

        list(service.stream_chat(ChatRequest(7, "openai", "gpt-test", "Read it", project_id=3)))

        self.assertLess(mcp_client.calls[0][1]["max_chars"], 3000 * 4)

    def test_full_context_skips_the_read_and_tells_the_model(self):
        mcp_client = PagedMCPClient()
        tool_call_service = FakeToolCallService()
        self.provider.context_window = lambda _config, _model: 1200
        self.provider.turns = [
            ModelTurn("", (ToolCall("call-1", "read_file", {"path": "draft.tex"}),)),
            ModelTurn("Answer without the file."),
        ]
        service = self.make_tool_service(mcp_client, tool_call_service)

        events = list(service.stream_chat(
            ChatRequest(7, "openai", "gpt-test", "Read it", project_id=3)
        ))

        self.assertEqual(mcp_client.calls, [])
        self.assertEqual(
            [event["tool_call"]["status"] for event in events if event["type"] == "tool_call"],
            ["pending", "running", "failed"],
        )
        self.assertIn("context is full", tool_call_service.failed[0][1])
        self.assertIn("context is full", self.provider.complete_chat_calls[1][2][-1]["content"])

    def test_unknown_context_window_uses_default(self):
        self.assertEqual(ChatService.context_window(object(), None, "m"), 4096)


    def make_local_tool_service(self, tool_call_service, run):
        local_tool = LocalTool(
            definition=ToolDefinition("update_project_settings", "Change settings.", {"type": "object"}),
            run=run,
        )
        return ChatService(
            connection_lookup=lambda _connection_id: self.connection,
            credential_store=self.credentials,
            providers=[self.provider],
            project_lookup=lambda _project_id: SimpleNamespace(path=None),
            mcp_client_factory=lambda _project_path: self.fail("MCP must not start without a path."),
            conversation_resolver=lambda _project_id: SimpleNamespace(id=12),
            tool_call_service=tool_call_service,
            local_tools=[local_tool],
        )

    def test_runs_local_tools_in_process_without_a_project_path(self):
        tool_call_service = FakeToolCallService()
        runs = []

        def run(project_id, arguments):
            runs.append((project_id, arguments))
            return {"name": "Fixed title"}

        self.provider.turns = [
            ModelTurn("", (ToolCall("call-1", "update_project_settings", {"title": "Fixed title"}),)),
            ModelTurn("Renamed."),
        ]
        service = self.make_local_tool_service(tool_call_service, run)

        chunks = list(service.stream_chat(
            ChatRequest(7, "openai", "gpt-test", "Fix the title", project_id=3)
        ))

        self.assertEqual(runs, [(3, {"title": "Fixed title"})])
        self.assertEqual(
            [event["tool_call"]["status"] for event in chunks if event["type"] == "tool_call"],
            ["pending", "running", "completed"],
        )
        self.assertEqual(
            [tool.name for tool in self.provider.complete_chat_calls[0][3]],
            ["update_project_settings"],
        )
        self.assertEqual(
            self.provider.complete_chat_calls[1][2][-1]["content"],
            '{"name": "Fixed title"}',
        )

    def test_rejected_local_tool_arguments_become_a_tool_error(self):
        tool_call_service = FakeToolCallService()

        def run(_project_id, _arguments):
            raise ValueError("tone is invalid.")

        self.provider.turns = [
            ModelTurn("", (ToolCall("call-1", "update_project_settings", {"tone": "Loud"}),)),
            ModelTurn("That tone isn't available."),
        ]
        service = self.make_local_tool_service(tool_call_service, run)

        chunks = list(service.stream_chat(
            ChatRequest(7, "openai", "gpt-test", "Make it loud", project_id=3)
        ))

        self.assertEqual(chunks[-1]["type"], "assistant_end")
        self.assertEqual(tool_call_service.completed, [(1, {
            "output_data": {"error": "tone is invalid."},
            "is_error": True,
            "error": "tone is invalid.",
        })])
        self.assertEqual(
            self.provider.complete_chat_calls[1][2][-1]["content"],
            "Tool error: tone is invalid.",
        )

    def test_local_tools_need_a_project(self):
        service = self.make_local_tool_service(FakeToolCallService(), lambda *_: {})

        chunks = list(service.stream_chat(ChatRequest(7, "openai", "gpt-test", "Hello")))

        self.assertEqual(self.provider.complete_chat_calls, [])
        self.assertEqual(chunks[1]["content"], "streamed ")


if __name__ == "__main__":
    unittest.main()
