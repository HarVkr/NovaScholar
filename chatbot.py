import streamlit as st
import datetime
from db import courses_collection2, faculty_collection, students_collection, vectors_collection, chat_history_collection
from PIL import Image
from dotenv import load_dotenv
import os
from datetime import datetime
from bson import ObjectId
from file_upload_vectorize import model

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
OPENAI_KEY = os.getenv('OPENAI_KEY')
GEMINI_KEY = os.getenv('GEMINI_KEY')

def insert_chat_message(user_id, session_id, role, content):
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow()
    }
    
    chat_history_collection.update_one(
        {"user_id": ObjectId(user_id), "session_id": session_id},
        {"$push": {"messages": message}, "$set": {"timestamp": datetime.utcnow()}},
        upsert=True
    )

def give_chat_response(user_id, session_id, question, title, description, context):
    context_prompt = f"""
    Based on the following session title, description, and context, answer the user's question in 3-4 lines:
    
    Title: {title}
    Description: {description}
    Context: {context}
    
    Question: {question}
    
    Please provide a clear and concise answer based on the information provided.
    """
    
    response = model.generate_content(context_prompt)
    if not response or not response.text:
        return "No response received from the model"
    
    assistant_response = response.text.strip()
    
    # Save the chat message
    insert_chat_message(user_id, session_id, "assistant", assistant_response)
    
    return assistant_response
