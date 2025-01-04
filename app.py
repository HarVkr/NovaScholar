import re
import streamlit as st
from datetime import datetime, date, time, timedelta
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
from create_course import create_course, courses_collection, generate_perplexity_response, PERPLEXITY_API_KEY
import json
from bson import ObjectId
client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
from dotenv import load_dotenv

load_dotenv()
# PERPLEXITY_API_KEY = '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'

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
    if "show_create_session_form" not in st.session_state:
        st.session_state.show_create_session_form = False
    if "show_enroll_course_page" not in st.session_state:
        st.session_state.show_enroll_course_page = False
    if "course_to_enroll" not in st.session_state:
        st.session_state.course_to_enroll = None

def login_user(username, password, user_type):
    """Login user based on credentials"""
    if user_type == "student":
        # user = students_collection.find_one({"full_name": username}) or students_collection.find_one({"username": username})
        user = students_collection.find_one({"$or": [{"full_name": username}, {"username": username}]})
    elif user_type == "faculty":
        user = faculty_collection.find_one({"full_name": username})
    elif user_type == "research_assistant":
        user = research_assistants_collection.find_one({"full_name": username})
    elif user_type == "analyst":
        user = analysts_collection.find_one({"full_name": username})

    if user and check_password_hash(user["password"], password):
        st.session_state.user_id = user["_id"]
        print(st.session_state.user_id)
        st.session_state.authenticated = True
        st.session_state.user_type = user_type
        st.session_state.username = username
        return True
    return False

# def login_form():
#     """Display login form"""
#     st.title("Welcome to NOVAScholar")

#     with st.form("login_form"):
        
#         user_type = st.selectbox(
#             "Please select your Role", ["student", "faculty", "research_assistant", "analyst"]
#         )
#         username = st.text_input("Username")
#         password = st.text_input("Password", type="password")
#         submit = st.form_submit_button("Login")

#         if submit:
#             if login_user(username, password, user_type):
#                 st.success("Login successful!")
#                 st.rerun()
#             else:
#                 st.error("Invalid credentials!")
def login_form():
    """Display enhanced login form"""
    st.title("Welcome to NOVAScholar")

    with st.form("login_form"):
        # Role selection at the top
        user_type = st.selectbox(
            "Please select your Role",
            ["student", "faculty", "research_assistant", "analyst"]
        )
        
        # Username/email and password stacked vertically
        username = st.text_input("Username or Email")
        password = st.text_input("Password", type="password")
        
        # Login button
        submit = st.form_submit_button("Login")

        if submit:
            # Handle both username and email login
            if '@' in username:
                username = extract_username(username)
            
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
            courses = courses_collection.find(
                {"course_id": {"$in": enrolled_course_ids}}
            )
            # courses += courses_collection2.find(
            #     {"course_id": {"$in": enrolled_course_ids}}
            # )
            # # course_titles = [course['title'] for course in courses]
            # return list(courses)
            # courses_cursor1 = courses_collection.find(
            #     {"course_id": {"$in": enrolled_course_ids}}
            # )
            # courses_cursor2 = courses_collection2.find(
            #     {"course_id": {"$in": enrolled_course_ids}}
            # )
            # courses = list(courses_cursor1) + list(courses_cursor2)
            return list(courses)
    elif user_type == "faculty":
        faculty = faculty_collection.find_one({"full_name": username})
        if faculty:
            course_ids = [
                course["course_id"] for course in faculty.get("courses_taught", [])
            ]
            # courses_1 = list(courses_collection2.find({"course_id": {"$in": course_ids}}))
            courses_2 = list(courses_collection.find({"course_id": {"$in": course_ids}}))
            return courses_2
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


def get_sessions(course_id, course_title):
    """Get sessions for a given course ID"""
    course = courses_collection.find_one({"course_id": course_id, "title": course_title})
    if course:
        return course.get("sessions", [])
    return []


