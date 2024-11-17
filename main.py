import streamlit as st
import datetime
from pathlib import Path
from utils.sample_data import SAMPLE_COURSES, SAMPLE_SESSIONS
from session_page import display_session_content
from db import courses_collection2, faculty_collection, students_collection
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib

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
    else:
        user = faculty_collection.find_one({"full_name": username})
    
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
        user_type = st.selectbox("Select User Type", ["student", "faculty"])
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

