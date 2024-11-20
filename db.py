# Setup for MongoDB
from pymongo import MongoClient
from datetime import datetime
from werkzeug.security import generate_password_hash
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
try:
    client.admin.command("ping")
    print("MongoDB connection successful")
except Exception as e:
    print(f"MongoDB connection failed: {e}")

db = client["novascholar_db"]

########
# Research Assistant Schema
research_assistant_schema = {
    "bsonType": "object",
    "required": ["full_name", "password", "email", "courses_assisted"],
    "properties": {
        "full_name": {
            "bsonType": "string",
            "description": "Full name of the research assistant",
        },
        "password": {
            "bsonType": "string",
            "description": "Hashed password of the research assistant",
        },
        "email": {
            "bsonType": "string",
            "description": "Email address of the research assistant",
        },
        "courses_assisted": {
            "bsonType": "array",
            "description": "List of courses the research assistant is assisting",
            "items": {
                "bsonType": "object",
                "required": ["course_id"],
                "properties": {
                    "course_id": {
                        "bsonType": "string",
                        "description": "ID of the course",
                    }
                },
            },
        },
    },
}

# Create research assistants collection
research_assistants_collection = db["research_assistants"]

# Create indexes
research_assistants_collection.create_index("full_name", unique=True)
research_assistants_collection.create_index("email", unique=True)


# Optional: Sample data insertion function
def insert_sample_research_assistants():
    sample_research_assistants = [
        {
            "full_name": "John Doe RA",
            "password": generate_password_hash("password123"),
            "email": "john.ra@example.com",
            "courses_assisted": [{"course_id": "CS101"}, {"course_id": "CS102"}],
        }
    ]

    try:
        research_assistants_collection.insert_many(sample_research_assistants)
        print("Sample research assistants inserted successfully!")
    except Exception as e:
        print(f"Error inserting sample research assistants: {e}")


###########


