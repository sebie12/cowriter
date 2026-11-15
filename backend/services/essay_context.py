"""Finds a project's main LaTeX essay and turns it into prose the proofreader can compare against."""

import re
from dataclasses import dataclass
from pathlib import Path

from backend.tools.files import latex_to_text


MAX_ESSAY_CHARS = 24_000
MAX_INCLUDE_DEPTH = 5
MAX_TEX_FILES = 200
_IGNORED_DIRECTORIES = {".git", "node_modules", "__pycache__", ".venv", "build", "out"}
_INCLUDE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
_COMMENT = re.compile(r"(?<!\\)%.*")


@dataclass(frozen=True)
class EssayContext:
    relative_path: str
    text: str
    truncated: bool


def _inside(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root)
    except (ValueError, OSError):
        return False
    return True


def _tex_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.tex"):
        if len(files) >= MAX_TEX_FILES:
            break
        relative_parts = path.relative_to(root).parts
        if any(part.startswith(".") or part in _IGNORED_DIRECTORIES for part in relative_parts[:-1]):
            continue
        if path.is_file() and _inside(root, path):
            files.append(path)
    return files


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def find_essay_file(root: Path) -> Path | None:
    """Prefer the file that starts the document; otherwise the largest .tex file."""
    files = _tex_files(root)
    if not files:
        return None
    documents = [path for path in files if "\\begin{document}" in _COMMENT.sub("", _read(path))]
    candidates = documents or files
    return max(candidates, key=lambda path: (path.stat().st_size, -len(path.parts)))


def _inline_includes(root: Path, path: Path, depth: int = 0) -> str:
    """Replace \\input/\\include with the included file's source so split essays read as one."""
    source = _COMMENT.sub("", _read(path))
    if depth >= MAX_INCLUDE_DEPTH:
        return source

    def replace(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        target = (path.parent / name)
        if target.suffix.lower() != ".tex":
            target = target.with_name(target.name + ".tex")
        if not target.is_file() or not _inside(root, target):
            return ""
        included = _inline_includes(root, target, depth + 1)
        # Preambles and macro files carry no prose; leave them out of the body.
        return "" if "\\documentclass" in included or "\\usepackage" in included else included

    return _INCLUDE.sub(replace, source)


def load_essay(project_path: str, max_chars: int = MAX_ESSAY_CHARS) -> EssayContext | None:
    root = Path(project_path).expanduser().resolve()
    if not root.is_dir():
        return None
    essay_file = find_essay_file(root)
    if essay_file is None:
        return None

    text, _ = latex_to_text(_inline_includes(root, essay_file))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return None
    truncated = len(text) > max_chars
    if truncated:
        cut = text.rfind("\n", 0, max_chars)
        text = text[: cut if cut > max_chars // 2 else max_chars].rstrip()
    return EssayContext(
        relative_path=essay_file.relative_to(root).as_posix(),
        text=text,
        truncated=truncated,
    )
