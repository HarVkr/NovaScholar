import pandas as pd
import json
import os
from datetime import datetime
import openai
from openai import OpenAI
import streamlit as st
from llama_index.core import VectorStoreIndex, Document
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.core.storage.storage_context import StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
from pymongo import MongoClient
import numpy as np
from numpy.linalg import norm
import PyPDF2
from io import BytesIO
import base64

MONGO_URI = os.getenv('MONGO_URI')
PERPLEXITY_KEY = os.getenv('PERPLEXITY_KEY')

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client['novascholar_db']

# Function to fetch data from Perplexity API
def fetch_perplexity_data(api_key, topic):
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    messages = [
        {
            "role": "system",
            "content": (
                "You are a expert providing official information about the given topic. Provide only verified information with atleast 3 working reference links for citations."
            ),
        },
        {
            "role": "user",
            "content": topic
        },
    ]
    
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
        response = client.chat.completions.create(
            model="llama-3.1-sonar-small-128k-online",
            messages=messages,
        )
        content = response.choices[0].message.content
        return content
    except Exception as e:
        st.error(f"Failed to fetch data from Perplexity API: {e}")
        return ""
    
def structure_data(api_key, generated_text, columns):
    prompt = f"You are given a large amount of data that can be structured into a table with many rows. Structure the following data into a JSON format with columns: {columns}. Data: {generated_text}. Ensure that you only output the data in JSON format without any other text at all, not even backtics `` and the word JSON. Do not include any other information in the output."
    messages = [
        {
            "role": "system",
            "content": "You are an AI that structures data into JSON format for converting unstructured text data into tables. Ensure that you have atlest as many rows in the output as much mentioned in the input text. Return the data in such a way that it is a list of dictionaried that can be converted to a pandas dataframe directly."
        },  
        {
            "role": "user",
            "content": prompt
        },
    ]
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.1,
        )
        json_content = response.choices[0].message.content
        return json.loads(json_content)
    except Exception as e:
        st.error(f"Failed to structure data using GPT-4o Mini: {e}")
        return []

def generate_theme_title(api_key, text):
    prompt = f"Provide a 2-3 word title that captures the main theme of the following text: {text} Return only the 2 3 word string and nothing else. Do not include any other information in the output."
    messages = [
        {
            "role": "system",
            "content": "You are an AI that generates concise titles for text content."
        },
        {
            "role": "user",
            "content": prompt
        },
    ]
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,
        )
        theme_title = response.choices[0].message.content.strip()
        return theme_title
    except Exception as e:
        st.error(f"Failed to generate theme title using GPT-4o Mini: {e}")
        return "Unnamed Theme"