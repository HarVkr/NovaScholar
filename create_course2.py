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

def generate_perplexity_response(api_key, course_name, duration_weeks, sessions_per_week):
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    
    # Calculate sessions based on duration
    total_sessions = duration_weeks * sessions_per_week  # Assuming 2 sessions per week
    
    prompt = f"""
    You are an expert educational AI assistant specializing in curriculum design and instructional planning. Your task is to generate a comprehensive, academically rigorous course structure for the course {course_name} that fits exactly within {duration_weeks} weeks with {total_sessions} total sessions ({sessions_per_week} sessions per week).

    Please generate a detailed course structure in JSON format following these specifications:

    1. The course structure must be designed for exactly {duration_weeks} weeks with {total_sessions} total sessions
    2. Each module should contain an appropriate number of sessions that sum up to exactly {total_sessions}
    3. Each session should be designed for a 1-1.5-hour class duration
    4. Follow standard academic practices and nomenclature
    5. Ensure progressive complexity from foundational to advanced concepts
    6. The course_title should exactly match the course name provided
    7. Ensure that the property names are enclosed in double quotes (") and followed by a colon (:), and the values are enclosed in double quotes (").
    8. **DO NOT INCLUDE THE WORD JSON IN THE OUTPUT STRING, DO NOT INCLUDE BACKTICKS (```) IN THE OUTPUT, AND DO NOT INCLUDE ANY OTHER TEXT, OTHER THAN THE ACTUAL JSON RESPONSE. START THE RESPONSE STRING WITH AN OPEN CURLY BRACE {{ AND END WITH A CLOSING CURLY BRACE }}.**

    The JSON response should follow this structure:
    {{
        "course_title": "string",
        "course_description": "string",
        "total_duration_weeks": {duration_weeks},
        "sessions_per_week": {sessions_per_week},
        "total_sessions": {total_sessions},
        "modules": [
            {{
                "module_title": "string",
                "module_duration_sessions": number,
                "sub_modules": [
                    {{
                        "title": "string",
                        "topics": [
                            {{
                                "title": "string",
                                "short_description": "string",
                                "concise_learning_objectives": ["string"]
                            }}
                        ]
                    }}
                ]
            }}
        ]
    }}

    Ensure that:
    1. The sum of all module_duration_sessions equals exactly {total_sessions}
    2. Each topic has clear learning objectives
    3. Topics build upon each other logically
    4. Content is distributed evenly across the available sessions
    5. **This Instruction is Strictly followed: **DO NOT INCLUDE THE WORD JSON IN THE OUTPUT STRING, DO NOT INCLUDE BACKTICKS (```) IN THE OUTPUT, AND DO NOT INCLUDE ANY OTHER TEXT, OTHER THAN THE ACTUAL JSON RESPONSE. START THE RESPONSE STRING WITH AN OPEN CURLY BRACE {{ AND END WITH A CLOSING CURLY BRACE }}.****

    """

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert educational AI assistant specializing in course design and curriculum planning. "
                "Your task is to generate accurate, detailed, and structured educational content that precisely fits "
                "the specified duration."
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
        
        # Validate session count
        course_plan = json.loads(content)
        total_planned_sessions = sum(
            module.get('module_duration_sessions', 0) 
            for module in course_plan.get('modules', [])
        )
        
        if abs(total_planned_sessions - total_sessions) > 5:
            raise ValueError(f"Generated plan has {total_planned_sessions} sessions, but {total_sessions} were requested")
            
        return content
    except Exception as e:
        st.error(f"Failed to fetch data from Perplexity API: {e}")
        return ""

def generate_session_resources(api_key, session_titles: List[str]):
    """
    Generate relevant resources for each session title separately
    """
    resources_prompt = f"""
    You are an expert educational content curator. For each session title provided, suggest highly relevant and accurate learning resources.
    Please provide resources for these sessions: {session_titles}

    For each session, provide resources in this JSON format:
    {{
        "session_resources": [
            {{
                "session_title": "string",
                "resources": {{
                    "readings": [
                        {{
                            "title": "string",
                            "url": "string",
                            "type": "string",
                            "estimated_read_time": "string"
                        }}
                    ],
                    "books": [
                        {{
                            "title": "string",
                            "author": "string",
                            "isbn": "string",
                            "chapters": "string"
                        }}
                    ],
                    "additional_resources": [
                        {{
                            "title": "string",
                            "url": "string",
                            "type": "string",
                            "description": "string"
                        }}
                    ]
                }}
            }}
        ]
    }}

    Guidelines:
    1. Ensure all URLs are real and currently active
    2. Prioritize high-quality, authoritative sources
    3. Include 1-2 resources of each type
    5. For readings, include a mix of academic and practical resources. It can exceed to 3-4 readings 
    6. Book references should be real, recently published works
    7. Additional resources can include tools, documentation, or practice platforms
    8. Ensure that the property names are enclosed in double quotes (") and followed by a colon (:), and the values are enclosed in double quotes (").
    9. ***NOTE: **DO NOT INCLUDE THE WORD JSON IN THE OUTPUT STRING, DO NOT INCLUDE BACKTICKS (```) IN THE OUTPUT, AND DO NOT INCLUDE ANY OTHER TEXT, OTHER THAN THE ACTUAL JSON RESPONSE. START THE RESPONSE STRING WITH AN OPEN CURLY BRACE {{ AND END WITH A CLOSING CURLY BRACE }}.**
    """

    messages = [
        {
            "role": "system",
            "content": "You are an expert educational content curator, focused on providing accurate and relevant learning resources.",
        },
        {
            "role": "user",
            "content": resources_prompt
        },
    ]

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
        response = client.chat.completions.create(
            model="llama-3.1-sonar-small-128k-online",
            messages=messages
        )
        print("Response is: \n", response.choices[0].message.content)
        # try:
        #     return json.loads(response.choices[0].message.content)
        # except json.JSONDecodeError as e:
        #     st.error(f"Failed to decode JSON response: {e}")
        #     return None
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Failed to generate resources: {e}")
        return None

