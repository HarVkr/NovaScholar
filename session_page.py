from collections import defaultdict
import json
import random
import requests
import streamlit as st
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
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
from bs4 import BeautifulSoup
from rubrics import display_rubrics_tab
from subjective_test_evaluation import evaluate_subjective_answers, display_evaluation_to_faculty

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_KEY')
client = MongoClient(MONGO_URI)
db = client["novascholar_db"]
polls_collection = db["polls"]
subjective_test_evaluation_collection = db["subjective_test_evaluation"]
assignment_evaluation_collection = db["assignment_evaluation"]
subjective_tests_collection = db["subjective_tests"]
synoptic_store_collection = db["synoptic_store"]
assignments_collection = db["assignments"]

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
    """Display pre-class materials for a session including external resources"""
    st.subheader("Pre-class Materials")
    print("Session ID is: ", session['session_id'])
    
    # Display uploaded materials
    materials = resources_collection.find({"session_id": session['session_id']})
    
    for material in materials:
        file_type = material.get('file_type', 'unknown')
        
        # Handle external resources
        if file_type == 'external':
            with st.expander(f"📌 {material['file_name']}"):
                st.markdown(f"Source: [{material['source_url']}]({material['source_url']})")
                
                if material['material_type'].lower() == 'video':
                    # Embed YouTube video if it's a YouTube URL
                    if 'youtube.com' in material['source_url'] or 'youtu.be' in material['source_url']:
                        video_id = extract_youtube_id(material['source_url'])
                        if video_id:
                            st.video(f"https://youtube.com/watch?v={video_id}")
                
                if st.button("View Content", key=f"view_external_{material['_id']}"):
                    st.text_area("Extracted Content", material['text_content'], height=300)
                
                if st.button("Mark as Read", key=f"external_{material['_id']}"):
                    create_notification(f"{material['material_type']} content marked as read!", "success")
        
        # Handle traditional file types
        else:
            with st.expander(f"{material['file_name']} ({material['material_type'].upper()})"):
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