# Define the course schema
course_schema = {
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
                "required": ["session_id", "title", "date", "status", "created_at"],
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
                                            "bsonType": "int",
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
                                                "required": [
                                                    "student_id",
                                                    "file_url",
                                                    "submitted_at",
                                                ],
                                                "properties": {
                                                    "student_id": {
                                                        "bsonType": "string",
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

# Create the collection with the schema
# db.create_collection("courses_collection2", validator={"$jsonSchema": course_schema})

# sample_course = {
#     "course_id": "CS101",
#     "title": "Introduction to Computer Science",
#     "description": "This course covers the basics of computer science and programming.",
#     "faculty": "Dr. John Doe",
#     "faculty_id": "F101",
#     "duration": "10 weeks",
#     "created_at": datetime.utcnow(),
#     "sessions": [
#         {
#             "session_id": "S101",
#             "title": "Introduction to Programming Fundamentals",
#             "date": datetime.utcnow() - timedelta(days=7),
#             "status": "completed",
#             "created_at": datetime.utcnow() - timedelta(days=7),
#             "pre_class": {
#                 "resources": [
#                     {
#                         "type": "pdf",
#                         "title": "Introduction to Python Basics",
#                         "url": "/assets/python_basics.pdf",
#                         "vector": [0.1, 0.2, 0.3]  # Example vector
#                     }
#                 ],
#                 "completion_required": True
#             },
#             "in_class": {
#                 "topics": ["Variables", "Data Types", "Basic Operations"],
#                 "quiz": {
#                     "title": "Python Basics Quiz",
#                     "questions": 5,
#                     "duration": 15
#                 },
#                 "polls": [
#                     {
#                         "question": "How comfortable are you with Python syntax?",
#                         "options": ["Very", "Somewhat", "Not at all"],
#                         "responses": {"Very": 10, "Somewhat": 5, "Not at all": 2}
#                     }
#                 ]
#             },
#             "post_class": {
#                 "assignments": [
#                     {
#                         "id": 1,
#                         "title": "Basic Python Programs",
#                         "due_date": datetime.utcnow() + timedelta(days=2),
#                         "status": "pending",
#                         "submissions": []
#                     }
#                 ]
#             }
#         },
#         {
#             "session_id": "S102",
#             "title": "Control Flow and Functions",
#             "date": datetime.utcnow() - timedelta(days=3),
#             "status": "completed",
#             "created_at": datetime.utcnow() - timedelta(days=3),
#             "pre_class": {
#                 "resources": [
#                     {
#                         "type": "pdf",
#                         "title": "Control Flow in Python",
#                         "url": "/assets/control_flow.pdf",
#                         "vector": [0.4, 0.5, 0.6]  # Example vector
#                     }
#                 ],
#                 "completion_required": True
#             },
#             "in_class": {
#                 "topics": ["If-else statements", "Loops", "Function definitions"],
#                 "quiz": {
#                     "title": "Control Flow Quiz",
#                     "questions": 8,
#                     "duration": 20
#                 },
#                 "polls": [
#                     {
#                         "question": "Which loop type do you find more intuitive?",
#                         "options": ["For loops", "While loops", "Both"],
#                         "responses": {"For loops": 12, "While loops": 8, "Both": 10}
#                     }
#                 ]
#             },
#             "post_class": {
#                 "assignments": [
#                     {
#                         "id": 2,
#                         "title": "Function Implementation Exercise",
#                         "due_date": datetime.utcnow() + timedelta(days=4),
#                         "status": "pending",
#                         "submissions": []
#                     }
#                 ]
#             }
#         }
#     ]
# }
courses_collection2 = db["courses_collection2"]


# Define the users schema
users_schema = {
    "bsonType": "object",
    "required": ["user_id", "username", "password", "role", "created_at"],
    "properties": {
        "user_id": {
            "bsonType": "string",
            "description": "Unique identifier for the user",
        },
        "username": {"bsonType": "string", "description": "Name of the User"},
        "password": {"bsonType": "string", "description": "Password of the user"},
        "role": {
            "bsonType": "string",
            "description": "Type of user (e.g., student, faculty)",
        },
        "created_at": {
            "bsonType": "date",
            "description": "Date when the user was created",
        },
    },
}
# Create the collection with the schema
# db.create_collection("users", validator={"$jsonSchema": users_schema})
users_collection = db["users"]


# Defining the Student Collection
student_schema = {
    "bsonType": "object",
    "required": ["SID", "full_name", "password", "enrolled_courses", "created_at"],
    "properties": {
        "SID": {
            "bsonType": "string",
            "description": "Unique identifier for the student",
        },
        "full_name": {"bsonType": "string", "description": "Full name of the student"},
        "password": {
            "bsonType": "string",
            "description": "Hashed password of the student",
        },
        "enrolled_courses": {
            "bsonType": "array",
            "description": "List of courses the student is enrolled in",
            "items": {
                "bsonType": "object",
                "required": ["course_id", "title"],
                "properties": {
                    "course_id": {
                        "bsonType": "string",
                        "description": "Unique identifier for the course",
                    },
                    "title": {
                        "bsonType": "string",
                        "description": "Title of the course",
                    },
                },
            },
        },
        "created_at": {
            "bsonType": "date",
            "description": "Date when the student was created",
        },
    },
}
# Defining the Faculty Collection
faculty_schema = {
    "bsonType": "object",
    "required": ["TID", "full_name", "password", "courses_taught", "created_at"],
    "properties": {
        "TID": {
            "bsonType": "string",
            "description": "Unique identifier for the faculty",
        },
        "full_name": {"bsonType": "string", "description": "Full name of the faculty"},
        "password": {
            "bsonType": "string",
            "description": "Hashed password of the faculty",
        },
        "courses_taught": {
            "bsonType": "array",
            "description": "List of courses the faculty is teaching",
            "items": {
                "bsonType": "object",
                "required": ["course_id", "title"],
                "properties": {
                    "course_id": {
                        "bsonType": "string",
                        "description": "Unique identifier for the course",
                    },
                    "title": {
                        "bsonType": "string",
                        "description": "Title of the course",
                    },
                },
            },
        },
        "created_at": {
            "bsonType": "date",
            "description": "Date when the faculty was created",
        },
    },
}
# Creating the Collections
# db.create_collection("students", validator={"$jsonSchema": student_schema})
# db.create_collection("faculty", validator={"$jsonSchema": faculty_schema})

students_collection = db["students"]
faculty_collection = db["faculty"]

# Defining the Vector Collection Schema
vector_schema = {
    "bsonType": "object",
    "required": ["resource_id", "vector"],
    "properties": {
        "resource_id": {
            "bsonType": "objectId",
            "description": "Unique identifier for the resource",
        },
        "vector": {
            "bsonType": "array",
            "description": "Vector representation of the resource",
            "items": {"bsonType": "double"},
        },
        "text": {"bsonType": "string", "description": "Text content of the resource"},
        "created_at": {
            "bsonType": "date",
            "description": "Date when the vector was created",
        },
    },
}
# Creating the Vector Collection
# db.create_collection("vectors", validator={"$jsonSchema": vector_schema})
vectors_collection = db["vectors"]


# Creating a Chat-History Collection
# Creating a Chat-History Collection
chat_history_schema = {
    "bsonType": "object",
    "required": ["user_id", "session_id", "messages", "timestamp"],
    "properties": {
        "user_id": {
            "bsonType": "objectId",
            "description": "Unique identifier for the user",
        },
        "session_id": {
            "bsonType": "string",
            "description": "Identifier for the session",
        },
        "timestamp": {
            "bsonType": "date",
            "description": "Timestamp when the chat session started",
        },
        "messages": {
            "bsonType": "array",
            "description": "List of chat messages",
            "items": {
                "bsonType": "object",
                "properties": {
                    "prompt": {
                        "bsonType": "string",
                        "description": "User's question or prompt",
                    },
                    "response": {
                        "bsonType": "string",
                        "description": "Assistant's response",
                    },
                    "timestamp": {
                        "bsonType": "date",
                        "description": "Timestamp of the message",
                    },
                },
            },
        },
    },
}

# Create the collection with the schema
# db.create_collection("chat_history", validator={"$jsonSchema": chat_history_schema})
chat_history_collection = db["chat_history"]


# Database setup for Research Assistant
# Research Assistant Schema
research_assistant_schema = {
    "bsonType": "object",
    "required": ["full_name", "password", "email", "courses_assisted"],
    "properties": {
        "full_name": {
            "bsonType": "string",
            "description": "Full name of the research assistant",
        },
        "password": {
            "bsonType": "string",
            "description": "Hashed password of the research assistant",
        },
        "email": {
            "bsonType": "string",
            "description": "Email address of the research assistant",
        },
        "courses_assisted": {
            "bsonType": "array",
            "description": "List of courses the research assistant is assisting",
            "items": {
                "bsonType": "object",
                "required": ["course_id"],
                "properties": {
                    "course_id": {
                        "bsonType": "string",
                        "description": "ID of the course",
                    }
                },
            },
        },
    },
}

# Create research assistants collection
research_assistants_collection = db["research_assistants"]

# Create indexes
research_assistants_collection.create_index("full_name", unique=True)
research_assistants_collection.create_index("email", unique=True)


# Optional: Sample data insertion function
# def insert_sample_research_assistants():
#     sample_research_assistants = [
#         {
#             "full_name": "John Doe RA",
#             "password": generate_password_hash("password123"),
#             "email": "john.ra@example.com",
#             "courses_assisted": [{"course_id": "CS101"}, {"course_id": "CS102"}],
#         }
#     ]

#     try:
#         research_assistants_collection.insert_many(sample_research_assistants)
#         print("Sample research assistants inserted successfully!")
#     except Exception as e:
#         print(f"Error inserting sample research assistants: {e}")

# if __name__ == "__main__":
#     insert_sample_research_assistants()
