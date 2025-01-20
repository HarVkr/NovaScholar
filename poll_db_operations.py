from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
class PollDatabase:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client["novascholar_db"]
    
    def create_poll(self, course_id, session_id, question, options, faculty_id):
        """Create a new poll"""
        poll = {
            "course_id": course_id,
            "session_id": session_id,
            "faculty_id": faculty_id,
            "question": question,
            "options": options,
            "status": "active",
            "created_at": datetime.now(),
            "responses": {option: 0 for option in options}
        }
        return self.db.polls.insert_one(poll)
    
    def get_active_polls(self, session_id):
        """Get all active polls for a session"""
        return list(self.db.polls.find({
            "session_id": session_id,
            "status": "active"
        }))
    
    def submit_response(self, poll_id, student_id, selected_option):
        """Submit a student's response to a poll"""
        try:
            # Record individual response
            response = {
                "poll_id": poll_id,
                "student_id": student_id,
                "selected_option": selected_option,
                "submitted_at": datetime.now()
            }
            self.db.poll_responses.insert_one(response)
            
            # Update aggregated results
            self.db.polls.update_one(
                {"_id": ObjectId(poll_id)},
                {"$inc": {f"responses.{selected_option}": 1}}
            )
            return True, "Vote recorded successfully"
            
        except Exception as e:
            if "duplicate key error" in str(e):
                return False, "You have already voted in this poll"
            return False, f"Error recording vote: {str(e)}"
    
    def close_poll(self, poll_id):
        """Close a poll"""
        return self.db.polls.update_one(
            {"_id": ObjectId(poll_id)},
            {"$set": {"status": "closed"}}
        )
    
    def get_poll_analytics(self, poll_id):
        """Get detailed analytics for a poll"""
        poll = self.db.polls.find_one({"_id": ObjectId(poll_id)})
        responses = self.db.poll_responses.find({"poll_id": ObjectId(poll_id)})
        return poll, list(responses)