def extract_youtube_id(url):
    """Extract YouTube video ID from URL"""
    if 'youtube.com' in url:
        try:
            return url.split('v=')[1].split('&')[0]
        except IndexError:
            return None
    elif 'youtu.be' in url:
        try:
            return url.split('/')[-1]
        except IndexError:
            return None
    return None


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
                                    questions
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

        st.subheader("Add Assignment")
        with st.form("add_assignment_form"):
            title = st.text_input("Assignment Title")
            description = st.text_area("Assignment Description")
            due_date = st.date_input("Due Date")
            submit = st.form_submit_button("Add Assignment")
            
            if submit:
                if not title or not description:
                    st.error("Please fill in all required fields.")
                    return
                    
                due_date = datetime.combine(due_date, datetime.min.time())
                assignment = {
                    "_id": ObjectId(),
                    "title": title,
                    "description": description,
                    "due_date": due_date,
                    "course_id": course_id,
                    "session_id": session['session_id'],
                    "faculty_id": faculty_id,
                    "created_at": datetime.utcnow(),
                    "status": "active",
                    "submissions": []
                }
                
                assignments_collection.insert_one(assignment)
                st.success("Assignment added successfully!")
                
        st.subheader("Existing Assignments")
        assignments = assignments_collection.find({
            "session_id": session['session_id'],
            "course_id": course_id
        })
        
        for assignment in assignments:
            with st.expander(f"📝 {assignment['title']}", expanded=True):
                st.markdown(f"**Due Date:** {assignment['due_date'].strftime('%Y-%m-%d')}")
                st.markdown(f"**Description:** {assignment['description']}")
                
                total_submissions = len(assignment.get('submissions', []))
                total_students = students_collection.count_documents({
                    "enrolled_courses": {
                        "$elemMatch": {"course_id": course_id}
                    }
                })
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Submissions", total_submissions)
                with col2:
                    submission_rate = (total_submissions / total_students * 100) if total_students > 0 else 0
                    st.metric("Submission Rate", f"{submission_rate:.1f}%")
                with col3:
                    st.metric("Pending Submissions", total_students - total_submissions)
                
                # Display evaluation button and status
                evaluation_status = st.empty()
                eval_button = st.button("View/Generate Evaluations", key=f"eval_{assignment['_id']}")
                
                if eval_button:
                    st.session_state.show_evaluations = True
                    st.session_state.current_assignment = assignment['_id']
                    
                    # Show evaluation interface in a new container instead of an expander
                    evaluation_container = st.container()
                    with evaluation_container:
                        from assignment_evaluation import display_evaluation_to_faculty
                        display_evaluation_to_faculty(session['session_id'], student_id, course_id)
                    
    else:  # Student view
        assignments = assignments_collection.find({
            "session_id": session['session_id'],
            "course_id": course_id,
            "status": "active"
        })
        
        for assignment in assignments:
            with st.expander(f"📝 {assignment['title']}", expanded=True):
                st.markdown(f"**Due Date:** {assignment['due_date'].strftime('%Y-%m-%d')}")
                st.markdown(f"**Description:** {assignment['description']}")
                
                existing_submission = next(
                    (sub for sub in assignment.get('submissions', []) 
                     if sub['student_id'] == str(student_id)),
                    None
                )
                
                if existing_submission:
                    st.success("Assignment submitted!")
                    st.markdown(f"**Submitted on:** {existing_submission['submitted_at'].strftime('%Y-%m-%d %H:%M')}")
                    
                    # Show evaluation status and feedback in the same container
                    evaluation = assignment_evaluation_collection.find_one({
                        "assignment_id": assignment['_id'],
                        "student_id": str(student_id)
                    })
                    
                    if evaluation:
                        st.markdown("### Evaluation")
                        st.markdown(evaluation['evaluation'])
                    else:
                        st.info("Evaluation pending. Check back later.")
                else:
                    uploaded_file = st.file_uploader(
                        "Upload your work",
                        type=['pdf', 'doc', 'docx', 'txt', 'py', 'ipynb', 'ppt', 'pptx'],
                        key=f"upload_{assignment['_id']}"
                    )
                    
                    if uploaded_file is not None:
                        if st.button("Submit Assignment", key=f"submit_{assignment['_id']}"):
                            text_content = extract_text_from_file(uploaded_file)
                            
                            submission = {
                                "student_id": str(student_id),
                                "file_name": uploaded_file.name,
                                "file_type": uploaded_file.type,
                                "file_content": uploaded_file.getvalue(),
                                "text_content": text_content,
                                "submitted_at": datetime.utcnow()
                            }
                            
                            assignments_collection.update_one(
                                {"_id": assignment['_id']},
                                {"$push": {"submissions": submission}}
                            )
                            
                            st.success("Assignment submitted successfully!")
                            st.rerun()            

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
    # Earlier Code:
    # """Get all user_ids from chat_history collection where session_id matches"""
    # user_ids = chat_history_collection.distinct("user_id", {"session_id": session['session_id']})
    # print(user_ids)
    # session_id = session['session_id']

    # all_chat_histories = []

    # for user_id in user_ids:
    #     result = get_chat_history(user_id, session_id)
    #     if result:
    #         for record in result:
    #             chat_history = {
    #                 "user_id": record["user_id"],
    #                 "session_id": record["session_id"],
    #                 "messages": record["messages"]
    #             }
    #             all_chat_histories.append(chat_history)
    #     else:
    #         st.warning("No chat history found for this session.")
    

    # # Pass the pre-class materials content to the analytics engine
    # topics = extract_topics_from_materials(session)
    # # dict_topics = convert_json_to_dict(topics)
    # print(topics)
    
    # # # Use the 1st analytics engine
    # # analytics_engine = NovaScholarAnalytics(all_topics_list=topics)
    # # # extracted_topics = analytics_engine._extract_topics(None, topics)
    # # # print(extracted_topics)

    # # results = analytics_engine.process_chat_history(all_chat_histories)
    # # faculty_report = analytics_engine.generate_faculty_report(results)
    # # print(faculty_report)
    # # # Pass this Faculty Report to an LLM model for refinements and clarity
    # # refined_report = get_response_from_llm(faculty_report)
    # # return refined_report

    # # Use the 2nd analytice engine (using LLM): 
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
    # analytics_generator = NovaScholarAnalytics()
    # analytics2 = analytics_generator.generate_analytics(all_chat_histories, topics)
    # # enriched_analytics = analytics_generator._enrich_analytics(analytics2)
    # print("Analytics is: ", analytics2)
    
    # if analytics2 == fallback_analytics:
    #     return None
    # else:
    #     return analytics2
    # # print(json.dumps(analytics, indent=2))


    # New Code:
    # Debug print 1: Check session
    print("Starting get_preclass_analytics with session:", session['session_id'])
    
    user_ids = chat_history_collection.distinct("user_id", {"session_id": session['session_id']})
    # Debug print 2: Check user_ids
    print("Found user_ids:", user_ids)
    
    all_chat_histories = []
    for user_id in user_ids:
        result = get_chat_history(user_id, session['session_id'])
        # Debug print 3: Check each chat history result
        print(f"Chat history for user {user_id}:", "Found" if result else "Not found")
        if result:
            for record in result:
                chat_history = {
                    "user_id": record["user_id"],
                    "session_id": record["session_id"],
                    "messages": record["messages"]
                }
                all_chat_histories.append(chat_history)

    # Debug print 4: Check chat histories
    print("Total chat histories collected:", len(all_chat_histories))

    # Extract topics with debug print
    topics = extract_topics_from_materials(session)
    # Debug print 5: Check topics
    print("Extracted topics:", topics)
    
    if not topics:
        print("Topics extraction failed")  # Debug print 6
        return None

    analytics_generator = NovaScholarAnalytics()
    analytics2 = analytics_generator.generate_analytics(all_chat_histories, topics)
    # Debug print 7: Check analytics
    print("Generated analytics:", analytics2)
    
    if analytics2 == fallback_analytics:
        print("Fallback analytics returned")  # Debug print 8
        return None
    else:
        return analytics2

