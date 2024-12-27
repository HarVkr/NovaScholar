from datetime import datetime, timedelta
import os
from typing import Dict, List, Any
from pymongo import MongoClient
import requests
import uuid
import openai
from openai import OpenAI
import streamlit as st
from bson import ObjectId
from dotenv import load_dotenv
import json

load_dotenv()
MONGODB_URI = os.getenv("MONGO_URI")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_KEY")

client = MongoClient(MONGODB_URI)
db = client['novascholar_db']
courses_collection = db['courses']

def generate_perplexity_response(api_key, course_name):
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}"
        }
        
        prompt = f"""
        You are an expert educational AI assistant specializing in curriculum design and instructional planning. Your task is to generate comprehensive, academically rigorous course structures for undergraduate level education.

        Please generate a detailed course structure for the course {course_name} in JSON format following these specifications:

        1. The course structure should be appropriate for a full semester (14-16 weeks)
        2. Each module should be designed for 2-4 weeks of instruction
        3. Follow standard academic practices and nomenclature
        4. Ensure progressive complexity from foundational to advanced concepts
        5. The course_title should exactly match the course name provided in the prompt. No additional information should be included in the course_title field.
        6: Ensure that the property names are enclosed in double quotes (") and followed by a colon (:), and the values are enclosed in double quotes (").
        7. **DO NOT INCLUDE THE WORD JSON IN THE OUTPUT STRING, DO NOT INCLUDE BACKTICKS (```) IN THE OUTPUT, AND DO NOT INCLUDE ANY OTHER TEXT, OTHER THAN THE ACTUAL JSON RESPONSE. START THE RESPONSE STRING WITH AN OPEN CURLY BRACE {{ AND END WITH A CLOSING CURLY BRACE }}.**

        
        The JSON response should follow this structure:
        {{
            "course_title": "string",
            "course_description": "string",
            "modules": [
                {{
                    "module_title": "string",
                    "sub_modules": [
                        {{
                            "title": "string",
                            "topics": [string],
                        }}
                    ]
                }}
            ]
        }}

        Example response:
        {{
            "course_title": "Advanced Natural Language Processing",
            "course_descriptio": "An advanced course covering modern approaches to NLP using deep learning, with focus on transformer architectures and their applications.",
            "modules": [
                {{
                    "module_title": "Foundations of Modern NLP",
                    "sub_modules": [
                        {{
                            "title": "Attention Mechanism",
                            "topics": [
                                "Self-attention",
                                "Multi-head attention",
                                "Positional encoding"
                            ]
                        }}
                    ]
                }}
            ]
        }}
        """

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert educational AI assistant specializing in course design and curriculum planning. "
                    "Your task is to generate accurate, detailed, and structured educational content for undergraduate-level and post-graduate-level courses. "
                    "Provide detailed and accurate information tailored to the user's prompt."
                    "Ensure that the responses are logical, follow standard academic practices, and include realistic concepts relevant to the course."
                ),
            },
            {
                "role": "user",
                "content": prompt
            },
        ]
        try:
            client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
            response = client.chat.completions.create(
                model="llama-3.1-sonar-small-128k-online",
                messages=messages
            )
            content = response.choices[0].message.content
            return content
        except Exception as e:
            st.error(f"Failed to fetch data from Perplexity API: {e}")
            return ""

def get_new_course_id():
    """Generate a new course ID by incrementing the last course ID"""
    last_course = courses_collection.find_one(sort=[("course_id", -1)])
    if last_course:
        last_course_id = int(last_course["course_id"][2:])
        new_course_id = f"CS{last_course_id + 1}"
    else:
        new_course_id = "CS101"
    return new_course_id


