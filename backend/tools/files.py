import os
from pathlib import Path

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


def register_file_tools(mcp):
    @mcp.tool()
    async def read_file(path: str) -> dict:
        """Read a UTF-8 text file using a path relative to the current project."""
        _, file_path = _project_path(path)
        if not file_path.is_file():
            raise ToolError("File not found.")
        return {"content": file_path.read_text(encoding="utf-8")}

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