# Load Analytics from a JSON file
# analytics = []
# with open(r'new_analytics2.json', 'r') as file:
#     analytics = json.load(file)

def display_preclass_analytics2(session, course_id):
    # Earlier Code:
    # Initialize or get analytics data from session state
    # if 'analytics_data' not in st.session_state:
    #     st.session_state.analytics_data = get_preclass_analytics(session)

    # analytics = st.session_state.analytics_data
    
    # print(analytics)


    # New Code:
    # Initialize or get analytics data from session state
    if 'analytics_data' not in st.session_state:
        # Add debug prints
        analytics_data = get_preclass_analytics(session)
        if analytics_data is None:
            st.info("Fetching new analytics data...")
        if analytics_data is None:
            st.error("Failed to generate analytics. Please check the following:")
            st.write("1. Ensure pre-class materials contain text content")
            st.write("2. Verify chat history exists for this session")
            st.write("3. Check if topic extraction was successful")
            return
        st.session_state.analytics_data = analytics_data

    analytics = st.session_state.analytics_data
    
    # Validate analytics data structure
    if not isinstance(analytics, dict):
        st.error(f"Invalid analytics data type: {type(analytics)}")
        return
        
    required_keys = ["topic_wise_insights", "ai_recommended_actions", "student_analytics"]
    missing_keys = [key for key in required_keys if key not in analytics]
    if missing_keys:
        st.error(f"Missing required keys in analytics data: {missing_keys}")
        return

    # Initialize topic indices only if we have valid data
    if 'topic_indices' not in st.session_state:
        try:
            st.session_state.topic_indices = list(range(len(analytics["topic_wise_insights"])))
        except Exception as e:
            st.error(f"Error creating topic indices: {str(e)}")
            st.write("Analytics data structure:", analytics)
            return

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
    
# def upload_preclass_materials(session_id, course_id):
#     """Upload pre-class materials for a session"""
#     st.subheader("Upload Pre-class Materials")
    