def validate_course_plan(course_plan):
    required_fields = ['course_title', 'course_description', 'modules']
    if not all(field in course_plan for field in required_fields):
        raise ValueError("Invalid course plan structure")
    
    for module in course_plan['modules']:
        if 'module_title' not in module or 'sub_modules' not in module:
            raise ValueError("Invalid module structure")

def create_session(title: str, date: datetime, module_name: str, resources: dict):
    """Create a session document with pre-class, in-class, and post-class components."""
    return {
        "session_id": ObjectId(),
        "title": title,
        "date": date,
        "status": "upcoming",
        "created_at": datetime.utcnow(),
        "module_name": module_name,
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
        },
        "external_resources": {
            "readings": resources.get("readings", []),
            "books": resources.get("books", []),
            "additional_resources": resources.get("additional_resources", [])
        }
    }

def create_course(course_name: str, start_date: datetime, duration_weeks: int, sessions_per_week: int):
    # First generate a course plan using Perplexity API
    # course_plan = generate_perplexity_response(PERPLEXITY_API_KEY, course_name, duration_weeks, sessions_per_week)
    # course_plan_json = json.loads(course_plan)
    
    # print("Course Structure is: \n", course_plan_json);

    # Earlier Code: 
    # Generate sessions for each module with resources
    # all_sessions = []
    # current_date = start_date
    
    # for module in course_plan_json['modules']:
    #     for sub_module in module['sub_modules']:
    #         for topic in sub_module['topics']:
    #             session = create_session(
    #                 title=topic['title'],
    #                 date=current_date,
    #                 module_name=module['module_title'],
    #                 resources=topic['resources']
    #             )
    #             all_sessions.append(session)
    #             current_date += timedelta(days=3.5)  # Spacing sessions evenly across the week
    
    # return course_plan_json, all_sessions

    # New Code:
    # Extract all session titles
    session_titles = []
    # Load the course plan JSON
    course_plan_json = {}
    with open('sample_files/sample_course.json', 'r') as file:
        course_plan_json = json.load(file)

    for module in course_plan_json['modules']:
        for sub_module in module['sub_modules']:
            for topic in sub_module['topics']:
                session_titles.append(topic['title'])
    
    # Generate resources for all sessions
    session_resources = generate_session_resources(PERPLEXITY_API_KEY, session_titles)
    # print("Session Resources are: \n", session_resources)
    resources = json.loads(session_resources)
    # print("Resources JSON is: \n", resources_json)
    
    # print("Session Resources are: \n", session_resources)

    # Create a mapping of session titles to their resources
    
    # Import Resources JSON
    # resources = {}
    # with open('sample_files/sample_course_resources.json', 'r') as file:
    #     resources = json.load(file)

    resources_map = {
        resource['session_title']: resource['resources']
        for resource in resources['session_resources']
    }
    print("Resources Map is: \n", resources_map)
    # print("Sample is: ", resources_map.get('Overview of ML Concepts, History, and Applications'));
    # Generate sessions with their corresponding resources
    all_sessions = []
    current_date = start_date
    
    for module in course_plan_json['modules']:
        for sub_module in module['sub_modules']:
            for topic in sub_module['topics']:
                session = create_session(
                    title=topic['title'],
                    date=current_date,
                    module_name=module['module_title'],
                    resources=resources_map.get(topic['title'], {})
                )
                all_sessions.append(session)
                current_date += timedelta(days=3.5)
    
    print("All Sessions are: \n", all_sessions)

def get_new_course_id():
    """Generate a new course ID by incrementing the last course ID"""
    last_course = courses_collection.find_one(sort=[("course_id", -1)])
    if last_course:
        last_course_id = int(last_course["course_id"][2:])
        new_course_id = f"CS{last_course_id + 1}"
    else:
        new_course_id = "CS101"
    return new_course_id

# if __name__ == "__main__":
#     course_name = "Introduction to Machine Learning"
#     start_date = datetime(2022, 9, 1)
#     duration_weeks = 4
#     create_course(course_name, start_date, duration_weeks, 3)