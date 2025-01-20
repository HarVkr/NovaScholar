# assignment_evaluation.py

import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import os
from openai import OpenAI
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()

# MongoDB setup
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client["novascholar_db"]
assignments_collection = db["assignments"]
assignment_evaluation_collection = db["assignment_evaluation"]
resources_collection = db["resources"]
students_collection = db["students"]

def evaluate_assignment(session_id, student_id, assignment_id):
    """
    Generate evaluation and analysis for submitted assignments
    """
    try:
        # Fetch assignment and student submission
        assignment = assignments_collection.find_one({"_id": assignment_id})
        if not assignment:
            return None

        # Find student's submission
        submission = next(
            (sub for sub in assignment.get('submissions', []) 
             if sub['student_id'] == str(student_id)),
            None
        )
        if not submission:
            return None

        # Default rubric for assignment evaluation
        default_rubric = """
        1. Understanding & Implementation (1-4):
           - Demonstrates understanding of assignment requirements
           - Implements required components correctly
           - Shows attention to detail
           
        2. Quality & Completeness (1-4):
           - Work is complete and thorough
           - Meets all assignment objectives
           - Shows evidence of effort and care
           
        3. Presentation & Organization (1-4):
           - Clear and professional presentation
           - Well-structured and organized
           - Follows required format and guidelines
        """

        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv('OPENAI_KEY'))

        # Create evaluation prompt
        prompt_template = f"""As an assignment evaluator, assess this student's submission based on the provided rubric criteria. Follow these guidelines:

        1. Evaluation Process:
        - Use each rubric criterion (scored 1-4)
        - Evaluate completeness and quality
        - Check alignment with assignment requirements
        - Calculate final score: sum of criteria scores converted to 10-point scale

        Assignment Title: {assignment['title']}
        Due Date: {assignment['due_date']}
        
        Submission Content:
        {submission.get('text_content', 'No text content available')}

        Rubric Criteria:
        {default_rubric}

        Provide your assessment in the following format:

        **Overall Score and Summary**
        - Score: [X]/10
        - Overall Assessment: [2-3 sentence summary]

        **Strengths**
        - [Key strength 1]
        - [Key strength 2]
        - [Key strength 3]

        **Areas for Improvement**
        - [Improvement point 1]
        - [Improvement point 2]
        - [Improvement point 3]

        **Specific Recommendations**
        [2-3 sentences with actionable feedback]
        """

        # Generate evaluation using OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt_template}],
            max_tokens=1000,
            temperature=0.4
        )

        # Store evaluation in MongoDB
        evaluation_doc = {
            "assignment_id": assignment_id,
            "student_id": student_id,
            "session_id": session_id,
            "evaluation": response.choices[0].message.content,
            "evaluated_at": datetime.utcnow()
        }
        
        assignment_evaluation_collection.insert_one(evaluation_doc)
        return evaluation_doc

    except Exception as e:
        print(f"Error in evaluate_assignment: {str(e)}")
        return None

def display_evaluation_to_faculty(session_id, student_id, course_id):
    """
    Display interface for faculty to generate and view assignment evaluations
    """
    st.header("Evaluate Assignments")

    try:
        # Fetch available assignments
        assignments = list(assignments_collection.find({
            "session_id": str(session_id),
            "course_id": course_id
        }))

        if not assignments:
            st.info("No assignments found for this session.")
            return

        # Select assignment
        assignment_options = {
            f"{assignment['title']} (Due: {assignment['due_date'].strftime('%Y-%m-%d')})" if 'due_date' in assignment else assignment['title']: assignment['_id'] 
            for assignment in assignments
        }
        
        if assignment_options:
            selected_assignment = st.selectbox(
                "Select Assignment to Evaluate",
                options=list(assignment_options.keys())
            )

            if selected_assignment:
                assignment_id = assignment_options[selected_assignment]
                assignment = assignments_collection.find_one({"_id": assignment_id})

                if assignment:
                    submissions = assignment.get('submissions', [])
                    if not submissions:
                        st.warning("No submissions found for this assignment.")
                        return

                    # Create a dropdown for student submissions
                    student_options = {
                        f"{students_collection.find_one({'_id': ObjectId(sub['student_id'])})['full_name']} (Submitted: {sub['submitted_at'].strftime('%Y-%m-%d %H:%M')})": sub['student_id']
                        for sub in submissions
                    }

                    selected_student = st.selectbox(
                        "Select Student Submission",
                        options=list(student_options.keys())
                    )

                    if selected_student:
                        student_id = student_options[selected_student]
                        submission = next(sub for sub in submissions if sub['student_id'] == student_id)

                        # Display submission details
                        st.subheader("Submission Details")
                        st.markdown(f"**Submitted:** {submission['submitted_at'].strftime('%Y-%m-%d %H:%M')}")
                        st.markdown(f"**File Name:** {submission['file_name']}")
                        
                        # Add download button for submitted file
                        if 'file_content' in submission:
                            st.download_button(
                                label="Download Submission",
                                data=submission['file_content'],
                                file_name=submission['file_name'],
                                mime=submission['file_type']
                            )

                        # Check for existing evaluation
                        existing_eval = assignment_evaluation_collection.find_one({
                            "assignment_id": assignment_id,
                            "student_id": student_id,
                            "session_id": str(session_id)
                        })

                        if existing_eval:
                            st.subheader("Evaluation Results")
                            st.markdown(existing_eval['evaluation'])
                            st.success("✓ Evaluation completed")
                            
                            if st.button("Regenerate Evaluation"):
                                with st.spinner("Regenerating evaluation..."):
                                    evaluation = evaluate_assignment(
                                        str(session_id),
                                        student_id,
                                        assignment_id
                                    )
                                    if evaluation:
                                        st.success("Evaluation regenerated successfully!")
                                        st.rerun()
                                    else:
                                        st.error("Error regenerating evaluation.")
                        else:
                            if st.button("Generate Evaluation"):
                                with st.spinner("Generating evaluation..."):
                                    evaluation = evaluate_assignment(
                                        str(session_id),
                                        student_id,
                                        assignment_id
                                    )
                                    if evaluation:
                                        st.success("Evaluation generated successfully!")
                                        st.markdown("### Generated Evaluation")
                                        st.markdown(evaluation['evaluation'])
                                        st.rerun()
                                    else:
                                        st.error("Error generating evaluation.")

    except Exception as e:
        st.error(f"An error occurred while loading the evaluations: {str(e)}")
        print(f"Error in display_evaluation_to_faculty: {str(e)}")

def display_assignment_results(assignment_id, student_id):
    """
    Display assignment results and analysis for a student
    """
    try:
        # Fetch analysis from evaluation collection
        analysis = assignment_evaluation_collection.find_one({
            "assignment_id": assignment_id,
            "student_id": str(student_id)
        })
        
        if not analysis:
            st.info("Evaluation will be available soon. Please check back later.")
            return
            
        st.header("Assignment Evaluation")
        
        # Display evaluation content
        st.markdown(analysis["evaluation"])
        
        # Display evaluation timestamp
        st.caption(f"Evaluation generated on: {analysis['evaluated_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
    except Exception as e:
        st.error("An error occurred while loading the evaluation. Please try again later.")
        print(f"Error in display_assignment_results: {str(e)}")