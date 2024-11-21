import streamlit as st
from datetime import datetime, date, time
from pathlib import Path
from utils.sample_data import SAMPLE_COURSES, SAMPLE_SESSIONS
from session_page import display_session_content
from db import (
    courses_collection2,
    faculty_collection,
    students_collection,
    research_assistants_collection,
    analysts_collection,
)
from werkzeug.security import generate_password_hash, check_password_hash
import os
from openai import OpenAI
from dotenv import load_dotenv

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
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "user_type" not in st.session_state:
        st.session_state.user_type = None
    if "username" not in st.session_state:
        st.session_state.username = None
    if "selected_course" not in st.session_state:
        st.session_state.selected_course = None
    if "show_create_course_form" not in st.session_state:
        st.session_state.show_create_course_form = False


def login_user(username, password, user_type):
    """Login user based on credentials"""
    if user_type == "student":
        user = students_collection.find_one({"full_name": username})
    elif user_type == "faculty":
        user = faculty_collection.find_one({"full_name": username})
    elif user_type == "research_assistant":
        user = research_assistants_collection.find_one({"full_name": username})
    elif user_type == "analyst":
        user = analysts_collection.find_one({"full_name": username})

    if user and check_password_hash(user["password"], password):
        st.session_state.user_id = user["_id"]
        st.session_state.authenticated = True
        st.session_state.user_type = user_type
        st.session_state.username = username
        return True
    return False


def login_form():
    """Display login form"""
    st.title("Welcome to NOVAScholar")

    with st.form("login_form"):
        user_type = st.selectbox(
            "Select User Type", ["student", "faculty", "research_assistant", "analyst"]
        )
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
            enrolled_course_ids = [
                course["course_id"] for course in student.get("enrolled_courses", [])
            ]
            courses = courses_collection2.find(
                {"course_id": {"$in": enrolled_course_ids}}
            )
            # course_titles = [course['title'] for course in courses]
            return list(courses)
    elif user_type == "faculty":
        faculty = faculty_collection.find_one({"full_name": username})
        if faculty:
            course_ids = [
                course["course_id"] for course in faculty.get("courses_taught", [])
            ]
            courses = courses_collection2.find({"course_id": {"$in": course_ids}})
            return list(courses)
    elif user_type == "research_assistant":
        research_assistant = research_assistants_collection.find_one(
            {"full_name": username}
        )
        if research_assistant:
            course_ids = [
                course["course_id"]
                for course in research_assistant.get("courses_assisted", [])
            ]
            courses = courses_collection2.find({"course_id": {"$in": course_ids}})
            return list(courses)
    else:
        return []


def get_course_ids():
    """Get course IDs for sample courses"""
    return [course["course_id"] for course in SAMPLE_COURSES]


def get_sessions(course_id):
    """Get sessions for a given course ID"""
    course = courses_collection2.find_one({"course_id": course_id})
    if course:
        return course.get("sessions", [])
    return []


def create_session(new_session, course_id):
    """Create a new session for a given course ID"""
    course = courses_collection2.find_one({"course_id": course_id})
    if course:
        last_session_id = max((session["session_id"] for session in course["sessions"]))
        last_session_id = int(last_session_id[1:])
        new_session_id = last_session_id + 1
        new_session["session_id"] = "S" + str(new_session_id)
        courses_collection2.update_one(
            {"course_id": new_session["course_id"]},
            {"$push": {"sessions": new_session}},
        )
        return True
    return False


