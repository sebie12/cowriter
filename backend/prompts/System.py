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

        system_prompt = "\n\n".join(instructions)

        return (
            "<|im_start|>system\n"
            f"{system_prompt}"
            "<|im_end|>\n"
        )
        
    @staticmethod
    def writer():
        return """
        Dont write in markdown notation, write text directly.

        Dont start introductions with hooks, and dont identify yourself, ground your responses in facts and evidence.

        Argument should be defined at the introduction.

        Try to narrow your topics, start broad end specific, and provide examples when possible. Use clear and concise language, and avoid unnecessary jargon or technical terms.
        """
