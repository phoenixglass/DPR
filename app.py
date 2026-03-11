# DPR Comment Generator - Streamlit App
#
# Clipboard-first tool for generating DPR billing comments from pasted Excel rows.
# Three independent paste areas: Wilt, Chap, Hunt.

from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from dpr.parser import parse_pasted_text
from dpr.comments import generate_comments, comments_only_text
from dpr.clipboard import copy_button_html

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PANES = ["Wilt", "Chap", "Hunt"]

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
# Generate button
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
            for warn in parse_result.warnings:
                st.warning(f"**{pane_name} — Warning:** {warn}")

            if parse_result.errors or parse_result.df.empty:
                continue

            processed_df, gen_warnings, unmapped = generate_comments(parse_result.df)

            for warn in gen_warnings:
                st.warning(f"**{pane_name} — Warning:** {warn}")

            pane_data[pane_name] = {
                "processed_df": processed_df,
                "c_text": comments_only_text(processed_df),
            }

        if not pane_data:
            st.stop()

        # ---------------------------------------------------------------------------
        # Output: tabbed results  [ All | Wilt | Chap | Hunt ]
        # ---------------------------------------------------------------------------
        st.markdown("---")

        out_tab_all, out_tab_wilt, out_tab_chap, out_tab_hunt = st.tabs(
            ["All", "Wilt", "Chap", "Hunt"]
        )

        def render_output_tab(pane_name: str, tab) -> None:
            """Render comments + copy + expander for one pane inside a tab."""
            with tab:
                if pane_name not in pane_data:
                    st.info(f"No data was pasted for **{pane_name}**.")
                    return

                data = pane_data[pane_name]
                c_text = data["c_text"]
                processed_df = data["processed_df"]

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
                        f"📋 Copy",
                        key=f"{pane_name}_comments",
                    ),
                    height=45,
                )

                display_cols = [c for c in processed_df.columns if not c.startswith("_")]
                with st.expander("Show processed rows"):
                    st.dataframe(processed_df[display_cols], use_container_width=True)

        # "All" tab — combined comments from every pane in Wilt → Chap → Hunt order
        with out_tab_all:
            all_comments = "\n".join(
                pane_data[p]["c_text"] for p in PANES if p in pane_data
            )
            all_dfs = [
                pane_data[p]["processed_df"] for p in PANES if p in pane_data
            ]

            st.markdown("**Comments Only**")
            st.text_area(
                label="",
                value=all_comments,
                height=260,
                key="all_comments_text",
                label_visibility="collapsed",
            )
            components.html(
                copy_button_html(all_comments, "📋 Copy", key="all_comments"),
                height=45,
            )

            with st.expander("Show processed rows"):
                combined_df = pd.concat(all_dfs, ignore_index=True)
                display_cols = [c for c in combined_df.columns if not c.startswith("_")]
                st.dataframe(combined_df[display_cols], use_container_width=True)

        render_output_tab(PANES[0], out_tab_wilt)
        render_output_tab(PANES[1], out_tab_chap)
        render_output_tab(PANES[2], out_tab_hunt)
