from datetime import datetime, timedelta
import streamlit as st

def format_datetime(dt):
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M")

def get_session_progress(username, course_id, session_id):
    """
    Get user's progress for a specific session
    Returns dict with pre_class, in_class, and post_class completion status
    """
    # Demo implementation - replace with actual database queries
    return {
        'pre_class': {
            'completed': True,
            'last_access': datetime.now() - timedelta(days=1),
            'resources_viewed': 3,
            'total_resources': 3
        },
        'in_class': {
            'completed': False,
            'attendance': True,
            'quiz_completed': False,
            'questions_asked': 5
        },
        'post_class': {
            'completed': False,
            'assignments_submitted': 1,
            'total_assignments': 2,
            'grade': None
        }
    }

def get_course_sessions(course_id):
    """Get all sessions for a course"""
    # Demo implementation - replace with database query
    return [
        {
            'id': 1,
            'title': 'Introduction to Programming Concepts',
            'date': datetime.now() + timedelta(days=i),
            'status': 'completed' if i < 0 else 'upcoming'
        }
        for i in range(-2, 5)
    ]

def display_progress_bar(completed, total, text=""):
    """Display a progress bar with text"""
    progress = completed / total if total > 0 else 0
    st.progress(progress)
    st.text(f"{text}: {completed}/{total} ({progress*100:.1f}%)")

def create_notification(message, type="info"):
    """Create a notification message"""
    if type == "success":
        st.success(message)
    elif type == "error":
        st.error(message)
    elif type == "warning":
        st.warning(message)
    else:
        st.info(message)

class SessionManager:
    """Manage session state and navigation"""
    @staticmethod
    def get_current_session():
        """Get current session information"""
        if 'current_session' not in st.session_state:
            st.session_state.current_session = 1
        return st.session_state.current_session
    
    @staticmethod
    def set_current_session(session_id):
        """Set current session"""
        st.session_state.current_session = session_id
    
    @staticmethod
    def clear_session():
        """Clear session state"""
        for key in list(st.session_state.keys()):
            del st.session_state[key]