def create_session_form(course_id):
    """Display form to create a new session and perform the creation operation"""
    st.title("Create New Session")

    with st.form("create_session_form"):
        session_title = st.text_input("Session Title")
        session_date = st.date_input("Session Date", date.today(), key="session_date")
        session_time = st.time_input(
            "Session Time", st.session_state.session_time, key="session_time"
        )

        if "show_create_session_form" not in st.session_state:
            st.session_state.show_create_session_form = False

        new_session_id = None
        # Generate new session ID
        course = courses_collection2.find_one({"course_id": course_id})
        if course and "sessions" in course and course["sessions"]:
            last_session_id = max(
                int(session["session_id"][1:]) for session in course["sessions"]
            )
            new_session_id = last_session_id + 1
        else:
            new_session_id = 1

        if st.form_submit_button("Create Session"):
            clicked = True
            new_session = {
                "session_id": f"S{new_session_id}",
                "course_id": course_id,
                "title": session_title,
                "date": datetime.combine(session_date, session_time),
                "status": "upcoming",
                "created_at": datetime.utcnow(),
                "pre_class": {
                    "resources": [],
                    "completetion_required": True,
                },
                "in_class": {
                    "topics": [],
                    "quiz": {"title": "", "questions": 0, "duration": 0},
                    "polls": [],
                },
                "post_class": {
                    "assignments": [],
                },
            }
            courses_collection2.update_one(
                {"course_id": course_id}, {"$push": {"sessions": new_session}}
            )
            st.success("Session created successfully!")
            st.session_state.show_create_session_form = False

    #     new_session_id = None
    #     creation_success = False
    #     # Generate new session ID
    #     course = courses_collection2.find_one({"course_id": course_id})
    #     if course and 'sessions' in course and course['sessions']:
    #         last_session_id = max((session['session_id'] for session in course['sessions']))
    #         last_session_id = int(last_session_id[1:])
    #         new_session_id = last_session_id + 1
    #     else:
    #         new_session_id = 1

    #         new_session = {
    #             "session_id": 'S' + new_session_id,
    #             "title": session_title,
    #             "date": datetime.datetime.combine(session_date, session_time).isoformat(),
    #             "status": "upcoming",
    #             "created_at": datetime.datetime.utcnow().isoformat(),
    #             "pre_class": {
    #                 "resources": [],
    #                 "completetion_required": True,
    #             },
    #             "in_class": {
    #                 "topics": [],
    #                 "quiz":
    #                 {
    #                     "title": '',
    #                     "questions": 0,
    #                     "duration": 0
    #                 },
    #                 "polls": []
    #             },
    #             "post_class": {
    #                 "assignments": [],
    #             }
    #         }
    #         courses_collection2.update_one(
    #             {"course_id": course_id},
    #             {"$push": {"sessions": new_session}}
    #             )
    #         creation_success = True
    #     st.form_submit_button("Create Session")
    # if creation_success == True:
    #     st.success("Session created successfully!")
    # else:


def get_new_student_id():
    """Generate a new student ID by incrementing the last student ID"""
    last_student = students_collection.find_one(sort=[("SID", -1)])
    if last_student:
        last_student_id = int(last_student["SID"][1:])
        new_student_id = f"S{last_student_id + 1}"
    else:
        new_student_id = "S101"
    return new_student_id


def get_new_faculty_id():
    """Generate a new faculty ID by incrementing the last faculty ID"""
    last_faculty = faculty_collection.find_one(sort=[("TID", -1)])
    if last_faculty:
        last_faculty_id = int(last_faculty["TID"][1:])
        new_faculty_id = f"T{last_faculty_id + 1}"
    else:
        new_faculty_id = "T101"
    return new_faculty_id


def get_new_course_id():
    """Generate a new course ID by incrementing the last course ID"""
    last_course = courses_collection2.find_one(sort=[("course_id", -1)])
    if last_course:
        last_course_id = int(last_course["course_id"][2:])
        new_course_id = f"CS{last_course_id + 1}"
    else:
        new_course_id = "CS101"
    return new_course_id


# def register_page():
#     st.title("Register")
#     if "user_type" not in st.session_state:
#         st.session_state.user_type = "student"

#     # Select user type
#     st.session_state.user_type = st.selectbox(
#         "Select User Type", ["student", "faculty", "research_assistant"]
#     )
#     user_type = st.session_state.user_type
#     print(user_type)

#     with st.form("register_form"):
#         # user_type = st.selectbox("Select User Type", ["student", "faculty", "research_assistant"])
#         # print(user_type)
#         full_name = st.text_input("Full Name")
#         password = st.text_input("Password", type="password")
#         confirm_password = st.text_input("Confirm Password", type="password")

#         if user_type == "student":
#             # Fetch courses for students to select from
#             courses = list(courses_collection2.find({}, {"course_id": 1, "title": 1}))
#             course_options = [
#                 f"{course['title']} ({course['course_id']})" for course in courses
#             ]
#             selected_courses = st.multiselect("Available Courses", course_options)

#         submit = st.form_submit_button("Register")

