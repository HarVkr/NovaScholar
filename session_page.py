import streamlit as st
from datetime import datetime
from utils.sample_data import SAMPLE_CHAT_HISTORY, SAMPLE_STUDENT_PROGRESS
from utils.helpers import display_progress_bar, create_notification, format_datetime
from utils.sample_data import SAMPLE_SESSIONS, SAMPLE_COURSES
from file_upload_vectorize import upload_resource, extract_text_from_file, create_vector_store, resources_collection, model, assignment_submit
from db import courses_collection2, chat_history_collection, students_collection, faculty_collection, vectors_collection
from chatbot import insert_chat_message
from bson import ObjectId
from live_polls import LivePollFeature

def get_current_user():
    if 'current_user' not in st.session_state:
        return None
    return students_collection.find_one({"_id": st.session_state.user_id})

def display_preclass_content(session, student_id):
    """Display pre-class materials for a session"""
    st.subheader("Pre-class Materials")
    
    # Display progress bar
    # progress = SAMPLE_STUDENT_PROGRESS.get(st.session_state.username, {}).get(session['session_id'], {}).get('pre_class', 0)
    # display_progress_bar(progress, 100, "Pre-class completion")

    # for resource in session['pre_class']['resources']:
    #     with st.expander(f"{resource['title']} ({resource['type'].upper()})"):
    #         if resource['type'] == 'pdf':
    #             st.markdown(f"📑 [Open PDF Document]({resource['url']})")
    #             if st.button("Mark PDF as Read", key=f"pdf_{resource['title']}"):
    #                 create_notification("PDF marked as read!", "success")
                    
    #         elif resource['type'] == 'video':
    #             st.markdown(f"🎥 Video Duration: {resource['duration']}")
    #             col1, col2 = st.columns([3, 1])
    #             with col1:
    #                 st.video("https://example.com/placeholder.mp4")
    #             with col2:
    #                 if st.button("Mark Video Complete", key=f"video_{resource['title']}"):
    #                     create_notification("Video marked as complete!", "success")
                        
    #         elif resource['type'] == 'reading':
    #             st.markdown(f"📖 Reading Assignment: Pages {resource['pages']}")
    #             if st.button("Mark Reading Complete", key=f"reading_{resource['title']}"):
    #                 create_notification("Reading marked as complete!", "success")
            
    #         st.markdown("---")
    #         st.markdown("**Notes:**")
    #         notes = st.text_area("Add your notes here", key=f"notes_{resource['title']}")
    #         if st.button("Save Notes", key=f"save_notes_{resource['title']}"):
    #             create_notification("Notes saved successfully!", "success")

    # Display pre-class materials
    print(f"student_id: {type(student_id)}")

    materials = resources_collection.find({"session_id": session['session_id']})
    print(f"materials: {type(materials)}")
    for material in materials:
        print(f"material: {type(material)}")
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

    user = get_current_user()
    print(f"user: {type(user)}")

    user = get_current_user()
    
    # Chat input
    # Add a check, if materials are available, only then show the chat input
    if(st.session_state.user_type == "student"):
        if materials:
            if prompt := st.chat_input("Ask a question about Pre-class Materials"):
                if len(st.session_state.messages) >= 20:
                    st.warning("Message limit (20) reached for this session.")
                    return

                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # Display User Message
                with st.chat_message("user"):
                    st.markdown(prompt)

                # Get document context
                context = ""
                materials = resources_collection.find({"session_id": session['session_id']})
                context = ""
                vector_data = None

                context = ""
                for material in materials:
                    resource_id = material['_id']
                    vector_data = vectors_collection.find_one({"resource_id": resource_id})
                    if vector_data and 'text' in vector_data:
                        context += vector_data['text'] + "\n"

                if not vector_data:
                    st.error("No Pre-class materials found for this session.")
                    return
                
                try:
                    # Generate response using Gemini
                    context_prompt = f"""
                    Based on the following context, answer the user's question:
                    
                    Context:
                    {context}
                    
                    Question: {prompt}
                    
                    Please provide a clear and concise answer based only on the information provided in the context.
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
    
    st.subheader("Your Chat History")
    # Initialize chat messages from database
    if 'messages' not in st.session_state:
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

def display_post_class_content(session, student_id, course_id):
    """Display post-class assignments and submissions"""
    st.header("Post-class Work")
    
    if st.session_state.user_type == 'faculty':
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
        # assignments += courses_collection2.find_one(
        #     {"course_id": course_id, "sessions.session_id": session['session_id']},
        #     {"sessions.$.post_class.assignments": 1}
        # )["sessions"][0]["post_class"]["assignments"]
        session_data = courses_collection2.find_one(
            {"course_id": course_id, "sessions.session_id": session['session_id']},
            {"sessions.$": 1}
        )
        assignments = session_data["sessions"][0]["post_class"]["assignments"]
        print(assignments)
        for assignment in assignments:
            with st.expander(f"Assignment: {assignment['title']}", expanded=True):
                st.markdown(f"**Due Date:** {assignment['due_date']}")
                st.markdown(f"**Status:** {assignment['status'].replace('_', ' ').title()}")
                
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
                        # Save the file to a location and get the file URL
                        assignment_submit(student_id, course_id, session['session_id'], uploaded_file.name, uploaded_file, uploaded_file.type)
                
                        # Display submitted assignments
                        st.markdown(f"📑 [Click to view Submission]({uploaded_file['file_name']})")
                        if st.button("View PDF", key=f"view_pdf_{uploaded_file['file_name']}"):
                            st.text_area("PDF Content", uploaded_file['text_content'], height=300)
                        if st.button("Download PDF", key=f"download_pdf_{uploaded_file['file_name']}"):
                            st.download_button(
                                label="Download PDF",
                                data=uploaded_file['file_content'],
                                file_name=uploaded_file['file_name'],
                                mime='application/pdf'
                        )

                # Feedback section (if assignment is completed)
                if assignment['status'] == 'completed':
                    st.markdown("### Feedback")
                    st.info("Feedback will be provided here once the assignment is graded.")
                
                




def display_preclass_analytics(session):
    """Display pre-class analytics for faculty"""
    st.subheader("Pre-class Analytics")
    
    # Display pre-class resource completion rates
    for resource in session['pre_class']['resources']:
        progress = SAMPLE_STUDENT_PROGRESS.get(resource['title'], 0)
        display_progress_bar(progress, 100, resource['title'])

def display_inclass_analytics(session):
    """Display in-class analytics for faculty"""
    st.subheader("In-class Analytics")
    
    # Display chat usage metrics
    chat_messages = SAMPLE_CHAT_HISTORY.get(session['session_id'], [])
    st.metric("Total Chat Messages", len(chat_messages))
    
    # Display live quiz/poll results
    # for poll in session['in_class']['polls']:
    #     st.subheader(poll['question'])
    #     for option, count in poll['responses'].items():
    #         st.metric(option, count)
    for poll in session.get('in_class', {}).get('polls', []):
        st.text(poll.get('question', 'No question available'))
        responses = poll.get('responses', {})
        if responses:
            for option, count in responses.items():
                st.metric(option, count)
        else:
            st.warning("No responses available for this poll")

def display_postclass_analytics(session):
    """Display post-class analytics for faculty"""
    st.subheader("Post-class Analytics")
    
    # # Display assignment completion rates
    # for assignment in session['post_class']['assignments']:
    #     progress = SAMPLE_STUDENT_PROGRESS.get(assignment['id'], 0)
    #     display_progress_bar(progress, 100, assignment['title'])


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




def display_session_content(student_id, course_id, session, username, user_type):
    st.title(f"Session {session['session_id']}: {session['title']}")
    st.markdown(f"**Date:** {format_datetime(session['date'])}")
    st.markdown(f"**Status:** {session['status'].replace('_', ' ').title()}")
    
    # Find the course_id of the session in 

    if st.session_state.user_type == 'student':
        tabs = (["Pre-class Work", "In-class Work", "Post-class Work"])
    else:
        tabs = (["Pre-class Analytics", "In-class Analytics", "Post-class Analytics"])

    # Create tabs for different sections
    # pre_class_tab, in_class_tab, post_class_tab, faculty_tab = st.tabs([
    #     "Pre-class Work",
    #     "In-class Work",
    #     "Post-class Work",
    #     "Faculty Analytics"
    # ])

    if st.session_state.user_type == 'student':
        pre_class_tab, in_class_tab, post_class_tab = st.tabs(["Pre-class Work", "In-class Work", "Post-class Work"])
    else:
        pre_class_work, in_class_work, post_class_work, preclass_analytics, inclass_analytics, postclass_analytics = st.tabs(["Pre-class Work", "In-class Work", "Post-class Work", "Pre-class Analytics", "In-class Analytics", "Post-class Analytics"])

    # Display pre-class materials
    if st.session_state.user_type == 'student':
        with pre_class_tab:
            display_preclass_content(session, student_id)
        
        with in_class_tab:
            display_in_class_content(session, st.session_state.user_type)
        
        # Post-class Content
        with post_class_tab:
            display_post_class_content(session, student_id, course_id)

    if st.session_state.user_type == 'faculty':
        with pre_class_work:
            upload_preclass_materials(session['session_id'], course_id)
        with in_class_work:
            display_in_class_content(session, st.session_state.user_type)
        with post_class_work:
            display_post_class_content(session, student_id, course_id)
        with preclass_analytics:
            display_preclass_analytics(session)
        with inclass_analytics:
            display_inclass_analytics(session)
        with postclass_analytics:
            display_postclass_analytics(session)