#     # File upload section
#     uploaded_file = st.file_uploader("Upload Material", type=['txt', 'pdf', 'docx'])
#     if uploaded_file is not None:
#         with st.spinner("Processing document..."):
#             file_name = uploaded_file.name
#             file_content = extract_text_from_file(uploaded_file)
#             if file_content:
#                 material_type = st.selectbox("Select Material Type", ["pdf", "docx", "txt"])
#                 if st.button("Upload Material"):
#                     upload_resource(course_id, session_id, file_name, uploaded_file, material_type)

#                     # Search for the newly uploaded resource's _id in resources_collection
#                     resource_id = resources_collection.find_one({"file_name": file_name})["_id"]
#                     create_vector_store(file_content, resource_id)
#                     st.success("Material uploaded successfully!")
                    
#     # Display existing materials
#     materials = resources_collection.find({"course_id": course_id, "session_id": session_id})
#     for material in materials:
#         st.markdown(f"""
#         * **{material['file_name']}** ({material['material_type']})  
#             Uploaded on: {material['uploaded_at'].strftime('%Y-%m-%d %H:%M')}
#         """)

def upload_preclass_materials(session_id, course_id):
    """Upload pre-class materials and manage external resources for a session"""
    st.subheader("Pre-class Materials Management")
    
    # Create tabs for different functionalities
    upload_tab, external_tab = st.tabs(["Upload Materials", "External Resources"])
    
    with upload_tab:
        # Original file upload functionality
        uploaded_file = st.file_uploader("Upload Material", type=['txt', 'pdf', 'docx'])
        if uploaded_file is not None:
            with st.spinner("Processing document..."):
                file_name = uploaded_file.name
                file_content = extract_text_from_file(uploaded_file)
                if file_content:
                    material_type = st.selectbox("Select Material Type", ["pdf", "docx", "txt"])
                    if st.button("Upload Material"):
                        upload_resource(course_id, session_id, file_name, uploaded_file, material_type)
                        st.success("Material uploaded successfully!")
    
    with external_tab:
        # Fetch and display external resources
        session_data = courses_collection.find_one(
            {"course_id": course_id, "sessions.session_id": session_id},
            {"sessions.$": 1}
        )
        
        if session_data and session_data.get('sessions'):
            session = session_data['sessions'][0]
            external = session.get('external_resources', {})
            
            # Display web articles
            if 'readings' in external:
                st.subheader("Web Articles and Videos")
                for reading in external['readings']:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{reading['title']}**")
                        st.markdown(f"Type: {reading['type']} | Est. time: {reading['estimated_read_time']}")
                        st.markdown(f"URL: [{reading['url']}]({reading['url']})")
                    with col2:
                        if st.button("Extract Content", key=f"extract_{reading['url']}"):
                            with st.spinner("Extracting content..."):
                                content = extract_external_content(reading['url'], reading['type'])
                                if content:
                                    resource_id = upload_external_resource(
                                        course_id,
                                        session_id,
                                        reading['title'],
                                        content,
                                        reading['type'].lower(),
                                        reading['url']
                                    )
                                    st.success("Content extracted and stored successfully!")
            
            # Display books
            if 'books' in external:
                st.subheader("Recommended Books")
                for book in external['books']:
                    st.markdown(f"""
                    **{book['title']}** by {book['author']}
                    - ISBN: {book['isbn']}
                    - Chapters: {book['chapters']}
                    """)
            
            # Display additional resources
            if 'additional_resources' in external:
                st.subheader("Additional Resources")
                for resource in external['additional_resources']:
                    st.markdown(f"""
                    **{resource['title']}** ({resource['type']})
                    - {resource['description']}
                    - URL: [{resource['url']}]({resource['url']})
                    """)

def extract_external_content(url, content_type):
    """Extract content from external resources based on their type"""
    try:
        if content_type.lower() == 'video' and 'youtube.com' in url:
            return extract_youtube_transcript(url)
        else:
            return extract_web_article(url)
    except Exception as e:
        st.error(f"Error extracting content: {str(e)}")
        return None

