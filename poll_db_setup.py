from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
def setup_mongodb():
    """Initialize MongoDB connection and create collections with indexes"""
    client = MongoClient(MONGO_URI)
    db = client["novascholar_db"]
    
    # Create indexes for polls collection
    db.polls.create_index([("session_id", 1), ("status", 1)])
    db.polls.create_index([("course_id", 1)])
    
    # Create unique index for poll_responses to prevent duplicate votes
    db.poll_responses.create_index(
        [("poll_id", 1), ("student_id", 1)],
        unique=True
    )
    
    return "Database setup completed successfully"

def print_all_polls():
    """Print all polls in the database"""
    client = MongoClient(MONGO_URI)
    db = client["novascholar_db"]
    
    polls = db.polls.find()
    for poll in polls:
        print(poll)

if __name__ == "__main__":
    print(print_all_polls())