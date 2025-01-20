import streamlit as st
from pymongo import MongoClient
from openai import OpenAI
from bson import ObjectId
import json
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
OPENAI_API_KEY = os.getenv('OPENAI_KEY')

client = MongoClient(MONGO_URI)
db = client['novascholar_db']
# db.create_collection("rubrics")
rubrics_collection = db['rubrics']
resources_collection = db['resources']
courses_collection = db['courses']

def generate_rubrics(api_key, session_title, outcome_description, taxonomy, pre_class_material):
    prompt = f"""
    You are an expert educational AI assistant specializing in instructional design. Generate a detailed rubric for the session titled "{session_title}". The rubric should be aligned with Bloom's Taxonomy level "{taxonomy}" and use numerical scoring levels (4,3,2,1) instead of descriptive levels. Use the following context:

    Session Outcome Description:
    {outcome_description}

    Pre-class Material:
    {pre_class_material}

    Please generate the rubric in JSON format with these specifications:
    1. Use numerical levels (4=Highest, 1=Lowest) instead of descriptive levels
    2. Include 4-5 relevant criteria based on the session outcome
    3. Each criterion should have clear descriptors for each numerical level
    4. Focus on objectively measurable aspects for evaluation
    5. Structure should be suitable for evaluating assignments and test answers

    ***IMPORTANT: DO NOT INCLUDE THE WORD JSON IN THE OUTPUT STRING, DO NOT INCLUDE BACKTICKS (```) IN THE OUTPUT, AND DO NOT INCLUDE ANY OTHER TEXT, OTHER THAN THE ACTUAL JSON RESPONSE. START THE RESPONSE STRING WITH AN OPEN CURLY BRACE {{ AND END WITH A CLOSING CURLY BRACE }}.***
    """

    messages = [
        {
            "role": "system",
            "content": "You are an expert educational AI assistant specializing in instructional design.",
        },
        {
            "role": "user",
            "content": prompt
        },
    ]

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Failed to generate rubrics: {e}")
        return None

def display_rubrics_tab(session, course_id):
    st.subheader("Generated Rubrics")

    # Fetch session details from the courses collection
    course_data = courses_collection.find_one(
        {"course_id": course_id, "sessions.session_id": session['session_id']},
        {"sessions.$": 1}
    )
    
    if course_data and 'sessions' in course_data and len(course_data['sessions']) > 0:
        session_data = course_data['sessions'][0]
        
        # Extract session learning outcomes
        if 'session_learning_outcomes' in session_data and len(session_data['session_learning_outcomes']) > 0:
            outcome = session_data['session_learning_outcomes'][0]
            outcome_description = outcome.get('outcome_description', '')
            taxonomy_level = outcome.get('bloom_taxonomy_level', '')
            
            # Display fetched information
            st.markdown("### Session Information")
            st.markdown(f"**Session Title:** {session['title']}")
            st.markdown(f"**Learning Outcome:** {outcome_description}")
            st.markdown(f"**Taxonomy Level:** {taxonomy_level}")

            # Fetch pre-class material
            pre_class_material_docs = resources_collection.find({"session_id": session['session_id']})
            pre_class_material = "\n".join([f"{doc.get('title', 'No Title')}: {doc.get('url', 'No URL')}" for doc in pre_class_material_docs])

            if st.button("Generate Rubric"):
                rubric = generate_rubrics(
                    OPENAI_API_KEY,
                    session['title'],
                    outcome_description,
                    taxonomy_level,
                    pre_class_material
                )
                
                if rubric:
                    st.json(rubric)
                    if st.button("Save Rubric"):
                        rubric_data = {
                            "course_id": course_id,
                            "session_id": session['session_id'],
                            "rubric": json.loads(rubric)
                        }
                        rubrics_collection.insert_one(rubric_data)
                        st.success("Rubric saved successfully!")
        else:
            st.error("No learning outcomes found for this session")
    else:
        st.error("Session data not found")