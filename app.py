"""
DPR Comment Generator — Streamlit App

Clipboard-first tool for generating DPR billing comments from pasted Excel rows.
Three independent paste areas: Wilt, Chap, Hunt.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from dpr.parser import parse_pasted_text
from dpr.comments import generate_comments, comments_only_text
from dpr.clipboard import copy_button_html

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DPR Comment Generator",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("DPR Comment Generator")
st.caption(
    "Paste Excel rows into any or all boxes below, then click **Process All**."
)


# ---------------------------------------------------------------------------
# Helper: render one pane's results
# ---------------------------------------------------------------------------
def render_pane_results(pane_name: str, raw_text: str) -> None:
    """Parse and process pasted text for one pane, rendering all results inline."""
    if not raw_text or not raw_text.strip():
        return

    # --- Parse ---
    result = parse_pasted_text(raw_text)

    for err in result.errors:
        st.error(f"**{pane_name} — Error:** {err}")
    for warn in result.warnings:
        st.warning(f"**{pane_name} — Warning:** {warn}")

    if result.errors or result.df.empty:
        return

    # --- Preview raw parsed table ---
    with st.expander(f"{pane_name} — Parsed Input ({len(result.df)} rows)", expanded=False):
        display_cols = [c for c in result.df.columns if not c.startswith("_")]
        st.dataframe(result.df[display_cols], use_container_width=True)

    # --- Generate comments ---
    processed_df, gen_warnings, unmapped = generate_comments(result.df)

    for warn in gen_warnings:
        st.warning(f"**{pane_name} — Warning:** {warn}")

    # --- Show processed table ---
    st.markdown(f"**{pane_name} — Processed Output**")
    display_cols = [c for c in processed_df.columns if not c.startswith("_")]
    st.dataframe(processed_df[display_cols], use_container_width=True)

    # --- Comments + copy ---
    st.markdown(f"**{pane_name} — Comments**")
    c_text = comments_only_text(processed_df)

    # Show comments in a read-only text area, with a single copy button (like your screenshot).
    # Streamlit doesn't have a native copy icon for text areas, so we keep using our HTML copy button.
    st.text_area(
        label="",
        value=c_text,
        height=260,
        key=f"{pane_name}_comments_text",
        label_visibility="collapsed",
    )

    components.html(
        copy_button_html(c_text, f"📋 Copy Comments ({pane_name})", key=f"{pane_name}_comments"),
        height=45,
    )


# ---------------------------------------------------------------------------
# Paste areas
# ---------------------------------------------------------------------------
st.markdown("---")

col_wilt, col_chap, col_hunt = st.columns(3)

with col_wilt:
    st.subheader("Wilt")
    wilt_text = st.text_area(
        "Paste Wilt rows here",
        height=200,
        key="wilt_input",
        label_visibility="collapsed",
        placeholder="Paste Excel rows (with or without header)…",
    )

with col_chap:
    st.subheader("Chap")
    chap_text = st.text_area(
        "Paste Chap rows here",
        height=200,
        key="chap_input",
        label_visibility="collapsed",
        placeholder="Paste Excel rows (with or without header)…",
    )

with col_hunt:
    st.subheader("Hunt")
    hunt_text = st.text_area(
        "Paste Hunt rows here",
        height=200,
        key="hunt_input",
        label_visibility="collapsed",
        placeholder="Paste Excel rows (with or without header)…",
    )

# ---------------------------------------------------------------------------
# Process button
# ---------------------------------------------------------------------------
st.markdown("---")
process_clicked = st.button("⚙️ Process All", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
if process_clicked:
    any_data = any([wilt_text.strip(), chap_text.strip(), hunt_text.strip()])
    if not any_data:
        st.error("Please paste data into at least one pane before processing.")
    else:
        for pane_name, pane_text in [("Wilt", wilt_text), ("Chap", chap_text), ("Hunt", hunt_text)]:
            if pane_text.strip():
                st.markdown(f"## {pane_name}")
                render_pane_results(pane_name, pane_text)
                st.markdown("---")