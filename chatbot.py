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


def give_chat_response(user_id, session_id, question, context, prompt):
    st.title("Chat with NOVA")
    st.write("Ask any question and NOVA will provide an answer.")
    
    with st.form("chat_form"):
        message = st.text_input("Message")
        submit = st.form_submit_button("Send")
        
        if submit:
            insert_chat_message(user_id, session_id, "user", message)
            st.write(f"You: {message}")
            
            # Get response from NOVA
            response = get_nova_response(question, context, prompt, message)
            insert_chat_message(user_id, session_id, "nova", response)
            st.write(f"NOVA: {response}")