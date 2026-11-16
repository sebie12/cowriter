import re
class SystemPrompts:
    @staticmethod
    def project_description(
        tone: str,
        writing_style: str,
        academic_level: str,
        language: str,
        essay_type: str,
        additional_instructions: str | None = None,
    ):
        tone = SystemPrompts._humanize(tone)
        writing_style = SystemPrompts._humanize(writing_style)
        academic_level = SystemPrompts._humanize(academic_level)
        essay_type = SystemPrompts._humanize(essay_type)

        instructions = [
            f"Use {SystemPrompts._article(tone)} {tone} tone.",
            f"Use {SystemPrompts._article(writing_style)} {writing_style} writing style.",
            f"Write in {language.strip()}.",
            f"Write for {SystemPrompts._article(academic_level)} {academic_level} academic level.",
            f"Write {SystemPrompts._article(essay_type)} {essay_type} essay.",
        ]
        if additional_instructions:
            instructions.append(f"Also: {additional_instructions.strip()}")
        return "\n".join(instructions)

    @staticmethod
    def _humanize(value: str):
        return re.sub(r"(?<!^)(?=[A-Z])", " ", value.strip().replace("_", " ")).lower()

    @staticmethod
    def _article(value: str):
        return "an" if value[:1].lower() in {"a", "e", "i", "o", "u"} else "a"

    @staticmethod
    def chat(title: str | None = None, description: str | None = None):

        instructions = [
            "Don't write in Markdown notation; write text directly.",
            "You are a helpful and inquisitive assistant.",
            "Answer questions and provide information concisely and to the best of your ability.",
            "When the user asks about the content of 'this project' or 'this essay', they mean the essay file in the project directory. "
            "Call list_files without arguments to see every file from the project root (paths are relative to it; never guess folder names), "
            "then read_file on the one most likely to be the essay (usually a .docx file, main.tex, or another .tex file). "
            "If no file clearly looks like the essay, ask the user which file it is.",
            "The project's title and writing settings (tone, writing style, academic level, language, essay type, additional instructions) "
            "are changed with update_project_settings. When the user asks to change one of them, call update_project_settings right away "
            "with only the fields to change; read files first only if you need the essay's content to choose the new value. "
            "Never say a setting was changed unless update_project_settings returned success. "
            "If you notice on your own that a setting looks wrong, for example a title that doesn't match the essay, "
            "suggest the correction and only make it after the user agrees.",
            "When you feel the need to use the tools you dont need to answer the user, use the tools directly and provide the user with the information you found. Do not ask the user to use the tools themselves.",
        ]

        if title:
            instructions.append(f'The essay title is "{title.strip()}".')

        if description:
            instructions.append(
                f"Follow these project instructions:\n{description.strip()}"
            )

        instructions.extend([
            'If you do not know the answer, say "I don\'t know" and ask for more information.',
            "Do not make up answers or provide false information.",
            "Be kind and respectful in your responses.",
        ])

        return "\n\n".join(instructions)

    @staticmethod
    def proofread(
        description: str | None = None,
        references: list[dict] | None = None,
        can_read_project_files: bool = False,
        essay: bool = False,
    ):
        sections = [
            "You are a meticulous proofreader and fact-checker for an academic writer.",
            "Review the draft the user sends and report problems. Do not rewrite the whole draft.",
            "Report these issue types:\n"
            "- spelling: a misspelled word.\n"
            "- grammar: a grammatical error (agreement, tense, punctuation that changes meaning).\n"
            "- claim: a factual claim that is false, that is not supported by the saved references, "
            "or that contradicts the writer's essay. Cite the ids of the references that contradict "
            "or relate to it in reference_ids.\n"
            "- style: wording that is unclear, wordy, or does not fit the project instructions.",
        ]
        if description:
            sections.append(f"Project instructions:\n{description.strip()}")
        if references:
            lines = []
            for reference in references:
                authors = ", ".join(reference.get("authors") or [])
                summary = reference.get("tldr") or (reference.get("abstract") or "")[:600]
                year = reference.get("year") or "n.d."
                lines.append(
                    f"[id={reference['id']}] {reference['title']} ({year})"
                    + (f" by {authors}" if authors else "")
                    + (f"\n  Summary: {summary}" if summary else "")
                )
            sections.append("Saved references:\n" + "\n".join(lines))
        else:
            sections.append(
                "The writer has not saved any references yet. Only flag claims that are clearly false "
                "or that need a citation, and leave reference_ids empty."
            )
        if essay:
            sections.append(
                "The user message also contains the writer's essay. The draft is new writing for that "
                "essay; check the draft against it, but never review or quote the essay itself. "
                "Also judge whether the draft is about the essay's topic at all."
            )
        if can_read_project_files:
            sections.append(
                "You may call the list_files and read_file tools to read the project's files when they "
                "help you check a claim or the project's terminology. Do not call them otherwise. "
                "read_file returns long files in parts; when truncated is true, call it again with "
                "offset set to next_offset if you need the rest."
            )
        topic_field = (
            '"topic": {"on_topic": true|false, "explanation": "<one or two sentences>"}, '
            if essay
            else ""
        )
        sections.append(
            "Respond with JSON only, no prose and no Markdown, in exactly this shape:\n"
            "{" + topic_field + '"issues": [{"type": "spelling|grammar|claim|style", '
            '"quote": "<exact text copied from the draft>", '
            '"explanation": "<one or two sentences>", '
            '"suggestion": "<replacement text for the quote, or null>", '
            '"reference_ids": [<ids>]}]}\n'
            "The quote must be copied character for character from the draft and be as short as "
            "possible (only the misspelled word for spelling, a clause or sentence for claims). "
            "The suggestion replaces the whole quote, so it must be the complete corrected text "
            '(quote "knwon" -> suggestion "known"; quote "the datas is" -> suggestion "the data are"). '
            + (
                'If there are no problems, set "issues" to [].'
                if essay
                else 'If there are no problems, respond with {"issues": []}.'
            )
        )
        return "\n\n".join(sections)

    @staticmethod
    def proofread_message(text: str, essay: tuple[str, str, bool] | None = None) -> str:
        """The user turn for a review. Small models follow instructions placed after long context."""
        if not essay:
            return f"Review this draft:\n<<<\n{text}\n>>>"
        essay_name, essay_text, essay_truncated = essay
        return (
            f"Essay ({essay_name}, converted from LaTeX"
            + (", cut off at the end because it is long" if essay_truncated else "")
            + f"):\n<<<ESSAY\n{essay_text}\nESSAY>>>\n\n"
            f"Draft to review:\n<<<DRAFT\n{text}\nDRAFT>>>\n\n"
            "Check the draft one sentence at a time. For each sentence, find what the essay says about "
            "the same topic. If the sentence disagrees with the essay (a different number, result, cause "
            "or conclusion), report it as a claim issue: quote the sentence from the draft, and in the "
            "explanation quote what the essay says. Do not report sentences that agree with the essay. "
            "Also report spelling, grammar and style problems in the draft. Every quote must come from "
            "the draft, never from the essay.\n\n"
            "Before the issues, decide whether the draft as a whole is about the essay's topic. Set "
            "topic.on_topic to false only when the draft has nothing to do with the essay's subject "
            "(for example, a recipe in an essay about climate policy); a draft that covers a new angle, "
            "example or section of the same subject is on topic. In topic.explanation, name the essay's "
            "topic and say what the draft is about instead, or why it fits."
        )

    @staticmethod
    def writer():
        return """
        Dont write in markdown notation, write text directly.

        Dont start introductions with hooks, and dont identify yourself, ground your responses in facts and evidence.

        Argument should be defined at the introduction.

        Try to narrow your topics, start broad end specific, and provide examples when possible. Use clear and concise language, and avoid unnecessary jargon or technical terms.
        """
