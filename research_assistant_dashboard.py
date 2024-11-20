import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

# Initialize OpenAI client
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_KEY"))


def get_research_papers(query):
    """Get research paper recommendations based on query"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful research assistant. Provide 10 relevant research papers with titles, authors, brief descriptions, and DOI/URL links. Format each paper as: \n\n1. **Title**\nAuthors: [names]\nLink: [DOI/URL]\nDescription: [brief summary]",
                },
                {
                    "role": "user",
                    "content": f"Give me 10 research papers about: {query}. Include valid DOI links or URLs to the papers where available.",
                },
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error getting recommendations: {str(e)}"


def analyze_research_gaps(papers):
    """Analyze gaps in research based on recommended papers"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a research analysis expert. Based on the provided papers, identify potential research gaps and future research directions.",
                },
                {
                    "role": "user",
                    "content": f"Based on these papers, what are the key areas that need more research?\n\nPapers:\n{papers}",
                },
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error analyzing research gaps: {str(e)}"


def display_research_assistant_dashboard():
    """Display research assistant dashboard"""
    # Initialize session state for recommendations
    if "recommendations" not in st.session_state:
        st.session_state.recommendations = None

    # Sidebar
    with st.sidebar:
        st.title(f"Welcome, {st.session_state.username}")
        if st.button("Logout", use_container_width=True):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

    # Main content
    st.title("Research Paper Recommendations")
    search_query = st.text_input("Enter research topic:")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Get Research Papers"):
            if search_query:
                with st.spinner("Fetching recommendations..."):
                    st.session_state.recommendations = get_research_papers(search_query)
                    st.markdown(st.session_state.recommendations)
            else:
                st.warning("Please enter a search query")

    with col2:
        if st.button("Analyze Research Gaps"):
            if st.session_state.recommendations:
                with st.spinner("Analyzing research gaps..."):
                    gaps = analyze_research_gaps(st.session_state.recommendations)
                    st.markdown("### Potential Research Gaps")
                    st.markdown(gaps)
            else:
                st.warning("Please get research papers first")

    # Display recommendations if they exist
    if st.session_state.recommendations:
        st.markdown("### Research Papers")
        st.markdown(st.session_state.recommendations)
