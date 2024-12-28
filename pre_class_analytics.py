import re
from bson import ObjectId
from pymongo import MongoClient
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
import os
from typing import List, Dict, Any
from transformers import pipeline
from textstat import flesch_reading_ease
from collections import Counter
import logging
import spacy
import json

# Load chat histories from JSON file
# all_chat_histories = []
# with open(r'all_chat_histories2.json', 'r') as file:
#     all_chat_histories = json.load(file)

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client['novascholar_db']

chat_history_collection = db['chat_history']

# def get_chat_history(user_id, session_id):
#     query = {
#         "user_id": ObjectId(user_id),
#         "session_id": session_id,
#         "timestamp": {"$lte": datetime.utcnow()}
#     }
#     result = chat_history_collection.find(query)
#     return list(result)

# if __name__ == "__main__":
#     user_ids = ["6738b70cc97dffb641c7d158", "6738b7b33f648a9224f7aa69"]
#     session_ids = ["S104"]
#     for user_id in user_ids:
#         for session_id in session_ids:
#             result = get_chat_history(user_id, session_id)
#             print(result)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NovaScholarAnalytics:
    def __init__(self):
        # Initialize NLP components
        self.nlp = spacy.load("en_core_web_sm")
        self.sentiment_analyzer = pipeline("sentiment-analysis",  model="finiteautomata/bertweet-base-sentiment-analysis", top_k=None)
        
        # Define question words for detecting questions
        self.question_words = {"what", "why", "how", "when", "where", "which", "who", "whose", "whom"}

        # Define question categories
        self.question_categories = {
            'conceptual': {'what', 'define', 'describe', 'explain'},
            'procedural': {'how', 'steps', 'procedure', 'process'},
            'reasoning': {'why', 'reason', 'cause', 'effect'},
            'clarification': {'clarify', 'mean', 'difference', 'between'}
        }
    
    def _categorize_questions(self, questions_df: pd.DataFrame) -> Dict[str, int]:
        """
        Categorize questions into different types based on their content.
        
        Args:
            questions_df: DataFrame containing questions
            
        Returns:
            Dictionary with question categories and their counts
        """
        categories_count = {
            'conceptual': 0,
            'procedural': 0,
            'reasoning': 0,
            'clarification': 0,
            'other': 0
        }
        
        for _, row in questions_df.iterrows():
            prompt_lower = row['prompt'].lower()
            categorized = False
            
            for category, keywords in self.question_categories.items():
                if any(keyword in prompt_lower for keyword in keywords):
                    categories_count[category] += 1
                    categorized = True
                    break
            
            if not categorized:
                categories_count['other'] += 1
        
        return categories_count


    def _identify_frustration(self, df: pd.DataFrame) -> List[str]:
        """
        Identify signs of frustration in student messages.
        
        Args:
            df: DataFrame containing messages
            
        Returns:
            List of topics/areas where frustration was detected
        """
        frustration_indicators = [
            "don't understand", "confused", "difficult", "hard to",
            "not clear", "stuck", "help", "can't figure"
        ]
        
        frustrated_messages = df[
            df['prompt'].str.lower().str.contains('|'.join(frustration_indicators), na=False)
        ]
        
        if len(frustrated_messages) == 0:
            return []
        
        # Extract topics from frustrated messages
        frustrated_topics = self._extract_topics(frustrated_messages)
        return list(set(frustrated_topics))  # Unique topic
    
    def _calculate_resolution_times(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate average time taken to resolve questions for different topics.
        
        Args:
            df: DataFrame containing messages
            
        Returns:
            Dictionary with topics and their average resolution times in minutes
        """
        resolution_times = {}
        
        # Group messages by topic
        topics = self._extract_topics(df)
        for topic in set(topics):
            escaped_topic = re.escape(topic)
            topic_msgs = df[df['prompt'].str.contains(escaped_topic, case=False)]
            if len(topic_msgs) >= 2:
                # Calculate time difference between first and last message
                start_time = pd.to_datetime(topic_msgs['timestamp'].iloc[0])
                end_time = pd.to_datetime(topic_msgs['timestamp'].iloc[-1])
                duration = (end_time - start_time).total_seconds() / 60  # Convert to minutes
                resolution_times[topic] = duration
        
        return resolution_times

    def _calculate_completion_rates(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate completion rates for different topics.
        
        Args:
            df: DataFrame containing messages
            
        Returns:
            Dictionary with topics and their completion rates
        """
        completion_rates = {}
        topics = self._extract_topics(df)
        
        for topic in set(topics):
            escaped_topic = re.escape(topic)
            topic_msgs = df[df['prompt'].str.contains(escaped_topic, case=False)]
            if len(topic_msgs) > 0:
                # Consider a topic completed if there are no frustrated messages in the last 2 messages
                last_msgs = topic_msgs.tail(2)
                frustrated = self._identify_frustration(last_msgs)
                completion_rates[topic] = 0.0 if frustrated else 1.0
        
        return completion_rates

    def _analyze_time_distribution(self, df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        Analyze time spent on different topics.
        
        Args:
            df: DataFrame containing messages
            
        Returns:
            Dictionary with time distribution statistics per topic
        """
        time_stats = {}
        topics = self._extract_topics(df)
        
        for topic in set(topics):
            escaped_topic = re.escape(topic)
            topic_msgs = df[df['prompt'].str.contains(escaped_topic, case=False)]
            if len(topic_msgs) >= 2:
                times = pd.to_datetime(topic_msgs['timestamp'])
                duration = (times.max() - times.min()).total_seconds() / 60
                
                time_stats[topic] = {
                    'total_minutes': duration,
                    'avg_minutes_per_message': duration / len(topic_msgs),
                    'message_count': len(topic_msgs)
                }
        
        return time_stats
    
    def _identify_coverage_gaps(self, df: pd.DataFrame) -> List[str]:
        """
        Identify topics with potential coverage gaps.
        
        Args:
            df: DataFrame containing messages
            
        Returns:
            List of topics with coverage gaps
        """
        gaps = []
        topics = self._extract_topics(df)
        topic_stats = self._analyze_time_distribution(df)
        
        for topic in set(topics):
            if topic in topic_stats:
                stats = topic_stats[topic]
                # Flag topics with very short interaction times or few messages
                if stats['total_minutes'] < 5 or stats['message_count'] < 3:
                    gaps.append(topic)
        
        return gaps
    
    def _calculate_student_metrics(self, df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        Calculate various metrics for each student.
        
        Args:
            df: DataFrame containing messages
            
        Returns:
            Dictionary with student metrics
        """
        student_metrics = {}
        
        for user_id in df['user_id'].unique():
            user_msgs = df[df['user_id'] == user_id]
            
            metrics = {
                'message_count': len(user_msgs),
                'question_count': len(user_msgs[user_msgs['prompt'].str.contains('|'.join(self.question_words), case=False)]),
                'avg_response_length': user_msgs['response'].str.len().mean(),
                'unique_topics': len(set(self._extract_topics(user_msgs))),
                'frustration_count': len(self._identify_frustration(user_msgs))
            }
            
            student_metrics[user_id] = metrics
        
        return student_metrics
    
    def _determine_student_cluster(self, metrics: Dict[str, float]) -> str:
        """
        Determine which cluster a student belongs to based on their metrics.
        
        Args:
            metrics: Dictionary containing student metrics
            
        Returns:
            Cluster label ('confident', 'engaged', or 'struggling')
        """
        # Simple rule-based clustering
        if metrics['frustration_count'] > 2 or metrics['question_count'] / metrics['message_count'] > 0.7:
            return 'struggling'
        elif metrics['message_count'] > 10 and metrics['unique_topics'] > 3:
            return 'engaged'
        else:
            return 'confident'
    
    def _identify_abandon_points(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Identify points where students abandoned topics.
        
        Args:
            df: DataFrame containing messages
            
        Returns:
            List of dictionaries containing abandon point information
        """
        abandon_points = []
        topics = self._extract_topics(df)
        
        for topic in set(topics):
            escaped_topic = re.escape(topic)
            topic_msgs = df[df['prompt'].str.contains(escaped_topic, case=False)]
            if len(topic_msgs) >= 2:
                # Check for large time gaps between messages
                times = pd.to_datetime(topic_msgs['timestamp'])
                time_gaps = times.diff()
                
                for idx, gap in enumerate(time_gaps):
                    if gap and gap.total_seconds() > 600:  # 10 minutes threshold
                        abandon_points.append({
                            'topic': topic,
                            'message_before': topic_msgs.iloc[idx-1]['prompt'],
                            'time_gap': gap.total_seconds() / 60,  # Convert to minutes
                            'resumed': idx < len(topic_msgs) - 1
                        })
        
        return abandon_points

    def process_chat_history(self, chat_history: List[Dict[Any, Any]]) -> Dict[str, Any]:
        """
        Process chat history data and generate comprehensive analytics.
        
        Args:
            chat_history: List of chat history documents
            session_info: Dictionary containing session metadata (topic, duration, etc.)
            
        Returns:
            Dictionary containing all analytics results
        """
        try:
            # Convert chat history to DataFrame for easier processing
            messages_data = []
            for chat in chat_history:
                for msg in chat['messages']:
                    messages_data.append({
                        'user_id': chat['user_id'],
                        'session_id': chat['session_id'],
                        'timestamp': msg['timestamp'],
                        'prompt': msg['prompt'],
                        'response': msg['response']
                    })
            
            df = pd.DataFrame(messages_data)
            
            # Generate all analytics
            analytics_results = {
                'topic_interaction': self._analyze_topic_interaction(df),
                'question_patterns': self._analyze_question_patterns(df),
                'sentiment_analysis': self._analyze_sentiment(df),
                'completion_trends': self._analyze_completion_trends(df),
                'student_clustering': self._cluster_students(df),
                'abandoned_conversations': self._analyze_abandoned_conversations(df)
            }
            
            return analytics_results
            
        except Exception as e:
            logger.error(f"Error processing chat history: {str(e)}")
            raise

    def _analyze_topic_interaction(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze topic interaction frequency and patterns."""
        topics = self._extract_topics(df)
        
        topic_stats = {
            'interaction_counts': Counter(topics),
            'revisit_patterns': self._calculate_topic_revisits(df, topics),
            'avg_time_per_topic': self._calculate_avg_time_per_topic(df, topics)
        }
        
        return topic_stats
    
    def _analyze_question_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze question patterns and identify difficult topics."""
        questions = df[df['prompt'].str.lower().str.split().apply(
            lambda x: any(word.lower() in self.question_words for word in x)
        )]
        
        question_stats = {
            'total_questions': len(questions),
            'question_types': self._categorize_questions(questions),
            'complex_chains': self._identify_complex_chains(df)
        }
        
        return question_stats
    
    def _analyze_sentiment(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Perform sentiment analysis on messages."""
        sentiments = []
        for prompt in df['prompt']:
            try:
                sentiment = self.sentiment_analyzer(prompt)[0]
                sentiments.append(sentiment['label'])
            except Exception as e:
                logger.warning(f"Error in sentiment analysis: {str(e)}")
                sentiments.append('NEUTRAL')
        
        sentiment_stats = {
            'overall_sentiment': Counter(sentiments),
            'frustration_indicators': self._identify_frustration(df),
            'resolution_times': self._calculate_resolution_times(df)
        }
        
        return sentiment_stats
    
    def _analyze_completion_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze topic completion trends and coverage."""
        completion_stats = {
            'completion_rates': self._calculate_completion_rates(df),
            'time_distribution': self._analyze_time_distribution(df),
            'coverage_gaps': self._identify_coverage_gaps(df)
        }
        
        return completion_stats
    
    def _cluster_students(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Cluster students based on interaction patterns."""
        student_metrics = self._calculate_student_metrics(df)
        
        clusters = {
            'confident': [],
            'engaged': [],
            'struggling': []
        }
        
        for student_id, metrics in student_metrics.items():
            cluster = self._determine_student_cluster(metrics)
            clusters[cluster].append(student_id)
            
        return clusters
    
    def _analyze_abandoned_conversations(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Identify and analyze abandoned conversations."""
        abandoned_stats = {
            'abandon_points': self._identify_abandon_points(df),
            'incomplete_topics': self._identify_incomplete_topics(df),
            'dropout_patterns': self._analyze_dropout_patterns(df)
        }
        
        return abandoned_stats
    
    def _identify_incomplete_topics(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Identify topics that were started but not completed by students.
        
        Args:
            df: DataFrame containing messages
            
        Returns:
            List of dictionaries containing incomplete topic information
        """
        incomplete_topics = []
        topics = self._extract_topics(df)
        
        for topic in set(topics):
            escaped_topic = re.escape(topic)
            topic_msgs = df[df['prompt'].str.contains(escaped_topic, case=False)]
            
            if len(topic_msgs) > 0:
                # Check for completion indicators
                last_msgs = topic_msgs.tail(3)  # Look at last 3 messages
                
                # Consider a topic incomplete if:
                # 1. There are unanswered questions
                # 2. Contains frustration indicators
                # 3. No positive confirmation/understanding indicators
                has_questions = last_msgs['prompt'].str.contains('|'.join(self.question_words), case=False).any()
                has_frustration = bool(self._identify_frustration(last_msgs))
                
                completion_indicators = ['understand', 'got it', 'makes sense', 'thank you', 'clear now']
                has_completion = last_msgs['prompt'].str.contains('|'.join(completion_indicators), case=False).any()
                
                if (has_questions or has_frustration) and not has_completion:
                    incomplete_topics.append({
                        'topic': topic,
                        'last_interaction': topic_msgs.iloc[-1]['timestamp'],
                        'message_count': len(topic_msgs),
                        'has_pending_questions': has_questions,
                        'shows_frustration': has_frustration
                    })
        
        return incomplete_topics

    def _analyze_dropout_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze patterns in where and why students tend to drop out of conversations.
        
        Args:
            df: DataFrame containing messages
            
        Returns:
            Dictionary containing dropout pattern analysis
        """
        dropout_analysis = {
            'timing_patterns': {},
            'topic_patterns': {},
            'complexity_indicators': {},
            'engagement_metrics': {}
        }
        
        # Analyze timing of dropouts
        timestamps = pd.to_datetime(df['timestamp'])
        time_gaps = timestamps.diff()
        dropout_points = time_gaps[time_gaps > pd.Timedelta(minutes=30)].index
        
        for point in dropout_points:
            # Get context before dropout
            context_msgs = df.loc[max(0, point-5):point]
            
            # Analyze timing
            time_of_day = timestamps[point].hour
            dropout_analysis['timing_patterns'][time_of_day] = \
                dropout_analysis['timing_patterns'].get(time_of_day, 0) + 1
            
            # Analyze topics at dropout points
            dropout_topics = self._extract_topics(context_msgs)
            for topic in dropout_topics:
                dropout_analysis['topic_patterns'][topic] = \
                    dropout_analysis['topic_patterns'].get(topic, 0) + 1
            
            # Analyze complexity
            msg_lengths = context_msgs['prompt'].str.len().mean()
            question_density = len(context_msgs[context_msgs['prompt'].str.contains(
                '|'.join(self.question_words), case=False)]) / len(context_msgs)
            
            dropout_analysis['complexity_indicators'][point] = {
                'message_length': msg_lengths,
                'question_density': question_density
            }
            
            # Analyze engagement
            dropout_analysis['engagement_metrics'][point] = {
                'messages_before_dropout': len(context_msgs),
                'response_times': time_gaps[max(0, point-5):point].mean().total_seconds() / 60
            }
        
        return dropout_analysis

    def _rank_topics_by_difficulty(self, analytics_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Rank topics by their difficulty based on various metrics from analytics results.
        
        Args:
            analytics_results: Dictionary containing all analytics data
            
        Returns:
            List of dictionaries containing topic difficulty rankings and scores
        """
        topic_difficulty = []
        
        # Extract relevant metrics for each topic
        topics = set()
        for topic in analytics_results['topic_interaction']['interaction_counts'].keys():
            
            # Calculate difficulty score based on multiple factors
            difficulty_score = 0
            
            # Factor 1: Question frequency
            question_count = sum(1 for chain in analytics_results['question_patterns']['complex_chains']
                            if chain['topic'] == topic)
            difficulty_score += question_count * 0.3
            
            # Factor 2: Frustration indicators
            frustration_count = sum(1 for indicator in analytics_results['sentiment_analysis']['frustration_indicators']
                                if topic.lower() in indicator.lower())
            difficulty_score += frustration_count * 0.25
            
            # Factor 3: Completion rate (inverse relationship)
            completion_rate = analytics_results['completion_trends']['completion_rates'].get(topic, 1.0)
            difficulty_score += (1 - completion_rate) * 0.25
            
            # Factor 4: Time spent (normalized)
            avg_time = analytics_results['topic_interaction']['avg_time_per_topic'].get(topic, 0)
            max_time = max(analytics_results['topic_interaction']['avg_time_per_topic'].values())
            normalized_time = avg_time / max_time if max_time > 0 else 0
            difficulty_score += normalized_time * 0.2
            
            topic_difficulty.append({
                'topic': topic,
                'difficulty_score': round(difficulty_score, 2),
                'metrics': {
                    'question_frequency': question_count,
                    'frustration_indicators': frustration_count,
                    'completion_rate': completion_rate,
                    'avg_time_spent': avg_time
                }
            })
        
        # Sort topics by difficulty score
        return sorted(topic_difficulty, key=lambda x: x['difficulty_score'], reverse=True)

    def _identify_support_needs(self, analytics_results: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identify specific support needs for students based on analytics results.
        
        Args:
            analytics_results: Dictionary containing all analytics data
            
        Returns:
            Dictionary containing support needs categorized by urgency
        """
        support_needs = {
            'immediate_attention': [],
            'monitoring_needed': [],
            'general_support': []
        }
        
        # Analyze struggling students
        for student_id in analytics_results['student_clustering']['struggling']:
            # Get student-specific metrics
            student_msgs = analytics_results.get('sentiment_analysis', {}).get('messages', [])
            frustration_topics = [topic for topic in analytics_results['sentiment_analysis']['frustration_indicators']
                                if any(msg['user_id'] == student_id for msg in student_msgs)]
            
            # Calculate engagement metrics
            engagement_level = len([chain for chain in analytics_results['question_patterns']['complex_chains']
                                if any(msg['user_id'] == student_id for msg in chain['messages'])])
            
            # Identify immediate attention needs
            if len(frustration_topics) >= 3 or engagement_level < 2:
                support_needs['immediate_attention'].append({
                    'student_id': student_id,
                    'issues': frustration_topics,
                    'engagement_level': engagement_level,
                    'recommended_actions': [
                        'Schedule one-on-one session',
                        'Review difficult topics',
                        'Provide additional resources'
                    ]
                })
            
            # Identify monitoring needs
            elif len(frustration_topics) >= 1 or engagement_level < 4:
                support_needs['monitoring_needed'].append({
                    'student_id': student_id,
                    'areas_of_concern': frustration_topics,
                    'engagement_level': engagement_level,
                    'recommended_actions': [
                        'Regular progress checks',
                        'Provide supplementary materials'
                    ]
                })
            
            # General support needs
            else:
                support_needs['general_support'].append({
                    'student_id': student_id,
                    'areas_for_improvement': frustration_topics,
                    'engagement_level': engagement_level,
                    'recommended_actions': [
                        'Maintain regular communication',
                        'Encourage participation'
                    ]
                })
        
        return support_needs


    def _extract_topics(self, df: pd.DataFrame) -> List[str]:
        """Extract topics from messages using spaCy."""
        topics = []
        for doc in self.nlp.pipe(df['prompt']):
            # Extract noun phrases as potential topics
            noun_phrases = [chunk.text for chunk in doc.noun_chunks]
            topics.extend(noun_phrases)
        return topics
    
    def _calculate_topic_revisits(self, df: pd.DataFrame, topics: List[str]) -> Dict[str, int]:
        """Calculate how often topics are revisited."""
        topic_visits = Counter(topics)
        return {topic: count for topic, count in topic_visits.items() if count > 1}
    
    def _calculate_avg_time_per_topic(self, df: pd.DataFrame, topics: List[str]) -> Dict[str, float]:
        """Calculate average time spent per topic."""
        topic_times = {}
        for topic in set(topics):
            escaped_topic = re.escape(topic)
            topic_msgs = df[df['prompt'].str.contains(escaped_topic, case=False)]
            if len(topic_msgs) > 1:
                time_diffs = pd.to_datetime(topic_msgs['timestamp']).diff()
                avg_time = time_diffs.mean().total_seconds() / 60  # Convert to minutes
                topic_times[topic] = avg_time
        return topic_times
    
    def _identify_complex_chains(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify complex conversation chains."""
        chains = []
        current_chain = []
        
        for idx, row in df.iterrows():
            if self._is_followup_question(row['prompt']):
                current_chain.append(row)
            else:
                if len(current_chain) >= 3:  # Consider 3+ related questions as complex chain
                    chains.append({
                        'messages': current_chain,
                        'topic': self._extract_topics([current_chain[0]['prompt']])[0],
                        'length': len(current_chain)
                    })
                current_chain = []
                
        return chains
    
    def _generate_topic_priority_list(self, analytics_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a prioritized list of topics for the upcoming session.
        
        Args:
            analytics_results: Dictionary containing all analytics data
            
        Returns:
            List of dictionaries containing topics and their priority scores
        """
        topic_priorities = []
        
        # Get difficulty rankings
        difficulty_ranking = self._rank_topics_by_difficulty(analytics_results)
        
        for topic_data in difficulty_ranking:
            topic = topic_data['topic']
            
            # Calculate priority score based on multiple factors
            priority_score = 0
            
            # Factor 1: Difficulty score (40% weight)
            priority_score += topic_data['difficulty_score'] * 0.4
            
            # Factor 2: Student frustration (25% weight)
            frustration_count = sum(1 for indicator in 
                                  analytics_results['sentiment_analysis']['frustration_indicators']
                                  if topic.lower() in indicator.lower())
            normalized_frustration = min(frustration_count / 5, 1)  # Cap at 5 frustrations
            priority_score += normalized_frustration * 0.25
            
            # Factor 3: Incomplete understanding (20% weight)
            incomplete_topics = analytics_results.get('abandoned_conversations', {}).get('incomplete_topics', [])
            if any(t['topic'] == topic for t in incomplete_topics):
                priority_score += 0.2
            
            # Factor 4: Coverage gaps (15% weight)
            if topic in analytics_results['completion_trends']['coverage_gaps']:
                priority_score += 0.15
            
            topic_priorities.append({
                'topic': topic,
                'priority_score': round(priority_score, 2),
                'reasons': {
                    'difficulty_level': topic_data['difficulty_score'],
                    'frustration_indicators': frustration_count,
                    'has_incomplete_understanding': any(t['topic'] == topic for t in incomplete_topics),
                    'has_coverage_gaps': topic in analytics_results['completion_trends']['coverage_gaps']
                },
                'recommended_focus_areas': self._generate_focus_recommendations(topic_data, analytics_results)
            })
        
        # Sort by priority score
        return sorted(topic_priorities, key=lambda x: x['priority_score'], reverse=True)

    def _generate_focus_recommendations(self, topic_data: Dict[str, Any], 
                                     analytics_results: Dict[str, Any]) -> List[str]:
        """Generate specific focus recommendations for a topic."""
        recommendations = []
        
        if topic_data['metrics']['question_frequency'] > 3:
            recommendations.append("Provide more detailed explanations and examples")
            
        if topic_data['metrics']['completion_rate'] < 0.7:
            recommendations.append("Break down complex concepts into smaller segments")
            
        if topic_data['metrics']['frustration_indicators'] > 2:
            recommendations.append("Review prerequisite concepts and provide additional context")
            
        return recommendations

    def _is_followup_question(self, prompt: str) -> bool:
        """Determine if a prompt is a follow-up question."""
        followup_indicators = {'also', 'then', 'additionally', 'furthermore', 'related to that'}
        return any(indicator in prompt.lower() for indicator in followup_indicators)
    
    def generate_faculty_report(self, analytics_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a comprehensive report for faculty."""
        report = {
            'key_findings': self._generate_key_findings(analytics_results),
            'recommended_actions': self._generate_recommendations(analytics_results),
            'topic_difficulty_ranking': self._rank_topics_by_difficulty(analytics_results),
            'student_support_needs': self._identify_support_needs(analytics_results),
            'topic_priorities': self._generate_topic_priority_list(analytics_results)
        }
    
        return report
    
    def _generate_key_findings(self, analytics_results: Dict[str, Any]) -> List[str]:
        """Generate key findings from analytics results."""
        findings = []
        
        # Analyze topic interaction patterns
        topic_stats = analytics_results['topic_interaction']
        low_interaction_topics = [topic for topic, count in topic_stats['interaction_counts'].items() 
                                if count < 3]  # Arbitrary threshold
        if low_interaction_topics:
            findings.append(f"Low engagement detected in topics: {', '.join(low_interaction_topics)}")
        
        # Analyze sentiment patterns
        sentiment_stats = analytics_results['sentiment_analysis']
        if sentiment_stats['frustration_indicators']:
            findings.append("Significant frustration detected in the following areas: " +
                          ', '.join(sentiment_stats['frustration_indicators']))
        
        # Analyze student clustering
        student_clusters = analytics_results['student_clustering']
        if len(student_clusters['struggling']) > 0:
            findings.append(f"{len(student_clusters['struggling'])} students showing signs of difficulty")
        
        return findings
    
    def _generate_recommendations(self, analytics_results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations for faculty."""
        recommendations = []
        
        # Analyze complex chains
        question_patterns = analytics_results['question_patterns']
        if question_patterns['complex_chains']:
            topics_needing_clarity = set(chain['topic'] for chain in question_patterns['complex_chains'])
            recommendations.append(f"Consider providing additional examples for: {', '.join(topics_needing_clarity)}")
        
        # Analyze completion trends
        completion_trends = analytics_results['completion_trends']
        low_completion_topics = [topic for topic, rate in completion_trends['completion_rates'].items() 
                               if rate < 0.7]  # 70% threshold
        if low_completion_topics:
            recommendations.append(f"Review and possibly simplify material for: {', '.join(low_completion_topics)}")
        
        return recommendations

# Example usage
if __name__ == "__main__":
    # Initialize analytics engine
    analytics_engine = NovaScholarAnalytics()
    
    # Sample usage with dummy data
    sample_chat_history = [
        {
            "user_id": "123",
            "session_id": "S101",
            "messages": [
                {
                    "prompt": "What is DevOps?",
                    "response": "DevOps is a software engineering practice...",
                    "timestamp": datetime.now()
                }
            ]
        }
    ]
    
    # Process analytics
    #results = analytics_engine.process_chat_history(all_chat_histories)
    
    # Generate faculty report
    #faculty_report = analytics_engine.generate_faculty_report(results)
    #print(faculty_report)
    # Print results
    # logger.info("Analytics processing completed")
    # logger.info(f"Key findings: {faculty_report['key_findings']}")
    # logger.info(f"Recommendations: {faculty_report['recommended_actions']}")
