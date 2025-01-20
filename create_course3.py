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
import google.generativeai as genai
from mistralai import Mistral

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

client = MongoClient(MONGODB_URI)
db = client['novascholar_db']
courses_collection = db['courses']

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")


def generate_course_outcomes(api_key, course_name, duration_weeks, sessions_per_week):
    prompt = f"""
    You are an expert educational AI assistant specializing in curriculum design and instructional planning. Your task is to generate a comprehensive, academically rigorous set of Course Learning Outcomes (CLOs) for the course {course_name}. These CLOs will serve as a foundation for instructional design and assessment planning.

    Please generate a detailed list of CLOs in JSON format following these specifications:

    1. The CLOs should be clear, concise, and aligned with Bloom's Taxonomy, progressively covering lower-order to higher-order cognitive skills.
    2. Each CLO must explicitly define the skills, knowledge, or abilities the student is expected to acquire upon completing the course.
    3. The CLOs must align with the overall course objective and encompass foundational to advanced concepts.
    4. Use academic language appropriate for higher education or professional training.
    5. Ensure the CLOs are measurable and actionable.
    6. **DO NOT INCLUDE THE WORD JSON IN THE OUTPUT STRING, DO NOT INCLUDE BACKTICKS (```) IN THE OUTPUT, AND DO NOT INCLUDE ANY OTHER TEXT, OTHER THAN THE ACTUAL JSON RESPONSE. START THE RESPONSE STRING WITH AN OPEN CURLY BRACE {{ AND END WITH A CLOSING CURLY BRACE }}.**

    The JSON response should follow this structure:
    {{
        "course_title": "string",
        "course_description": "string",
        "learning_outcomes": [
            {{
                "outcome_number": CO + number,
                "outcome_description": "string",
                "aligned_blooms_taxonomy_level": "string"
            }}
        ]
    }}

    Ensure that:
    1. Each outcome has a unique outcome_number starting from 1.
    2. The aligned_blooms_taxonomy_level must be one of the following: "Remember", "Understand", "Apply", "Analyze", "Evaluate", or "Create".
    3. The total number of CLOs should appropriately cover the breadth and depth of the course content, typically 5-7 CLOs.
    4. **This Instruction is Strictly followed: DO NOT INCLUDE THE WORD JSON IN THE OUTPUT STRING, DO NOT INCLUDE BACKTICKS (```) IN THE OUTPUT, AND DO NOT INCLUDE ANY OTHER TEXT, OTHER THAN THE ACTUAL JSON RESPONSE. START THE RESPONSE STRING WITH AN OPEN CURLY BRACE {{ AND END WITH A CLOSING CURLY BRACE }}.**

    """
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert educational AI assistant specializing in course design and curriculum planning. "
                "Your task is to generate accurate, detailed, and structured educational content that precisely fits "
                "the specified requirements."
            ),
        },
        {
            "role": "user",
            "content": prompt
        },
    ]
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json"
        )
    )
    try: 
        response_json = json.loads(response.text)
        return response.text;
    except json.JSONDecodeError as e:
        print("Error decoding COs JSON response:", e)

