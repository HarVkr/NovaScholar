import streamlit as st
from streamlit_option_menu import option_menu


# Page Configuration
st.set_page_config(page_title="Enhanced Navigation Demo", layout="wide")

# Top Navigation Bar using option_menu
selected = option_menu(
    menu_title=None,
    options=["Home", "Documentation", "Examples", "Community", "About"],
    icons=["house", "book", "code", "people", "info-circle"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#fafafa"},
        "icon": {"color": "orange", "font-size": "25px"}, 
        "nav-link": {
            "font-size": "15px",
            "text-align": "center",
            "margin":"0px",
            "--hover-color": "#eee",
        },
        "nav-link-selected": {"background-color": "#0083B8"},
    }
)

# Sidebar Navigation
with st.sidebar:
    st.header("Navigation Menu")
    
    # Main Menu Items
    selected_side = option_menu(
        menu_title="Go to",
        options=["Dashboard", "Analytics", "Reports", "Settings"],
        icons=["speedometer2", "graph-up", "file-text", "gear"],
        menu_icon="list",
        default_index=0,
    )
    
    # Expandable Reports Section
    if selected_side == "Reports":
        with st.expander("Reports", expanded=True):
            st.button("Weekly Report")
            st.button("Monthly Report")
            st.button("Annual Report")

# Main Content Area based on top navigation
if selected == "Home":
    st.title("Welcome to Home")
    st.write("This is the home page content.")
    
    # Dashboard Content
    st.header("Dashboard")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Sales", "$12,345", "+2.5%")
    with col2:
        st.metric("Users", "1,234", "-8%")
    with col3:
        st.metric("Conversion", "3.2%", "+1.2%")

elif selected == "Documentation":
    st.title("Documentation")
    st.write("Documentation content goes here.")
    
elif selected == "Examples":
    st.title("Examples")
    st.write("Example content goes here.")
    
elif selected == "Community":
    st.title("Community")
    st.write("Community content goes here.")
    
elif selected == "About":
    st.title("About")
    st.write("About content goes here.")

# Content based on sidebar selection
if selected_side == "Analytics":
    st.header("Analytics")
    st.line_chart({"data": [1, 5, 2, 6, 2, 1]})
elif selected_side == "Settings":
    st.header("Settings")
    st.toggle("Dark Mode")
    st.toggle("Notifications")
    st.slider("Volume", 0, 100, 50)

# Footer
st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #0E1117;
        color: white;
        text-align: center;
        padding: 10px;
        font-size: 14px;
    }
    </style>
    <div class='footer'>
        © 2024 Your App Name • Privacy Policy • Terms of Service
    </div>
    """,
    unsafe_allow_html=True
)