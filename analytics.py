import os
import pandas as pd
import numpy as np
from numpy.linalg import norm
from pymongo import MongoClient
import openai
from openai import OpenAI
import streamlit as st
from datetime import datetime

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI')

client = MongoClient(MONGO_URI)
db = client['digital_nova']
themes_collection = db['themes']
corpus_collection = db['corpus']
vectors_collection = db['vectors']  # Reference to 'vectors' collection
users_collection = db['users']

# Function to create embeddings
def create_embeddings(text, openai_api_key):
    client = OpenAI(api_key=openai_api_key)
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# Function to calculate cosine similarity
def cosine_similarity(v1, v2):
    v1 = np.array(v1)
    v2 = np.array(v2)
    dot_product = np.dot(v1, v2)
    norm_product = norm(v1) * norm(v2)
    return dot_product / norm_product if norm_product != 0 else 0

def derive_analytics(goal, reference_text, openai_api_key, context=None, synoptic=None):
    """
    Analyze subjective answers with respect to pre-class materials and synoptic, and provide detailed feedback
    
    Args:
        goal (str): Analysis objective
        reference_text (str): Student's answer text
        openai_api_key (str): OpenAI API key
        context (str, optional): Pre-class material content for comparison
        synoptic (str, optional): Synoptic content for evaluation
    """
    template = f"""Given a student's answer to a subjective question, analyze it following these specific guidelines. Compare it with the provided pre-class materials and synoptic (if available) to assess correctness and completeness.

    1. Analyze the text as an experienced educational assessor, considering:
       - Conceptual understanding
       - Factual accuracy
       - Completeness of response
       - Use of relevant terminology
       - Application of concepts

    2. Structure the output in markdown with two sections:

    **Correctness Assessment**
    - Rate overall correctness on a scale of 1-10

    **Evidence-Based Feedback**
    - Provide specific evidence from the student's answer to justify the score reduction
    - Highlight the exact lines or phrases that need improvement

    Pre-class Materials Context:
    {context if context else "No reference materials provided"}

    Synoptic:
    {synoptic if synoptic else "No synoptic provided"}

    Student's Answer:
    {reference_text}

    Rules:
    - Base assessment strictly on provided content
    - Be specific in feedback and suggestions
    """
    
    # Initialize OpenAI client
    client = OpenAI(api_key=openai_api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": "You are an educational assessment expert."},
                {"role": "user", "content": template}
            ],
            temperature=0.7
        )
        analysis = response.choices[0].message.content
        return analysis
    except Exception as e:
        print(f"Error in generating analysis with OpenAI: {str(e)}")
        return "Error generating analysis"
