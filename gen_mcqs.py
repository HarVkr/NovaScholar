import ast
from pymongo import MongoClient
from datetime import datetime
import openai
import google.generativeai as genai
from google.generativeai import GenerativeModel
from dotenv import load_dotenv
import os
from file_upload_vectorize import resources_collection, vectors_collection, courses_collection2, faculty_collection

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
OPENAI_KEY = os.getenv('OPENAI_KEY')
GEMINI_KEY = os.getenv('GEMINI_KEY')

# Configure APIs
openai.api_key = OPENAI_KEY
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client['novascholar_db']
quizzes_collection = db["quizzes"]

def strip_code_markers(response_text):
    """Strip off the markers ``` and python from a LLM model's response"""
    if response_text.startswith("```python"):
        response_text = response_text[len("```python"):].strip()
    if response_text.startswith("```"):
        response_text = response_text[len("```"):].strip()
    if response_text.endswith("```"):
        response_text = response_text[:-len("```")].strip()
    return response_text


# New function to generate MCQs using Gemini
def generate_mcqs(context, num_questions, session_title, session_description):
    """Generate MCQs either from context or session details"""
    try:
        # Initialize Gemini model
        if context:
            prompt = f"""
            Based on the following content, generate {num_questions} multiple choice questions.
            Format each question as a Python dictionary with the following structure:
            {{
                "question": "Question text here",
                "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
                "correct_option": "A) option1" or "B) option2" or "C) option3" or "D) option4"
            }}
            
            Content:
            {context}
            
            Generate challenging but clear questions that test understanding of key concepts.
            Return only the Python list of dictionaries.
            """
        else:
            prompt = f"""
            Generate {num_questions} multiple choice questions about the topic:
            Title: {session_title}
            Description: {session_description}
            
            Format each question as a Python dictionary with the following structure:
            {{
                "question": "Question text here",
                "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
                "correct_option": "A" or "B" or "C" or "D"
            }}
            
            Generate challenging but clear questions.
            Return only the Python list of dictionaries without any additional formatting or markers
            Do not write any other text, do not start the response with (```python), do not end the response with backticks(```)
            A Sample response should look like this: Response Text: [
                {
                    "question": "Which of the following is NOT a valid data type in C++?",
                    "options": ["int", "double", "boolean", "char"],
                    "correct_option": "C"
                }
            ] (Notice that there are no backticks(```) around the response and no (```python)) 
            .
            """
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        print("Response Text:", response_text)
        modified_response_text = strip_code_markers(response_text)
        print("Response Text Modified to:", modified_response_text)
        # Extract and parse the response to get the list of MCQs
        mcqs = ast.literal_eval(modified_response_text)  # Be careful with eval, consider using ast.literal_eval for production
        print(mcqs)
        if not mcqs:
            raise ValueError("No questions generated")
        return mcqs
    except Exception as e:
        print(f"Error generating MCQs: , error: {e}")
        return None

# New function to save quiz to database
def save_quiz(course_id, session_id, title, questions, user_id):
    """Save quiz to database"""
    try:
        quiz_data = {
            "user_id": user_id,
            "course_id": course_id,
            "session_id": session_id,
            "title": title,
            "questions": questions,
            "created_at": datetime.utcnow(),
            "status": "active",
            "submissions": []
        }
        result = quizzes_collection.insert_one(quiz_data)
        return result.inserted_id
    except Exception as e:
        print(f"Error saving quiz: {e}")
        return None
    

def get_student_quiz_score(quiz_id, student_id):
    """Get student's score for a specific quiz"""
    quiz = quizzes_collection.find_one(
        {
            "_id": quiz_id,
            "submissions.student_id": student_id
        },
        {"submissions.$": 1}
    )
    if quiz and quiz.get('submissions'):
        return quiz['submissions'][0].get('score')
    return None

# def submit_quiz_answers(quiz_id, student_id, student_answers):
#     """Submit and score student's quiz answers"""
#     quiz = quizzes_collection.find_one({"_id": quiz_id})
#     if not quiz:
#         return None
    
#     # Calculate score
#     correct_answers = 0
#     total_questions = len(quiz['questions'])
    
#     for q_idx, question in enumerate(quiz['questions']):
#         if student_answers.get(str(q_idx)) == question['correct_option']:
#             correct_answers += 1
    
#     score = (correct_answers / total_questions) * 100
    
#     # Store submission
#     submission_data = {
#         "student_id": student_id,
#         "answers": student_answers,
#         "score": score,
#         "submitted_at": datetime.utcnow()
#     }
    
#     # Update quiz with submission
#     quizzes_collection.update_one(
#         {"_id": quiz_id},
#         {
#             "$push": {"submissions": submission_data}
#         }
#     )
    
#     return score
def submit_quiz_answers(quiz_id, student_id, student_answers):
    """Submit and score student's quiz answers"""
    try:
        quiz = quizzes_collection.find_one({"_id": quiz_id})
        if not quiz:
            return None
        
        # Calculate score
        correct_answers = 0
        total_questions = len(quiz['questions'])
        
        for q_idx, question in enumerate(quiz['questions']):
            student_answer = student_answers.get(str(q_idx))
            if student_answer:  # Only check if answer was provided
                # Extract the option letter (A, B, C, D) from the full answer string
                answer_letter = student_answer.split(')')[0].strip()
                if answer_letter == question['correct_option']:
                    correct_answers += 1
        
        score = (correct_answers / total_questions) * 100
        
        # Store submission
        submission_data = {
            "student_id": student_id,
            "answers": student_answers,
            "score": score,
            "submitted_at": datetime.utcnow()
        }
        
        # Update quiz with submission
        result = quizzes_collection.update_one(
            {"_id": quiz_id},
            {"$push": {"submissions": submission_data}}
        )
        
        return score if result.modified_count > 0 else None
        
    except Exception as e:
        print(f"Error submitting quiz: {e}")
        return None