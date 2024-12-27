from collections import defaultdict
import json
import random
import streamlit as st
from datetime import datetime
from utils.helpers import display_progress_bar, create_notification, format_datetime
from file_upload_vectorize import upload_resource, extract_text_from_file, create_vector_store, resources_collection, model, assignment_submit
from db import courses_collection2, chat_history_collection, students_collection, faculty_collection, vectors_collection
from chatbot import give_chat_response
from bson import ObjectId
from live_polls import LivePollFeature
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from gen_mcqs import generate_mcqs, save_quiz, quizzes_collection, get_student_quiz_score, submit_quiz_answers
from create_course import courses_collection
from pre_class_analytics import NovaScholarAnalytics
import openai
from openai import OpenAI



load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
OPENAI_KEY = os.getenv('OPENAI_KEY')
client = MongoClient(MONGO_URI)
db = client["novascholar_db"]
polls_collection = db["polls"]


def get_current_user():
    if 'current_user' not in st.session_state:
        return None
    return students_collection.find_one({"_id": st.session_state.user_id})

# def display_preclass_content(session, student_id, course_id):
    """Display pre-class materials for a session"""
    
    # Initialize 'messages' in session_state if it doesn't exist
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        
    # Display pre-class materials
    materials = list(resources_collection.find({"course_id": course_id, "session_id": session['session_id']}))
    st.subheader("Pre-class Materials")
    
    if materials:
        for material in materials:
            with st.expander(f"{material['file_name']} ({material['material_type'].upper()})"):
                file_type = material.get('file_type', 'unknown')
                if file_type == 'application/pdf':
                    st.markdown(f"📑 [Open PDF Document]({material['file_name']})")
                    if st.button("View PDF", key=f"view_pdf_{material['file_name']}"):
                        st.text_area("PDF Content", material['text_content'], height=300)
                    if st.button("Download PDF", key=f"download_pdf_{material['file_name']}"):
                        st.download_button(
                            label="Download PDF",
                            data=material['file_content'],
                            file_name=material['file_name'],
                            mime='application/pdf'
                        )
                    if st.button("Mark PDF as Read", key=f"pdf_{material['file_name']}"):
                        create_notification("PDF marked as read!", "success")
    else:
        st.info("No pre-class materials uploaded by the faculty.")
        st.subheader("Upload Pre-class Material")
        
        # File upload section for students
        uploaded_file = st.file_uploader("Upload Material", type=['txt', 'pdf', 'docx'])
        if uploaded_file is not None:
            with st.spinner("Processing document..."):
                file_name = uploaded_file.name
                file_content = extract_text_from_file(uploaded_file)
                if file_content:
                    material_type = st.selectbox("Select Material Type", ["pdf", "docx", "txt"])
                    if st.button("Upload Material"):
                        upload_resource(course_id, session['session_id'], file_name, uploaded_file, material_type)

                        # Search for the newly uploaded resource's _id in resources_collection
                        resource_id = resources_collection.find_one({"file_name": file_name})["_id"]
                        create_vector_store(file_content, resource_id)
                        st.success("Material uploaded successfully!")
        
    st.subheader("Learn the Topic Using Chatbot")
    st.write(f"**Session Title:** {session['title']}")
    st.write(f"**Description:** {session.get('description', 'No description available.')}")
    
    # Chatbot interface
    if prompt := st.chat_input("Ask a question about the session topic"):
        if len(st.session_state.messages) >= 20:
            st.warning("Message limit (20) reached for this session.")
            return

        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display User Message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response from chatbot
        context = ""
        for material in materials:
            if 'text_content' in material:
                context += material['text_content'] + "\n"
        
        response = give_chat_response(student_id, session['session_id'], prompt, session['title'], session.get('description', ''), context)
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Display Assistant Response
        with st.chat_message("assistant"):
            st.markdown(response)
    
    # st.subheader("Your Chat History")
    # for message in st.session_state.messages:
    #     content = message.get("content", "")  # Default to an empty string if "content" is not present
    #     role = message.get("role", "user")  # Default to "user" if "role" is not present
    #     with st.chat_message(role):
    #         st.markdown(content)
    # user = get_current_user()
    