def generate_module_outcomes(course_name, course_outcomes, duration_weeks, sessions_per_week):
    total_sessions = duration_weeks * sessions_per_week
    prompt = f"""
        You are an expert educational AI assistant specializing in curriculum design and instructional planning. Your task is to break down the provided Course Learning Outcomes (CLOs) for the course {course_name} into logically structured modules and corresponding Module Learning Outcomes (MLOs). The structure must fit exactly within {duration_weeks} weeks with {total_sessions} total sessions ({sessions_per_week} sessions per week). Each module will be designed to align with specific CLOs and distribute content evenly across the available sessions.
        
        Here are the Course Learning Outcomes (CLOs) for the course {course_name} in JSON format:
        {course_outcomes}

        Please generate the module structure in JSON format following these specifications:

        1. Break the CLOs into logically grouped **modules**, ensuring that each module has a clear focus and progresses from foundational to advanced concepts.
        2. Each module must include:
            - A **module title** summarizing its focus.
            - A list of aligned CLOs that are covered within the module.
            - Module Learning Outcomes (MLOs) that are measurable and actionable, aligned with the CLOs.
            - The number of sessions allocated to the module (module_duration_sessions), such that the total sessions across all modules sum up to {total_sessions}.
        3. Ensure that the module_duration_sessions are evenly distributed while allowing for some variation based on the complexity of the module.
        4. Progressively distribute content so that earlier modules cover foundational concepts, and later modules cover advanced topics.
        5. The number of sessions allocated to each module must reflect the relative depth and complexity of its content.
        6. Ensure all modules fit within {duration_weeks} weeks and {sessions_per_week} sessions per week.

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
                    "aligned_CLOs": ["CLO1", "CLO2", ...],
                    "module_learning_outcomes": [
                        {{
                            "outcome_number": "MLO + number",
                            "outcome_description": "string",
                            "aligned_blooms_taxonomy_level": "string"
                        }}
                    ]
                }}
            ]
        }}

        Ensure that:
        1. The sum of all module_duration_sessions equals exactly {total_sessions}.
        2. Each MLO is aligned with its respective CLOs and measurable within the allocated sessions.
        3. Modules are well-distributed and follow a logical progression of topics.
        4. **This Instruction is Strictly followed: DO NOT INCLUDE THE WORD JSON IN THE OUTPUT STRING, DO NOT INCLUDE BACKTICKS (```) IN THE OUTPUT, AND DO NOT INCLUDE ANY OTHER TEXT, OTHER THAN THE ACTUAL JSON RESPONSE. START THE RESPONSE STRING WITH AN OPEN CURLY BRACE {{ AND END WITH A CLOSING CURLY BRACE }}.**
    """
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json"
        )
    )
    try:
        response_json = json.loads(response.text)
        return response.text
    except json.JSONDecodeError as e:
        print("Error decoding Modules JSON response:", e)

def generate_submodule_outcomes(course_name, course_outcomes, module_outcomes, duration_weeks, sessions_per_week):
    prompt = f"""
        You are an expert educational AI assistant specializing in instructional design. Your task is to further break down each module from the given course structure into submodules. Each submodule will cover specific concepts or topics within the module, along with corresponding Submodule Learning Outcomes (SMLOs).

        Here are the Course Learning Outcomes (CLOs) for the course {course_name}:
        {course_outcomes}
        and the Module Learning Outcomes (MLOs) for each module:
        {module_outcomes}
        
        Please follow these guidelines for creating submodules and SMLOs:

        1. For each module, create 2-3 submodules depending on its scope and duration.
        2. Assign each submodule a clear, concise title summarizing its focus.
        3. Each submodule must align with at least one Module Learning Outcome (MLO) and, by extension, its parent CLO(s).
        4. For each submodule, define 1-2 Submodule Learning Outcomes (SMLOs) that are measurable, actionable, and aligned with Bloom's Taxonomy.
        5. Distribute the total allocated sessions (module_duration_sessions) evenly among submodules, allowing slight variations for complex topics.
        6. Ensure that submodules progress logically within the module, starting with foundational concepts and advancing to more complex topics.
        7. Align the submodules with the total sessions allocated to the module to ensure they fit within the course timeline.

        The JSON response should follow this structure:
        {{
            "module_title": "string",
            "submodules": [
                {{
                    "submodule_title": "string",
                    "submodule_duration_sessions": number,
                    "aligned_MLOs": ["MLO1", "MLO2", ...],
                    "submodule_learning_outcomes": [
                        {{
                            "outcome_number": "SMLO + number",
                            "outcome_description": "string",
                            "aligned_blooms_taxonomy_level": "string"
                        }}
                    ]
                }}
            ]
        }}

        Ensure that:
        1. The sum of all submodule_duration_sessions within a module equals the module's allocated sessions (module_duration_sessions).
        2. SMLOs are specific, measurable, and actionable, aligning with their respective MLOs and CLOs.
        3. Submodules are logically ordered, with earlier submodules focusing on foundational concepts and later ones covering advanced topics.
        4. **This Instruction is Strictly followed: DO NOT INCLUDE THE WORD JSON IN THE OUTPUT STRING, DO NOT INCLUDE BACKTICKS (```) IN THE OUTPUT, AND DO NOT INCLUDE ANY OTHER TEXT, OTHER THAN THE ACTUAL JSON RESPONSE. START THE RESPONSE STRING WITH AN OPEN CURLY BRACE {{ AND END WITH A CLOSING CURLY BRACE }}.**
    """
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json"
        )
    )
    try:
        parse_model_response(response.text)
        return response.text
    except json.JSONDecodeError as e:
        print("Error decoding Submodules JSON response:", e)

