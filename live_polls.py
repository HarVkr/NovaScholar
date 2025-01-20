# live_poll_feature.py

import streamlit as st
import pandas as pd
from datetime import datetime
from poll_db_operations import PollDatabase

class LivePollFeature:
    def __init__(self):
        self.db = PollDatabase()
    
    def display_faculty_interface(self, session_id):
        """Display the faculty interface for managing polls"""
        st.subheader("Live Polls Management")
        
        # Create new poll
        with st.expander("Create New Poll", expanded=False):
            question = st.text_input("Poll Question")
            
            num_options = st.number_input("Number of Options", 
                                        min_value=2, 
                                        max_value=6, 
                                        value=4)
            
            options = []
            for i in range(num_options):
                option = st.text_input(f"Option {i+1}", 
                                     key=f"option_{i}")
                if option:
                    options.append(option)
            
            if st.button("Create Poll") and question and len(options) >= 2:
                self.db.create_poll(
                    st.session_state.selected_course,
                    session_id,
                    question,
                    options,
                    st.session_state.user_id
                )
                st.success("Poll created successfully!")
                st.rerun()
        
        # Display active polls
        active_polls = self.db.get_active_polls(session_id)
        if active_polls:
            st.subheader("Active Polls")
            for poll in active_polls:
                with st.expander(f"Poll: {poll['question']}", expanded=True):
                    # Display results
                    self._display_poll_results(poll)
                    
                    if st.button("Close Poll", 
                               key=f"close_{str(poll['_id'])}"):
                        self.db.close_poll(poll['_id'])
                        st.success("Poll closed successfully!")
                        st.rerun()
    
    def display_student_interface(self, session_id):
        """Display the student interface for participating in polls"""
        st.subheader("Live Polls")
        
        active_polls = self.db.get_active_polls(session_id)
        if not active_polls:
            st.info("No active polls at the moment.")
            return
        
        for poll in active_polls:
            with st.expander(f"Poll: {poll['question']}", expanded=True):
                selected_option = st.radio(
                    "Your response:",
                    options=poll['options'],
                    key=f"poll_{str(poll['_id'])}"
                )
                
                if st.button("Submit Response", 
                           key=f"submit_{str(poll['_id'])}"):
                    success, message = self.db.submit_response(
                        poll['_id'],
                        st.session_state.user_id,
                        selected_option
                    )
                    if success:
                        st.success(message)
                    else:
                        st.warning(message)
                    st.rerun()
                
                # self._display_poll_results(poll)
    
    def _display_poll_results(self, poll):
        """Helper method to display poll results"""
        responses_df = pd.DataFrame(
            list(poll['responses'].items()),
            columns=['Option', 'Votes']
        )
        
        total_votes = responses_df['Votes'].sum()
        
        # Calculate percentages
        if total_votes > 0:
            responses_df['Percentage'] = (
                responses_df['Votes'] / total_votes * 100
            ).round(1)
        else:
            responses_df['Percentage'] = 0
        
        # Display metrics
        st.metric("Total Responses", total_votes)
        
        # Display charts
        st.bar_chart(responses_df.set_index('Option')['Votes'])
        
        # Display detailed statistics
        if st.session_state.user_type == 'faculty':
            st.dataframe(responses_df)