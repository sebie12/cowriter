import tempfile
import unittest
from pathlib import Path

from backend.services.essay_context import find_essay_file, load_essay
from backend.services.proofread_service import MAX_CONTEXT_TOKENS, MIN_CONTEXT_TOKENS, context_tokens_for


def write(root: Path, name: str, text: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class EssayContextTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_prefers_the_file_that_begins_the_document(self):
        write(self.root, "notes.tex", "x" * 5000)
        write(self.root, "main.tex", "\\documentclass{article}\\begin{document}Hi\\end{document}")
        self.assertEqual(find_essay_file(self.root).name, "main.tex")

    def test_falls_back_to_the_largest_tex_file(self):
        write(self.root, "a.tex", "Short.")
        write(self.root, "b.tex", "A much longer chapter of prose.")
        self.assertEqual(find_essay_file(self.root).name, "b.tex")

    def test_ignores_hidden_and_build_directories(self):
        write(self.root, ".git/huge.tex", "\\begin{document}" + "x" * 9000)
        write(self.root, "essay.tex", "\\begin{document}Body\\end{document}")
        self.assertEqual(find_essay_file(self.root).name, "essay.tex")

    def test_inlines_chapters_but_not_preambles(self):
        write(self.root, "preamble.tex", "\\usepackage{amsmath}")
        write(self.root, "chapters/intro.tex", "Batteries drain faster with the model running.")
        write(
            self.root,
            "main.tex",
            "\\documentclass{article}\n\\input{preamble.tex}\n\\begin{document}\n"
            "\\input{chapters/intro}\n% a hidden comment\nResults follow.\n\\end{document}\n",
        )
        essay = load_essay(str(self.root))
        self.assertEqual(essay.relative_path, "main.tex")
        self.assertIn("Batteries drain faster with the model running.", essay.text)
        self.assertIn("Results follow.", essay.text)
        self.assertNotIn("hidden comment", essay.text)
        self.assertNotIn("amsmath", essay.text)

    def test_includes_outside_the_project_are_skipped(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        write(Path(outside.name), "secret.tex", "Top secret text.")
        write(
            self.root,
            "main.tex",
            f"\\begin{{document}}\\input{{{outside.name}/secret}}Visible.\\end{{document}}",
        )
        essay = load_essay(str(self.root))
        self.assertNotIn("Top secret", essay.text)
        self.assertIn("Visible.", essay.text)

    def test_long_essays_are_truncated(self):
        write(self.root, "main.tex", "\\begin{document}" + "Sentence here.\n\n" * 400 + "\\end{document}")
        essay = load_essay(str(self.root), max_chars=500)
        self.assertTrue(essay.truncated)
        self.assertLessEqual(len(essay.text), 500)

    def test_missing_folder_or_no_tex_files_gives_none(self):
        self.assertIsNone(load_essay(str(self.root / "missing")))
        write(self.root, "notes.md", "Not LaTeX")
        self.assertIsNone(load_essay(str(self.root)))


class ContextTokenTests(unittest.TestCase):
    def test_context_window_is_sized_and_bounded(self):
        self.assertEqual(context_tokens_for("short"), MIN_CONTEXT_TOKENS)
        self.assertEqual(context_tokens_for("x" * 30_000), 12288)
        self.assertEqual(context_tokens_for("x" * 1_000_000), MAX_CONTEXT_TOKENS)


if __name__ == "__main__":
    unittest.main()
