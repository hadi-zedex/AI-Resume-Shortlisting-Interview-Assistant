import streamlit as st


def st_html(content: str) -> None:
    """
    Render HTML safely via st.markdown.

    Streamlit uses CommonMark, where a blank line (or whitespace-only line)
    terminates an HTML block. Any content after the blank line is then
    processed as Markdown — which causes deeply-indented HTML to appear
    as a code block instead of being rendered.

    This helper strips whitespace-only lines before passing to st.markdown,
    preventing premature HTML block termination.

    Args:
        content: Raw HTML string to render.
    """
    cleaned = "\n".join(
        line for line in content.splitlines() if line.strip()
    )
    st.markdown(cleaned, unsafe_allow_html=True)