def display_preclass_content(session, student_id, course_id):
    """Display pre-class materials for a session"""
    st.subheader("Pre-class Materials")

    # Display pre-class materials
    materials = resources_collection.find({"session_id": session['session_id']})
    for material in materials:
        with st.expander(f"{material['file_name']} ({material['material_type'].upper()})"):
            file_type = material.get('file_type', 'unknown')
            if file_type == 'application/pdf':
                st.markdown(f"📑 [Open PDF Document]({material['file_name']})")
                if st.button("View PDF", key=f"view_pdf_{material['file_name']}"):
                    st.text_area("PDF Content", material['text_content'], height=300)
                if st.button("Download PDF", key=f"download_pdf_{material['file_name']}"):
                    st.download_button(
                        label="Download PDF",
                        data=material['file_content'],
                        file_name=material['file_name'],
                        mime='application/pdf'
                    )
                if st.button("Mark PDF as Read", key=f"pdf_{material['file_name']}"):
                    create_notification("PDF marked as read!", "success")

    # Initialize 'messages' in session_state if it doesn't exist
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Chat input
    # Add a check, if materials are available, only then show the chat input
    if(st.session_state.user_type == "student"):
        if materials:
            if prompt := st.chat_input("Ask a question about Pre-class Materials"):
                # if len(st.session_state.messages) >= 20:
                #     st.warning("Message limit (20) reached for this session.")
                #     return

                st.session_state.messages.append({"role": "user", "content": prompt})

                # Display User Message
                with st.chat_message("user"):
                    st.markdown(prompt)

                # Get document context
                context = ""
                print(session['session_id'])
                materials = resources_collection.find({"session_id": session['session_id']})
                print(materials)
                context = ""
                vector_data = None

                # for material in materials:
                #     print(material)
                context = ""
                for material in materials:
                    resource_id = material['_id']
                    print(resource_id)
                    vector_data = vectors_collection.find_one({"resource_id": resource_id})
                    # print(vector_data)
                    if vector_data and 'text' in vector_data:
                        context += vector_data['text'] + "\n"

                if not vector_data:
                    st.error("No Pre-class materials found for this session.")
                    return

                try:
                    # Generate response using Gemini
                    # context_prompt = f"""
                    # Based on the following context, answer the user's question:
                    
                    # Context:
                    # {context}
                    
                    # Question: {prompt}
                    
                    # Please provide a clear and concise answer based only on the information provided in the context.
                    # """
                    context_prompt = f"""
                    You are a highly intelligent and resourceful assistant capable of synthesizing information from the provided context. 

                    Context:
                    {context}

                    Instructions:
                    1. Base your answers primarily on the given context. 
                    2. If the answer to the user's question is not explicitly in the context but can be inferred or synthesized from the information provided, do so thoughtfully.
                    3. Only use external knowledge or web assistance when:
                    - The context lacks sufficient information, and
                    - The question requires knowledge beyond what can be reasonably inferred from the context.
                    4. Clearly state if you are relying on web assistance for any part of your answer.

                    Question: {prompt}

                    Please provide a clear and comprehensive answer based on the above instructions.
                    """

                    response = model.generate_content(context_prompt)
                    if not response or not response.text:
                        st.error("No response received from the model")
                        return

                    assistant_response = response.text
                    # Display Assistant Response
                    with st.chat_message("assistant"):
                        st.markdown(assistant_response)

                    # Build the message
                    new_message = {
                        "prompt": prompt,
                        "response": assistant_response,
                        "timestamp": datetime.utcnow()
                    }
                    st.session_state.messages.append(new_message)

                    # Update database
                    try:
                        chat_history_collection.update_one(
                            {
                                "user_id": student_id,
                                "session_id": session['session_id']
                            },
                            {
                                "$push": {"messages": new_message},
                                "$setOnInsert": {
                                    "user_id": student_id,
                                    "session_id": session['session_id'],
                                    "timestamp": datetime.utcnow()
                                }
                            },
                            upsert=True
                        )
                    except Exception as db_error:
                        st.error(f"Error saving chat history: {str(db_error)}")
                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")

    else:
        st.subheader("Upload Pre-class Material")
        # File upload section for students
        uploaded_file = st.file_uploader("Upload Material", type=['txt', 'pdf', 'docx'])
        if uploaded_file is not None:
            with st.spinner("Processing document..."):
                file_name = uploaded_file.name
                file_content = extract_text_from_file(uploaded_file)
                if file_content:
                    material_type = st.selectbox("Select Material Type", ["pdf", "docx", "txt"])
                    if st.button("Upload Material"):
                        resource_id = upload_resource(course_id, session['session_id'], file_name, uploaded_file, material_type)

                        # Search for the newly uploaded resource's _id in resources_collection
                        # resource_id = resources_collection.find_one({"file_name": file_name})["_id"]
                        create_vector_store(file_content, resource_id)
                        st.success("Material uploaded successfully!")

    # st.subheader("Your Chat History")
    if st.button("View Chat History"):
        # Initialize chat messages from database
        if 'messages' not in st.session_state or not st.session_state.messages:
            existing_chat = chat_history_collection.find_one({
                "user_id": student_id,
                "session_id": session['session_id']
            })
            if existing_chat and 'messages' in existing_chat:
                st.session_state.messages = existing_chat['messages']
            else:
                st.session_state.messages = []

        # Display existing chat history
        try:
            for message in st.session_state.messages:
                if 'prompt' in message and 'response' in message:
                    with st.chat_message("user"):
                        st.markdown(message["prompt"])
                    with st.chat_message("assistant"):
                        st.markdown(message["response"])
        except Exception as e:
            st.error(f"Error displaying chat history: {str(e)}")
            st.session_state.messages = []
    
    if st.session_state.user_type == 'student':
        st.subheader("Create a Practice Quiz")
        questions = []
        quiz_id = ""
        with st.form("create_quiz_form"):
            num_questions = st.number_input("Number of Questions", min_value=1, max_value=20, value=2)
            submit_quiz = st.form_submit_button("Generate Quiz")
            if submit_quiz:
                # Get pre-class materials from resources_collection
                materials = resources_collection.find({"session_id": session['session_id']})
                context = ""
                for material in materials:
                    if 'text_content' in material:
                        context += material['text_content'] + "\n"

                if not context:
                    st.error("No pre-class materials found for this session.")
                    return

                # Generate MCQs from context
                questions = generate_mcqs(context, num_questions, session['title'], session.get('description', ''))
                if questions:
                    quiz_id = save_quiz(course_id, session['session_id'], "Practice Quiz", questions, student_id)
                    if quiz_id:
                            st.success("Quiz saved successfully!")
                            st.session_state.show_quizzes = True
                    else:
                            st.error("Error saving quiz.")
                else:
                    st.error("Error generating questions.")

        # if st.button("Attempt Practice Quizzes "):
            # quizzes = list(quizzes_collection.find({"course_id": course_id, "session_id": session['session_id'], "user_id": student_id}))
            
            
        if getattr(st.session_state, 'show_quizzes', False):
            # quiz = quizzes_collection.find_one({"course_id": course_id, "session_id": session['session_id'], "user_id": student_id})
            quiz = quizzes_collection.find_one(
                {"course_id": course_id, "session_id": session['session_id'], "user_id": student_id},
                sort=[("created_at", -1)]
            )
            if not quiz:
                st.info("No practice quizzes created.")
            else:
                    with st.expander(f"📝 Practice Quiz", expanded=False):
                        # Check if student has already taken this quiz
                        existing_score = get_student_quiz_score(quiz['_id'], student_id)
                        
                        if existing_score is not None:
                            st.success(f"Quiz completed! Your score: {existing_score:.1f}%")
                            
                            # Display correct answers after submission
                            st.subheader("Quiz Review")
                            for i, question in enumerate(quiz['questions']):
                                st.markdown(f"**Question {i+1}:** {question['question']}")
                                for opt in question['options']:
                                    if opt.startswith(question['correct_option']):
                                        st.markdown(f"✅ {opt}")
                                    else:
                                        st.markdown(f"- {opt}")
                            
                        else:
                             # Initialize quiz state for this specific quiz
                            quiz_key = f"quiz_{quiz['_id']}_student_{student_id}"
                            if quiz_key not in st.session_state:
                                st.session_state[quiz_key] = {
                                    'submitted': False,
                                    'score': None,
                                    'answers': {}
                                }

                            # If quiz was just submitted, show the results
                            if st.session_state[quiz_key]['submitted']:
                                st.success(f"Quiz submitted successfully! Your score: {st.session_state[quiz_key]['score']:.1f}%")
                                # Reset the quiz state
                                st.session_state[quiz_key]['submitted'] = False


                            # Display quiz questions
                            st.write("Please select your answers:")
                            
                            # Create a form for quiz submission
                            form_key = f"quiz_form_{quiz['_id']}_student_{student_id}"
                            with st.form(key=form_key):
                                student_answers = {}
                                
                                for i, question in enumerate(quiz['questions']):
                                    st.markdown(f"**Question {i+1}:** {question['question']}")
                                    options = [opt for opt in question['options']]
                                    # student_answers[str(i)] = st.radio(
                                    #     f"Select answer for question {i+1}:",
                                    #     options=options,
                                    #     key=f"q_{i}",
                                    #     index=None
                                    # ) 
                                    answer = st.radio(
                                        f"Select answer for question {i+1}:",
                                        options=options,
                                        key=f"{quiz['_id']}_{i}",  # Simplify the radio button key
                                        index=None
                                    )
                                    if answer:  # Only add to answers if a selection was made
                                        student_answers[str(i)] = answer                               

                                # Submit button
                                # submitted =  st.form_submit_button("Submit Quiz")
                                print("Before the submit button")
                                submit_button = st.form_submit_button("Submit Quiz")
                                print("After the submit button")
                            if submit_button and student_answers:
                                print("Clicked the button")
                                print(student_answers)
                                correct_answers = 0
                                for i, question in enumerate(quiz['questions']):
                                    if student_answers[str(i)] == question['correct_option']:
                                        correct_answers += 1
                                score = (correct_answers / len(quiz['questions'])) * 100
                                
                                if score is not None:
                                    st.success(f"Quiz submitted successfully! Your score: {score:.1f}%")
                                    st.session_state[quiz_key]['submitted'] = True
                                    st.session_state[quiz_key]['score'] = score
                                    st.session_state[quiz_key]['answers'] = student_answers
                                    # This will trigger a rerun, but now we'll handle it properly
                                    st.rerun()
                        
                                else:
                                    st.error("Error submitting quiz. Please try again.")
                                # correct_answers = 0
                                # for i, question in enumerate(quiz['questions']):
                                #     if student_answers[str(i)] == question['correct_option']:
                                #         correct_answers += 1
                                # score = (correct_answers / len(quiz['questions'])) * 100
                                # print(score)
                                # try:
                                #     quizzes_collection.update_one(
                                #         {"_id": quiz['_id']},
                                #         {"$push": {"submissions": {"student_id": student_id, "score": score}}}
                                #     )
                                #     st.success(f"Quiz submitted successfully! Your score: {score:.1f}%")
                                # except Exception as db_error:
                                #     st.error(f"Error saving submission: {str(db_error)}")