def create_session(new_session, course_id):
    """Create a new session for a given course ID"""
    course = courses_collection2.find_one({"course_id": course_id}) | courses_collection.find_one({"course_id": course_id})
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

    if 'session_time' not in st.session_state:
        st.session_state.session_time = datetime.now().time()
    if 'show_create_session_form' not in st.session_state:
        st.session_state.show_create_session_form = False

    with st.form("create_session_form"):
        session_title = st.text_input("Session Title")
        session_date = st.date_input("Session Date", date.today(), key="session_date")
        session_time = st.time_input(
            "Session Time", st.session_state.session_time, key="session_time"
        )

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


# def register_page():
#     st.title("Register")
#     if "user_type" not in st.session_state:
#         st.session_state.user_type = "student"

#     # Select user type
#     st.session_state.user_type = st.selectbox(
#         "Please select your Role", ["student", "faculty", "research_assistant", "analyst"]
#     )
#     user_type = st.session_state.user_type
#     print(user_type)

#     with st.form("register_form"):

#         full_name = st.text_input("Full Name")
#         password = st.text_input("Password", type="password")
#         confirm_password = st.text_input("Confirm Password", type="password")

#         if user_type == "student":
#             # Fetch courses for students to select from
#             courses = list(courses_collection.find({}, {"course_id": 1, "title": 1}))
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
#                 elif user_type == "analyst":
#                     # new_analyst_id = get_new_analyst_id()
#                     analysts_collection.insert_one(
#                         {
#                             # "AID": new_analyst_id,
#                             "full_name": full_name,
#                             "password": hashed_password,
#                             "created_at": datetime.utcnow(),
#                         }
#                     )
#                     st.success("Analyst registered successfully!")
#             else:
#                 st.error("Passwords do not match")
def register_page():
    st.title("Register for NOVAScholar")
    if "user_type" not in st.session_state:
        st.session_state.user_type = "student"

    # Select user type
    st.session_state.user_type = st.selectbox(
        "Please select your Role", 
        ["student", "faculty", "research_assistant", "analyst"]
    )
    user_type = st.session_state.user_type

    with st.form("register_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input("Full Name")
            email = st.text_input("Institutional Email")
            phone = st.text_input("Phone Number")
        
        with col2:
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")

        if user_type == "student":
            courses = list(courses_collection.find({}, {"course_id": 1, "title": 1}))
            course_options = [f"{course['title']} ({course['course_id']})" for course in courses]
            selected_courses = st.multiselect("Available Courses", course_options)

        submit = st.form_submit_button("Register")

        if submit:
            # Validate email
            email_valid, email_msg = validate_email(email)
            if not email_valid:
                st.error(email_msg)
                return

            # Validate phone
            phone_valid, phone_msg = validate_phone(phone)
            if not phone_valid:
                st.error(phone_msg)
                return

            # Validate password match
            if password != confirm_password:
                st.error("Passwords do not match")
                return

            # Extract username from email
            username = extract_username(email)

            # Check if username already exists
            if user_type == "student":
                existing_user = students_collection.find_one({"username": username})
            elif user_type == "faculty":
                existing_user = faculty_collection.find_one({"username": username})
            elif user_type == "research_assistant":
                existing_user = research_assistants_collection.find_one({"username": username})
            elif user_type == "analyst":
                existing_user = analysts_collection.find_one({"username": username})

            if existing_user:
                st.error("A user with this email already exists")
                return

            # Hash password and create user
            hashed_password = generate_password_hash(password)
            
            user_data = {
                "username": username,
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "password": hashed_password,
                "created_at": datetime.utcnow()
            }

            if user_type == "student":
                new_student_id = get_new_student_id()
                enrolled_courses = [
                    {
                        "course_id": course.split("(")[-1][:-1],
                        "title": course.split(" (")[0],
                    }
                    for course in selected_courses
                ]
                user_data["SID"] = new_student_id
                user_data["enrolled_courses"] = enrolled_courses
                students_collection.insert_one(user_data)
                st.success(f"Student registered successfully! Your username is: {username}")
                
            elif user_type == "faculty":
                new_faculty_id = get_new_faculty_id()
                user_data["TID"] = new_faculty_id
                user_data["courses_taught"] = []
                faculty_collection.insert_one(user_data)
                st.success(f"Faculty registered successfully! Your username is: {username}")
                
            elif user_type == "research_assistant":
                research_assistants_collection.insert_one(user_data)
                st.success(f"Research Assistant registered successfully! Your username is: {username}")
                
            elif user_type == "analyst":
                analysts_collection.insert_one(user_data)
                st.success(f"Analyst registered successfully! Your username is: {username}")

# Create Course feature
def create_course_form(faculty_name, faculty_id):
    """Display enhanced form to create a new course with AI-generated content"""
    st.title("Create New Course")
    
    if 'course_plan' not in st.session_state:
        st.session_state.course_plan = None
    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = False

    # Initial Course Creation Form
    if not st.session_state.course_plan:
        with st.form("initial_course_form"):
            col1, col2 = st.columns(2)
            with col1:
                course_name = st.text_input("Course Name", placeholder="e.g., Introduction to Computer Science")
                faculty_info = st.text_input("Faculty", value=faculty_name, disabled=True)
            with col2:
                duration_weeks = st.number_input("Duration (weeks)", min_value=1, max_value=16, value=12)
                start_date = st.date_input("Start Date")
            
            generate_button = st.form_submit_button("Generate Course Structure", use_container_width=True)
            
            if generate_button and course_name:
                with st.spinner("Generating course structure..."):
                    try:
                        course_plan = generate_perplexity_response(PERPLEXITY_API_KEY, course_name)
                        # print(course_plan)
                        st.session_state.course_plan = json.loads(course_plan)
                        st.session_state.start_date = start_date
                        st.session_state.duration_weeks = duration_weeks
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generating course structure: {e}")
    
    # Display and Edit Generated Course Content
    if st.session_state.course_plan:
        with st.expander("Course Overview", expanded=True):
            if not st.session_state.edit_mode:
                st.subheader(st.session_state.course_plan['course_title'])
                st.write(st.session_state.course_plan['course_description'])
                edit_button = st.button("Edit Course Details", use_container_width=True)
                if edit_button:
                    st.session_state.edit_mode = True
                    st.rerun()
            else:
                with st.form("edit_course_details"):
                    st.session_state.course_plan['course_title'] = st.text_input(
                        "Course Title", 
                        value=st.session_state.course_plan['course_title']
                    )
                    st.session_state.course_plan['course_description'] = st.text_area(
                        "Course Description", 
                        value=st.session_state.course_plan['course_description']
                    )
                    if st.form_submit_button("Save Course Details"):
                        st.session_state.edit_mode = False
                        st.rerun()
        
        # Display Modules and Sessions
        st.subheader("Course Modules and Sessions")
        
        start_date = st.session_state.start_date
        current_date = start_date
        
        all_sessions = []
        for module_idx, module in enumerate(st.session_state.course_plan['modules']):
            with st.expander(f"📚 Module {module_idx + 1}: {module['module_title']}", expanded=True):
                # Edit module title
                new_module_title = st.text_input(
                    f"Module {module_idx + 1} Title",
                    value=module['module_title'],
                    key=f"module_{module_idx}"
                )
                module['module_title'] = new_module_title
                
                for sub_idx, sub_module in enumerate(module['sub_modules']):
                    st.markdown(f"### 📖 {sub_module['title']}")
                    
                    # Create sessions for each topic
                    for topic_idx, topic in enumerate(sub_module['topics']):
                        session_key = f"session_{module_idx}_{sub_idx}_{topic_idx}"
                        
                        with st.container():
                            col1, col2, col3 = st.columns([3, 2, 1])
                            with col1:
                                new_topic = st.text_input(
                                    "Topic",
                                    value=topic,
                                    key=f"{session_key}_topic"
                                )
                                sub_module['topics'][topic_idx] = new_topic
                            
                            with col2:
                                session_date = st.date_input(
                                    "Session Date",
                                    value=current_date,
                                    key=f"{session_key}_date"
                                )
                            
                            with col3:
                                session_status = st.selectbox(
                                    "Status",
                                    options=["upcoming", "in-progress", "completed"],
                                    key=f"{session_key}_status"
                                )
                            
                            # Create session object
                            session = {
                                "session_id": str(ObjectId()),
                                "title": new_topic,
                                "date": datetime.combine(session_date, datetime.min.time()),
                                "status": session_status,
                                "module_name": module['module_title'],
                                "created_at": datetime.utcnow(),
                                "pre_class": {
                                    "resources": [],
                                    "completion_required": True
                                },
                                "in_class": {
                                    "quiz": [],
                                    "polls": []
                                },
                                "post_class": {
                                    "assignments": []
                                }
                            }
                            all_sessions.append(session)
                            current_date = session_date + timedelta(days=7)
        
        new_course_id = get_new_course_id()
        course_title = st.session_state.course_plan['course_title']
        # Final Save Button
        if st.button("Save Course", type="primary", use_container_width=True):
            try:
                course_doc = {
                    "course_id": new_course_id,
                    "title": course_title,
                    "description": st.session_state.course_plan['course_description'],
                    "faculty": faculty_name,
                    "faculty_id": faculty_id,
                    "duration": f"{st.session_state.duration_weeks} weeks",
                    "start_date": datetime.combine(st.session_state.start_date, datetime.min.time()),
                    "created_at": datetime.utcnow(),
                    "sessions": all_sessions
                }
                
                # Insert into database
                courses_collection.insert_one(course_doc)
                
                st.success("Course successfully created!")

                # Update faculty collection
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

                # Clear session state
                st.session_state.course_plan = None
                st.session_state.edit_mode = False
                
                # Optional: Add a button to view the created course
                if st.button("View Course"):
                    # Add navigation logic here
                    pass
                
            except Exception as e:
                st.error(f"Error saving course: {e}")
    
from research_assistant_dashboard import display_research_assistant_dashboard
from goals2 import display_analyst_dashboard
def enroll_in_course(course_id, course_title, student):
    """Enroll a student in a course"""
    if student:
        courses = student.get("enrolled_courses", [])
        if course_id not in [course["course_id"] for course in courses]:
            course = courses_collection.find_one({"course_id": course_id})
            if course:
                courses.append(
                    {
                        "course_id": course["course_id"],
                        "title": course["title"],
                    }
                )
                students_collection.update_one(
                    {"_id": st.session_state.user_id},
                    {"$set": {"enrolled_courses": courses}},
                )
                st.success(f"Enrolled in course {course_title}")
                st.experimental_rerun()
            else:
                st.error("Course not found")
        else:
            st.warning("Already enrolled in this course")

# def enroll_in_course_page(course_id):
#     """Enroll a student in a course"""
#     student = students_collection.find_one({"_id": st.session_state.user_id})
#     course_title = courses_collection.find_one({"course_id": course_id})["title"]

#     course = courses_collection.find_one({"course_id": course_id})
#     if course:
#         st.title(course["title"])
#         st.subheader("Course Description:")
#         st.write(course["description"])
#         st.write(f"Faculty: {course['faculty']}")
#         st.write(f"Duration: {course['duration']}")

#         st.title("Course Sessions")
#         for session in course["sessions"]:
#             st.write(f"Session: {session['title']}")
#             st.write(f"Date: {session['date']}")
#             st.write(f"Status: {session['status']}")
#             st.write("----")
#     else:
#         st.error("Course not found")

#     enroll_button = st.button("Enroll in Course", key="enroll_button", use_container_width=True)
#     if enroll_button:
#         enroll_in_course(course_id, course_title, student)
def enroll_in_course_page(course_id):
    """Display an aesthetically pleasing course enrollment page"""
    student = students_collection.find_one({"_id": st.session_state.user_id})
    course = courses_collection.find_one({"course_id": course_id})
    
    if not course:
        st.error("Course not found")
        return
        
    # Create two columns for layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Course header section
        st.title(course["title"])
        st.markdown(f"*{course['description']}*")
        
        # Course details in an expander
        with st.expander("Course Details", expanded=True):
            st.markdown(f"👨‍🏫 **Faculty:** {course['faculty']}")
            st.markdown(f"⏱️ **Duration:** {course['duration']}")
        
        # Sessions in a clean card-like format
        st.subheader("📚 Course Sessions")
        for idx, session in enumerate(course["sessions"], 1):
            with st.container():
                st.markdown(f"""
                ---
                ### Session {idx}: {session['title']}
                🗓️ **Date:** {session['date']}  
                📌 **Status:** {session['status']}
                """)
    
    with col2:
        with st.container():
            st.markdown("### Ready to Learn?")
            st.markdown("Click below to enroll in this course")
            
            # Check if already enrolled
            courses = student.get("enrolled_courses", [])
            is_enrolled = course_id in [c["course_id"] for c in courses]
            
            if is_enrolled:
                st.info("✅ You are already enrolled in this course")
            else:
                enroll_button = st.button(
                    "🎓 Enroll Now",
                    key="enroll_button",
                    use_container_width=True
                )
                if enroll_button:
                    enroll_in_course(course_id, course["title"], student)

def show_available_courses(username, user_type, user_id):
    """Display available courses for enrollment"""
    st.title("Available Courses")
    
    courses = list(courses_collection.find({}, {"course_id": 1, "title": 1}))
    course_options = [
        f"{course['title']} ({course['course_id']})" for course in courses
    ]
    
    selected_course = st.selectbox("Select a Course to Enroll", course_options)
    # if selected_courses:
    #     for course in selected_courses:
    #         course_id = course.split("(")[-1][:-1]
    #         course_title = course.split(" (")[0]
    #         enroll_in_course(course_id, course_title, user_id)
    #     st.success("Courses enrolled successfully!")
    if selected_course:
        course_id = selected_course.split("(")[-1][:-1]
        enroll_in_course_page(course_id)

def validate_email(email):
    """Validate email format and domain"""
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    # You can add additional institution-specific validation here
    # For example, checking if the domain is from your institution
    # allowed_domains = ["spit.ac.in"]  # Add more domains as needed
    # domain = email.split('@')[1]
    # if domain not in allowed_domains:
    #     return False, "Please use your institutional email address"
    
    return True, "Valid email"

def validate_phone(phone):
    """Validate phone number format"""
    # Assuming Indian phone numbers
    pattern = r'^[6-9]\d{9}$'
    if not re.match(pattern, phone):
        return False, "Invalid phone number format. Please enter a 10-digit Indian mobile number"
    return True, "Valid phone number"

def extract_username(email):
    """Extract username from email"""
    return email.split('@')[0]




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

            # Enroll in Courses
            if st.session_state.user_type == "student":
                if st.button(
                    "Enroll in a New Course", key="enroll_course", use_container_width=True
                ):
                    st.session_state.show_enroll_course_page = True
                
            # if st.session_state.show_enroll_course_form: 
            #     courses = list(courses_collection.find({}, {"course_id": 1, "title": 1}))
            #     courses += list(courses_collection2.find({}, {"course_id": 1, "title": 1}))
            #     course_options = [f"{course['title']} ({course['course_id']})" for course in courses]
            #     course_to_enroll = st.selectbox("Available Courses", course_options)
            #     st.session_state.course_to_enroll = course_to_enroll

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
                print("Selected Course ID: ", selected_course_id)

                st.session_state.selected_course = selected_course
                st.session_state.selected_course_id = selected_course_id

                # Display course sessions
                sessions = get_sessions(selected_course_id, selected_course)

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
        elif st.session_state.get("show_enroll_course_page"):
            show_available_courses(st.session_state.username, st.session_state.user_type, st.session_state.user_id)
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
