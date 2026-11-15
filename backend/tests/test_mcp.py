import asyncio
import json
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


    def test_read_file_cleans_latex_and_paginates(self):
        def data(result):
            return json.loads(result.content[0].text)

        async def run_test():
            with tempfile.TemporaryDirectory() as directory:
                project_directory = Path(directory)
                Path(project_directory, "paper.tex").write_text(
                    "\\documentclass{article}\n\\usepackage{amsmath}\n% private note\n"
                    "\\begin{document}\n\\section{Intro}\nThis is \\emph{important} prose.\n"
                    "\\end{document}\n",
                    encoding="utf-8",
                )
                Path(project_directory, "broken.tex").write_text(
                    "\\begin{itemize} unclosed {", encoding="utf-8"
                )
                long_text = " ".join(f"word{index}" for index in range(200))
                Path(project_directory, "notes.txt").write_text(long_text, encoding="utf-8")
                async with MCPClient(
                    sys.executable,
                    ["-m", "backend.mcp_server"],
                    {"COWRITER_PROJECT_PATH": str(project_directory)},
                    Path(__file__).resolve().parents[2],
                ) as client:
                    latex = await client.call_tool("read_file", {"path": "paper.tex"})
                    broken = await client.call_tool("read_file", {"path": "broken.tex"})
                    first = await client.call_tool(
                        "read_file", {"path": "notes.txt", "max_chars": 100}
                    )
                    rest = await client.call_tool(
                        "read_file",
                        {"path": "notes.txt", "offset": data(first)["next_offset"]},
                    )
                    beyond = await client.call_tool(
                        "read_file", {"path": "notes.txt", "offset": 10**6}
                    )

                content = data(latex)["content"]
                self.assertIn("Intro", content)
                self.assertIn("This is important prose.", content)
                self.assertNotIn("\\", content)
                self.assertNotIn("private note", content)
                self.assertNotIn("amsmath", content)

                self.assertFalse(data(broken)["cleaned"])
                self.assertIn("unclosed", data(broken)["content"])

                self.assertTrue(data(first)["truncated"])
                self.assertLessEqual(len(data(first)["content"]), 100)
                self.assertTrue(data(first)["content"].endswith(" "))
                self.assertFalse(data(rest)["truncated"])
                self.assertIsNone(data(rest)["next_offset"])
                self.assertEqual(
                    data(first)["content"] + data(rest)["content"],
                    long_text,
                )
                self.assertTrue(beyond.is_error)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