def display_in_class_content(session, user_type):
    # """Display in-class activities and interactions"""
    """Display in-class activities and interactions"""
    st.header("In-class Activities")
    
    # Initialize Live Polls feature
    live_polls = LivePollFeature()
    
    # Display appropriate interface based on user role
    if user_type == 'faculty':
        live_polls.display_faculty_interface(session['session_id'])
    else:
        live_polls.display_student_interface(session['session_id'])

def generate_random_assignment_id():
    """Generate a random integer ID for assignments"""
    return random.randint(100000, 999999)

def display_post_class_content(session, student_id, course_id):
    """Display post-class assignments and submissions"""
    st.header("Post-class Work")
    
    if st.session_state.user_type == 'faculty':
        """Create quiz section UI for faculty"""
        st.subheader("Create Quiz")
        
        questions = []
        with st.form("create_quiz_form"):
            quiz_title = st.text_input("Quiz Title")
            num_questions = st.number_input("Number of Questions", min_value=1, max_value=20, value=5)
            
            # Option to choose quiz generation method
            generation_method = st.radio(
                "Question Generation Method",
                ["Generate from Pre-class Materials", "Generate Random Questions"]
            )
            
            submit_quiz = st.form_submit_button("Generate Quiz")
            if submit_quiz:
                if generation_method == "Generate from Pre-class Materials":
                    # Get pre-class materials from resources_collection
                    materials = resources_collection.find({"session_id": session['session_id']})
                    context = ""
                    for material in materials:
                        if 'text_content' in material:
                            context += material['text_content'] + "\n"
                    
                    if not context:
                        st.error("No pre-class materials found for this session.")
                        return
                    
                    # Generate MCQs from context
                    questions = generate_mcqs(context, num_questions, session['title'], session.get('description', ''))
                else:
                    # Generate random MCQs based on session title and description
                    questions = generate_mcqs(None, num_questions, session['title'], session.get('description', ''))
                    print(questions)
                
                if questions:
                    # Preview generated questions
                    st.subheader("Preview Generated Questions")
                    for i, q in enumerate(questions, 1):
                        st.markdown(f"**Question {i}:** {q['question']}")
                        for opt in q['options']:
                            st.markdown(f"- {opt}")
                        st.markdown(f"*Correct Answer: {q['correct_option']}*")
                    
                    # Save quiz 
                    quiz_id = save_quiz(course_id, session['session_id'], quiz_title, questions)
                    if quiz_id:
                        st.success("Quiz saved successfully!")
                    else:
                        st.error("Error saving quiz.")
                else:
                    st.error("Error generating questions.")

        st.subheader("Add Assignments")
        # Add assignment form
        with st.form("add_assignment_form"):
            title = st.text_input("Assignment Title")
            due_date = st.date_input("Due Date")
            due_date = datetime.strptime(due_date.strftime('%Y-%m-%d'), '%Y-%m-%d')
            submit = st.form_submit_button("Add Assignment")
            
            if submit:
                due_date = datetime.combine(due_date, datetime.min.time())
                # Save the assignment to the database
                assignment_id = ObjectId()
                print("Assignment ID: ", assignment_id)
                assignment = {
                    "id": ObjectId(),
                    "title": title,
                    "due_date": due_date,
                    "status": "pending",
                    "submissions": []
                }
                courses_collection2.update_one(
                    {"course_id": course_id, "sessions.session_id": session['session_id']},
                    {"$push": {"sessions.$.post_class.assignments": assignment}}
                )
                st.success("Assignment added successfully!")
    else:
        # Display assignments
        session_data = courses_collection2.find_one(
            {"course_id": course_id, "sessions.session_id": session['session_id']},
            {"sessions.$": 1}
        )
        
        if session_data and "sessions" in session_data and len(session_data["sessions"]) > 0:
            assignments = session_data["sessions"][0].get("post_class", {}).get("assignments", [])
            for assignment in assignments:
                title = assignment.get("title", "No Title")
                due_date = assignment.get("due_date", "No Due Date")
                status = assignment.get("status", "No Status")
                assignment_id = assignment.get("id", "No ID")

                with st.expander(f"Assignment: {title}", expanded=True):
                    st.markdown(f"**Due Date:** {due_date}")
                    st.markdown(f"**Status:** {status.replace('_', ' ').title()}")
                    
                    # Assignment details
                    st.markdown("### Instructions")
                    st.markdown("Complete the assignment according to the provided guidelines.")
                    
                    # File submission
                    st.markdown("### Submission")
                    uploaded_file = st.file_uploader(
                        "Upload your work",
                        type=['pdf', 'py', 'ipynb'],
                        key=f"upload_{assignment['id']}"
                    )
                    
                    if uploaded_file is not None:
                        st.success("File uploaded successfully!")

                        # if st.button("Submit Assignment", key=f"submit_{assignment['id']}"):
                        #     assignment_submit(student_id, course_id, session['session_id'], assignment_id, uploaded_file.name, uploaded_file, uploaded_file.type)
                        if st.button("Submit Assignment", key=f"submit_{assignment['id']}"):
                            # Extract text content from the file
                            text_content = extract_text_from_file(uploaded_file)
                            
                            # Call assignment_submit function
                            success = assignment_submit(
                                student_id=student_id,
                                course_id=course_id,
                                session_id=session['session_id'],
                                assignment_id=assignment['id'],
                                file_name=uploaded_file.name,
                                file_content=uploaded_file,
                                text_content=text_content,
                                material_type="assignment"
                            )
                            
                            if success:
                                st.success("Assignment submitted successfully!")
                            else:
                                st.error("Error saving submission.")
                    # Feedback section (if assignment is completed)
                    if assignment['status'] == 'completed':
                        st.markdown("### Feedback")
                        st.info("Feedback will be provided here once the assignment is graded.")
        else:
            st.warning("No assignments found for this session.")            
                
