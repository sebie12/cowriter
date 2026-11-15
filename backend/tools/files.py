import os
from pathlib import Path

import pypandoc
from mcp.server.mcpserver.exceptions import ToolError


def _project_root() -> Path:
    configured_path = os.environ.get("COWRITER_PROJECT_PATH")
    if not configured_path:
        raise ToolError("No project directory was configured for this MCP server.")
    root = Path(configured_path).resolve()
    if not root.is_dir():
        raise ToolError("The configured project directory does not exist.")
    return root


def _project_path(relative_path: str) -> tuple[Path, Path]:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ToolError("A relative project path is required.")

    root = _project_root()
    requested = Path(relative_path)
    if requested.is_absolute():
        raise ToolError("Only paths relative to the project directory are allowed.")

    target = (root / requested).resolve()
    try:
        target.relative_to(root)
    except ValueError as error:
        raise ToolError("The path is outside the project directory.") from error
    return root, target


def latex_to_text(source: str) -> tuple[str, bool]:
    """Convert LaTeX to plain prose; returns (text, converted)."""
    try:
        return pypandoc.convert_text(
            source, "plain", format="latex", extra_args=["--wrap=none"]
        ), True
    except (RuntimeError, OSError):
        # Malformed LaTeX still beats no content at all.
        return source, False


def _readable_text(file_path: Path) -> tuple[str, bool]:
    """Return the file's text, with LaTeX markup converted to plain prose."""
    source = file_path.read_text(encoding="utf-8")
    if file_path.suffix.lower() != ".tex":
        return source, True
    return latex_to_text(source)


def _page(text: str, offset: int, max_chars: int | None) -> tuple[str, int | None]:
    """Slice text from offset, ending on whitespace so words aren't split."""
    if max_chars is None or offset + max_chars >= len(text):
        return text[offset:], None
    end = offset + max_chars
    boundary = text.rfind(" ", offset, end)
    newline = text.rfind("\n", offset, end)
    boundary = max(boundary, newline)
    if boundary > offset:
        end = boundary + 1
    return text[offset:end], end


def register_file_tools(mcp):
    @mcp.tool()
    async def read_file(path: str, offset: int = 0, max_chars: int | None = None) -> dict:
        """Read a text file using a path relative to the current project.

        LaTeX files come back as plain prose. Long files come back in parts: when
        `truncated` is true, call again with `offset` set to `next_offset`.
        """
        _, file_path = _project_path(path)
        if not file_path.is_file():
            raise ToolError("File not found.")
        if max_chars is not None and max_chars < 1:
            raise ToolError("max_chars must be positive.")

        text, cleaned = _readable_text(file_path)
        if offset < 0 or (offset > 0 and offset >= len(text)):
            raise ToolError("offset is outside the file.")
        content, next_offset = _page(text, offset, max_chars)
        return {
            "content": content,
            "offset": offset,
            "next_offset": next_offset,
            "total_chars": len(text),
            "truncated": next_offset is not None,
            "cleaned": cleaned,
        }

    @mcp.tool()
    async def list_files(directory: str = ".") -> dict:
        """Recursively list files under a project-relative directory."""
        root, directory_path = _project_path(directory)
        if not directory_path.is_dir():
            raise ToolError("Directory not found.")
        return {
            "files": sorted(
                path.relative_to(root).as_posix()
                for path in directory_path.rglob("*")
                if path.is_file()
            )
        }
