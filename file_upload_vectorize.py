from pymongo import MongoClient
from datetime import datetime
import openai
import google.generativeai as genai
import streamlit as st
from db import courses_collection2, faculty_collection, students_collection, vectors_collection
from PIL import Image
import PyPDF2, docx, io
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Document
from bson import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
OPENAI_KEY = os.getenv('OPENAI_KEY')
GEMINI_KEY = os.getenv('GEMINI_KEY')


client = MongoClient(MONGO_URI)
db = client['novascholar_db']
resources_collection = db['resources']

# Configure APIs
openai.api_key = OPENAI_KEY
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

def upload_resource(course_id, session_id, file_name, file_content, material_type):
    # material_data = {
    #     "session_id": session_id,
    #     "course_id": course_id,
    #     "file_name": file_name,
    #     "file_content": file_content,
    #     "material_type": material_type,
    #     "uploaded_at": datetime.utcnow()
    # }
    # return resources_collection.insert_one(material_data)
    resource_id = ObjectId()
    
    # Extract text content from the file
    text_content = extract_text_from_file(file_content)
    
    # Read the file content
    file_content.seek(0)  # Reset the file pointer to the beginning
    original_file_content = file_content.read()
    

    resource_data = {
        "resource_id": resource_id,
        "course_id": course_id,
        "session_id": session_id,
        "file_name": file_name,
        "file_type": file_content.type,
        "text_content": text_content,
        "file_content": original_file_content,  # Store the original file content
        "material_type": material_type,
        "uploaded_at": datetime.utcnow()
    }
    
    resources_collection.insert_one(resource_data)
    return resource_id

def extract_text_from_file(uploaded_file):
    text = ""
    file_type = uploaded_file.type
    
    try:
        if file_type == "text/plain":
            text = uploaded_file.getvalue().decode("utf-8")
        elif file_type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(io.BytesIO(uploaded_file.getvalue()))
            for para in doc.paragraphs:
                text += para.text + "\n"
        return text
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def get_embedding(text):
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding

def create_vector_store(text, resource_id):
    resource_object_id = ObjectId(resource_id)
    document = Document(text=text)
    embedding = get_embedding(text)
    
    vector_data = {
        "resource_id": resource_object_id,
        "vector": embedding,
        "text": text,
        "created_at": datetime.utcnow()
    }
    
    vectors_collection.insert_one(vector_data)
    
    return VectorStoreIndex.from_documents([document])