def display_preclass_analytics(session, course_id):
    """Display pre-class analytics for faculty based on chat interaction metrics"""
    st.subheader("Pre-class Analytics")
    
    # Get all enrolled students
    # enrolled_students = list(students_collection.find({"enrolled_courses": session['course_id']}))
    enrolled_students = list(students_collection.find({
        "enrolled_courses.course_id": course_id
    }))
    # total_students = len(enrolled_students)
    
    total_students = students_collection.count_documents({
        "enrolled_courses": {
            "$elemMatch": {"course_id": course_id}
        }
    })


    if total_students == 0:
        st.warning("No students enrolled in this course.")
        return
    
    # Get chat history for all students in this session
    chat_data = list(chat_history_collection.find({
        "session_id": session['session_id']
    }))
    
    # Create a DataFrame to store student completion data
    completion_data = []
    incomplete_students = []
    
    for student in enrolled_students:
        student_id = student['_id']
        student_name = student.get('full_name', 'Unknown')
        student_sid = student.get('SID', 'Unknown')
        
        # Find student's chat history
        student_chat = next((chat for chat in chat_data if chat['user_id'] == student_id), None)
        
        if student_chat:
            messages = student_chat.get('messages', [])
            message_count = len(messages)
            status = "Completed" if message_count >= 20 else "Incomplete"

            # Format chat history for display
            chat_history = []
            for msg in messages:
                timestamp_str = msg.get('timestamp', '')
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str)
                else:
                    timestamp = timestamp_str
                # timestamp = msg.get('timestamp', '').strftime("%Y-%m-%d %H:%M:%S")
                chat_history.append({
                    # 'timestamp': timestamp,
                    'timestamp': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    'prompt': msg.get('prompt'),
                    'response': msg.get('response')
                })
            
            message_count = len(student_chat.get('messages', []))
            status = "Completed" if message_count >= 20 else "Incomplete"
            if status == "Incomplete":
                incomplete_students.append({
                    'name': student_name,
                    'sid': student_sid,
                    'message_count': message_count
                })
        else:
            message_count = 0
            status = "Not Started"
            chat_history = []
            incomplete_students.append({
                'name': student_name,
                'sid': student_sid,
                'message_count': 0
            })
            
        completion_data.append({
            'Student Name': student_name,
            'SID': student_sid,
            'Messages': message_count,
            'Status': status,
            'Chat History': chat_history
        })
    
    # Create DataFrame
    df = pd.DataFrame(completion_data)
    
    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    
    completed_count = len(df[df['Status'] == 'Completed'])
    incomplete_count = len(df[df['Status'] == 'Incomplete'])
    not_started_count = len(df[df['Status'] == 'Not Started'])
    
    with col1:
        st.metric("Completed", completed_count)
    with col2:
        st.metric("Incomplete", incomplete_count)
    with col3:
        st.metric("Not Started", not_started_count)
    
    # Display completion rate progress bar
    completion_rate = (completed_count / total_students) * 100
    st.markdown("### Overall Completion Rate")
    st.progress(completion_rate / 100)
    st.markdown(f"**{completion_rate:.1f}%** of students have completed pre-class materials")

    # Create tabs for different views
    tab1, tab2 = st.tabs(["Student Overview", "Detailed Chat History"])
    
    with tab1:
        # Display completion summary table
        st.markdown("### Student Completion Details")
        summary_df = df[['Student Name', 'SID', 'Messages', 'Status']].copy()
        st.dataframe(
            summary_df.style.apply(lambda x: ['background-color: #90EE90' if v == 'Completed' 
                                            else 'background-color: #FFB6C1' if v == 'Incomplete'
                                            else 'background-color: #FFE4B5' 
                                            for v in x],
                                 subset=['Status'])
        )
        
    with tab2:
        # Display detailed chat history
        st.markdown("### Student Chat Histories")
        
        # Add student selector
        selected_student = st.selectbox(
            "Select a student to view chat history:",
            options=df['Student Name'].tolist()
        )
        
        # Get selected student's data
        student_data = df[df['Student Name'] == selected_student].iloc[0]
        print(student_data)
        chat_history = student_data['Chat History']
        # Refresh chat history when a new student is selected
        if 'selected_student' not in st.session_state or st.session_state.selected_student != selected_student:
            st.session_state.selected_student = selected_student
            st.session_state.selected_student_chat_history = chat_history
        else:
            chat_history = st.session_state.selected_student_chat_history
        # Display student info and chat statistics
        st.markdown(f"**Student ID:** {student_data['SID']}")
        st.markdown(f"**Status:** {student_data['Status']}")
        st.markdown(f"**Total Messages:** {student_data['Messages']}")
        
        


        # Display chat history in a table
        if chat_history:
            chat_df = pd.DataFrame(chat_history)
            st.dataframe(
                chat_df.style.apply(lambda x: ['background-color: #E8F0FE' if v == 'response' else 'background-color: #FFFFFF' for v in x], subset=['prompt']), use_container_width=True
            )
        else:
            st.info("No chat history available for this student.")
    
    # Display students who haven't completed
    if incomplete_students:
        st.markdown("### Students Requiring Follow-up")
        incomplete_df = pd.DataFrame(incomplete_students)
        st.markdown(f"**{len(incomplete_students)} students** need to complete the pre-class materials:")
        
        # Create a styled table for incomplete students
        st.table(
            incomplete_df.style.apply(lambda x: ['background-color: #FFFFFF' 
                                               for _ in range(len(x))]))
        
        # Export option for incomplete students list
        csv = incomplete_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download Follow-up List",
            csv,
            "incomplete_students.csv",
            "text/csv",
            key='download-csv'
        )

