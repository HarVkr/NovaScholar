from db import courses_collection2
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from datetime import datetime



load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["novascholar_db"]

# Define the updated course schema
updated_course_schema = {
    "bsonType": "object",
    "required": [
        "course_id",
        "title",
        "description",
        "faculty",
        "faculty_id",
        "duration",
        "created_at",
    ],
    "properties": {
        "course_id": {
            "bsonType": "string",
            "description": "Unique identifier for the course",
        },
        "title": {"bsonType": "string", "description": "Title of the course"},
        "description": {
            "bsonType": "string",
            "description": "Description of the course",
        },
        "faculty": {"bsonType": "string", "description": "Name of the faculty"},
        "duration": {"bsonType": "string", "description": "Duration of the course"},
        "created_at": {
            "bsonType": "date",
            "description": "Date when the course was created",
        },
        "sessions": {
            "bsonType": "array",
            "description": "List of sessions associated with the course",
            "items": {
                "bsonType": "object",
                "required": ["session_id", "title", "date"],
                "properties": {
                    "session_id": {
                        "bsonType": "string",
                        "description": "Unique identifier for the session",
                    },
                    "title": {
                        "bsonType": "string",
                        "description": "Title of the session",
                    },
                    "date": {"bsonType": "date", "description": "Date of the session"},
                    "status": {
                        "bsonType": "string",
                        "description": "Status of the session (e.g., completed, upcoming)",
                    },
                    "created_at": {
                        "bsonType": "date",
                        "description": "Date when the session was created",
                    },
                    "pre_class": {
                        "bsonType": "object",
                        "description": "Pre-class segment data",
                        "properties": {
                            "resources": {
                                "bsonType": "array",
                                "description": "List of pre-class resources",
                                "items": {
                                    "bsonType": "object",
                                    "required": ["type", "title", "url"],
                                    "properties": {
                                        "type": {
                                            "bsonType": "string",
                                            "description": "Type of resource (e.g., pdf, video)",
                                        },
                                        "title": {
                                            "bsonType": "string",
                                            "description": "Title of the resource",
                                        },
                                        "url": {
                                            "bsonType": "string",
                                            "description": "URL of the resource",
                                        },
                                        "vector": {
                                            "bsonType": "array",
                                            "description": "Vector representation of the resource",
                                            "items": {"bsonType": "double"},
                                        },
                                    },
                                },
                            },
                            "completion_required": {
                                "bsonType": "bool",
                                "description": "Indicates if completion of pre-class resources is required",
                            },
                        },
                    },
                    "in_class": {
                        "bsonType": "object",
                        "description": "In-class segment data",
                        "properties": {
                            "topics": {
                                "bsonType": "array",
                                "description": "List of topics covered in the session",
                                "items": {"bsonType": "string"},
                            },
                            "quiz": {
                                "bsonType": "object",
                                "description": "Quiz data",
                                "properties": {
                                    "title": {
                                        "bsonType": "string",
                                        "description": "Title of the quiz",
                                    },
                                    "questions": {
                                        "bsonType": "int",
                                        "description": "Number of questions in the quiz",
                                    },
                                    "duration": {
                                        "bsonType": "int",
                                        "description": "Duration of the quiz in minutes",
                                    },
                                },
                            },
                            "polls": {
                                "bsonType": "array",
                                "description": "List of polls conducted during the session",
                                "items": {
                                    "bsonType": "object",
                                    "required": ["question", "options"],
                                    "properties": {
                                        "question": {
                                            "bsonType": "string",
                                            "description": "Poll question",
                                        },
                                        "options": {
                                            "bsonType": "array",
                                            "description": "List of poll options",
                                            "items": {"bsonType": "string"},
                                        },
                                        "responses": {
                                            "bsonType": "object",
                                            "description": "Responses to the poll",
                                            "additionalProperties": {"bsonType": "int"},
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "post_class": {
                        "bsonType": "object",
                        "description": "Post-class segment data",
                        "properties": {
                            "assignments": {
                                "bsonType": "array",
                                "description": "List of assignments",
                                "items": {
                                    "bsonType": "object",
                                    "required": ["id", "title", "due_date", "status"],
                                    "properties": {
                                        "id": {
                                            "bsonType": ["objectId", "int"],
                                            "description": "Assignment ID",
                                        },
                                        "title": {
                                            "bsonType": "string",
                                            "description": "Title of the assignment",
                                        },
                                        "due_date": {
                                            "bsonType": "date",
                                            "description": "Due date of the assignment",
                                        },
                                        "status": {
                                            "bsonType": "string",
                                            "description": "Status of the assignment (e.g., pending, completed)",
                                        },
                                        "submissions": {
                                            "bsonType": "array",
                                            "description": "List of submissions",
                                            "items": {
                                                "bsonType": "object",
                                                "properties": {
                                                    "student_id": {
                                                        "bsonType": "objectId",
                                                        "description": "ID of the student who submitted the assignment",
                                                    },
                                                    "file_url": {
                                                        "bsonType": "string",
                                                        "description": "URL of the submitted file",
                                                    },
                                                    "submitted_at": {
                                                        "bsonType": "date",
                                                        "description": "Date when the assignment was submitted",
                                                    },
                                                },
                                            },
                                        },
                                    },
                                },
                            }
                        },
                    },
                },
            },
        },
    },
}

# Update the schema using the collMod command
db.command({
    "collMod": "courses_collection2",
    "validator": {"$jsonSchema": updated_course_schema}
})

print("Schema updated successfully!")