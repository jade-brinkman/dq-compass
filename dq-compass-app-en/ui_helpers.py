"""
Shared visual style for the DQ Compass app.
Colors and components follow the project deck (red / black / white, numbered tags).

Color mapping used throughout the app:
- Black  = primary action (confirm, continue, generate) -> theme primaryColor
- Red    = brand accent (tags, numbered badges, borders) AND the reset/danger action
- Grey   = secondary / disabled actions
"""

import streamlit as st

RED = "#E2001A"
BLACK = "#1A1A1A"
GREY = "#5C5C5C"

# Dark theme colors
DARK_BG = "#0E1117"
DARK_SECONDARY_BG = "#1E2127"
DARK_TEXT = "#FAFAFA"

# Light theme colors
LIGHT_BG = "#FFFFFF"
LIGHT_SECONDARY_BG = "#F5F5F5"
LIGHT_TEXT = "#1A1A1A"

# Keys tracked in session state - used by the reset action
SESSION_KEYS = [
    "data_uploaded", "uploaded_file_path", "uploaded_df", "uploaded_filename",
    "rules", "report_generated", "last_run_results",
    "basic_quality_checks", "gdpr_check", "theme",
]


def ensure_session_state():
    """
    Initializes every session_state key the app relies on, if it isn't there
    yet. Must be called at the top of Home.py AND of every page — Streamlit's
    multipage navigation lets a user land directly on a page (a bookmarked
    URL, a shared link, a browser refresh while on that page) without ever
    running Home.py in that browser session, so each page has to be able to
    initialize its own state rather than assume Home.py already did it.
    """
    defaults = {
        "data_uploaded": False,
        "uploaded_file_path": None,
        "uploaded_df": None,
        "uploaded_filename": None,
        "rules": [],
        "report_generated": False,
        "last_run_results": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_current_theme():
    """Get current theme from session state, default to light."""
    if "theme" not in st.session_state:
        st.session_state.theme = "light"
    return st.session_state.theme


def toggle_theme():
    """Toggle between light and dark themes."""
    current = get_current_theme()
    st.session_state.theme = "dark" if current == "light" else "light"


def get_theme_colors():
    """Return color dictionary based on current theme."""
    theme = get_current_theme()
    if theme == "dark":
        return {
            "bg": DARK_BG,
            "secondary_bg": DARK_SECONDARY_BG,
            "text": DARK_TEXT,
            "card_bg": DARK_SECONDARY_BG,
            "border": "#3D4350",
            "grey": "#9CA3AF",  # Lighter grey for dark mode
        }
    else:
        return {
            "bg": LIGHT_BG,
            "secondary_bg": LIGHT_SECONDARY_BG,
            "text": LIGHT_TEXT,
            "card_bg": LIGHT_BG,
            "border": "#E0E0E0",
            "grey": GREY,
        }


def inject_base_style():
    colors = get_theme_colors()
    theme = get_current_theme()

    # Theme-specific CSS
    theme_css = f"""
    /* Theme: {theme} */
    .stApp {{
        background-color: {colors['bg']} !important;
        color: {colors['text']} !important;
    }}
    .stApp > header {{
        background-color: {colors['bg']} !important;
    }}
    .main .block-container {{
        background-color: {colors['bg']} !important;
    }}

    /* Force text colors for dark theme */
    .stApp, .stApp p, .stApp span, .stApp div, .stApp label,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown li,
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] span, [data-testid="stMarkdownContainer"] li,
    .stTextInput label, .stSelectbox label, .stMultiSelect label,
    .stNumberInput label, .stTextArea label, .stFileUploader label,
    .stMetric label, .stMetric [data-testid="stMetricValue"],
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"],
    .stExpander summary, .stExpander [data-testid="stExpanderDetails"],
    .stTabs [data-baseweb="tab"], .stCaption, .element-container {{
        color: {colors['text']} !important;
    }}

    /* Table and dataframe styling */
    .stDataFrame, .stDataFrame th, .stDataFrame td,
    [data-testid="stTable"], [data-testid="stTable"] th, [data-testid="stTable"] td {{
        color: {colors['text']} !important;
        background-color: {colors['secondary_bg']} !important;
    }}

    /* Input fields */
    .stTextInput input, .stNumberInput input, .stTextArea textarea,
    .stSelectbox > div > div, .stMultiSelect > div > div {{
        background-color: {colors['secondary_bg']} !important;
        color: {colors['text']} !important;
        border-color: {colors['border']} !important;
    }}

    /* Expanders */
    .streamlit-expanderHeader {{
        background-color: {colors['secondary_bg']} !important;
        color: {colors['text']} !important;
    }}
    [data-testid="stExpander"] {{
        background-color: {colors['secondary_bg']} !important;
        border-color: {colors['border']} !important;
    }}

    /* Alerts and messages */
    .stAlert {{
        background-color: {colors['secondary_bg']} !important;
    }}
    .stAlert p {{
        color: {colors['text']} !important;
    }}

    /* Metrics */
    [data-testid="stMetricValue"] {{
        color: {colors['text']} !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {colors['grey']} !important;
    }}

    /* File uploader */
    [data-testid="stFileUploader"] {{
        background-color: {colors['secondary_bg']} !important;
    }}
    [data-testid="stFileUploader"] section {{
        background-color: {colors['secondary_bg']} !important;
        border-color: {colors['border']} !important;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: {colors['bg']} !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {colors['secondary_bg']} !important;
        color: {colors['text']} !important;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {RED} !important;
        color: white !important;
    }}

    /* Dividers */
    hr {{
        border-color: {colors['border']} !important;
    }}

    /* Navigation bar */
    .dq-navbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.8rem 1.5rem;
        background: {colors['secondary_bg']};
        border-bottom: 2px solid {RED};
        margin: -1rem -1rem 1.5rem -1rem;
        position: sticky;
        top: 0;
        z-index: 999;
    }}
    .dq-navbar-brand {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .dq-navbar-logo {{
        font-size: 1.5rem;
        font-weight: 800;
        color: {RED};
    }}
    .dq-navbar-title {{
        font-size: 1.1rem;
        font-weight: 600;
        color: {colors['text']};
    }}
    .dq-navbar-menu {{
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .dq-nav-link {{
        padding: 8px 16px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.9rem;
        color: {colors['text']};
        background: transparent;
        border: 2px solid transparent;
        transition: all 0.2s ease;
        cursor: pointer;
    }}
    .dq-nav-link:hover {{
        background: {RED}20;
        border-color: {RED};
        color: {RED};
    }}
    .dq-nav-link.active {{
        background: {RED};
        color: white;
        border-color: {RED};
    }}
    .dq-nav-link.disabled {{
        color: {colors['grey']};
        cursor: not-allowed;
        opacity: 0.5;
    }}
    .dq-nav-link.disabled:hover {{
        background: transparent;
        border-color: transparent;
        color: {colors['grey']};
    }}
    .dq-navbar-actions {{
        display: flex;
        align-items: center;
        gap: 12px;
    }}
    .dq-theme-toggle {{
        background: {colors['card_bg']};
        border: 2px solid {colors['border']};
        border-radius: 8px;
        padding: 6px 12px;
        cursor: pointer;
        font-size: 1rem;
        transition: all 0.2s ease;
    }}
    .dq-theme-toggle:hover {{
        border-color: {RED};
    }}
    .dq-reset-link {{
        padding: 6px 14px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.85rem;
        color: {RED};
        background: transparent;
        border: 2px solid {RED};
        transition: all 0.2s ease;
        cursor: pointer;
    }}
    .dq-reset-link:hover {{
        background: {RED};
        color: white;
    }}
    """

    st.markdown(f"""
    <style>
    {theme_css}

    .dq-tag {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 0.2rem 0 0.8rem 0;
    }}
    .dq-tag-badge {{
        background-color: {RED};
        color: white;
        font-weight: 700;
        font-size: 0.85rem;
        padding: 4px 10px;
        border-radius: 4px;
        letter-spacing: 0.5px;
    }}
    .dq-tag-label {{
        font-weight: 700;
        font-size: 1rem;
        color: {colors['text']};
        letter-spacing: 1px;
        text-transform: uppercase;
    }}
    .dq-step-card {{
        border: 3px solid {RED};
        border-radius: 14px;
        padding: 32px 14px 18px 14px;
        text-align: center;
        position: relative;
        margin-top: 24px;
        min-height: 110px;
        background: {colors['card_bg']};
    }}
    .dq-step-card.disabled {{
        border-color: {colors['border']};
    }}
    .dq-step-number {{
        width: 42px;
        height: 42px;
        border-radius: 50%;
        border: 3px solid {RED};
        background: {colors['card_bg']};
        color: {RED};
        font-weight: 800;
        font-size: 1.1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: -50px auto 12px auto;
    }}
    .dq-step-card.disabled .dq-step-number {{
        border-color: {colors['border']};
        color: {colors['grey']};
    }}
    .dq-step-title {{
        font-weight: 700;
        color: {colors['text']};
        font-size: 1rem;
        margin-bottom: 4px;
    }}
    .dq-step-sub {{
        color: {colors['grey']};
        font-size: 0.82rem;
    }}
    .dq-arrow {{
        font-size: 1.8rem;
        font-weight: 900;
        color: {colors['text']};
        text-align: center;
        margin-top: 55px;
    }}
    div.stButton > button {{
        border-radius: 8px;
        font-weight: 700;
    }}

    /* Navigation buttons - ALL nav buttons base style */
    .st-key-nav_home button,
    .st-key-nav_upload button,
    .st-key-nav_rules button,
    .st-key-nav_report button,
    .st-key-nav_theme button,
    .st-key-nav_reset button {{
        background-color: {colors['secondary_bg']} !important;
        color: {colors['text']} !important;
        border: 2px solid {colors['border']} !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }}
    /* Force text color inside secondary nav buttons */
    .st-key-nav_home button[kind="secondary"] p,
    .st-key-nav_home button[kind="secondary"] span,
    .st-key-nav_upload button[kind="secondary"] p,
    .st-key-nav_upload button[kind="secondary"] span,
    .st-key-nav_rules button[kind="secondary"] p,
    .st-key-nav_rules button[kind="secondary"] span,
    .st-key-nav_report button[kind="secondary"] p,
    .st-key-nav_report button[kind="secondary"] span,
    .st-key-nav_theme button[kind="secondary"] p,
    .st-key-nav_theme button[kind="secondary"] span,
    .st-key-nav_reset button[kind="secondary"] p,
    .st-key-nav_reset button[kind="secondary"] span {{
        color: {colors['text']} !important;
    }}
    /* Override Streamlit's secondary button default white background */
    button[kind="secondary"] {{
        background-color: {colors['secondary_bg']} !important;
        border-color: {colors['border']} !important;
    }}
    button[kind="secondary"] p,
    button[kind="secondary"] span {{
        color: {colors['text']} !important;
    }}

    /* Nav buttons hover state */
    .st-key-nav_home button:hover,
    .st-key-nav_upload button:hover,
    .st-key-nav_rules button:hover:not(:disabled),
    .st-key-nav_report button:hover:not(:disabled),
    .st-key-nav_theme button:hover {{
        background-color: {RED}20 !important;
        border-color: {RED} !important;
        color: {RED} !important;
    }}
    .st-key-nav_home button:hover p,
    .st-key-nav_home button:hover span,
    .st-key-nav_upload button:hover p,
    .st-key-nav_upload button:hover span,
    .st-key-nav_rules button:hover:not(:disabled) p,
    .st-key-nav_rules button:hover:not(:disabled) span,
    .st-key-nav_report button:hover:not(:disabled) p,
    .st-key-nav_report button:hover:not(:disabled) span,
    .st-key-nav_theme button:hover p,
    .st-key-nav_theme button:hover span {{
        color: {RED} !important;
    }}

    /* Disabled nav buttons */
    .st-key-nav_rules button:disabled,
    .st-key-nav_report button:disabled {{
        background-color: {colors['secondary_bg']} !important;
        color: {colors['grey']} !important;
        border-color: {colors['border']} !important;
        opacity: 0.5 !important;
        cursor: not-allowed !important;
    }}
    .st-key-nav_rules button:disabled p,
    .st-key-nav_rules button:disabled span,
    .st-key-nav_report button:disabled p,
    .st-key-nav_report button:disabled span {{
        color: {colors['grey']} !important;
    }}

    /* PRIMARY/ACTIVE buttons - force red background with white text */
    .st-key-nav_home button[data-testid="stBaseButton-primary"],
    .st-key-nav_upload button[data-testid="stBaseButton-primary"],
    .st-key-nav_rules button[data-testid="stBaseButton-primary"],
    .st-key-nav_report button[data-testid="stBaseButton-primary"],
    .st-key-nav_home [data-testid="stBaseButton-primary"],
    .st-key-nav_upload [data-testid="stBaseButton-primary"],
    .st-key-nav_rules [data-testid="stBaseButton-primary"],
    .st-key-nav_report [data-testid="stBaseButton-primary"],
    div[data-testid="stButton"].st-key-nav_home button[kind="primary"],
    div[data-testid="stButton"].st-key-nav_upload button[kind="primary"],
    div[data-testid="stButton"].st-key-nav_rules button[kind="primary"],
    div[data-testid="stButton"].st-key-nav_report button[kind="primary"] {{
        background-color: {RED} !important;
        color: white !important;
        border-color: {RED} !important;
    }}

    /* Force ALL primary buttons in nav to be red with white text */
    /* Target the p element inside buttons which contains the text */
    .st-key-nav_home button[kind="primary"] p,
    .st-key-nav_upload button[kind="primary"] p,
    .st-key-nav_rules button[kind="primary"] p,
    .st-key-nav_report button[kind="primary"] p,
    .st-key-nav_home button[kind="primary"] span,
    .st-key-nav_upload button[kind="primary"] span,
    .st-key-nav_rules button[kind="primary"] span,
    .st-key-nav_report button[kind="primary"] span {{
        color: white !important;
    }}

    /* Override Streamlit's default primary button colors completely */
    button[kind="primary"] {{
        background-color: {RED} !important;
        border-color: {RED} !important;
    }}
    button[kind="primary"] p,
    button[kind="primary"] span,
    button[kind="primary"] div {{
        color: white !important;
    }}

    /* Reset button special styling */
    .st-key-nav_reset button {{
        background-color: transparent !important;
        color: {RED} !important;
        border: 2px solid {RED} !important;
    }}
    .st-key-nav_reset button p,
    .st-key-nav_reset button span {{
        color: {RED} !important;
    }}
    .st-key-nav_reset button:hover {{
        background-color: {RED} !important;
        color: white !important;
    }}
    .st-key-nav_reset button:hover p,
    .st-key-nav_reset button:hover span {{
        color: white !important;
    }}

    /* Theme button */
    .st-key-nav_theme button {{
        background-color: {colors['card_bg']} !important;
        border: 2px solid {colors['border']} !important;
        color: {colors['text']} !important;
    }}
    .st-key-nav_theme button p,
    .st-key-nav_theme button span {{
        color: {colors['text']} !important;
    }}

    /* Reset button: outlined red, distinct from the black primary actions */
    .st-key-reset_container button {{
        background-color: {colors['card_bg']};
        color: {RED};
        border: 2px solid {RED};
    }}
    .st-key-reset_container button:hover {{
        background-color: {RED};
        color: white;
        border: 2px solid {RED};
    }}

    /* Hide default Streamlit sidebar */
    [data-testid="stSidebar"] {{
        display: none;
    }}
    [data-testid="stSidebarCollapsedControl"] {{
        display: none;
    }}

    /* Footer styling */
    .dq-footer {{
        text-align: center;
        color: {colors['grey']};
        padding: 1rem 0;
        margin-top: 2rem;
        border-top: 1px solid {colors['border']};
    }}

    /* Additional overrides for dark mode text visibility */
    .stMarkdown, .stMarkdown *, .stText, .stCaption,
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{
        color: {colors['text']} !important;
    }}

    /* Code blocks */
    code, pre, .stCodeBlock {{
        background-color: {colors['secondary_bg']} !important;
        color: {colors['text']} !important;
    }}

    /* Download buttons */
    .stDownloadButton button {{
        background-color: {colors['secondary_bg']} !important;
        color: {colors['text']} !important;
        border-color: {colors['border']} !important;
    }}
    .stDownloadButton button:hover {{
        border-color: {RED} !important;
        color: {RED} !important;
    }}

    /* Progress bar background */
    .stProgress > div {{
        background-color: {colors['secondary_bg']} !important;
    }}

    /* Checkbox and radio */
    .stCheckbox label, .stRadio label {{
        color: {colors['text']} !important;
    }}

    /* Plotly charts - ensure visibility */
    .js-plotly-plot {{
        width: 100% !important;
        min-height: 300px !important;
    }}
    [data-testid="stPlotlyChart"] {{
        width: 100% !important;
        min-height: 300px !important;
    }}
    .stPlotlyChart {{
        width: 100% !important;
        min-height: 300px !important;
    }}

    /* Success/Warning/Error/Info boxes text */
    .stSuccess, .stWarning, .stError, .stInfo {{
        color: {colors['text']} !important;
    }}
    .stSuccess *, .stWarning *, .stError *, .stInfo * {{
        color: inherit !important;
    }}
    </style>
    """, unsafe_allow_html=True)


def render_tag(number: str, label: str):
    """Small red numbered tag, e.g. render_tag('01', 'How it works')"""
    st.markdown(f"""
    <div class="dq-tag">
        <span class="dq-tag-badge">{number}</span>
        <span class="dq-tag-label">{label}</span>
    </div>
    """, unsafe_allow_html=True)


def render_step_card(number: str, title: str, subtitle: str, disabled: bool = False):
    css_class = "dq-step-card disabled" if disabled else "dq-step-card"
    st.markdown(f"""
    <div class="{css_class}">
        <div class="dq-step-number">{number}</div>
        <div class="dq-step-title">{title}</div>
        <div class="dq-step-sub">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def render_arrow():
    st.markdown('<div class="dq-arrow">&#9654;</div>', unsafe_allow_html=True)


def render_navbar(current_page: str = "home"):
    """
    Render a horizontal navigation bar at the top of the page.

    Args:
        current_page: One of "home", "upload", "rules", "report"
    """
    theme = get_current_theme()
    theme_icon = "\u263e" if theme == "light" else "\u2600"  # Moon or Sun

    # Check states for enabling/disabling links
    data_uploaded = st.session_state.get("data_uploaded", False)
    rules_defined = len(st.session_state.get("rules", [])) > 0

    # Build navigation links
    def get_link_class(page, disabled=False):
        if disabled:
            return "dq-nav-link disabled"
        if current_page == page:
            return "dq-nav-link active"
        return "dq-nav-link"

    # Create columns for the navbar buttons
    nav_cols = st.columns([2, 1, 1, 1, 1, 1, 1])

    with nav_cols[0]:
        st.markdown(f"""
        <div class="dq-navbar-brand">
            <span class="dq-navbar-logo">DQ</span>
            <span class="dq-navbar-title">Compass</span>
        </div>
        """, unsafe_allow_html=True)

    with nav_cols[1]:
        if st.button("\u2302 Home", key="nav_home", use_container_width=True,
                     type="primary" if current_page == "home" else "secondary"):
            st.switch_page("Home.py")

    with nav_cols[2]:
        if st.button("\u21e7 Upload", key="nav_upload", use_container_width=True,
                     type="primary" if current_page == "upload" else "secondary"):
            st.switch_page("pages/1_Upload_Data.py")

    with nav_cols[3]:
        if st.button("\u2699 Rules", key="nav_rules", use_container_width=True,
                     disabled=not data_uploaded,
                     type="primary" if current_page == "rules" else "secondary"):
            st.switch_page("pages/2_Define_Rules.py")

    with nav_cols[4]:
        if st.button("\u2630 Report", key="nav_report", use_container_width=True,
                     disabled=not rules_defined,
                     type="primary" if current_page == "report" else "secondary"):
            st.switch_page("pages/3_Quality_Report.py")

    with nav_cols[5]:
        if st.button(f"{theme_icon} Theme", key="nav_theme", use_container_width=True):
            toggle_theme()
            st.rerun()

    with nav_cols[6]:
        if st.button("\u21bb Reset", key="nav_reset", use_container_width=True):
            # Keep theme preference
            current_theme = st.session_state.get("theme", "light")
            st.session_state.clear()
            st.session_state.theme = current_theme
            st.switch_page("Home.py")

    st.markdown("---")


def render_reset_button():
    """Legacy function - kept for backward compatibility but now does nothing.
    Navigation is handled by render_navbar().
    """
    pass
