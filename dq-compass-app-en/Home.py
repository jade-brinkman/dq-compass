#!/usr/bin/env python3
"""
DQ Compass - Universal Data Quality Platform
Main entry point for the Streamlit application

Lets any user:
1. Upload a CSV file
2. Define quality rules through a simple form
3. Generate a visual quality report
"""

import streamlit as st
from pathlib import Path
import sys

from ui_helpers import inject_base_style, render_tag, render_step_card, render_arrow, render_navbar, ensure_session_state

# Page configuration
st.set_page_config(
    page_title="DQ Compass - Home",
    layout="wide",
    initial_sidebar_state="collapsed"
)

ensure_session_state()
inject_base_style()
render_navbar(current_page="home")

# Header
st.title("DQ Compass")
st.subheader("Universal Data Quality Platform")

st.markdown("---")

# Section 01 - Welcome
render_tag("01", "Welcome")

st.markdown("""
This platform lets you assess the quality of **any dataset** by defining
your own control rules, adapted to your domain.

**Available control types**: Completeness, Validity, Uniqueness, Consistency,
Freshness, Reconciliation, Composite uniqueness.
""")

st.markdown("---")

# Section 02 - How it works, with navigation buttons
render_tag("02", "How it works")

rules_defined = len(st.session_state.rules) > 0

col1, col_arrow1, col2, col_arrow2, col3 = st.columns([3, 0.6, 3, 0.6, 3])

with col1:
    render_step_card("1", "Upload data", "Import your CSV file")
    if st.button("Upload data", type="primary", use_container_width=True):
        st.switch_page("pages/1_Upload_Data.py")

with col_arrow1:
    render_arrow()

with col2:
    render_step_card(
        "2", "Define rules", "Create your quality checks",
        disabled=not st.session_state.data_uploaded
    )
    if st.button(
        "Define rules",
        use_container_width=True,
        disabled=not st.session_state.data_uploaded,
        help=None if st.session_state.data_uploaded else "Upload your data first"
    ):
        st.switch_page("pages/2_Define_Rules.py")

with col_arrow2:
    render_arrow()

with col3:
    render_step_card(
        "3", "Quality report", "Review results and anomalies",
        disabled=not rules_defined
    )
    if st.button(
        "Quality report",
        use_container_width=True,
        disabled=not rules_defined,
        help=None if rules_defined else "Define at least one rule first"
    ):
        st.switch_page("pages/3_Quality_Report.py")

st.markdown("---")

# Section 03 - Session status
render_tag("03", "Session status")

col1, col2, col3 = st.columns(3)

with col1:
    if st.session_state.data_uploaded:
        st.success("Data uploaded")
        if st.session_state.uploaded_df is not None:
            st.metric("Rows", len(st.session_state.uploaded_df))
            st.metric("Columns", len(st.session_state.uploaded_df.columns))
    else:
        st.warning("Waiting for data")

with col2:
    if len(st.session_state.rules) > 0:
        st.success(f"{len(st.session_state.rules)} rule(s) defined")
    else:
        st.info("No rules defined yet")

with col3:
    if st.session_state.report_generated:
        st.success("Report generated")
    else:
        st.info("Report not generated")

# Footer
st.markdown("""
<div class="dq-footer">
    <small>DQ Compass - Universal data quality platform</small>
</div>
""", unsafe_allow_html=True)
