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
# from pre_class_analytics import NovaScholarAnalytics
from pre_class_analytics2 import NovaScholarAnalytics
import openai
from openai import OpenAI
import google.generativeai as genai
from goals2 import GoalAnalyzer
from openai import OpenAI
import asyncio
import numpy as np
import re
from analytics import derive_analytics, create_embeddings, cosine_similarity

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_KEY')
client = MongoClient(MONGO_URI)
db = client["novascholar_db"]
polls_collection = db["polls"]
subjective_tests_collection = db["subjective_tests"]
synoptic_store_collection = db["synoptic_store"]

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
    print("Session ID is: ", session['session_id'])
    # Display pre-class materials
    materials = resources_collection.find({"session_id": session['session_id']})
    for material in materials:
        with st.expander(f"{material['file_name']} ({material['material_type'].upper()})"):
            file_type = material.get('file_type', 'unknown')
            if file_type == 'application/pdf':
                st.markdown(f"📑 [Open PDF Document]({material['file_name']})")
                if st.button("View PDF", key=f"view_pdf_{material['_id']}"):
                    st.text_area("PDF Content", material['text_content'], height=300)
                if st.button("Download PDF", key=f"download_pdf_{material['_id']}"):
                    st.download_button(
                        label="Download PDF",
                        data=material['file_content'],
                        file_name=material['file_name'],
                        mime='application/pdf'
                    )
                if st.button("Mark PDF as Read", key=f"pdf_{material['_id']}"):
                    create_notification("PDF marked as read!", "success")
            elif file_type == 'text/plain':
                st.markdown(f"📄 [Open Text Document]({material['file_name']})")
                if st.button("View Text", key=f"view_text_{material['_id']}"):
                    st.text_area("Text Content", material['text_content'], height=300)
                if st.button("Download Text", key=f"download_text_{material['_id']}"):
                    st.download_button(
                        label="Download Text",
                        data=material['file_content'],
                        file_name=material['file_name'],
                        mime='text/plain'
                    )
                if st.button("Mark Text as Read", key=f"text_{material['_id']}"):
                    create_notification("Text marked as read!", "success")
            elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                st.markdown(f"📄 [Open Word Document]({material['file_name']})")
                if st.button("View Word", key=f"view_word_{material['_id']}"):
                    st.text_area("Word Content", material['text_content'], height=300)
                if st.button("Download Word", key=f"download_word_{material['_id']}"):
                    st.download_button(
                        label="Download Word",
                        data=material['file_content'],
                        file_name=material['file_name'],
                        mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    )
                if st.button("Mark Word as Read", key=f"word_{material['_id']}"):
                    create_notification("Word document marked as read!", "success")
            elif file_type == 'application/vnd.openxmlformats-officedocument.presentationml.presentation':
                st.markdown(f"📊 [Open PowerPoint Presentation]({material['file_name']})")
                if st.button("View PowerPoint", key=f"view_pptx_{material['_id']}"):
                    st.text_area("PowerPoint Content", material['text_content'], height=300)
                if st.button("Download PowerPoint", key=f"download_pptx_{material['_id']}"):
                    st.download_button(
                        label="Download PowerPoint",
                        data=material['file_content'],
                        file_name=material['file_name'],
                        mime='application/vnd.openxmlformats-officedocument.presentationml.presentation'
                    )
                if st.button("Mark PowerPoint as Read", key=f"pptx_{material['_id']}"):
                    create_notification("PowerPoint presentation marked as read!", "success")

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
                print("Session ID is: ", session['session_id'])
                materials = resources_collection.find({"session_id": session['session_id']})
                print(materials)
                context = ""
                vector_data = None

                # for material in materials:
                #     print(material)
                context = ""
                for material in materials:
                    resource_id = material['_id']
                    print("Supposed Resource ID is: ", resource_id)
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
                    # context_prompt = f"""
                    # You are a highly intelligent and resourceful assistant capable of synthesizing information from the provided context. 

                    # Context:
                    # {context}

                    # Instructions:
                    # 1. Base your answers primarily on the given context. 
                    # 2. If the answer to the user's question is not explicitly in the context but can be inferred or synthesized from the information provided, do so thoughtfully.
                    # 3. Only use external knowledge or web assistance when:
                    # - The context lacks sufficient information, and
                    # - The question requires knowledge beyond what can be reasonably inferred from the context.
                    # 4. Clearly state if you are relying on web assistance for any part of your answer.
                    # 5. Do not respond with a negative. If the answer is not in the context, provide a thoughtful response based on the information available on the web about it.

                    # Question: {prompt}

                    # Please provide a clear and comprehensive answer based on the above instructions.
                    # """
                    context_prompt = f"""
                    You are a highly intelligent and resourceful assistant capable of synthesizing information from the provided context and external sources.

                    Context:
                    {context}

                    Instructions:
                    1. Base your answers on the provided context wherever possible.
                    2. If the answer to the user's question is not explicitly in the context:
                    - Use external knowledge or web assistance to provide a clear and accurate response.
                    3. Do not respond negatively. If the answer is not in the context, use web assistance or your knowledge to generate a thoughtful response.
                    4. Clearly state if part of your response relies on web assistance.

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
                        upload_resource(course_id, session['session_id'], file_name, uploaded_file, material_type)
                        # print("Resource ID is: ", resource_id)
                        # Search for the newly uploaded resource's _id in resources_collection
                        # resource_id = resources_collection.find_one({"file_name": file_name})["_id"]
                        st.success("Material uploaded successfully!")
                        # st.experimental_rerun()

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
        faculty_id = st.session_state.user_id
        st.subheader("Create Subjective Test")
        
        # Create a form for test generation
        with st.form("create_subjective_test_form"):
            test_title = st.text_input("Test Title")
            num_subjective_questions = st.number_input("Number of Subjective Questions", min_value=1, value=5)
            generation_method = st.radio(
                "Question Generation Method",
                ["Generate from Pre-class Materials", "Generate Random Questions"]
            )
            generate_test_btn = st.form_submit_button("Generate Test")

        # Handle test generation outside the form
        if generate_test_btn:
            if not test_title:
                st.error("Please enter a test title.")
                return

            context = ""
            if generation_method == "Generate from Pre-class Materials":
                materials = resources_collection.find({"session_id": session['session_id']})
                for material in materials:
                    if 'text_content' in material:
                        context += material['text_content'] + "\n"

            with st.spinner("Generating questions and synoptic..."):
                try:
                    # Store generated content in session state to persist between rerenders
                    questions = generate_questions(
                        context if context else None,
                        num_subjective_questions,
                        session['title'],
                        session.get('description', '')
                    )
                    
                    if questions:
                        synoptic = generate_synoptic(
                            questions,
                            context if context else None,
                            session['title'],
                            num_subjective_questions
                        )
                        
                        if synoptic:
                            # Store in session state
                            st.session_state.generated_questions = questions
                            st.session_state.generated_synoptic = synoptic
                            st.session_state.test_title = test_title
                            
                            # Display preview
                            st.subheader("Preview Subjective Questions and Synoptic")
                            for i, (q, s) in enumerate(zip(questions, synoptic), 1):
                                st.markdown(f"**Question {i}:** {q['question']}")
                                with st.expander(f"View Synoptic {i}"):
                                    st.markdown(s)
                            
                            # Save button outside the form
                            if st.button("Save Test"):
                                test_id = save_subjective_test(
                                    course_id,
                                    session['session_id'],
                                    test_title,
                                    questions,
                                    synoptic
                                )
                                if test_id:
                                    st.success("Subjective test saved successfully!")
                                else:
                                    st.error("Error saving subjective test.")
                        else:
                            st.error("Error generating synoptic answers. Please try again.")
                    else:
                        st.error("Error generating questions. Please try again.")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

        # Display previously generated test if it exists in session state
        elif hasattr(st.session_state, 'generated_questions') and hasattr(st.session_state, 'generated_synoptic'):
            st.subheader("Preview Subjective Questions and Synoptic")
            for i, (q, s) in enumerate(zip(st.session_state.generated_questions, st.session_state.generated_synoptic), 1):
                st.markdown(f"**Question {i}:** {q['question']}")
                with st.expander(f"View Synoptic {i}"):
                    st.markdown(s)
            
            if st.button("Save Test"):
                test_id = save_subjective_test(
                    course_id,
                    session['session_id'],
                    st.session_state.test_title,
                    st.session_state.generated_questions,
                    st.session_state.generated_synoptic
                )
                if test_id:
                    st.success("Subjective test saved successfully!")
                    # Clear session state after successful save
                    del st.session_state.generated_questions
                    del st.session_state.generated_synoptic
                    del st.session_state.test_title
                else:
                    st.error("Error saving subjective test.")

        # st.subheader("Create quiz section UI for faculty")
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
                    quiz_id = save_quiz(course_id, session['session_id'], quiz_title, questions, faculty_id)
                    if quiz_id:
                        st.success("Quiz saved successfully!")
                    else:
                        st.error("Error saving quiz.")

        st.subheader("Add Assignments")
        # Add assignment form
        with st.form("add_assignment_form"):
            title = st.text_input("Assignment Title")
            due_date = st.date_input("Due Date")
            submit = st.form_submit_button("Add Assignment")
            
            if submit:
                due_date = datetime.combine(due_date, datetime.min.time())
                # Save the assignment to the database
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
        client = OpenAI(api_key=OPENAI_API_KEY)
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

import typing_extensions as typing 
from typing import Union, List, Dict

# class Topics(typing.TypedDict):
#     overarching_theme: List[Dict[str, Union[str, List[Dict[str, Union[str, List[str]]]]]]]
#     indirect_topics: List[Dict[str, str]]

def extract_topics_from_materials(session):
    """Extract topics from pre-class materials"""
    materials = resources_collection.find({"session_id": session['session_id']})
    texts = ""
    if materials:
        for material in materials:
            if 'text_content' in material:
                text = material['text_content']
                texts += text + "\n"
            else:
                st.warning("No text content found in the material.")
                return
    else:
        st.error("No pre-class materials found for this session.")
        return

    if texts:
        context_prompt = f"""
        Task: Extract Comprehensive Topics in a List Format
        You are tasked with analyzing the provided text content and extracting a detailed, flat list of topics.

        Instructions:
        Identify All Topics: Extract a comprehensive list of all topics, subtopics, and indirect topics present in the provided text content. This list should include:

        Overarching themes
        Main topics
        Subtopics and their sub-subtopics
        Indirectly related topics
        Flat List Format: Provide a flat list where each item is a topic. Ensure topics at all levels (overarching, main, sub, sub-sub, indirect) are represented as individual entries in the list.

        Be Exhaustive: Ensure the response captures every topic, subtopic, and indirectly related concept comprehensively.

        Output Requirements:
        Use this structure:
        {{
            "topics": [
                "Topic 1",
                "Topic 2",
                "Topic 3",
                ...
            ]
        }}
        Do Not Include: Do not include backticks, hierarchical structures, or the word 'json' in your response.

        Content to Analyze:
        {texts}
        """
        try:
            # response = model.generate_content(context_prompt, generation_config=genai.GenerationConfig(response_mime_type="application/json", response_schema=list[Topics]))
            response = model.generate_content(context_prompt, generation_config=genai.GenerationConfig(temperature=0.3))
            if not response or not response.text:
                st.error("Error extracting topics from materials.")
                return
            
            topics = response.text
            return topics
        except Exception as e:
            st.error(f"Error extracting topics: {str(e)}")
            return None
    else:
        st.error("No text content found in the pre-class materials.")
        return None

def convert_json_to_dict(json_str):
    try:
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Error converting JSON to dictionary. {str(e)}")
        return None

# Load topics from a JSON file
# topics = []
# with open(r'topics.json', 'r') as file:
#     topics = json.load(file)

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
    

    # Pass the pre-class materials content to the analytics engine
    topics = extract_topics_from_materials(session)
    # dict_topics = convert_json_to_dict(topics)
    print(topics)
    
    # # Use the 1st analytics engine
    # analytics_engine = NovaScholarAnalytics(all_topics_list=topics)
    # # extracted_topics = analytics_engine._extract_topics(None, topics)
    # # print(extracted_topics)

    # results = analytics_engine.process_chat_history(all_chat_histories)
    # faculty_report = analytics_engine.generate_faculty_report(results)
    # print(faculty_report)
    # # Pass this Faculty Report to an LLM model for refinements and clarity
    # refined_report = get_response_from_llm(faculty_report)
    # return refined_report

    # Use the 2nd analytice engine (using LLM): 
    fallback_analytics = {
        "topic_insights": [],
            "student_insights": [],
            "recommended_actions": [
                {
                    "action": "Review analytics generation process",
                    "priority": "high",
                    "target_group": "system_administrators",
                    "reasoning": "Analytics generation failed",
                    "expected_impact": "Restore analytics functionality"
                }
            ],
            "course_health": {
                "overall_engagement": 0,
                "critical_topics": [],
                "class_distribution": {
                    "high_performers": 0,
                    "average_performers": 0,
                    "at_risk": 0
                }
            },
            "intervention_metrics": {
                "immediate_attention_needed": [],
                "monitoring_required": []
            }
    }
    analytics_generator = NovaScholarAnalytics()
    analytics2 = analytics_generator.generate_analytics(all_chat_histories, topics)
    # enriched_analytics = analytics_generator._enrich_analytics(analytics2)
    print("Analytics is: ", analytics2)
    
    if analytics2 == fallback_analytics:
        return None
    else:
        return analytics2
    # print(json.dumps(analytics, indent=2))


# Load Analytics from a JSON file
# analytics = []
# with open(r'new_analytics2.json', 'r') as file:
#     analytics = json.load(file)

def display_preclass_analytics2(session, course_id):
    # Initialize or get analytics data from session state
    if 'analytics_data' not in st.session_state:
        st.session_state.analytics_data = get_preclass_analytics(session)

    analytics = st.session_state.analytics_data
    
    print(analytics)
    # Enhanced CSS for better styling and interactivity
    st.markdown("""
        <style>
        /* General styles */
        .section-title {
            color: #1a237e;
            font-size: 1.5rem;
            font-weight: 600;
            margin-top: 1rem 0 1rem 0;
        }
        
        /* Topic list styles */
        .topic-list {
            max-width: 800px;
            margin: 0 auto;
        }
        .topic-header {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin: 0.5rem 0;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.2s ease;
        }
        .topic-header:hover {
            background-color: #f8fafc;
            transform: translateX(5px);
        }
        .topic-header h3 {
            color: #1e3a8a;
            font-size: 1.1rem;
            font-weight: 500;
            margin: 0;
        }
        .topic-struggling-rate {
            background-color: #dbeafe;
            padding: 0.25rem 0.75rem;
            border-radius: 16px;
            font-size: 0.85rem;
            color: #1e40af;
        }
        .topic-content {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-top: none;
            border-radius: 0 0 8px 8px;
            padding: 1.25rem;
            margin-top: -0.5rem;
            margin-bottom: 1rem;
        }
        .topic-content .section-heading {
            color: #2c5282;
            font-size: 1rem;
            font-weight: 600;
            margin: 1rem 0 0.5rem 0;
        }
        .topic-content ul {
            margin: 0;
            padding-left: 1.25rem;
            font-size: 0.85rem;
            color: #4a5568;
        }
        
        /* Recommendation card styles */
        .recommendation-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        .recommendation-card {
            background-color: #f8fafc;
            border-radius: 8px;
            padding: 1.25rem;
            border-left: 4px solid #3b82f6;
            margin-bottom: 1rem;
        }
        .recommendation-card h4 {
            color: #1e40af;
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .recommendation-card .priority-badge {
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            background-color: #dbeafe;
            color: #1e40af;
            text-transform: uppercase;
        }
        
        /* Student analytics styles */
        .student-filters {
            background-color: #f8fafc;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        .analytics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        .student-metrics-card {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 1rem;
            border: 1px solid #e5e7eb;
            margin-bottom: 1rem;
        }
        .student-metrics-card .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }
        .student-metrics-card .student-id {
            color: #1e40af;
            font-size: 1rem;
            font-weight: 600;
        }
        .student-metrics-card .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
        }
        .metric-box {
            background-color: #f8fafc;
            padding: 0.75rem;
            border-radius: 6px;
        }
        .metric-box .label {
            font-size: 0.9rem;
            color: #6b7280;
            margin-bottom: 0.25rem;
            font-weight: 500;
        }
        .metric-box .value {
            font-size: 0.9rem;
            color: #1f2937;
            font-weight: 600;
        }
        .struggling-topics {
            grid-column: span 2;
            margin-top: 0.5rem;
        }
        .struggling-topics .label{
            font-size: 0.9rem;
            font-weight: 600;        
        }
        .struggling-topics .value{
            font-size: 0.9rem;
            font-weight: 500;        
        }
        .recommendation-text {
            grid-column: span 2;
            font-size: 0.95rem;
            color: #4b5563;
            margin-top: 0.75rem;
            padding-top: 0.75rem;
            border-top: 1px solid #e5e7eb;
        }
        .reason{
            font-size: 1rem;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)

    # Topic-wise Analytics Section
    st.markdown('<h2 class="section-title">Topic-wise Analytics</h2>', unsafe_allow_html=True)
    
    # Initialize session state for topic expansion
    if 'expanded_topic' not in st.session_state:
        st.session_state.expanded_topic = None
    
    # Store topic indices in session state if not already done
    if 'topic_indices' not in st.session_state:
        st.session_state.topic_indices = list(range(len(analytics["topic_wise_insights"])))

    if st.session_state.topic_indices: 
        st.markdown('<div class="topic-list">', unsafe_allow_html=True)
        for idx in st.session_state.topic_indices:
            topic = analytics["topic_wise_insights"][idx]
            topic_id = f"topic_{idx}"
            
            # Create clickable header
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(
                    topic["topic"],
                    key=f"topic_button_{idx}",
                    use_container_width=True,
                    type="secondary"
                ):
                    st.session_state.expanded_topic = topic_id if st.session_state.expanded_topic != topic_id else None
            
            with col2:
                st.markdown(f"""
                    <div style="text-align: right;">
                        <span class="topic-struggling-rate">{topic["struggling_percentage"]*100:.1f}% Struggling</span>
                    </div>
                """, unsafe_allow_html=True)
            
            # Show content if topic is expanded
            if st.session_state.expanded_topic == topic_id:
                st.markdown(f"""
                    <div class="topic-content">
                        <div class="section-heading">Key Issues</div>
                        <ul>
                            {"".join([f"<li>{issue}</li>" for issue in topic["key_issues"]])}
                        </ul>
                        <div class="section-heading">Key Misconceptions</div>
                        <ul>
                            {"".join([f"<li>{misc}</li>" for misc in topic["key_misconceptions"]])}
                        </ul>
                    </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # AI Recommendations Section
        st.markdown('<h2 class="section-title">AI-Powered Recommendations</h2>', unsafe_allow_html=True)
        st.markdown('<div class="recommendation-grid">', unsafe_allow_html=True)
        for idx, rec in enumerate(analytics["ai_recommended_actions"]):
            st.markdown(f"""
                <div class="recommendation-card">
                    <h4>
                        <span>Recommendation {idx + 1}</span>
                        <span class="priority-badge">{rec["priority"]}</span>
                    </h4>
                    <p>{rec["action"]}</p>
                    <p><span class="reason">Reason:</span>  {rec["reasoning"]}</p>
                    <p><span class="reason">Expected Outcome:</span>  {rec["expected_outcome"]}</p>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Student Analytics Section
        st.markdown('<h2 class="section-title">Student Analytics</h2>', unsafe_allow_html=True)
        
        # Filters
        with st.container():
            # st.markdown('<div class="student-filters">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                concept_understanding = st.selectbox(
                    "Filter by Understanding",
                    ["All", "Strong", "Moderate", "Needs Improvement"]
                )
            with col2:
                participation_level = st.selectbox(
                    "Filter by Participation",
                    ["All", "High (>80%)", "Medium (50-80%)", "Low (<50%)"]
                )
            with col3:
                struggling_topic = st.selectbox(
                    "Filter by Struggling Topic",
                    ["All"] + list(set([topic for student in analytics["student_analytics"] 
                                    for topic in student["struggling_topics"]]))
                )
            # st.markdown('</div>', unsafe_allow_html=True)

        # Display student metrics in a grid
        st.markdown('<div class="analytics-grid">', unsafe_allow_html=True)
        for student in analytics["student_analytics"]:
            # Apply filters
            if (concept_understanding != "All" and 
                student["engagement_metrics"]["concept_understanding"].replace("_", " ").title() != concept_understanding):
                continue
                
            participation = student["engagement_metrics"]["participation_level"] * 100
            if participation_level != "All":
                if participation_level == "High (>80%)" and participation <= 80:
                    continue
                elif participation_level == "Medium (50-80%)" and (participation < 50 or participation > 80):
                    continue
                elif participation_level == "Low (<50%)" and participation >= 50:
                    continue
                    
            if struggling_topic != "All" and struggling_topic not in student["struggling_topics"]:
                continue

            st.markdown(f"""
                <div class="student-metrics-card">
                    <div class="header">
                        <span class="student-id">Student {student["student_id"][-6:]}</span>
                    </div>
                    <div class="metrics-grid">
                        <div class="metric-box">
                            <div class="label">Participation</div>
                            <div class="value">{student["engagement_metrics"]["participation_level"]*100:.1f}%</div>
                        </div>
                        <div class="metric-box">
                            <div class="label">Understanding</div>
                            <div class="value">{student["engagement_metrics"]["concept_understanding"].replace('_', ' ').title()}</div>
                        </div>
                        <div class="struggling-topics">
                            <div class="label">Struggling Topics: </div>
                            <div class="value">{", ".join(student["struggling_topics"]) if student["struggling_topics"] else "None"}</div>
                        </div>
                        <div class="recommendation-text">
                            {student["personalized_recommendation"]}
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def reset_analytics_state():
    """
    Helper function to reset the analytics state when needed
    (e.g., when loading a new session or when data needs to be refreshed)
    """
    if 'analytics_data' in st.session_state:
        del st.session_state.analytics_data
    if 'expanded_topic' in st.session_state:
        del st.session_state.expanded_topic
    if 'topic_indices' in st.session_state:
        del st.session_state.topic_indice

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

def display_subjective_test_tab(student_id, course_id, session_id):
    """Display subjective tests for students"""
    st.header("Subjective Tests")
    
    try:
        subjective_tests = list(subjective_tests_collection.find({
            "course_id": course_id,
            "session_id": session_id,
            "status": "active"
        }))

        if not subjective_tests:
            st.info("No subjective tests available for this session.")
            return

        for test in subjective_tests:
            with st.expander(f"📝 {test['title']}", expanded=True):
                # Check for existing submission
                existing_submission = next(
                    (sub for sub in test.get('submissions', []) 
                     if sub['student_id'] == str(student_id)), 
                    None
                )
                
                if existing_submission:
                    st.success("Test completed! Your answers have been submitted.")
                    st.subheader("Your Answers")
                    for i, ans in enumerate(existing_submission['answers']):
                        st.markdown(f"**Question {i+1}:** {test['questions'][i]['question']}")
                        st.markdown(f"**Your Answer:** {ans}")
                        st.markdown("---")
                else:
                    st.write("Please write your answers:")
                    with st.form(key=f"subjective_test_form_{test['_id']}"):
                        student_answers = []
                        for i, question in enumerate(test['questions']):
                            st.markdown(f"**Question {i+1}:** {question['question']}")
                            answer = st.text_area(
                                "Your answer:",
                                key=f"q_{test['_id']}_{i}",
                                height=200
                            )
                            student_answers.append(answer)

                        if st.form_submit_button("Submit Test"):
                            if all(answer.strip() for answer in student_answers):
                                success = submit_subjective_test(
                                    test['_id'],
                                    str(student_id),
                                    student_answers
                                )
                                if success:
                                    st.success("Test submitted successfully!")
                                    st.rerun()
                                else:
                                    st.error("Error submitting test. Please try again.")
                            else:
                                st.error("Please answer all questions before submitting.")
                                
    except Exception as e:
        st.error(f"An error occurred while loading the tests. Please try again later.")
        print(f"Error in display_subjective_test_tab: {str(e)}", flush=True)

def display_session_content(student_id, course_id, session, username, user_type):
    st.title(f"{session['title']}")

    # Check if the date is a string or a datetime object
    if isinstance(session['date'], str):
        # Convert date string to datetime object
        session_date = datetime.fromisoformat(session['date'])
    else:
        session_date = session['date']

    course_name = courses_collection.find_one({"course_id": course_id})['title']
    
    st.markdown(f"**Date:** {format_datetime(session_date)}")
    st.markdown(f"**Course Name:** {course_name}")

    # Find the course_id of the session in 

    if user_type == 'student':
        # Create all tabs at once for students
        tabs = st.tabs([
            "Pre-class Work",
            "In-class Work", 
            "Post-class Work",
            "Quizzes",
            "Subjective Tests",
            "Group Work",
            "End Terms"
        ])
        if len(tabs) <= 7:
            with tabs[0]:
                display_preclass_content(session, student_id, course_id)
            with tabs[1]:
                display_in_class_content(session, user_type)
            with tabs[2]:
                display_post_class_content(session, student_id, course_id)
            with tabs[3]:
                display_quiz_tab(student_id, course_id, session['session_id'])
            with tabs[4]:
                display_subjective_test_tab(student_id, course_id, session['session_id'])
            with tabs[5]:
                st.subheader("Group Work")
                st.info("Group work content will be available soon.")
            with tabs[6]:
                st.subheader("End Terms")
                st.info("End term content will be available soon.")
        else:
            st.error("Error creating tabs. Please try again.")
    
    else:  # faculty user
        # Create all tabs at once for faculty
        tabs = st.tabs([
            "Pre-class Work",
            "In-class Work",
            "Post-class Work",
            "Pre-class Analytics",
            "In-class Analytics",
            "Post-class Analytics",
            "End Terms"
        ])
        with tabs[0]:
            upload_preclass_materials(session['session_id'], course_id)
        with tabs[1]:
            display_in_class_content(session, user_type)
        with tabs[2]:
            display_post_class_content(session, student_id, course_id)
        with tabs[3]:
            display_preclass_analytics(session, course_id)
        with tabs[4]:
            display_inclass_analytics(session, course_id)
        with tabs[5]:
            display_postclass_analytics(session, course_id)
        with tabs[6]:
            st.subheader("End Terms")
            st.info("End term content will be available soon.")

def parse_model_response(response_text):
    """Enhanced parser for model responses with better error handling.
    
    Args:
        response_text (str): Raw response text from the model
        
    Returns:
        dict or list: Parsed response object
        
    Raises:
        ValueError: If parsing fails
    """
    import json
    import ast
    import re
    
    # Remove markdown formatting and whitespace
    cleaned_text = re.sub(r'```[a-zA-Z]*\n', '', response_text)
    cleaned_text = cleaned_text.replace('```', '').strip()
    
    # Try multiple parsing methods
    parsing_methods = [
        # Method 1: Direct JSON parsing
        lambda x: json.loads(x),
        
        # Method 2: AST literal evaluation
        lambda x: ast.literal_eval(x),
        
        # Method 3: Extract and parse content between curly braces
        lambda x: json.loads(re.search(r'\{.*\}', x, re.DOTALL).group()),
        
        # Method 4: Extract and parse content between square brackets
        lambda x: json.loads(re.search(r'\[.*\]', x, re.DOTALL).group()),
        
        # Method 5: Try to fix common JSON formatting issues and parse
        lambda x: json.loads(x.replace("'", '"').replace('\n', '\\n'))
    ]
    
    last_error = None
    for parse_method in parsing_methods:
        try:
            result = parse_method(cleaned_text)
            if result:  # Ensure we have actual content
                return result
        except Exception as e:
            last_error = e
            continue
            
    raise ValueError(f"Could not parse the model's response: {last_error}")

def generate_questions(context, num_questions, session_title, session_description):
    """Generate subjective questions based on context or session details"""
    try:
        # Construct the prompt
        prompt = f"""You are a professional educator creating {num_questions} subjective questions.
        
        Topic: {session_title}
        Description: {session_description}
        {'Context: ' + context if context else ''}
        
        Generate exactly {num_questions} questions in this specific format:
        [
            {{"question": "Write your first question here?"}},
            {{"question": "Write your second question here?"}}
        ]
        
        Requirements:
        1. Questions must require detailed explanations
        2. Focus on critical thinking and analysis
        3. Ask for specific examples or case studies
        4. Questions should test deep understanding
        
        IMPORTANT: Return ONLY the JSON array. Do not include any additional text or explanations.
        """

        # Generate response
        response = model.generate_content(prompt)
        questions = parse_model_response(response.text)
        
        # Validate response
        if not isinstance(questions, list):
            raise ValueError("Generated content is not a list")
        
        if len(questions) != num_questions:
            raise ValueError(f"Generated {len(questions)} questions instead of {num_questions}")
            
        # Validate each question
        for q in questions:
            if not isinstance(q, dict) or 'question' not in q:
                raise ValueError("Invalid question format")
        
        return questions

    except Exception as e:
        print(f"Error generating questions: {str(e)}")
        return None

def generate_synoptic(questions, context, session_title, num_questions):
    """Generate synoptic answers for the questions with improved error handling and response validation.
    
    Args:
        questions (list): List of question dictionaries
        context (str): Additional context for answer generation
        session_title (str): Title of the session
        num_questions (int): Expected number of questions
        
    Returns:
        list: List of synoptic answers or None if generation fails
    """
    try:
        # First, let's validate our input
        if not questions or not isinstance(questions, list):
            raise ValueError("Questions must be provided as a non-empty list")
            
        # Format questions for better prompt clarity
        formatted_questions = "\n".join(
            f"{i+1}. {q['question']}" 
            for i, q in enumerate(questions)
        )
        
        # Construct a more structured prompt
        prompt = f"""You are a subject matter expert creating detailed model answers for {num_questions} questions about {session_title}.

        Here are the questions:
        {formatted_questions}
        {f'Additional context: {context}' if context else ''}

        Please provide {num_questions} comprehensive answers following this JSON format:
        {{
            "answers": [
                {{
                    "answer": "Your detailed answer for question 1...",
                    "key_points": ["Point 1", "Point 2", "Point 3"]
                }},
                {{
                    "answer": "Your detailed answer for question 2...",
                    "key_points": ["Point 1", "Point 2", "Point 3"]
                }}
            ]
        }}

        Requirements for each answer:
        1. Minimum 150 words
        2. Include specific examples and evidence
        3. Reference key concepts and terminology
        4. Demonstrate critical analysis
        5. Structure with clear introduction, body, and conclusion

        IMPORTANT: Return ONLY the JSON object with the answers array. No additional text.
        """

        # Generate response
        response = model.generate_content(prompt)
        
        # Parse and validate the response
        parsed_response = parse_model_response(response.text)
        
        # Additional validation of parsed response
        if not isinstance(parsed_response, (dict, list)):
            raise ValueError("Response must be a dictionary or list")
            
        # Handle both possible valid response formats
        if isinstance(parsed_response, dict):
            answers = parsed_response.get('answers', [])
        else:  # If it's a list
            answers = parsed_response
        
        # Validate answer count
        if len(answers) != num_questions:
            raise ValueError(f"Expected {num_questions} answers, got {len(answers)}")
        
        # Extract just the answer texts for consistency with existing code
        final_answers = []
        for ans in answers:
            if isinstance(ans, dict):
                answer_text = ans.get('answer', '')
                key_points = ans.get('key_points', [])
                formatted_answer = f"{answer_text}\n\nKey Points:\n" + "\n".join(f"• {point}" for point in key_points)
                final_answers.append(formatted_answer)
            else:
                final_answers.append(str(ans))
        
        # Final validation of the answers
        for i, answer in enumerate(final_answers):
            if not answer or len(answer.split()) < 50:  # Basic length check
                raise ValueError(f"Answer {i+1} is too short or empty")
        
        # Save the synoptic to the synoptic_store collection
        synoptic_data = {
            "session_title": session_title,
            "questions": questions,
            "synoptic": final_answers,
            "created_at": datetime.utcnow()
        }
        synoptic_store_collection.insert_one(synoptic_data)
        
        return final_answers

    except Exception as e:
        # Log the error for debugging
        print(f"Error in generate_synoptic: {str(e)}")
        print(f"Response text: {response.text if 'response' in locals() else 'No response generated'}")
        return None

def save_subjective_test(course_id, session_id, title, questions, synoptic):
    """Save subjective test to database"""
    try:
        # Format questions to include metadata
        formatted_questions = []
        for q in questions:
            formatted_question = {
                "question": q["question"],
                "expected_points": q.get("expected_points", []),
                "difficulty_level": q.get("difficulty_level", "medium"),
                "suggested_time": q.get("suggested_time", "5 minutes")
            }
            formatted_questions.append(formatted_question)

        test_data = {
            "course_id": course_id,
            "session_id": session_id,
            "title": title,
            "questions": formatted_questions,
            "synoptic": synoptic,
            "created_at": datetime.utcnow(),
            "status": "active",
            "submissions": []
        }
        
        result = subjective_tests_collection.insert_one(test_data)
        return result.inserted_id
    except Exception as e:
        print(f"Error saving subjective test: {e}")
        return None

def submit_subjective_test(test_id, student_id, student_answers):
    """Submit subjective test answers and trigger analysis"""
    try:
        submission_data = {
            "student_id": student_id,
            "answers": student_answers,
            "submitted_at": datetime.utcnow()
        }
        
        result = subjective_tests_collection.update_one(
            {"_id": test_id},
            {
                "$push": {
                    "submissions": submission_data
                }
            }
        )
        
        if result.modified_count > 0:
            try:
                # Trigger grading and analysis
                analysis = analyze_subjective_answers(test_id, student_id)
                if analysis:
                    # Update the submission with the analysis and score
                    subjective_tests_collection.update_one(
                        {"_id": test_id, "submissions.student_id": student_id},
                        {
                            "$set": {
                                "submissions.$.analysis": analysis,
                                "submissions.$.score": analysis.get('correctness_score')
                            }
                        }
                    )
                    return True
                else:
                    print("Error: Analysis failed")
                    return False
            except Exception as e:
                print(f"Warning: Grading failed but submission was saved: {e}")
                return True  # We still return True since the submission itself was successful
            
        print("Error: No document was modified")
        return False
        
    except Exception as e:
        print(f"Error submitting subjective test: {str(e)}")
        return False

def analyze_subjective_answers(test_id, student_id):
    """Analyze subjective test answers for correctness and improvements"""
    try:
        # Get test and submission details
        test_doc = subjective_tests_collection.find_one({"_id": test_id})
        if not test_doc:
            print(f"Test document not found for test_id: {test_id}")
            return None
            
        submission = next(
            (sub for sub in test_doc.get('submissions', []) if sub['student_id'] == student_id),
            None
        )
        
        if not submission:
            print(f"No submission found for student_id: {student_id}")
            return None
        
        # Get questions and answers
        questions = test_doc.get('questions', [])
        student_answers = submission.get('answers', [])
        
        if not questions or not student_answers:
            print("No questions or answers found")
            return None
            
        # Retrieve the synoptic from the synoptic_store collection
        synoptic_doc = synoptic_store_collection.find_one({"session_title": test_doc.get('title')})
        synoptic = synoptic_doc.get('synoptic', '') if synoptic_doc else ''
        
        # Analyze each question separately
        all_analyses = []
        total_score = 0
        
        for i, (question, answer) in enumerate(zip(questions, student_answers), 1):
            # Format content for individual question
            analysis_content = f"Question {i}: {question['question']}\nAnswer: {answer}\n\n"
            
            # Get analysis for this question
            individual_analysis = derive_analytics(
                goal="Analyze and Grade",
                reference_text=analysis_content,
                openai_api_key=OPENAI_API_KEY,
                context=test_doc.get('context', ''),
                synoptic=synoptic[i-1] if isinstance(synoptic, list) else synoptic
            )
            
            if individual_analysis:
                # Extract score for this question
                try:
                    score_match = re.search(r'(\d+)(?:/10)?', individual_analysis)
                    if score_match:
                        question_score = int(score_match.group(1))
                        if 1 <= question_score <= 10:
                            total_score += question_score
                except:
                    question_score = 0
                
                # Format individual analysis
                formatted_analysis = f"\n\n## Question {i} Analysis\n\n{individual_analysis}"
                all_analyses.append(formatted_analysis)
        
        if not all_analyses:
            print("Error: No analyses generated")
            return None
            
        # Calculate average score
        average_score = round(total_score / len(questions)) if questions else 0
        
        # Combine all analyses
        combined_analysis = "\n".join(all_analyses)
        
        # Format final results
        analysis_results = {
            "content_analysis": combined_analysis,
            "analyzed_at": datetime.utcnow(),
            "correctness_score": average_score
        }
        
        return analysis_results
        
    except Exception as e:
        print(f"Error in analyze_subjective_answers: {str(e)}")
        return None

def display_subjective_test_tab(student_id, course_id, session_id):
    """Display subjective tests for students"""
    st.header("Subjective Tests")
    
    try:
        # Query for active tests
        subjective_tests = list(subjective_tests_collection.find({
            "course_id": course_id,
            "session_id": session_id,
            "status": "active"
        }))

        if not subjective_tests:
            st.info("No subjective tests available for this session.")
            return

        for test in subjective_tests:
            with st.expander(f"📝 {test['title']}", expanded=True):
                # Check for existing submission
                existing_submission = next(
                    (sub for sub in test.get('submissions', []) 
                     if sub['student_id'] == str(student_id)), 
                    None
                )
                
                if existing_submission:
                    st.success("Test completed! Your answers have been submitted.")
                    st.subheader("Your Answers")
                    for i, ans in enumerate(existing_submission['answers']):
                        st.markdown(f"**Question {i+1}:** {test['questions'][i]['question']}")
                        st.markdown(f"**Your Answer:** {ans}")
                        st.markdown("---")
                    
                    # Display analysis
                    display_subjective_analysis(test['_id'], str(student_id), test.get('context', ''))
                else:
                    st.write("Please write your answers:")
                    with st.form(key=f"subjective_test_form_{test['_id']}"):
                        student_answers = []
                        for i, question in enumerate(test['questions']):
                            st.markdown(f"**Question {i+1}:** {question['question']}")
                            answer = st.text_area(
                                "Your answer:",
                                key=f"q_{test['_id']}_{i}",
                                height=200
                            )
                            student_answers.append(answer)

                        if st.form_submit_button("Submit Test"):
                            if all(answer.strip() for answer in student_answers):
                                success = submit_subjective_test(
                                    test['_id'],
                                    str(student_id),
                                    student_answers
                                )
                                if success:
                                    st.success("Test submitted successfully!")
                                    st.rerun()
                                else:
                                    st.error("Error submitting test. Please try again.")
                            else:
                                st.error("Please answer all questions before submitting.")
    except Exception as e:
        print(f"Error in display_subjective_test_tab: {str(e)}", flush=True)
        st.error("An error occurred while loading the tests. Please try again later.")
    
def display_subjective_analysis(test_id, student_id, context):
    """Display subjective test analysis to students and faculty"""
    try:
        test_doc = subjective_tests_collection.find_one({"_id": test_id})
        submission = next(
            (sub for sub in test_doc.get('submissions', []) if sub['student_id'] == student_id),
            None
        )
        
        if not submission:
            st.warning("No submission found for analysis.")
            return
            
        # Get or generate analysis
        analysis = submission.get('analysis')
        if not analysis:
            analysis = analyze_subjective_answers(test_id, student_id, context)
            if not analysis:
                st.error("Could not generate analysis.")
                return
        
        # Display analysis results
        st.subheader("Answer Analysis")
        
        # Content analysis
        st.markdown("### Evidence-Based Feedback")
        st.markdown(analysis.get('content_analysis', 'No analysis available'))
        
        # Improvement suggestions
        # st.markdown("### Suggested Improvements")
        # st.markdown(analysis.get('suggested_improvements', 'No suggestions available'))
        
        # Analysis timestamp
        analyzed_at = analysis.get('analyzed_at')
        if analyzed_at:
            st.caption(f"Analysis performed at: {analyzed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
    except Exception as e:
        st.error(f"Error displaying analysis: {e}")