#         if submit:
#             if password == confirm_password:
#                 hashed_password = generate_password_hash(password)
#                 if user_type == "student":
#                     new_student_id = get_new_student_id()
#                     enrolled_courses = [
#                         {
#                             "course_id": course.split("(")[-1][:-1],
#                             "title": course.split(" (")[0],
#                         }
#                         for course in selected_courses
#                     ]
#                     students_collection.insert_one(
#                         {
#                             "SID": new_student_id,
#                             "full_name": full_name,
#                             "password": hashed_password,
#                             "enrolled_courses": enrolled_courses,
#                             "created_at": datetime.utcnow(),
#                         }
#                     )
#                     st.success(
#                         f"Student registered successfully with ID: {new_student_id}"
#                     )
#                 elif user_type == "faculty":
#                     new_faculty_id = get_new_faculty_id()
#                     faculty_collection.insert_one(
#                         {
#                             "TID": new_faculty_id,
#                             "full_name": full_name,
#                             "password": hashed_password,
#                             "courses_taught": [],
#                             "created_at": datetime.utcnow(),
#                         }
#                     )
#                     st.success(
#                         f"Faculty registered successfully with ID: {new_faculty_id}"
#                     )
#                 elif user_type == "research_assistant":
#                     research_assistants_collection.insert_one(
#                         {
#                             "full_name": full_name,
#                             "password": hashed_password,
#                             "created_at": datetime.utcnow(),
#                         }
#                     )
#                     st.success("Research Assistant registered successfully!")
#             else:
#                 st.error("Passwords do not match")


def get_new_analyst_id():
    """Generate a new analyst ID by incrementing the last analyst ID"""
    last_analyst = analysts_collection.find_one(sort=[("AID", -1)])
    if last_analyst:
        last_id = int(last_analyst["AID"][1:])
        new_id = f"A{last_id + 1}"
    else:
        new_id = "A1"
    return new_id


def register_page():
    st.title("Register")
    if "user_type" not in st.session_state:
        st.session_state.user_type = "student"

    # Select user type
    st.session_state.user_type = st.selectbox(
        "Select User Type", ["student", "faculty", "research_assistant", "analyst"]
    )
    user_type = st.session_state.user_type
    print(user_type)

    with st.form("register_form"):
        full_name = st.text_input("Full Name")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        if user_type == "student":
            # Fetch courses for students to select from
            courses = list(courses_collection2.find({}, {"course_id": 1, "title": 1}))
            course_options = [
                f"{course['title']} ({course['course_id']})" for course in courses
            ]
            selected_courses = st.multiselect("Available Courses", course_options)

        submit = st.form_submit_button("Register")

        if submit:
            if password == confirm_password:
                hashed_password = generate_password_hash(password)
                if user_type == "student":
                    new_student_id = get_new_student_id()
                    enrolled_courses = [
                        {
                            "course_id": course.split("(")[-1][:-1],
                            "title": course.split(" (")[0],
                        }
                        for course in selected_courses
                    ]
                    students_collection.insert_one(
                        {
                            "SID": new_student_id,
                            "full_name": full_name,
                            "password": hashed_password,
                            "enrolled_courses": enrolled_courses,
                            "created_at": datetime.utcnow(),
                        }
                    )
                    st.success(
                        f"Student registered successfully with ID: {new_student_id}"
                    )
                elif user_type == "faculty":
                    new_faculty_id = get_new_faculty_id()
                    faculty_collection.insert_one(
                        {
                            "TID": new_faculty_id,
                            "full_name": full_name,
                            "password": hashed_password,
                            "courses_taught": [],
                            "created_at": datetime.utcnow(),
                        }
                    )
                    st.success(
                        f"Faculty registered successfully with ID: {new_faculty_id}"
                    )
                elif user_type == "research_assistant":
                    research_assistants_collection.insert_one(
                        {
                            "full_name": full_name,
                            "password": hashed_password,
                            "created_at": datetime.utcnow(),
                        }
                    )
                    st.success("Research Assistant registered successfully!")
                elif user_type == "analyst":
                    # new_analyst_id = get_new_analyst_id()
                    analysts_collection.insert_one(
                        {
                            # "AID": new_analyst_id,
                            "full_name": full_name,
                            "password": hashed_password,
                            "created_at": datetime.utcnow(),
                        }
                    )
                    st.success("Analyst registered successfully!")
            else:
                st.error("Passwords do not match")


