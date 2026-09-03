from pathlib import Path

if __package__ and __package__.startswith("backend."):
    from ..tools.files import _project_path, _project_root
else:
    from tools.files import _project_path, _project_root


def list_files() -> list[str]:
    root = _project_root()
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    )


def fetch_file(file_id: str) -> str:
    _, file_path = _project_path(file_id)
    if not file_path.is_file():
        raise ValueError(f"File {file_id!r} was not found.")
    return Path(file_path).read_text(encoding="utf-8")