def display_inclass_analytics(session, course_id):
    """Display in-class analytics for faculty"""
    st.subheader("In-class Analytics")
    
    # Get all enrolled students count for participation rate calculation
    total_students = students_collection.count_documents({
        "enrolled_courses": {
            "$elemMatch": {"course_id": course_id}
        }
    })
    
    if total_students == 0:
        st.warning("No students enrolled in this course.")
        return
    
    # Get all polls for this session
    polls = polls_collection.find({
        "session_id": session['session_id']
    })
    
    polls_list = list(polls)
    if not polls_list:
        st.warning("No polls have been conducted in this session yet.")
        return
    
    # Overall Poll Participation Metrics
    st.markdown("### Overall Poll Participation")
    
    # Calculate overall participation metrics
    total_polls = len(polls_list)
    participating_students = set()
    poll_participation_data = []
    
    for poll in polls_list:
        respondents = set(poll.get('respondents', []))
        participating_students.update(respondents)
        poll_participation_data.append({
            'Poll Title': poll.get('question', 'Untitled Poll'),
            'Respondents': len(respondents),
            'Participation Rate': (len(respondents) / total_students * 100)
        })
    
    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Polls Conducted", total_polls)
    with col2:
        st.metric("Active Participants", len(participating_students))
    with col3:
        avg_participation = sum(p['Participation Rate'] for p in poll_participation_data) / total_polls
        st.metric("Average Participation Rate", f"{avg_participation:.1f}%")
    
    # Participation Trend Graph
    # st.markdown("### Poll Participation Trends")
    # participation_df = pd.DataFrame(poll_participation_data)
    
    # # Create line chart for participation trends
    # fig = px.line(participation_df, 
    #               x='Poll Title', 
    #               y='Participation Rate',
    #               title='Poll Participation Rates Over Time',
    #               markers=True)
    # fig.update_layout(
    #     xaxis_title="Polls",
    #     yaxis_title="Participation Rate (%)",
    #     yaxis_range=[0, 100]
    # )
    # st.plotly_chart(fig)
    
    # Individual Poll Results
    st.markdown("### Individual Poll Results")
    
    for poll in polls_list:
        with st.expander(f"📊 {poll.get('question', 'Untitled Poll')}"):
            responses = poll.get('responses', {})
            respondents = poll.get('respondents', [])
            
            # Calculate metrics for this poll
            response_count = len(respondents)
            participation_rate = (response_count / total_students) * 100
            
            # Display poll metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Responses", response_count)
            with col2:
                st.metric("Participation Rate", f"{participation_rate:.1f}%")
            
            if responses:
                # Create DataFrame for responses
                response_df = pd.DataFrame(list(responses.items()), 
                                         columns=['Option', 'Votes'])
                response_df['Percentage'] = (response_df['Votes'] / response_df['Votes'].sum() * 100).round(1)
                
                # Display response distribution
                fig = px.bar(response_df, 
                           x='Option', 
                           y='Votes',
                           title='Response Distribution',
                           text='Percentage')
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                st.plotly_chart(fig)
                
                # Display detailed response table
                st.markdown("#### Detailed Response Breakdown")
                response_df['Percentage'] = response_df['Percentage'].apply(lambda x: f"{x}%")
                st.table(response_df)
            
            # Non-participating students
            non_participants = list(students_collection.find({
                "courses": course_id,
                "_id": {"$nin": respondents}
            }))
            
            


            if non_participants:
                st.markdown("#### Students Who Haven't Participated")
                non_participant_data = [{
                    'Name': student.get('name', 'Unknown'),
                    'SID': student.get('sid', 'Unknown')
                } for student in non_participants]
                st.table(pd.DataFrame(non_participant_data))
    
    # Export functionality for participation data
    st.markdown("### Export Analytics")
    
    if st.button("Download Poll Analytics Report"):
        # Create a more detailed DataFrame for export
        export_data = []
        for poll in polls_list:
            poll_data = {
                'Poll Question': poll.get('question', 'Untitled'),
                'Total Responses': len(poll.get('respondents', [])),
                'Participation Rate': f"{(len(poll.get('respondents', [])) / total_students * 100):.1f}%"
            }
            # Add response distribution
            for option, votes in poll.get('responses', {}).items():
                poll_data[f"Option: {option}"] = votes
            export_data.append(poll_data)
        
        export_df = pd.DataFrame(export_data)
        csv = export_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Complete Report",
            csv,
            "poll_analytics.csv",
            "text/csv",
            key='download-csv'
        )
    