import json
import ast
import re
import time
def parse_model_response(response_text):
    """Enhanced parser for model responses with better error handling.
    
    Args:
        response_text (str): Raw response text from the model
        
    Returns:
        dict or list: Parsed response object
        
    Raises:
        ValueError: If parsing fails
    """
    
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

def extract_session_titles_concepts(session_data):
        """Extracts session titles and key concepts from the session data.
        
        Args:
            session_data (dict): Parsed JSON data containing session information
            
        Returns:
            list: List of dictionaries with session titles and key concepts
        """
        session_info = []
        for module in session_data.get("submodules", []):
            for session in module.get("sessions", []):
                session_info.append({
                    "title": session.get("session_title", ""),
                    "key_concepts": session.get("key_concepts", [])
                })
        return session_info

def generate_session_outcomes(course_name, course_outcomes, module_outcomes, submodule_outcomes, duration_weeks, sessions_per_week):
    prompt = f"""
        You are an expert educational AI assistant specializing in instructional design and assessment. Your task is to create highly focused and measurable Session-Level Learning Outcomes (SLOs) that are aligned with their parent Submodule Learning Outcomes (SMLOs) and ready to serve as the foundation for rubric-based evaluations.

        ### Context:
        Course Name: {course_name}
        Course Outcomes (CLOs): {course_outcomes}
        Module Outcomes (MLOs): {module_outcomes}
        Submodule Outcomes (SMLOs): {submodule_outcomes}

        ### Instructions for SLO Generation:
        1. **For Each Submodule**: Break down its allocated sessions (submodule_duration_sessions) into Session-Level Learning Outcomes (SLOs) that:
        - Are immediately actionable, measurable, and achievable within a single session (60-90 minutes).
        - Are directly aligned with their parent SMLO, contributing to its achievement.
        - Include observable behaviors or outputs using **action-oriented verbs** from Bloom's Taxonomy (e.g., analyze, demonstrate, create, justify).
        - Are specific and detailed enough to support rubric development.

        2. **Structure for Each Session**:
        - **Session Title**: A concise and clear session title that captures its focus.
        - **Prerequisites**: Any prerequisite knowledge or skills required.
        - **Key Concepts**: Specific concepts or skills that will be covered.
        - **Session Learning Outcomes (SLOs)**: Include 2-3 outcomes that:
            - Define precise tasks or objectives for the session.
            - Specify the expected level of understanding, skill, or performance.
            - Directly support the parent SMLO while promoting progressive learning.

        3. **Progressive Learning**: Ensure that earlier sessions address foundational knowledge, while later sessions build on this foundation, leading to higher-order skills and integration of concepts.

        4. **Output Format**: Ensure the output follows this strict JSON structure:
        
        "submodules": [
            {{
                "submodule_title": "string",
                "sessions": [
                    {{
                        "session_number": number,
                        "session_title": "string",
                        "prerequisites": ["string"],
                        "key_concepts": ["string"],
                        "session_learning_outcomes": [
                            {{
                                "outcome_number": "SLO + number",
                                "outcome_description": "string",
                                "aligned_smlo": "SMLO + number",
                                "bloom_taxonomy_level": "string"
                            }}
                        ]
                    }}
                ]
            }}
        ]

        ### Example of Rubric-Ready SLOs:
        - **Poor Example**: "Understand agile methodologies."
        - **Good Example**: "Identify and describe the key principles of the Agile Manifesto, providing examples of how each principle applies to software development."

        **Important Instructions**:
        1. Ensure every SLO can be directly translated into rubric criteria (e.g., clarity, accuracy, application).
        2. **DO NOT INCLUDE THE WORD JSON IN THE OUTPUT STRING, DO NOT USE BACKTICKS (```), AND DO NOT INCLUDE ANY OTHER TEXT EXCEPT THE JSON RESPONSE. START WITH AN OPEN CURLY BRACE {{ AND END WITH A CLOSING CURLY BRACE }}.**
        3. Make sure every SLO is relevant to its parent SMLO.
    """
    
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json"
        )
    )
    try:
        parse_model_response(response.text)
        return response.text
    except json.JSONDecodeError as e:
        print("Error decoding Session Learning Outcomes JSON response:", e)