def extract_youtube_transcript(url):
    """Extract transcript from YouTube videos"""
    try:
        # Extract video ID from URL
        video_id = url.split('v=')[1].split('&')[0]
        
        # Get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        # Combine transcript text
        full_text = ' '.join([entry['text'] for entry in transcript])
        return full_text
    except Exception as e:
        st.error(f"Could not extract YouTube transcript: {str(e)}")
        return None

def extract_web_article(url):
    """Extract text content from web articles"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted tags
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        # Extract text from paragraphs
        paragraphs = soup.find_all('p')
        text_content = ' '.join([p.get_text().strip() for p in paragraphs])
        
        return text_content
    except Exception as e:
        st.error(f"Could not extract web article content: {str(e)}")
        return None

def upload_external_resource(course_id, session_id, title, content, content_type, source_url):
    """Upload extracted external resource content to the database"""
    resource_data = {
        "_id": ObjectId(),
        "course_id": course_id,
        "session_id": session_id,
        "file_name": f"{title} ({content_type})",
        "file_type": "external",
        "text_content": content,
        "material_type": content_type,
        "source_url": source_url,
        "uploaded_at": datetime.utcnow()
    }
    
    # Check if resource already exists
    existing_resource = resources_collection.find_one({
        "session_id": session_id,
        "source_url": source_url
    })
    
    if existing_resource:
        return existing_resource["_id"]
    
    # Insert new resource
    resources_collection.insert_one(resource_data)
    resource_id = resource_data["_id"]
    
    # Update course document
    courses_collection.update_one(
        {
            "course_id": course_id,
            "sessions.session_id": session_id
        },
        {
            "$push": {"sessions.$.pre_class.resources": resource_id}
        }
    )
    
    if content:
        create_vector_store(content, resource_id)
    
    return resource_id

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
        session_date = datetime.fromisoformat(session['date'])
    else:
        session_date = session['date']

    course_name = courses_collection.find_one({"course_id": course_id})['title']
    
    st.markdown(f"**Date:** {format_datetime(session_date)}")
    st.markdown(f"**Course Name:** {course_name}")

    if user_type == 'student':
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
                display_subjective_test_tab(student_id, course_id, session['session_id'])  # Added this line
            with tabs[5]:
                #display_group_work_tab(session, student_id)
                st.info("End term content will be available soon.")
            with tabs[6]:
                st.subheader("End Terms")
                st.info("End term content will be available soon.")
    else:  # faculty user
        tabs = st.tabs([
            "Pre-class Work",
            "In-class Work",
            "Post-class Work",
            "Pre-class Analytics",
            "In-class Analytics",
            "Post-class Analytics",
            "Rubrics",
            "End Terms",
            "Evaluate Subjective Tests"  # New tab for evaluation
        ])
        with tabs[0]:
            upload_preclass_materials(session['session_id'], course_id)
        with tabs[1]:
            display_in_class_content(session, user_type)
        with tabs[2]:
            display_post_class_content(session, student_id, course_id)
        with tabs[3]:
            display_preclass_analytics2(session, course_id)
        with tabs[4]:
            display_inclass_analytics(session, course_id)
        with tabs[5]:
            display_postclass_analytics(session, course_id)
        with tabs[6]:
            display_rubrics_tab(session, course_id)
        with tabs[7]:
            st.subheader("End Terms")
            st.info("End term content will be available soon.")
        with tabs[8]:  # New tab for evaluation
            display_evaluation_to_faculty(session['session_id'], student_id, course_id)

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

def save_subjective_test(course_id, session_id, title, questions):
    """Save subjective test to database with proper ID handling"""
    try:
        # Ensure proper string format for IDs
        course_id = str(course_id)
        session_id = str(session_id)
        
        # Format questions
        formatted_questions = []
        for q in questions:
            formatted_question = {
                "question": q["question"],
                "expected_points": [],
                "difficulty_level": "medium",
                "suggested_time": "5 minutes"
            }
            formatted_questions.append(formatted_question)

        test_data = {
            "course_id": course_id,
            "session_id": session_id,
            "title": title,
            "questions": formatted_questions,
            "created_at": datetime.utcnow(),
            "status": "active",
            "submissions": []
        }
        
        result = subjective_tests_collection.insert_one(test_data)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error saving test: {e}")
        return None

def submit_subjective_test(test_id, student_id, answers):
    """Submit test answers with proper ID handling"""
    try:
        # Ensure IDs are strings
        test_id = str(test_id)
        student_id = str(student_id)
        
        # Create submission document
        submission = {
            "student_id": student_id,
            "answers": answers,
            "submitted_at": datetime.utcnow(),
            "status": "submitted"
        }
        
        # Update test document with new submission
        result = subjective_tests_collection.update_one(
            {"_id": ObjectId(test_id)},
            {"$push": {"submissions": submission}}
        )
        
        return result.modified_count > 0
    except Exception as e:
        print(f"Error submitting test: {e}")
        return False

def display_subjective_test_tab(student_id, course_id, session_id):
    """Display subjective tests and results for students"""
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

        # Create tabs for Tests and Results
        test_tab, results_tab = st.tabs(["Available Tests", "Test Results"])
        
        with test_tab:
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
        
        with results_tab:
            # Display results for completed tests
            completed_tests = [
                test for test in subjective_tests
                if any(sub['student_id'] == str(student_id) for sub in test.get('submissions', []))
            ]
            
            if not completed_tests:
                st.info("You haven't completed any tests yet.")
                return
                
            # Create a selectbox for choosing which test results to view
            test_options = {
                f"{test['title']} (Submitted: {next(sub['submitted_at'].strftime('%Y-%m-%d') for sub in test['submissions'] if sub['student_id'] == str(student_id))})"
                : test['_id']
                for test in completed_tests
            }
            
            selected_test = st.selectbox(
                "Select a test to view results:",
                options=list(test_options.keys())
            )
            
            if selected_test:
                test_id = test_options[selected_test]
                display_test_results(test_id, student_id)
                
    except Exception as e:
        st.error("An error occurred while loading the tests. Please try again later.")
        print(f"Error in display_subjective_test_tab: {str(e)}")
        
def display_test_results(test_id, student_id):
    """
    Display test results and analysis for a student
    
    Args:
        test_id: ObjectId or str of the test
        student_id: str of the student ID
    """
    try:
        # Fetch analysis from evaluation collection
        analysis = subjective_test_evaluation_collection.find_one({
            "test_id": test_id,
            "student_id": str(student_id)
        })
        
        if not analysis:
            st.info("Analysis will be available soon. Please check back later.")
            return
            
        st.header("Test Analysis")
        
        # Display overall evaluation summary if available
        if "overall_summary" in analysis:
            with st.expander("Overall Performance Summary", expanded=True):
                st.markdown(analysis["overall_summary"])
                
        # Display individual question evaluations
        st.subheader("Question-wise Analysis")
        for eval_item in analysis.get('evaluations', []):
            with st.expander(f"Question {eval_item['question_number']}", expanded=True):
                st.markdown("**Question:**")
                st.markdown(eval_item['question'])
                
                st.markdown("**Your Answer:**")
                st.markdown(eval_item['answer'])
                
                st.markdown("**Evaluation:**")
                st.markdown(eval_item['evaluation'])
                
                # Extract and display score if available
                if "Score:" in eval_item['evaluation']:
                    score_line = next((line for line in eval_item['evaluation'].split('\n') if "Score:" in line), None)
                    if score_line:
                        score = score_line.split("Score:")[1].strip()
                        st.metric("Score", score)
                
                # Display improvement points if available
                if "Key Areas for Improvement" in eval_item['evaluation']:
                    st.markdown("**Areas for Improvement:**")
                    improvement_section = eval_item['evaluation'].split("Key Areas for Improvement")[1]
                    points = [point.strip('- ').strip() for point in improvement_section.split('\n') if point.strip().startswith('-')]
                    for point in points:
                        if point:  # Only display non-empty points
                            st.markdown(f"• {point}")
                
        # Display evaluation timestamp
        if "evaluated_at" in analysis:
            st.caption(f"Analysis generated on: {analysis['evaluated_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
    except Exception as e:
        st.error("An error occurred while loading the analysis. Please try again later.")
        print(f"Error in display_test_results: {str(e)}")