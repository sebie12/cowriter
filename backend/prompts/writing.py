def improve_writing_prompt(
    text: str,
    instructions: str,
) -> str:
    return f"""
You are an assistant helping a user improve their writing.

Task:
{instructions}

Text:
{text}

Preserve the author's intended meaning.
Do not invent facts or citations.
"""