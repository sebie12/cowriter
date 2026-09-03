def register_resources_tools(mcp):
    from backend.resources.project import list_files, fetch_file

    @mcp.tool()
    def list_project_files() -> list[str]:
        """List all files in the current project."""
        return list_files()

    @mcp.tool()
    def fetch_project_file(path: str) -> str:
        """Read a project file by its relative path."""
        return fetch_file(path)