def create_course(course_name, start_date, duration_weeks):
        # Generate course overview
        # overview_prompt = f"""Generate an overview for the undergraduate course {course_name} 
        # Include all relevant concepts and key topics covered in a typical curriculum. 
        # The response should be concise (300-400 words). Ensure that your response is in a valid JSON format."""
        
        # overview_prompt2 = f"""Generate an overview for the undergraduate course {course_name}. 
        #                     The overview should include:
        #                     The course title, a detailed course description, 
        #                     a division of all relevant concepts and key topics into 4-6 logical modules, 
        #                     capturing the flow and structure of a typical curriculum.
        #                     Ensure the response adheres to the following JSON format:
        #                         {{
        #                             'overview': 'string',
        #                             'modules': [
        #                                 {{
        #                                     'name': 'string',
        #                                     'description': 'string'
        #                                 }}
        #                             ]
        #                         }}
        #                     overview: A detailed description of the course.
        #                     modules: An array of 4-6 objects, each representing a logical module with a name and a brief description
        #                     **DO NOT INCLUDE THE WORD JSON IN THE OUTPUT STRING, DO NOT INCLUDE BACKTICKS (```) IN THE OUTPUT, AND DO NOT INCLUDE ANY OTHER TEXT, OTHER THAN THE ACTUAL JSON RESPONSE. START THE RESPONSE STRING WITH AN OPEN CURLY BRACE {{ AND END WITH A CLOSING CURLY BRACE }}"""
        
        # course_overview = generate_perplexity_response(PERPLEXITY_API_KEY, overview_prompt2)
        # # print(course_overview)
        # course_overview_store = course_overview
        # # print(course_overview_store)
        # # Generate modules
        # # modules_prompt = f"Based on this overview: {course_overview}\nCreate 4-6 logical modules for the course, each module should group related concepts and each module may include reference books if applicable"
        # sub_modules_prompt = f"""Using the provided modules in the overview {course_overview_store}, generate 2-3 submodules for each module. 
        #                         Each submodule should represent a cohesive subset of the module's topics, logically organized for teaching purposes.
        #                         Ensure the response adheres to the following JSON format:
        #                         {
        #                             'modules': [
        #                                 {
        #                                     'name': 'string',
        #                                     'sub_modules': [
        #                                         {
        #                                             'name': 'string',
        #                                             'description': 'string'
        #                                         }
        #                                     ]
        #                                 }
        #                             ]
        #                         }
        #                         modules: An array where each object contains the name of the module and its corresponding sub_modules.
        #                         sub_modules: An array of 2-3 objects for each module, each having a name and a brief description."
        #                         **DO NOT INCLUDE THE WORD JSON IN THE OUTPUT STRING, DO NOT INCLUDE BACKTICKS (```) IN THE OUTPUT, AND DO NOT INCLUDE ANY OTHER TEXT, OTHER THAN THE ACTUAL JSON RESPONSE. START THE RESPONSE STRING WITH AN OPEN CURLY BRACE {{ AND END WITH A CLOSING CURLY BRACE }}
        #                     """
        # sub_modules = generate_perplexity_response(PERPLEXITY_API_KEY, sub_modules_prompt)
        
        # # modules_response = generate_perplexity_response(modules_prompt)
        # print(sub_modules)
        
        # total_sessions = duration_weeks * sessions_per_week

        course_plan = generate_perplexity_response(PERPLEXITY_API_KEY, course_name)
        course_plan_json = json.loads(course_plan)
        
        # Generate sessions for each module
        all_sessions = []
        for module in course_plan_json['modules']:
            for sub_module in module['sub_modules']:
                for topic in sub_module['topics']:
                    session = create_session(
                        title=topic,
                        date=start_date,
                        module_name=module['module_title']
                    )
                    # print(session)
                    all_sessions.append(session)
                    start_date += timedelta(days=7)  # Next session after a week

        # sample_sessions = [
        #     {'session_id': ObjectId('6767d0bbad8316ac358def25'), 'title': 'What is Generative AI?', 'date': datetime(2024, 12, 22, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 504599), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def26'), 'title': 'History and Evolution of AI', 'date': datetime(2024, 12, 29, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 504599), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def27'), 'title': 'Types of Generative AI (e.g., GANs, VAEs, LLMs)', 'date': datetime(2025, 1, 5, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 505626), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def28'), 'title': 'Overview of popular GenAI tools (e.g., ChatGPT, Claude, Google Gemini)', 'date': datetime(2025, 1, 12, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 506559), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def29'), 'title': 'Frameworks for building GenAI models (e.g., TensorFlow, PyTorch)', 'date': datetime(2025, 1, 19, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 506559), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def2a'), 'title': 'Integration with other AI technologies', 'date': datetime(2025, 1, 26, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 507612), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def2b'), 'title': 'Text-to-text models (e.g., GPT-3, BERT)', 'date': datetime(2025, 2, 2, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 508512), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def2c'), 'title': 'Text generation for content creation and marketing', 'date': datetime(2025, 2, 9, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 508512), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def2d'), 'title': 'Chatbots and conversational interfaces', 'date': datetime(2025, 2, 16, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 509612), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def2e'), 'title': 'Generative Adversarial Networks (GANs)', 'date': datetime(2025, 2, 23, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 509612), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def2f'), 'title': 'Variational Autoencoders (VAEs)', 'date': datetime(2025, 3, 2, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 510612), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def30'), 'title': 'Applications in art, design, and media', 'date': datetime(2025, 3, 9, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 511497), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def31'), 'title': 'Understanding prompt design principles', 'date': datetime(2025, 3, 16, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 511497), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def33'), 'title': 'Advanced techniques for fine-tuning models', 'date': datetime(2025, 3, 30, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 512514), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def34'), 'title': 'Ethical implications of AI-generated content', 'date': datetime(2025, 4, 6, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 513613), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def35'), 'title': 'Addressing bias in AI models', 'date': datetime(2025, 4, 13, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 514639), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def36'), 'title': 'Regulatory frameworks and guidelines', 'date': datetime(2025, 4, 20, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 514639), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def37'), 'title': 'Case studies from various industries (e.g., marketing, healthcare, finance)', 'date': datetime(2025, 4, 27, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 515610), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def38'), 'title': 'Success stories and challenges faced by companies using GenAI', 'date': datetime(2025, 5, 4, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 515610), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def39'), 'title': 'Guidelines for developing a GenAI project', 'date': datetime(2025, 5, 11, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 516614), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def3a'), 'title': 'Tools and resources for project implementation', 'date': datetime(2025, 5, 18, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 516614), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def3b'), 'title': 'Best practices for testing and deployment', 'date': datetime(2025, 5, 25, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 517563), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}}
        # ]

        # small_sample_sessions = [
        #     {'session_id': ObjectId('6767d0bbad8316ac358def25'), 'title': 'What is Generative AI?', 'date': datetime(2024, 12, 22, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 504599), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        #     {'session_id': ObjectId('6767d0bbad8316ac358def26'), 'title': 'History and Evolution of AI', 'date': datetime(2024, 12, 29, 14, 11, 27, 153899), 'status': 'upcoming', 'created_at': datetime(2024, 12, 22, 8, 41, 31, 504599), 'pre_class': {'resources': [], 'completion_required': True}, 'in_class': {'quiz': [], 'polls': []}, 'post_class': {'assignments': []}},
        # ]


        # print(all_sessions)

        print("Number of sessions:", len(all_sessions))
        # Create course document
        # course_description = course_plan_json['course_description']
        # course_doc = {
        #     "course_id": get_new_course_id(),
        #     "title": course_name,
        #     "description": course_description,
        #     "faculty": faculty_name,
        #     "faculty_id": faculty_id,
        #     "duration": f"{duration_weeks} weeks",
        #     "created_at": datetime.utcnow(),
        #     "sessions": all_sessions
        # }
        # try:
        #     courses_collection.insert_one(course_doc)
        # except Exception as e:
        #     st.error(f"Failed to insert course data into the database: {e}")

        # print(course_plan)

def create_session(title: str, date: datetime, module_name: str):
        """Create a session document with pre-class, in-class, and post-class components."""
        return {
            "session_id": ObjectId(),
            "title": title,
            "date": date,
            "status": "upcoming",
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

# Usage example:
if __name__ == "__main__":
    create_course("Introduction to Data Analytics", datetime.now(), 2)