def display_postclass_analytics(session, course_id):
    """Display post-class analytics for faculty"""
    st.subheader("Post-class Analytics")
    
    # Get all assignments for this session
    session_data = courses_collection2.find_one(
        {"sessions.session_id": session['session_id']},
        {"sessions.$": 1}
    )
    
    if not session_data or 'sessions' not in session_data:
        st.warning("No assignments found for this session.")
        return
    
    assignments = session_data['sessions'][0].get('post_class', {}).get('assignments', [])
    
    for assignment in assignments:
        with st.expander(f"📝 Assignment: {assignment.get('title', 'Untitled')}"):
            # Get submission analytics
            submissions = assignment.get('submissions', [])
            # total_students = students_collection.count_documents({"courses": session['course_id']})
            total_students = students_collection.count_documents({
                "enrolled_courses": {
                    "$elemMatch": {"course_id": course_id}
                }
            })
            # Calculate submission metrics
            submitted_count = len(submissions)
            submission_rate = (submitted_count / total_students) * 100 if total_students > 0 else 0
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Submissions Received", submitted_count)
            with col2:
                st.metric("Submission Rate", f"{submission_rate:.1f}%")
            with col3:
                st.metric("Pending Submissions", total_students - submitted_count)
            
            # Display submission timeline
            if submissions:
                submission_dates = [sub.get('submitted_at') for sub in submissions if 'submitted_at' in sub]
                if submission_dates:
                    df = pd.DataFrame(submission_dates, columns=['Submission Date'])
                    fig = px.histogram(df, x='Submission Date', 
                                     title='Submission Timeline',
                                     labels={'Submission Date': 'Date', 'count': 'Number of Submissions'})
                    st.plotly_chart(fig)
            
            # Display submission status breakdown
            status_counts = {
                'pending': total_students - submitted_count,
                'submitted': submitted_count,
                'late': len([sub for sub in submissions if sub.get('is_late', False)])
            }
            
            st.markdown("### Submission Status Breakdown")
            status_df = pd.DataFrame(list(status_counts.items()), 
                                   columns=['Status', 'Count'])
            st.bar_chart(status_df.set_index('Status'))
            
            # List of students who haven't submitted
            if status_counts['pending'] > 0:
                st.markdown("### Students with Pending Submissions")
                # submitted_ids = [sub.get('student_id') for sub in submissions]
                submitted_ids = [ObjectId(sub.get('student_id')) for sub in submissions]
                print(submitted_ids)
                pending_students = students_collection.find({
                    "enrolled_courses.course_id": course_id,
                    "_id": {"$nin": submitted_ids}
                })
                print(pending_students)
                for student in pending_students:
                    st.markdown(f"- {student.get('full_name', 'Unknown Student')} (SID: {student.get('SID', 'Unknown SID')})")

def get_chat_history(user_id, session_id):
    query = {
        "user_id": ObjectId(user_id),
        "session_id": session_id,
        "timestamp": {"$lte": datetime.utcnow()}
    }
    result = chat_history_collection.find(query)
    return list(result)