def merge_course_structure(cos, module_outcomes, submodules_los, sample_sessions_se):
    # Load JSON data
    cos_data = cos
    module_outcomes_data = module_outcomes
    submodules_los_data = submodules_los
    sample_sessions_se_data = sample_sessions_se

    # Create a mapping of submodule titles to their sessions
    submodule_sessions_map = {}
    for submodule in sample_sessions_se_data['submodules']:
        submodule_sessions_map[submodule['submodule_title']] = submodule['sessions']

    # Create a mapping of module titles to their submodules
    module_submodules_map = {}
    for module in submodules_los_data['modules']:
        module_submodules_map[module['module_title']] = module['submodules']

    # Merge submodules into modules
    for module in module_outcomes_data['modules']:
        module_title = module['module_title']
        if module_title in module_submodules_map:
            submodules = module_submodules_map[module_title]
            for submodule in submodules:
                submodule_title = submodule['submodule_title']
                if submodule_title in submodule_sessions_map:
                    submodule['sessions'] = submodule_sessions_map[submodule_title]
            module['submodules'] = submodules

    # Merge modules into course structure
    course_structure = cos_data
    course_structure['modules'] = module_outcomes_data['modules']

    return course_structure

def generate_session_resources(api_key, course_title, session_titles: List[str]):
    """
    Generate relevant resources for each session title separately
    """
    resources_prompt = f"""
        You are an expert educational content curator with deep knowledge of instructional design and high-quality resource selection. Your task is to provide session-specific learning resources and course-level reference books for the course: {course_title}.

        Guidelines for Resource Curation:
        1. For each session, suggest **highly relevant and accurate learning resources** based on the session title and key concepts provided.
        2. For the course as a whole, provide at most two **top reference books** that comprehensively cover the course objectives, including both academic and practical perspectives.
        3. Resources can include:
            - **Web articles or blogs** (ensure they are from authoritative and credible sources)
            - **Videos** (e.g., YouTube or other educational platforms)
            - **PDFs, PPTs, or other downloadable formats**
            - **Official documentation** for tools, platforms, or technologies
        4. Provide **multiple resources per session**, tailored to the topic's depth and complexity. Collectively, the number should not exceed 3.
        5. **IMPORTANT: MAKE SURE READINGS AND VIDEOS ARE GIVEN SEPARATELY. READINGS SHOULD NOT CONTAIN VIDEOS, IT SHOULD ONLY CONTAIN READING MATERIAL AND VICE-VERSA FOR VIDEOS**
        6. Ensure all URLs are **active and accessible**. Resources must be up-to-date, and links should work reliably.
        7. Reference books for the course should be **real, recently published works** and relevant to the course-level outcomes.

        Output Format:
        {{
            "course_reference_books": [
                {{
                    "title": "string",
                    "author": "string",
                    "publisher": "string",
                    "year": number,
                    "description": "string"
                }}
            ],
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
                        "videos": [
                            {{
                                "title": "string",
                                "url": "string",
                                "type": "string",
                                "duration": "string"
                            }}
                        ]
                    }}
                }}
            ]
        }}

        Additional Instructions:
        - Ensure **property names are enclosed in double quotes (")** and values are properly formatted.
        - Reference books should include **a brief description** to explain why they are relevant to the course.
        - Responses should be concise, structured, and focused exclusively on the requested information.
        - ***IMPORTANT: DO NOT INCLUDE THE WORD JSON IN THE OUTPUT STRING, DO NOT INCLUDE BACKTICKS (```) IN THE OUTPUT, AND DO NOT INCLUDE ANY OTHER TEXT, OTHER THAN THE ACTUAL JSON RESPONSE. START THE RESPONSE STRING WITH AN OPEN CURLY BRACE {{ AND END WITH A CLOSING CURLY BRACE }}.***

        Here are the session titles and key concepts for which you need to generate resources: {session_titles}.
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

def generate_resources_by_titles_chunking(session_titles, course_title):
    def chunk_list(lst, chunk_size):
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]
    
    all_session_resources = []
    course_reference_books = None  # Initialize this variable

    # Process each chunk of session titles
    for i, chunk in enumerate(chunk_list(session_titles, 10)):
        session_resources_chunk = generate_session_resources(PERPLEXITY_API_KEY, course_title, chunk)
        if session_resources_chunk:
            if "session_resources" in session_resources_chunk:
                # Parse the JSON string if it's a string
                if isinstance(session_resources_chunk, str):
                    session_resources_chunk = json.loads(session_resources_chunk)
                all_session_resources.extend(session_resources_chunk["session_resources"])
            # all_session_resources.extend(session_resources_chunk["session_resources"])
            # Only take the course_reference_books from the first chunk
            else:
                print("Some problem occured. Session resources chunk:", session_resources_chunk)
            
            if i == 0 and "course_reference_books" in session_resources_chunk:
                course_reference_books = session_resources_chunk.get("course_reference_books", [])
        time.sleep(2)

    # Combine all session resources into a single dictionary
    complete_session_resources = {
        "course_reference_books": course_reference_books,
        "session_resources": all_session_resources
    }
    # Save the complete session resources to a JSON file
    output_file_path = 'sample_files/session_resources2.json'
    with open(output_file_path, 'w') as outfile:
        try:
            json.dump(complete_session_resources, outfile, indent=4)
        except Exception as e:
            print(f"Failed to save session resources to file: {e}")
    
     # Debug print before return
    print("Type of complete_session_resources:", type(complete_session_resources))
    print("Content of complete_session_resources:", complete_session_resources)
    

    return complete_session_resources

if __name__ == "__main__":
    # course_name = "Introduction to Machine Learning"
    # duration_weeks = 12
    # sessions_per_week = 2
    # Load COs from JSON file:
    # with open('sample_files/cos.json', 'r') as file:
    #     course_outcomes = json.load(file)
    
    # # Load MLOs from JSON file:
    # with open('sample_files/module_outcomes.json', 'r') as file:
    #     module_outcomes = json.load(file)
    
    # # Load SMLOs from JSON file:
    # with open('sample_files/submodules_los.json', 'r') as file:
    #     submodules_outcomes = json.load(file)

    # print("Generating Course Outcomes...")
    # course_outcomes = generate_course_outcomes(GEMINI_API_KEY, course_name, duration_weeks, sessions_per_week)
    # print("Generating Modules...")
    # module_outcomes = generate_module_outcomes(course_name, course_outcomes, duration_weeks, sessions_per_week)
    # print("Generating Submodules...")
    # submodules_outcomes = generate_submodule_outcomes(course_name, course_outcomes, module_outcomes, duration_weeks, sessions_per_week)
    # print("Generating Sessions...")
    # session_outcomes = generate_session_outcomes(course_name, course_outcomes, module_outcomes, submodules_outcomes, duration_weeks, sessions_per_week)
    # print(session_outcomes)
    # print("Extracting Session Titles...")
    # # Load Sessions from JSON file:
    with open('sample_files/sample_sessions_se.json', 'r') as file:
        session_data = json.load(file)
    session_titles_concepts = extract_session_titles_concepts(session_data)
    print(session_titles_concepts)
    # print("Generating Session Resources...")
    # # Chunk the session titles into batches of 10
    # def chunk_list(lst, chunk_size):
    #     for i in range(0, len(lst), chunk_size):
    #         yield lst[i:i + chunk_size]

    # Extract session titles from session_titles_concepts
    session_titles = [session["title"] for session in session_titles_concepts]

    # # Initialize an empty list to store all session resources
    # all_session_resources = []

    # # Process each chunk of session titles
    # for chunk in chunk_list(session_titles, 10):
    #     session_resources_chunk = generate_session_resources(PERPLEXITY_API_KEY, course_name, chunk)
    #     if session_resources_chunk:
    #         all_session_resources.extend(json.loads(session_resources_chunk)["session_resources"])
    #     time.sleep(2)

    # # Combine all session resources into a single dictionary
    # complete_session_resources = {
    #     "course_reference_books": json.loads(session_resources_chunk)["course_reference_books"],
    #     "session_resources": all_session_resources
    # }

    # # Save the complete session resources to a JSON file
    # output_file_path = 'sample_files/session_resources.json'
    # with open(output_file_path, 'w') as outfile:
    #     json.dump(complete_session_resources, outfile, indent=4)
    # print(complete_session_resources)


    # session_resources = generate_session_resources(PERPLEXITY_API_KEY, course_name, session_titles_concepts)
    
    # # Save session resources to a JSON file
    # output_file_path = 'sample_files/session_resources.json'
    # with open(output_file_path, 'w') as outfile:
    #     json.dump(session_resources, outfile, indent=4)
    # print(session_resources)

    # Create course structure
    # course_structure = merge_course_structure(course_outcomes, module_outcomes, submodules_outcomes, session_outcomes)
    # Save course structure to a JSON file
    # output_file_path = 'sample_files/course_structure2.json'
    # with open(output_file_path, 'w') as outfile:
    #     json.dump(course_structure, outfile, indent=4)
    # print(course_structure)
    resources = generate_resources_by_titles_chunking(session_titles, "Software Engineering")
    print(resources)
    



