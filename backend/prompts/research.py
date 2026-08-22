def improve_writing_prompt(
    text: str,
    instructions: str,
) -> str:
    return f"""
You are an assistant helping a user research a given topic.

Task:
{instructions}

Do not invent facts or citations.
"""