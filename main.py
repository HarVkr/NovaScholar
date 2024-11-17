import streamlit as st
import datetime
from pathlib import Path
from utils.sample_data import SAMPLE_COURSES, SAMPLE_SESSIONS
from session_page import display_session_content
from db import courses_collection2, faculty_collection, students_collection, research_assistants_collection
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
import os
import openai
from openai import OpenAI

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


def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'user_type' not in st.session_state:
        st.session_state.user_type = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'selected_course' not in st.session_state:
        st.session_state.selected_course = None

def login_user(username, password, user_type):
    """Login user based on credentials"""
    if user_type == "student":
        user = students_collection.find_one({"full_name": username})
    elif user_type == "faculty":
        user = faculty_collection.find_one({"full_name": username})
    elif user_type == "research_assistant":
        user = research_assistants_collection.find_one({"full_name": username})
    
    if user and check_password_hash(user['password'], password):
        st.session_state.user_id = user['_id']
        st.session_state.authenticated = True
        st.session_state.user_type = user_type
        st.session_state.username = username
        return True
    return False


def login_form():
    """Display login form"""
    st.title("Welcome to NOVAScholar")
    
    with st.form("login_form"):
        user_type = st.selectbox("Select User Type", ["student", "faculty", "research_assistant"])
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if login_user(username, password, user_type):
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials!")

def get_courses(username, user_type):
    if user_type == "student":
        student = students_collection.find_one({"full_name": username})
        if student:
            enrolled_course_ids = [course['course_id'] for course in student.get('enrolled_courses', [])]
            courses = courses_collection2.find({"course_id": {"$in": enrolled_course_ids}})
            # course_titles = [course['title'] for course in courses]
            print(courses)
            return list(courses)
    elif user_type == "faculty":
        faculty = faculty_collection.find_one({"full_name": username})
        if faculty:
            course_ids = [course['course_id'] for course in faculty.get('courses_taught', [])]
            courses = courses_collection2.find({"course_id": {"$in": course_ids}})
            return list(courses)
    else: 
        return []

def get_course_ids():
    """Get course IDs for sample courses"""
    return [course['course_id'] for course in SAMPLE_COURSES]

def get_sessions(course_id):
    """Get sessions for a given course ID"""
    course = courses_collection2.find_one({"course_id": course_id})
    if course:
        return course.get('sessions', [])
    return []

def main_dashboard():
    if st.session_state.user_type == "research_assistant":
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
                        st.session_state.recommendations = get_research_papers(
                            search_query
                        )
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

    else:
    # st.title(f"Welcome, {st.session_state.username}")
        selected_course_id = None
        with st.sidebar:
            st.title("Courses")

            # Course selection
            enrolled_courses = get_courses(st.session_state.username, st.session_state.user_type)
            course_titles = [course['title'] for course in enrolled_courses]
            course_ids = [course['course_id'] for course in enrolled_courses]

            selected_course = st.selectbox("Select Course", course_titles)
            selected_course_id = course_ids[course_titles.index(selected_course)]
            print(selected_course_id)

            st.session_state.selected_course = selected_course
            st.session_state.selected_course_id = selected_course_id

            # Display course sessions
            sessions = get_sessions(selected_course_id)
            print(sessions)

            st.title("Sessions")
            for i, session in enumerate(sessions, start=1):
                if st.button(f"Session {i}", key=f"session_{i}", use_container_width=True):
                    st.session_state.selected_session = session

            if st.button("Logout", use_container_width=True):
                for key in st.session_state.keys():
                    del st.session_state[key]
                st.rerun()

        # Main content
        if 'selected_session' in st.session_state:
            display_session_content(st.session_state.user_id, selected_course_id, st.session_state.selected_session, st.session_state.username, st.session_state.user_type)


def main():
    st.set_page_config(
        page_title="NOVAScholar",
        page_icon="📚",
        layout="wide"
    )
    init_session_state()

    if not st.session_state.authenticated:
        login_form()
    else:
        main_dashboard()

if __name__ == "__main__":
    main()

