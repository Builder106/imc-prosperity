"""The Intara section component: a v2 Streamlit component mounted in the page DOM."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import streamlit as st

_DIR = Path(__file__).resolve().parent

# GSAP is inlined ahead of the module so the component never depends on a CDN at runtime. Its
# UMD wrapper writes to `this.window`, which strict module code can't do on the real window, so
# it runs against a scratch scope and the module reads `gsap` from there.
_GSAP = (_DIR / "ground" / "gsap.min.js").read_text(encoding="utf-8")
_section = st.components.v2.component(
    "intara_section",
    html=(_DIR / "ground" / "ground.html").read_text(encoding="utf-8"),
    css=(_DIR / "ground" / "ground.css").read_text(encoding="utf-8"),
    js=f"const gsapScope = {{}};\n(function () {{\n{_GSAP}\n}}).call(gsapScope);\n"
    + (_DIR / "ground" / "ground.js").read_text(encoding="utf-8"),
    # Mounted in the page DOM so headings, focus and links are part of the document.
    isolate_styles=False,
)


def intara_section(
    data: dict[str, object],
    *,
    on_place: Callable[[], None],
    on_replay: Callable[[], None],
    on_nav: Callable[[], None],
) -> object:
    """Mount the section. State values arrive through the callbacks before the next run."""
    return _section(
        key="intara",
        data=data,
        default={"place": None, "replay": None},
        on_place_change=on_place,
        on_replay_change=on_replay,
        on_nav_change=on_nav,
    )


def component_value(name: str) -> object:
    """Read one state or trigger value of the mounted section from session state."""
    state = st.session_state.get("intara")
    if state is None:
        return None
    if isinstance(state, dict):
        return state.get(name)
    return getattr(state, name, None)
