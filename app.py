# DPR Comment Generator - Streamlit App
#
# Clipboard-first tool for generating DPR billing comments from pasted Excel rows.
# Three independent paste areas: Wilt, Chap, Hunt.

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from dpr.parser import parse_pasted_text
from dpr.comments import generate_comments, comments_only_text
from dpr.clipboard import copy_button_html

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PANES = ["Wilt", "Chap", "Hunt"]

# Color mapping per location
PANE_COLORS = {
    "Wilt": "#D9E8F7",   # light blue
    "Chap": "#E6DDF5",   # pale lavender
    "Hunt": "#F6D7C9",   # soft peach
}

# Slightly darker shades for hover / selected state
PANE_COLORS_ACTIVE = {
    "Wilt": "#b8d0e8",
    "Chap": "#cfc4ea",
    "Hunt": "#ecc0a8",
}

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DPR Comment Generator",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS: tab colors + neutral Generate button
# ---------------------------------------------------------------------------
_tab_css_parts = []
for _i, _pane in enumerate(PANES, start=1):
    _col = PANE_COLORS[_pane]
    _col_active = PANE_COLORS_ACTIVE[_pane]
    _tab_css_parts.append(f"""
    [data-baseweb="tab-list"] button[role="tab"]:nth-child({_i}) {{
        background-color: {_col} !important;
        border-radius: 4px 4px 0 0;
    }}
    [data-baseweb="tab-list"] button[role="tab"]:nth-child({_i}):hover,
    [data-baseweb="tab-list"] button[role="tab"]:nth-child({_i})[aria-selected="true"] {{
        background-color: {_col_active} !important;
    }}""")

st.markdown(
    f"""<style>
{''.join(_tab_css_parts)}

/* Neutral Generate button — override primary accent */
div[data-testid="stButton"] > button[kind="primaryFormSubmit"],
div[data-testid="stButton"] > button[kind="primary"] {{
    background-color: #f0f2f6 !important;
    color: #31333f !important;
    border: 1px solid #d0d3db !important;
    box-shadow: none !important;
}}
div[data-testid="stButton"] > button[kind="primaryFormSubmit"]:hover,
div[data-testid="stButton"] > button[kind="primary"]:hover {{
    background-color: #e2e5ed !important;
    border-color: #b0b3bb !important;
}}
</style>""",
    unsafe_allow_html=True,
)

st.title("DPR Comment Generator")
st.caption(
    "Paste Excel rows into any or all tabs below, then click **Generate**."
)

# ---------------------------------------------------------------------------
# Input: tabbed paste areas
# ---------------------------------------------------------------------------
input_tab_wilt, input_tab_chap, input_tab_hunt = st.tabs(["Wilt", "Chap", "Hunt"])

with input_tab_wilt:
    wilt_text = st.text_area(
        "Paste Wilt rows here",
        height=250,
        key="wilt_input",
        label_visibility="collapsed",
        placeholder="Paste Excel rows (with or without header)…",
    )

with input_tab_chap:
    chap_text = st.text_area(
        "Paste Chap rows here",
        height=250,
        key="chap_input",
        label_visibility="collapsed",
        placeholder="Paste Excel rows (with or without header)…",
    )

with input_tab_hunt:
    hunt_text = st.text_area(
        "Paste Hunt rows here",
        height=250,
        key="hunt_input",
        label_visibility="collapsed",
        placeholder="Paste Excel rows (with or without header)…",
    )

# ---------------------------------------------------------------------------
# Generate button  (neutral style via CSS above)
# ---------------------------------------------------------------------------
generate_clicked = st.button("⚙️ Generate", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
if generate_clicked:
    any_data = any([wilt_text.strip(), chap_text.strip(), hunt_text.strip()])
    if not any_data:
        st.error("Please paste data into at least one tab before generating.")
    else:
        # Process each pane and collect results
        pane_data: dict[str, dict] = {}

        for pane_name, pane_text in zip(PANES, [wilt_text, chap_text, hunt_text]):
            if not pane_text.strip():
                continue

            parse_result = parse_pasted_text(pane_text)

            for err in parse_result.errors:
                st.error(f"**{pane_name} — Error:** {err}")

            if parse_result.errors or parse_result.df.empty:
                continue

            processed_df, gen_warnings, unmapped = generate_comments(parse_result.df)

            all_warnings = list(parse_result.warnings) + list(gen_warnings)

            pane_data[pane_name] = {
                "processed_df": processed_df,
                "c_text": comments_only_text(processed_df),
                "warnings": all_warnings,
            }

        if not pane_data:
            st.stop()

        # ---------------------------------------------------------------------------
        # Output: tabbed results  [ Wilt | Chap | Hunt ]
        # ---------------------------------------------------------------------------
        st.markdown("---")

        out_tab_wilt, out_tab_chap, out_tab_hunt = st.tabs(["Wilt", "Chap", "Hunt"])

        def render_output_tab(pane_name: str, tab) -> None:
            """Render optional warnings expander + comments + copy + processed rows."""
            with tab:
                if pane_name not in pane_data:
                    st.info(f"No data was pasted for **{pane_name}**.")
                    return

                data = pane_data[pane_name]
                c_text = data["c_text"]
                processed_df = data["processed_df"]
                warnings = data["warnings"]

                # Warnings — collapsed expander, only shown when there are warnings
                if warnings:
                    with st.expander(
                        f"{pane_name} — Warnings ({len(warnings)})", expanded=False
                    ):
                        for w in warnings:
                            st.warning(w)

                st.markdown("**Comments Only**")
                st.text_area(
                    label="",
                    value=c_text,
                    height=260,
                    key=f"{pane_name}_comments_text",
                    label_visibility="collapsed",
                )
                components.html(
                    copy_button_html(
                        c_text,
                        "📋 Copy",
                        key=f"{pane_name}_comments",
                    ),
                    height=45,
                )

                display_cols = [c for c in processed_df.columns if not c.startswith("_")]
                with st.expander("Show processed rows"):
                    st.dataframe(processed_df[display_cols], use_container_width=True)

        render_output_tab(PANES[0], out_tab_wilt)
        render_output_tab(PANES[1], out_tab_chap)
        render_output_tab(PANES[2], out_tab_hunt)
