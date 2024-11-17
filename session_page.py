import streamlit as st
from datetime import datetime
from utils.sample_data import SAMPLE_CHAT_HISTORY, SAMPLE_STUDENT_PROGRESS
from utils.helpers import display_progress_bar, create_notification, format_datetime
from utils.sample_data import SAMPLE_SESSIONS, SAMPLE_COURSES
from file_upload_vectorize import upload_resource, extract_text_from_file, create_vector_store, resources_collection
from db import courses_collection2
def display_preclass_content(session, username):
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
    materials = resources_collection.find({"session_id": session['session_id']})
    for material in materials:
        # with st.expander(f"{material['file_name']} ({material['material_type'].upper()})"):
        #     if material['material_type'] == 'pdf':
        #         # st.markdown(f"📑 [Open PDF Document]({material['url']})")
        #         if st.button("Mark PDF as Read", key=f"pdf_{material['file_name']}"):
        #             create_notification("PDF marked as read!", "success")
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

def display_in_class_content(session):
    """Display in-class activities and interactions"""
    st.header("In-class Activities")
    
    # Topics covered
    with st.expander("Topics Covered", expanded=True):
        for topic in session['in_class']['topics']:
            st.markdown(f"- {topic}")
    
    # Live Quiz section
    st.subheader("Session Quiz")
    quiz = session['in_class']['quiz']
    with st.expander(f"Quiz: {quiz['title']}"):
        st.markdown(f"- Number of questions: {quiz['questions']}")
        st.markdown(f"- Time allowed: {quiz['duration']} minutes")
        if session['status'] == 'in_progress':
            if st.button("Start Quiz"):
                create_notification("Quiz will begin shortly!", "info")
        else:
            st.info("Quiz not available at this time")
    
    # Live Polls
    st.subheader("Interactive Polls")
    for idx, poll in enumerate(session['in_class']['polls']):
        with st.expander(f"Poll {idx + 1}: {poll['question']}"):
            selected_option = st.radio(
                "Your response:",
                options=poll['options'],
                key=f"poll_{session['session_id']}_{idx}"
            )
            if st.button("Submit Response", key=f"submit_poll_{idx}"):
                create_notification("Poll response recorded!", "success")
    
    # Chat Interface
    st.subheader("Class Discussion")
    chat_container = st.container()
    with chat_container:
        # Display existing messages
        messages = SAMPLE_CHAT_HISTORY.get(session['session_id'], [])
        for msg in messages:
            with st.chat_message(msg['user']):
                st.write(msg['message'])
        
        # New message input
        if session['status'] == 'in_progress':
            if prompt := st.chat_input("Ask a question..."):
                if len(messages) < 20:
                    with st.chat_message("user"):
                        st.write(prompt)
                    with st.chat_message("assistant"):
                        st.write("This is a sample response to your question.")
                else:
                    create_notification("Message limit (20) reached for this session.", "warning")

def display_post_class_content(session):
    """Display post-class assignments and submissions"""
    st.header("Post-class Work")
    
    # Display assignments
    for assignment in session['post_class']['assignments']:
        with st.expander(f"Assignment: {assignment['title']}", expanded=True):
            st.markdown(f"**Due Date:** {format_datetime(assignment['due_date'])}")
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
                    create_notification("Assignment submitted successfully!", "success")
            
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
    
    # Display assignment completion rates
    for assignment in session['post_class']['assignments']:
        progress = SAMPLE_STUDENT_PROGRESS.get(assignment['id'], 0)
        display_progress_bar(progress, 100, assignment['title'])


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




def display_session_content(course_id, session, username):
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
            display_preclass_content(session, username)
        
        with in_class_tab:
            display_in_class_content(session)
        
        # Post-class Content
        with post_class_tab:
            display_post_class_content(session)

    if st.session_state.user_type == 'faculty':
        with pre_class_work:
            upload_preclass_materials(session['session_id'], course_id)
        with preclass_analytics:
            display_preclass_analytics(session)
        with inclass_analytics:
            display_inclass_analytics(session)
        with postclass_analytics:
            display_postclass_analytics(session)