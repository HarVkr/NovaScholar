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
MONGO_URI = "mongodb+srv://akhilvaidya22:qN2dxc1cpwD64TeI@digital-nova.cbbsn.mongodb.net/?retryWrites=true&w=majority&appName=digital-nova"

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

# analytics.py
def derive_analytics(goal, reference_text, openai_api_key, context=None):
    """
    Analyze subjective answers with respect to pre-class materials and provide detailed feedback
    
    Args:
        goal (str): Analysis objective
        reference_text (str): Student's answer text
        openai_api_key (str): OpenAI API key
        context (str, optional): Pre-class material content for comparison
    """
    template = f"""Given a student's answer to a subjective question, analyze it following these specific guidelines. Compare it with the provided pre-class materials (if available) to assess correctness and completeness.

    1. Analyze the text as an experienced educational assessor, considering:
       - Conceptual understanding
       - Factual accuracy
       - Completeness of response
       - Use of relevant terminology
       - Application of concepts

    2. Structure the output in markdown with four sections:

    **Correctness Assessment**
    - Rate overall correctness on a scale of 1-10

    **Content Analysis**
    - Analyze how well the answer addresses the question
    - Evaluate the use of examples and supporting evidence
    - Assess the logical flow and structure
    - Note any unique insights or perspectives
    - Highlight particularly strong points

    **Areas for Improvement**
    - Identify specific concepts needing clarification
    - Point out missing key points from reference materials
    - Suggest ways to strengthen the argument
    - Recommend additional examples or evidence needed
    - Provide specific suggestions for better concept application

    **Key Terms Analysis**
    - List important terms used correctly
    - Identify missing key terms from reference materials
    - Note any terms used incorrectly
    - Suggest additional relevant terminology

    Pre-class Materials Context:
    {context if context else "No reference materials provided"}

    Student's Answer:
    {reference_text}

    Rules:
    - Base assessment strictly on provided content
    - Be specific in feedback and suggestions
    """

    client = OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4-0125-preview",
        messages=[
            {"role": "user", "content": template}
        ],
        max_tokens=1500,
        temperature=0.2,
    )
    return response.choices[0].message.content
