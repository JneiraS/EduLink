from pathlib import Path

CSS = Path(__file__).resolve().parents[2] / "app" / "interfaces" / "web" / "static" / "css" / "app.css"


def _root_block(css: str) -> str:
    start = css.index(":root")
    end = css.index("}", start)
    return css[start:end]


def test_heading_color_token_is_theme_aware():
    css = CSS.read_text()
    block = _root_block(css)
    assert "--bs-heading-color: var(--text);" in block