from datetime import datetime, timedelta

SAMPLE_COURSES = [
    {
        'course_id': 'CS101',
        'title': 'Introduction to Computer Science',
        'description': 'This course covers the basics of computer science and programming.',
        'instructor': 'Dr. John Doe',
        'duration': '10 weeks'
    },
    {
        'course_id': 'CS102',
        'title': 'Data Structures and Algorithms',
        'description': 'This course introduces data structures and algorithms for efficient data processing.',
        'instructor': 'Dr. Jane Smith',
        'duration': '12 weeks'
    },
    {
        'course_id': 'CS103',
        'title': 'Advanced Python Programming',
        'description': 'This course covers advanced topics in Python programming, including file handling and exception management.',
        'instructor': 'Dr. Emily Johnson',
        'duration': '8 weeks'
    }
]

SAMPLE_SESSIONS = [
    {
        'id': 1,
        'course_id': 'CS101',
        'title': 'Introduction to Programming Fundamentals',
        'date': datetime.now() - timedelta(days=7),
        'status': 'completed',
        'pre_class': {
            'resources': [
                {'type': 'pdf', 'title': 'Introduction to Python Basics', 'url': '/assets/python_basics.pdf'},
                {'type': 'video', 'title': 'Programming Fundamentals', 'duration': '15:00'},
                {'type': 'reading', 'title': 'Chapter 1: Getting Started', 'pages': '1-15'}
            ],
            'completion_required': True
        },
        'in_class': {
            'topics': ['Variables', 'Data Types', 'Basic Operations'],
            'quiz': {
                'title': 'Python Basics Quiz',
                'questions': 5,
                'duration': 15
            },
            'polls': [
                {'question': 'How comfortable are you with Python syntax?', 'options': ['Very', 'Somewhat', 'Not at all']}
            ]
        },
        'post_class': {
            'assignments': [
                {
                    'id': 1,
                    'title': 'Basic Python Programs',
                    'due_date': datetime.now() + timedelta(days=2),
                    'status': 'pending'
                }
            ]
        }
    },
    {
        'id': 2,
        'course_id': 'CS101',
        'title': 'Control Flow and Functions',
        'date': datetime.now() - timedelta(days=3),
        'status': 'completed',
        'pre_class': {
            'resources': [
                {'type': 'pdf', 'title': 'Control Flow in Python', 'url': '/assets/control_flow.pdf'},
                {'type': 'video', 'title': 'Functions and Methods', 'duration': '20:00'}
            ],
            'completion_required': True
        },
        'in_class': {
            'topics': ['If-else statements', 'Loops', 'Function definitions'],
            'quiz': {
                'title': 'Control Flow Quiz',
                'questions': 8,
                'duration': 20
            },
            'polls': [
                {'question': 'Which loop type do you find more intuitive?', 'options': ['For loops', 'While loops', 'Both']}
            ]
        },
        'post_class': {
            'assignments': [
                {
                    'id': 2,
                    'title': 'Function Implementation Exercise',
                    'due_date': datetime.now() + timedelta(days=4),
                    'status': 'pending'
                }
            ]
        }
    },
    {
        'id': 3,
        'course_id': 'CS102',
        'title': 'Data Structures',
        'date': datetime.now(),
        'status': 'in_progress',
        'pre_class': {
            'resources': [
                {'type': 'pdf', 'title': 'Python Data Structures', 'url': '/assets/data_structures.pdf'},
                {'type': 'video', 'title': 'Lists and Dictionaries', 'duration': '25:00'}
            ],
            'completion_required': True
        },
        'in_class': {
            'topics': ['Lists', 'Tuples', 'Dictionaries', 'Sets'],
            'quiz': {
                'title': 'Data Structures Quiz',
                'questions': 10,
                'duration': 25
            },
            'polls': [
                {'question': 'Which data structure do you use most often?', 'options': ['Lists', 'Dictionaries', 'Sets', 'Tuples']}
            ]
        },
        'post_class': {
            'assignments': [
                {
                    'id': 3,
                    'title': 'Data Structure Implementation',
                    'due_date': datetime.now() + timedelta(days=7),
                    'status': 'not_started'
                }
            ]
        }
    },
    {
        'id': 4,
        'course_id': 'CS101',
        'title': 'Object-Oriented Programming',
        'date': datetime.now() + timedelta(days=4),
        'status': 'upcoming',
        'pre_class': {
            'resources': [
                {'type': 'pdf', 'title': 'OOP Concepts', 'url': '/assets/oop_concepts.pdf'},
                {'type': 'video', 'title': 'Classes and Objects', 'duration': '30:00'}
            ],
            'completion_required': True
        },
        'in_class': {
            'topics': ['Classes', 'Objects', 'Inheritance', 'Polymorphism'],
            'quiz': {
                'title': 'OOP Concepts Quiz',
                'questions': 12,
                'duration': 30
            },
            'polls': [
                {'question': 'Have you used OOP before?', 'options': ['Yes', 'No', 'Not sure'], 'responses': {'For loops': 12, 'While loops': 8, 'Both': 10}}
            ]
        },
        'post_class': {
            'assignments': [
                {
                    'id': 4,
                    'title': 'Class Implementation Project',
                    'due_date': datetime.now() + timedelta(days=11),
                    'status': 'not_started'
                }
            ]
        }
    },
    {
        'id': 5,
        'course_id': 'CS103',
        'title': 'File Handling and Exception Management',
        'date': datetime.now() + timedelta(days=7),
        'status': 'upcoming',
        'pre_class': {
            'resources': [
                {'type': 'pdf', 'title': 'File Operations in Python', 'url': '/assets/file_ops.pdf'},
                {'type': 'video', 'title': 'Exception Handling', 'duration': '20:00'}
            ],
            'completion_required': True
        },
        'in_class': {
            'topics': ['File Operations', 'Exception Handling', 'Context Managers'],
            'quiz': {
                'title': 'File Operations Quiz',
                'questions': 8,
                'duration': 20
            },
            'polls': [
                {'question': 'How often do you handle exceptions in your code?', 
                 'options': ['Always', 'Sometimes', 'Rarely', 'Never'],
                 'responses': {'Very': 10, 'Somewhat': 15, 'Not at all': 5} 
                }
            ]
        },
        'post_class': {
            'assignments': [
                {
                    'id': 5,
                    'title': 'File Processing Application',
                    'due_date': datetime.now() + timedelta(days=14),
                    'status': 'not_started'
                }
            ]
        }
    }
]

# Chatbot message history
SAMPLE_CHAT_HISTORY = {
    1: [
        {'user': 'student1', 'message': 'What is the difference between list and tuple?', 'timestamp': datetime.now()},
        {'user': 'chatbot', 'message': 'Lists are mutable (can be modified) while tuples are immutable (cannot be modified after creation).', 'timestamp': datetime.now()}
    ]
}

# Student progress data
SAMPLE_STUDENT_PROGRESS = {
    'user1': {
        1: {'pre_class': 50, 'in_class': 80, 'post_class': 90},
        2: {'pre_class': 100, 'in_class': 75, 'post_class': 85},
        3: {'pre_class': 50, 'in_class': 0, 'post_class': 0},
        4: {'pre_class': 0, 'in_class': 0, 'post_class': 0},
        5: {'pre_class': 0, 'in_class': 0, 'post_class': 0}
    }
}