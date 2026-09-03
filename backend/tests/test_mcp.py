import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

from backend.mcp_client import MCPClient


class MCPIntegrationTests(unittest.TestCase):
    def test_discovers_and_calls_bundled_file_tools(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as directory:
                project_directory = Path(directory, "project")
                project_directory.mkdir()
                Path(project_directory, "draft.txt").write_text("Draft content", encoding="utf-8")
                Path(directory, "outside.txt").write_text("Private content", encoding="utf-8")
                async with MCPClient(
                    sys.executable,
                    ["-m", "backend.mcp_server"],
                    {"COWRITER_PROJECT_PATH": str(project_directory)},
                    Path(__file__).resolve().parents[2],
                ) as client:
                    tools = await client.list_tools()
                    result = await client.call_tool("read_file", {"path": "draft.txt"})
                    escaped_result = await client.call_tool("read_file", {"path": "../outside.txt"})

                self.assertEqual({tool.name for tool in tools}, {"read_file", "list_files"})
                self.assertIn("Draft content", result.content[0].text)
                self.assertTrue(escaped_result.is_error)
                self.assertNotIn("Private content", escaped_result.content[0].text)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