# Create Course feature
def create_course_form(faculty_name, faculty_id):
    """Display form to create a new course"""
    st.title("Create New Course")
    faculty = faculty_collection.find_one({"_id": faculty_id})
    if not faculty:
        st.error("Faculty not found")
        return
    faculty_str_id = faculty["TID"]

    with st.form("create_course_form"):
        course_title = st.text_input("Course Title")
        course_description = st.text_area("Course Description")
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        duration = -(
            -((end_date - start_date).days) // 7
        )  # Ceiling division to round up to the next week

        if st.form_submit_button("Create Course"):
            new_course_id = get_new_course_id()
            course = {
                "course_id": new_course_id,
                "title": course_title,
                "description": course_description,
                "faculty": faculty_name,
                "faculty_id": faculty_str_id,
                # "start_date": start_date.isoformat(),
                # "end_date": end_date.isoformat(),
                "start_date": datetime.combine(
                    start_date, datetime.min.time()
                ),  # Store as datetime
                "end_date": datetime.combine(
                    end_date, datetime.min.time()
                ),  # Store as datetime
                "duration": f"{duration} weeks",
                "created_at": datetime.utcnow(),
                "sessions": [],
            }

            # Insert course into courses collection
            courses_collection2.insert_one(course)

            # Update faculty's courses_taught array
            faculty_collection.update_one(
                {"_id": st.session_state.user_id},
                {
                    "$push": {
                        "courses_taught": {
                            "course_id": new_course_id,
                            "title": course_title,
                        }
                    }
                },
            )

            st.success(f"Course created successfully with ID: {new_course_id}")
            st.session_state.show_create_course_form = False
            st.rerun()


from research_assistant_dashboard import display_research_assistant_dashboard

from goals2 import display_analyst_dashboard


def main_dashboard():
    if st.session_state.user_type == "research_assistant":
        display_research_assistant_dashboard()
    elif st.session_state.user_type == "analyst":
        display_analyst_dashboard()
    else:
        selected_course_id = None
        create_session = False
        with st.sidebar:
            st.title(f"Welcome, {st.session_state.username}")
            if st.session_state.user_type == "student":
                st.title("Enrolled Courses")
            else:
                st.title("Your Courses")

            # Course selection
            enrolled_courses = get_courses(
                st.session_state.username, st.session_state.user_type
            )

            if st.session_state.user_type == "faculty":
                if st.button(
                    "Create New Course", key="create_course", use_container_width=True
                ):
                    st.session_state.show_create_course_form = True

            if not enrolled_courses:
                st.warning("No courses found")
            else:
                course_titles = [course["title"] for course in enrolled_courses]
                course_ids = [course["course_id"] for course in enrolled_courses]

                selected_course = st.selectbox("Select Course", course_titles)
                selected_course_id = course_ids[course_titles.index(selected_course)]
                print(selected_course_id)

                st.session_state.selected_course = selected_course
                st.session_state.selected_course_id = selected_course_id

                # Display course sessions
                sessions = get_sessions(selected_course_id)

                st.title("Course Sessions")
                for i, session in enumerate(sessions, start=1):
                    if st.button(
                        f"Session {i}", key=f"session_{i}", use_container_width=True
                    ):
                        st.session_state.selected_session = session

                if st.session_state.user_type == "faculty":
                    # Create new session
                    # create_session =  st.button("Create New Session Button", key="create_session", use_container_width=True)
                    if st.button(
                        "Create New Session",
                        key="create_session",
                        use_container_width=True,
                    ):
                        st.session_state.show_create_session_form = True

            if st.button("Logout", use_container_width=True):
                for key in st.session_state.keys():
                    del st.session_state[key]
                st.rerun()

        # if create_session:
        #     create_session_form(selected_course_id)
        if st.session_state.get("show_create_course_form"):
            create_course_form(st.session_state.username, st.session_state.user_id)
        elif st.session_state.get("show_create_session_form"):
            create_session_form(selected_course_id)
        else:
            # Main content
            if "selected_session" in st.session_state:
                display_session_content(
                    st.session_state.user_id,
                    selected_course_id,
                    st.session_state.selected_session,
                    st.session_state.username,
                    st.session_state.user_type,
                )
            else:
                st.info("Select a session to view details")
        # # Main content
        # if 'selected_session' in st.session_state:
        #     display_session_content(st.session_state.user_id, selected_course_id, st.session_state.selected_session, st.session_state.username, st.session_state.user_type)
        # if create_session:
        #     create_session_form(selected_course_id)


def main():
    st.set_page_config(page_title="NOVAScholar", page_icon="📚", layout="wide")
    init_session_state()
    # modify_courses_collection_schema()

    if not st.session_state.authenticated:
        login_tab, register_tab = st.tabs(["Login", "Register"])

        with register_tab:
            register_page()
        with login_tab:
            login_form()
    else:
        main_dashboard()


if __name__ == "__main__":
    main()
