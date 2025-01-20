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
subjective_tests_collection = db["subjective_tests"]
subjective_test_evaluation_collection = db["subjective_test_evaluation"]
resources_collection = db["resources"]
students_collection = db["students"]

def evaluate_subjective_answers(session_id, student_id, test_id):
    """
    Generate evaluation and analysis for subjective test answers
    """
    try:
        # Fetch test and student submission
        test = subjective_tests_collection.find_one({"_id": test_id})
        if not test:
            return None

        # Find student's submission
        submission = next(
            (sub for sub in test.get('submissions', []) 
             if sub['student_id'] == str(student_id)),
            None
        )
        if not submission:
            return None

        # Fetch pre-class materials
        pre_class_materials = resources_collection.find({"session_id": session_id})
        pre_class_content = ""
        for material in pre_class_materials:
            if 'text_content' in material:
                pre_class_content += material['text_content'] + "\n"

        # Default rubric (can be customized later)
        default_rubric = """
        1. Content Understanding (1-4):
           - Demonstrates comprehensive understanding of core concepts
           - Accurately applies relevant theories and principles
           - Provides specific examples and evidence
           
        2. Critical Analysis (1-4):
           - Shows depth of analysis
           - Makes meaningful connections
           - Demonstrates original thinking
           
        3. Organization & Clarity (1-4):
           - Clear structure and flow
           - Well-developed arguments
           - Effective use of examples
        """

        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv('OPENAI_KEY'))

        evaluations = []
        for i, (question, answer) in enumerate(zip(test['questions'], submission['answers'])):
            analysis_content = f"""
            Question: {question['question']}
            Student Answer: {answer}
            """

            prompt_template = f"""As an educational assessor, evaluate this student's answer based on the provided rubric criteria and pre-class materials. Follow these assessment guidelines:
            
            1. Evaluation Process:
            - Use each rubric criterion (scored 1-4) for internal assessment
            - Compare response with pre-class materials
            - Check alignment with all rubric requirements
            - Calculate final score: sum of criteria scores converted to 10-point scale

            Pre-class Materials:
            {pre_class_content[:1000]}  # Truncate to avoid token limits

            Rubric Criteria:
            {default_rubric}

            Question and Answer:
            {analysis_content}

            Provide your assessment in the following format:

            **Score and Evidence**
            - Score: [X]/10
            - Evidence for deduction: [One-line reference to most significant gap or inaccuracy]

            **Key Areas for Improvement**
            - [Concise improvement point 1]
            - [Concise improvement point 2]
            - [Concise improvement point 3]
            """

            # Generate evaluation using OpenAI
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt_template}],
                max_tokens=500,
                temperature=0.4
            )

            evaluations.append({
                "question_number": i + 1,
                "question": question['question'],
                "answer": answer,
                "evaluation": response.choices[0].message.content
            })

        # Store evaluation in MongoDB
        evaluation_doc = {
            "test_id": test_id,
            "student_id": student_id,
            "session_id": session_id,
            "evaluations": evaluations,
            "evaluated_at": datetime.utcnow()
        }
        
        subjective_test_evaluation_collection.insert_one(evaluation_doc)
        return evaluation_doc

    except Exception as e:
        print(f"Error in evaluate_subjective_answers: {str(e)}")
        return None

def display_evaluation_to_faculty(session_id, student_id, course_id):
    """
    Display interface for faculty to generate and view evaluations
    """
    st.header("Evaluate Subjective Tests")

    try:
        # Fetch available tests
        tests = list(subjective_tests_collection.find({
            "session_id": str(session_id),
            "status": "active"
        }))

        if not tests:
            st.info("No subjective tests found for this session.")
            return

        # Select test
        test_options = {
            f"{test['title']} (Created: {test['created_at'].strftime('%Y-%m-%d %H:%M')})" if 'created_at' in test else test['title']: test['_id'] 
            for test in tests
        }
        
        if test_options:
            selected_test = st.selectbox(
                "Select Test to Evaluate",
                options=list(test_options.keys())
            )

            if selected_test:
                test_id = test_options[selected_test]
                test = subjective_tests_collection.find_one({"_id": test_id})

                if test:
                    submissions = test.get('submissions', [])
                    if not submissions:
                        st.warning("No submissions found for this test.")
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

                        st.markdown(f"**Submission Date:** {submission.get('submitted_at', 'No submission date')}")
                        st.markdown("---")

                        # Display questions and answers
                        st.subheader("Submission Details")
                        for i, (question, answer) in enumerate(zip(test['questions'], submission['answers'])):
                            st.markdown(f"**Question {i+1}:** {question['question']}")
                            st.markdown(f"**Answer:** {answer}")
                            st.markdown("---")

                        # Check for existing evaluation
                        existing_eval = subjective_test_evaluation_collection.find_one({
                            "test_id": test_id,
                            "student_id": student_id,
                            "session_id": str(session_id)
                        })

                        if existing_eval:
                            st.subheader("Evaluation Results")
                            for eval_item in existing_eval['evaluations']:
                                st.markdown(f"### Evaluation for Question {eval_item['question_number']}")
                                st.markdown(eval_item['evaluation'])
                                st.markdown("---")
                            
                            st.success("✓ Evaluation completed")
                            if st.button("Regenerate Evaluation", key=f"regenerate_{student_id}_{test_id}"):
                                with st.spinner("Regenerating evaluation..."):
                                    evaluation = evaluate_subjective_answers(
                                        str(session_id),
                                        student_id,
                                        test_id
                                    )
                                    if evaluation:
                                        st.success("Evaluation regenerated successfully!")
                                        st.rerun()
                                    else:
                                        st.error("Error regenerating evaluation.")
                        else:
                            st.subheader("Generate Evaluation")
                            if st.button("Generate Evaluation", key=f"evaluate_{student_id}_{test_id}"):
                                with st.spinner("Generating evaluation..."):
                                    evaluation = evaluate_subjective_answers(
                                        str(session_id),
                                        student_id,
                                        test_id
                                    )
                                    if evaluation:
                                        st.success("Evaluation generated successfully!")
                                        st.markdown("### Generated Evaluation")
                                        for eval_item in evaluation['evaluations']:
                                            st.markdown(f"#### Question {eval_item['question_number']}")
                                            st.markdown(eval_item['evaluation'])
                                            st.markdown("---")
                                        st.rerun()
                                    else:
                                        st.error("Error generating evaluation.")

    except Exception as e:
        st.error(f"An error occurred while loading the evaluations: {str(e)}")
        print(f"Error in display_evaluation_to_faculty: {str(e)}")