def get_response_from_llm(raw_data):
    messages = [
        {
            "role": "system",
            "content": "You are an AI that refines raw analytics data into actionable insights for faculty reports."
        },
        {
            "role": "user",
            "content": f"""
            Based on the following analytics data, refine and summarize the insights:

            Raw Data:
            {raw_data}

            Instructions:
            1. Group similar topics together under appropriate categories.
            2. Remove irrelevant or repetitive entries.
            3. Summarize the findings into actionable insights.
            4. Provide concise recommendations for improvement based on the findings.

            Output:
            Provide a structured response with the following format:
            {{
            "Low Engagement Topics": ["List of Topics"],
            "Frustration Areas": ["List of areas"],
            "Recommendations": ["Actionable recommendations"],
            }}
            """
        }
    ]
    try:
        client = OpenAI(api_key=OPENAI_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2
        )
        content = response.choices[0].message.content
        return json.loads(content) 
    
    except Exception as e:
        st.error(f"Error generating response: {str(e)}")
        return None

def get_preclass_analytics(session):
    """Get all user_ids from chat_history collection where session_id matches"""
    user_ids = chat_history_collection.distinct("user_id", {"session_id": session['session_id']})
    print(user_ids)
    session_id = session['session_id']

    all_chat_histories = []

    for user_id in user_ids:
        result = get_chat_history(user_id, session_id)
        if result:
            for record in result:
                chat_history = {
                    "user_id": record["user_id"],
                    "session_id": record["session_id"],
                    "messages": record["messages"]
                }
                all_chat_histories.append(chat_history)
        else:
            st.warning("No chat history found for this session.")
    
    # Use the analytics engine
    analytics_engine = NovaScholarAnalytics()
    results = analytics_engine.process_chat_history(all_chat_histories)
    faculty_report = analytics_engine.generate_faculty_report(results)
    
    # Pass this Faculty Report to an LLM model for refinements and clarity
    refined_report = get_response_from_llm(faculty_report)
    return refined_report

