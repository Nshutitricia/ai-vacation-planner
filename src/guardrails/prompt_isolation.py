def isolate(tag: str, text: str) -> str:
    """Wrap untrusted text in tags so a prompt can tell data from instructions.

    Angle brackets are removed first, so the text cannot close the tag early
    and smuggle instructions outside of it.
    """
    cleaned = text.replace("<", " ").replace(">", " ")
    return f"<{tag}>\n{cleaned}\n</{tag}>"