def display_preclass_analytics2(session, course_id):
    refined_report = get_preclass_analytics(session)
    st.subheader("Pre-class Analytics")
    if refined_report:
        # Custom CSS to improve the look and feel
        st.markdown("""
            <style>
            .metric-card {
                background-color: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .header-text {
                color: #1f77b4;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 20px;
            }
            .subheader {
                color: #2c3e50;
                font-size: 17px;
                font-weight: 500;
                margin-bottom: 10px;
            }
            .insight-text {
                color: #34495e;
                font-size: 16px;
                line-height: 1.6;
            }
            .glossary-card {
                padding: 15px;
                margin-top: 40px;
            }
            </style>
        """, unsafe_allow_html=True)

        # Header
        # st.markdown("<h1 style='text-align: center; color: #2c3e50;'>Pre-Class Analytics Dashboard</h1>", unsafe_allow_html=True)
        # st.markdown("<p style='text-align: center; color: #7f8c8d;'>Insights from Student Interactions</p>", unsafe_allow_html=True)
        
        # Create three columns for metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("<p class='header-text'>🎯 Low Engagement Topics</p>", unsafe_allow_html=True)
            
            # Group topics by category
            topics = refined_report["Low Engagement Topics"]
            # categories = defaultdict(list)
            for i, topic in enumerate(topics):
                st.markdown(f"{i + 1}.  <p class='subheader'>{topic}</p>", unsafe_allow_html=True)

            # # Categorize topics (you can modify these categories based on your needs)
            # for topic in topics:
            #     if "Data" in topic and ("Type" in topic or "Structure" in topic):
            #         categories["Data Types"].append(topic)
            #     elif "Analytics" in topic:
            #         categories["Analytics Concepts"].append(topic)
            #     else:
            #         categories["General Concepts"].append(topic)
            
            # Display categorized topics
            # for category, items in categories.items():
            #     st.markdown(f"<p class='subheader'>{category}</p>", unsafe_allow_html=True)
            #     i = 0
            #     for i, item in items:
            #         st.markdown(f"{i + 1} {item}", unsafe_allow_html=True)

        with col2:
            st.markdown("<p class='header-text'>⚠️ Frustration Areas</p>", unsafe_allow_html=True)
            for i, area in enumerate(refined_report["Frustration Areas"]):
                st.markdown(f"{i + 1}.  <p class='subheader'>{area}</p>", unsafe_allow_html=True)

        with col3:
            st.markdown("<p class='header-text'>💡 Recommendations</p>", unsafe_allow_html=True)
            for i, rec in enumerate(refined_report["Recommendations"]):
                st.markdown(f"{i + 1}.  <p class='subheader'>{rec}</p>", unsafe_allow_html=True)

        # Glossary section
        st.markdown("<div class='glossary-card'>", unsafe_allow_html=True)
        # st.markdown("<h3 style='color: #2c3e50;'>Understanding the Metrics</h3>", unsafe_allow_html=True)
        
        explanations = {
            "Low Engagement Topics": "Topics where students showed minimal interaction or understanding during their chat sessions. These areas may require additional focus during classroom instruction.",
            "Frustration Areas": "Specific concepts or topics where students expressed difficulty or confusion during their interactions with the chatbot. These areas may need immediate attention or alternative teaching approaches.",
            "Recommendations": "AI-generated suggestions for improving student engagement and understanding, based on the analyzed chat interactions and identified patterns."
        }
        
        st.subheader("Understanding the Metrics")

        for metric, explanation in explanations.items():
            # st.markdown(f"<p class='subheader'>{metric}</p>", unsafe_allow_html=True)
            # st.markdown(f"<p class='insight-text'>{explanation}</p>", unsafe_allow_html=True)
            st.markdown(f"<span class='subheader'>**{metric}**</span>:  <span class='subheader'>{explanation}</span>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)


def display_session_analytics(session, course_id):
    """Display session analytics for faculty"""
    st.header("Session Analytics")

    # Display Pre-class Analytics
    display_preclass_analytics2(session, course_id)

    # Display In-class Analytics
    display_inclass_analytics(session, course_id)

    # Display Post-class Analytics
    display_postclass_analytics(session, course_id)





def upload_preclass_materials(session_id, course_id):
    """Upload pre-class materials for a session"""
    st.subheader("Upload Pre-class Materials")
    
    # File upload section
    uploaded_file = st.file_uploader("Upload Material", type=['txt', 'pdf', 'docx'])
    if uploaded_file is not None:
        with st.spinner("Processing document..."):
            file_name = uploaded_file.name
            file_content = extract_text_from_file(uploaded_file)
            if file_content:
                material_type = st.selectbox("Select Material Type", ["pdf", "docx", "txt"])
                if st.button("Upload Material"):
                    upload_resource(course_id, session_id, file_name, uploaded_file, material_type)

                    # Search for the newly uploaded resource's _id in resources_collection
                    resource_id = resources_collection.find_one({"file_name": file_name})["_id"]
                    create_vector_store(file_content, resource_id)
                    st.success("Material uploaded successfully!")
                    
    # Display existing materials
    materials = resources_collection.find({"course_id": course_id, "session_id": session_id})
    for material in materials:
        st.markdown(f"""
        * **{material['file_name']}** ({material['material_type']})  
            Uploaded on: {material['uploaded_at'].strftime('%Y-%m-%d %H:%M')}
        """)

def display_quiz_tab(student_id, course_id, session_id):
    """Display quizzes for students"""
    st.header("Course Quizzes")
    
    # Get available quizzes for this session
    quizzes = quizzes_collection.find({
        "course_id": course_id,
        "session_id": session_id,
        "status": "active"
    })
    
    quizzes = list(quizzes)
    if not quizzes:
        st.info("No quizzes available for this session.")
        return
    
    for quiz in quizzes:
        with st.expander(f"📝 {quiz['title']}", expanded=True):
            # Check if student has already taken this quiz
            existing_score = get_student_quiz_score(quiz['_id'], student_id)
            
            if existing_score is not None:
                st.success(f"Quiz completed! Your score: {existing_score:.1f}%")
                
                # Display correct answers after submission
                st.subheader("Quiz Review")
                for i, question in enumerate(quiz['questions']):
                    st.markdown(f"**Question {i+1}:** {question['question']}")
                    for opt in question['options']:
                        if opt.startswith(question['correct_option']):
                            st.markdown(f"✅ {opt}")
                        else:
                            st.markdown(f"- {opt}")
                
            else:
                # Display quiz questions
                st.write("Please select your answers:")
                
                # Create a form for quiz submission
                with st.form(f"quiz_form_{quiz['_id']}"):
                    student_answers = {}
                    
                    for i, question in enumerate(quiz['questions']):
                        st.markdown(f"**Question {i+1}:** {question['question']}")
                        options = [opt for opt in question['options']]
                        student_answers[str(i)] = st.radio(
                            f"Select answer for question {i+1}:",
                            options=options,
                            key=f"q_{quiz['_id']}_{i}"
                        )
                    
                    # Submit button
                    if st.form_submit_button("Submit Quiz"):
                        print(student_answers)
                        score = submit_quiz_answers(quiz['_id'], student_id, student_answers)
                        if score is not None:
                            st.success(f"Quiz submitted successfully! Your score: {score:.1f}%")
                            st.rerun()  # Refresh to show results
                        else:
                            st.error("Error submitting quiz. Please try again.")

def display_session_content(student_id, course_id, session, username, user_type):
    st.title(f"{session['title']}")

    # Check if the date is a string or a datetime object
    if isinstance(session['date'], str):
        # Convert date string to datetime object
        session_date = datetime.fromisoformat(session['date'])
    else:
        session_date = session['date']

    course_name = courses_collection2.find_one({"course_id": course_id})['title']
    
    st.markdown(f"**Date:** {format_datetime(session_date)}")
    st.markdown(f"**Course Name:** {course_name}")

    # Find the course_id of the session in 

    if st.session_state.user_type == 'student':
        tabs = (["Pre-class Work", "In-class Work", "Post-class Work"])
    else:
        tabs = (["Session Analytics"])

    if st.session_state.user_type == 'student':
        pre_class_tab, in_class_tab, post_class_tab, quiz_tab = st.tabs(["Pre-class Work", "In-class Work", "Post-class Work", "Quizzes"])
    else:
        pre_class_work, in_class_work, post_class_work, preclass_analytics, inclass_analytics, postclass_analytics = st.tabs(["Pre-class Work", "In-class Work", "Post-class Work", "Pre-class Analytics", "In-class Analytics", "Post-class Analytics"])
        # pre_class_work, in_class_work, post_class_work, session_analytics = st.tabs(["Pre-class Work", "In-class Work", "Post-class Work", "Session Analytics"])
    # Display pre-class materials
    if st.session_state.user_type == 'student':
        with pre_class_tab:
            display_preclass_content(session, student_id, course_id)
        with in_class_tab:
            display_in_class_content(session, st.session_state.user_type)
        
        # Post-class Content
        with post_class_tab:
            display_post_class_content(session, student_id, course_id)
        with quiz_tab:
            display_quiz_tab(student_id, course_id, session['session_id'])

    if st.session_state.user_type == 'faculty':
        with pre_class_work:
            upload_preclass_materials(session['session_id'], course_id)
        with in_class_work:
            display_in_class_content(session, st.session_state.user_type)
        with post_class_work:
            display_post_class_content(session, student_id, course_id)
        with preclass_analytics:
            display_preclass_analytics2(session, course_id)
        with inclass_analytics:
            display_inclass_analytics(session, course_id)
        with postclass_analytics:
            display_postclass_analytics(session, course_id)
        # with session_analytics: 
        #     display_session_analytics(session, course_id)
