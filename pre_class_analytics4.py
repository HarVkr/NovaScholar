import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Tuple
import spacy
from collections import Counter, defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from textblob import TextBlob
import networkx as nx
from scipy import stats
import logging
import json
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TopicDifficulty(Enum):
    EASY = "easy"
    MODERATE = "moderate"
    DIFFICULT = "difficult"
    VERY_DIFFICULT = "very_difficult"

@dataclass
class QuestionMetrics:
    complexity_score: float
    follow_up_count: int
    clarification_count: int
    time_spent: float
    sentiment_score: float

@dataclass
class TopicInsights:
    difficulty_level: TopicDifficulty
    common_confusion_points: List[str]
    question_patterns: List[str]
    time_distribution: Dict[str, float]
    engagement_metrics: Dict[str, float]
    recommended_focus_areas: List[str]

class PreClassAnalytics:
    def __init__(self, nlp_model: str = "en_core_web_lg"):
        """Initialize the analytics system with necessary components."""
        self.nlp = spacy.load(nlp_model)
        self.question_indicators = {
            "what", "why", "how", "when", "where", "which", "who", 
            "whose", "whom", "can", "could", "would", "will", "explain"
        }
        self.confusion_indicators = {
            "confused", "don't understand", "unclear", "not clear",
            "stuck", "difficult", "hard", "help", "explain again"
        }
        self.follow_up_indicators = {
            "also", "another", "additionally", "furthermore", "moreover",
            "besides", "related", "similarly", "again"
        }
        
    def preprocess_chat_history(self, chat_history: List[Dict]) -> pd.DataFrame:
        """Convert chat history to DataFrame with enhanced features."""
        messages = []
        for chat in chat_history:
            user_id = chat['user_id']['$oid']
            for msg in chat['messages']:
                messages.append({
                    'user_id': user_id,
                    'timestamp': pd.to_datetime(msg['timestamp']['$date']),
                    'prompt': msg['prompt'],
                    'response': msg['response'],
                    'is_question': any(q in msg['prompt'].lower() for q in self.question_indicators),
                    'shows_confusion': any(c in msg['prompt'].lower() for c in self.confusion_indicators),
                    'is_followup': any(f in msg['prompt'].lower() for f in self.follow_up_indicators)
                })
        
        df = pd.DataFrame(messages)
        df['sentiment'] = df['prompt'].apply(lambda x: TextBlob(x).sentiment.polarity)
        return df

    def extract_topic_hierarchies(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Extract hierarchical topic relationships from conversations."""
        topic_hierarchy = defaultdict(list)
        
        for _, row in df.iterrows():
            doc = self.nlp(row['prompt'])
            
            # Extract main topics and subtopics using noun chunks and dependencies
            main_topics = []
            subtopics = []
            
            for chunk in doc.noun_chunks:
                if chunk.root.dep_ in ('nsubj', 'dobj'):
                    main_topics.append(chunk.text.lower())
                else:
                    subtopics.append(chunk.text.lower())
            
            # Build hierarchy
            for main_topic in main_topics:
                topic_hierarchy[main_topic].extend(subtopics)
        
        # Clean and deduplicate
        return {k: list(set(v)) for k, v in topic_hierarchy.items()}

    def analyze_topic_difficulty(self, df: pd.DataFrame, topic: str) -> TopicDifficulty:
        """Determine topic difficulty based on various metrics."""
        topic_msgs = df[df['prompt'].str.contains(topic, case=False)]
        
        # Calculate difficulty indicators
        confusion_rate = topic_msgs['shows_confusion'].mean()
        question_rate = topic_msgs['is_question'].mean()
        follow_up_rate = topic_msgs['is_followup'].mean()
        avg_sentiment = topic_msgs['sentiment'].mean()
        
        # Calculate composite difficulty score
        difficulty_score = (
            confusion_rate * 0.4 +
            question_rate * 0.3 +
            follow_up_rate * 0.2 +
            (1 - (avg_sentiment + 1) / 2) * 0.1
        )
        
        # Map score to difficulty level
        if difficulty_score < 0.3:
            return TopicDifficulty.EASY
        elif difficulty_score < 0.5:
            return TopicDifficulty.MODERATE
        elif difficulty_score < 0.7:
            return TopicDifficulty.DIFFICULT
        else:
            return TopicDifficulty.VERY_DIFFICULT

    def identify_confusion_patterns(self, df: pd.DataFrame, topic: str) -> List[str]:
        """Identify common patterns in student confusion."""
        confused_msgs = df[
            (df['prompt'].str.contains(topic, case=False)) & 
            (df['shows_confusion'])
        ]['prompt']
        
        patterns = []
        for msg in confused_msgs:
            doc = self.nlp(msg)
            
            # Extract key phrases around confusion indicators
            for sent in doc.sents:
                for token in sent:
                    if token.text.lower() in self.confusion_indicators:
                        # Get context window around confusion indicator
                        context = sent.text
                        patterns.append(context)
        
        # Group similar patterns
        if patterns:
            vectorizer = TfidfVectorizer(ngram_range=(1, 3))
            tfidf_matrix = vectorizer.fit_transform(patterns)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            # Cluster similar patterns
            G = nx.Graph()
            for i in range(len(patterns)):
                for j in range(i + 1, len(patterns)):
                    if similarity_matrix[i][j] > 0.5:  # Similarity threshold
                        G.add_edge(i, j)
            
            # Extract representative patterns from each cluster
            clusters = list(nx.connected_components(G))
            return [patterns[min(cluster)] for cluster in clusters]
        
        return []

    def analyze_question_patterns(self, df: pd.DataFrame, topic: str) -> List[str]:
        """Analyze patterns in student questions about the topic."""
        topic_questions = df[
            (df['prompt'].str.contains(topic, case=False)) & 
            (df['is_question'])
        ]['prompt']
        
        question_types = defaultdict(list)
        for question in topic_questions:
            doc = self.nlp(question)
            
            # Categorize questions
            if any(token.text.lower() in {"what", "define", "explain"} for token in doc):
                question_types["conceptual"].append(question)
            elif any(token.text.lower() in {"how", "steps", "process"} for token in doc):
                question_types["procedural"].append(question)
            elif any(token.text.lower() in {"why", "reason", "because"} for token in doc):
                question_types["reasoning"].append(question)
            else:
                question_types["other"].append(question)
        
        # Extract patterns from each category
        patterns = []
        for category, questions in question_types.items():
            if questions:
                vectorizer = TfidfVectorizer(ngram_range=(1, 3))
                tfidf_matrix = vectorizer.fit_transform(questions)
                
                # Get most representative questions
                feature_array = np.mean(tfidf_matrix.toarray(), axis=0)
                tfidf_sorting = np.argsort(feature_array)[::-1]
                features = vectorizer.get_feature_names_out()
                
                patterns.append(f"{category}: {' '.join(features[tfidf_sorting[:3]])}")
        
        return patterns

    def analyze_time_distribution(self, df: pd.DataFrame, topic: str) -> Dict[str, float]:
        """Analyze time spent on different aspects of the topic."""
        topic_msgs = df[df['prompt'].str.contains(topic, case=False)].copy()
        if len(topic_msgs) < 2:
            return {}
        
        topic_msgs['time_diff'] = topic_msgs['timestamp'].diff()
        
        # Calculate time distribution
        distribution = {
            'total_time': topic_msgs['time_diff'].sum().total_seconds() / 60,
            'avg_time_per_message': topic_msgs['time_diff'].mean().total_seconds() / 60,
            'max_time_gap': topic_msgs['time_diff'].max().total_seconds() / 60,
            'time_spent_on_questions': topic_msgs[topic_msgs['is_question']]['time_diff'].sum().total_seconds() / 60,
            'time_spent_on_confusion': topic_msgs[topic_msgs['shows_confusion']]['time_diff'].sum().total_seconds() / 60
        }
        
        return distribution

    def calculate_engagement_metrics(self, df: pd.DataFrame, topic: str) -> Dict[str, float]:
        """Calculate student engagement metrics for the topic."""
        topic_msgs = df[df['prompt'].str.contains(topic, case=False)]
        
        metrics = {
            'message_count': len(topic_msgs),
            'question_ratio': topic_msgs['is_question'].mean(),
            'confusion_ratio': topic_msgs['shows_confusion'].mean(),
            'follow_up_ratio': topic_msgs['is_followup'].mean(),
            'avg_sentiment': topic_msgs['sentiment'].mean(),
            'engagement_score': 0.0  # Will be calculated below
        }
        
        # Calculate engagement score
        metrics['engagement_score'] = (
            metrics['message_count'] * 0.3 +
            metrics['question_ratio'] * 0.25 +
            metrics['follow_up_ratio'] * 0.25 +
            (metrics['avg_sentiment'] + 1) / 2 * 0.2  # Normalize sentiment to 0-1
        )
        
        return metrics

    def generate_topic_insights(self, df: pd.DataFrame, topic: str) -> TopicInsights:
        """Generate comprehensive insights for a topic."""
        difficulty = self.analyze_topic_difficulty(df, topic)
        confusion_points = self.identify_confusion_patterns(df, topic)
        question_patterns = self.analyze_question_patterns(df, topic)
        time_distribution = self.analyze_time_distribution(df, topic)
        engagement_metrics = self.calculate_engagement_metrics(df, topic)
        
        # Generate recommended focus areas based on insights
        focus_areas = []
        
        if difficulty in (TopicDifficulty.DIFFICULT, TopicDifficulty.VERY_DIFFICULT):
            focus_areas.append("Fundamental concept reinforcement needed")
        
        if confusion_points:
            focus_areas.append(f"Address common confusion around: {', '.join(confusion_points[:3])}")
        
        if engagement_metrics['confusion_ratio'] > 0.3:
            focus_areas.append("Consider alternative teaching approaches")
        
        if time_distribution.get('time_spent_on_questions', 0) > time_distribution.get('total_time', 0) * 0.5:
            focus_areas.append("More practical examples or demonstrations needed")
        
        return TopicInsights(
            difficulty_level=difficulty,
            common_confusion_points=confusion_points,
            question_patterns=question_patterns,
            time_distribution=time_distribution,
            engagement_metrics=engagement_metrics,
            recommended_focus_areas=focus_areas
        )

    def analyze_student_progress(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze individual student progress and learning patterns."""
        student_progress = {}
        
        for student_id in df['user_id'].unique():
            student_msgs = df[df['user_id'] == student_id]
            
            # Calculate student-specific metrics
            progress = {
                'total_messages': len(student_msgs),
                'questions_asked': student_msgs['is_question'].sum(),
                'confusion_instances': student_msgs['shows_confusion'].sum(),
                'avg_sentiment': student_msgs['sentiment'].mean(),
                'topic_engagement': {},
                'learning_pattern': self._identify_learning_pattern(student_msgs)
            }
            
            # Analyze topic-specific engagement
            topics = self.extract_topic_hierarchies(student_msgs)
            for topic in topics:
                topic_msgs = student_msgs[student_msgs['prompt'].str.contains(topic, case=False)]
                progress['topic_engagement'][topic] = {
                    'message_count': len(topic_msgs),
                    'confusion_rate': topic_msgs['shows_confusion'].mean(),
                    'sentiment_trend': stats.linregress(
                        range(len(topic_msgs)),
                        topic_msgs['sentiment']
                    ).slope
                }
            
            student_progress[student_id] = progress
        
        return student_progress

    def _identify_learning_pattern(self, student_msgs: pd.DataFrame) -> str:
        """Identify student's learning pattern based on their interaction style."""
        # Calculate key metrics
        question_ratio = student_msgs['is_question'].mean()
        confusion_ratio = student_msgs['shows_confusion'].mean()
        follow_up_ratio = student_msgs['is_followup'].mean()
        sentiment_trend = stats.linregress(
            range(len(student_msgs)),
            student_msgs['sentiment']
        ).slope
        
        # Identify pattern
        if question_ratio > 0.6:
            return "Inquisitive Learner"
        elif confusion_ratio > 0.4:
            return "Needs Additional Support"
        elif follow_up_ratio > 0.5:
            return "Deep Dive Learner"
        elif sentiment_trend > 0:
            return "Progressive Learner"
        else:
            return "Steady Learner"

    def generate_comprehensive_report(self, chat_history: List[Dict]) -> Dict[str, Any]:
        """Generate a comprehensive analytics report."""
        # Preprocess chat history
        df = self.preprocess_chat_history(chat_history)
        
        # Extract topics
        topics = self.extract_topic_hierarchies(df)
        
        report = {
            'topics': {},
            'student_progress': self.analyze_student_progress(df),
            'overall_metrics': {
                'total_conversations': len(df),
                'unique_students': df['user_id'].nunique(),
                'avg_sentiment': df['sentiment'].mean(),
                'most_discussed_topics': Counter(
                    topic for topics_list in topics.values() 
                    for topic in topics_list
                ).most_common(5)
            }
        }
        
        # Generate topic-specific insights
        for main_topic, subtopics in topics.items():
            subtopic_insights = {}
            for subtopic in subtopics:
                subtopic_insights[subtopic] = {
                    'insights': self.generate_topic_insights(df, subtopic),
                    'related_topics': [t for t in subtopics if t != subtopic],
                    'student_engagement': {
                        student_id: self.calculate_engagement_metrics(
                            df[df['user_id'] == student_id], 
                            subtopic
                        )
                        for student_id in df['user_id'].unique()
                    }
                }
            
            report['topics'][main_topic] = {
                'insights': self.generate_topic_insights(df, main_topic),
                'subtopics': subtopic_insights,
                'topic_relationships': {
                    'hierarchy_depth': len(subtopics),
                    'connection_strength': self._calculate_topic_connections(df, main_topic, subtopics),
                    'progression_path': self._identify_topic_progression(df, main_topic, subtopics)
                }
            }
        
        # Add temporal analysis
        report['temporal_analysis'] = {
            'daily_engagement': df.groupby(df['timestamp'].dt.date).agg({
                'user_id': 'count',
                'is_question': 'sum',
                'shows_confusion': 'sum',
                'sentiment': 'mean'
            }).to_dict(),
            'peak_activity_hours': df.groupby(df['timestamp'].dt.hour)['user_id'].count().nlargest(3).to_dict(),
            'learning_trends': self._analyze_learning_trends(df)
        }
        
        # Add recommendations
        report['recommendations'] = self._generate_recommendations(report)
        
        return report

    def _calculate_topic_connections(self, df: pd.DataFrame, main_topic: str, subtopics: List[str]) -> Dict[str, float]:
        """Calculate connection strength between topics based on co-occurrence."""
        connections = {}
        main_topic_msgs = df[df['prompt'].str.contains(main_topic, case=False)]
        
        for subtopic in subtopics:
            cooccurrence = df[
                df['prompt'].str.contains(main_topic, case=False) & 
                df['prompt'].str.contains(subtopic, case=False)
            ].shape[0]
            
            connection_strength = cooccurrence / len(main_topic_msgs) if len(main_topic_msgs) > 0 else 0
            connections[subtopic] = connection_strength
        
        return connections

    def _identify_topic_progression(self, df: pd.DataFrame, main_topic: str, subtopics: List[str]) -> List[str]:
        """Identify optimal topic progression path based on student interactions."""
        topic_difficulties = {}
        
        for subtopic in subtopics:
            difficulty = self.analyze_topic_difficulty(df, subtopic)
            topic_difficulties[subtopic] = difficulty.value
        
        # Sort subtopics by difficulty
        return sorted(subtopics, key=lambda x: topic_difficulties[x])

    def _analyze_learning_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze overall learning trends across the dataset."""
        return {
            'sentiment_trend': stats.linregress(
                range(len(df)),
                df['sentiment']
            )._asdict(),
            'confusion_trend': stats.linregress(
                range(len(df)),
                df['shows_confusion']
            )._asdict(),
            'engagement_progression': self._calculate_engagement_progression(df)
        }

    def _calculate_engagement_progression(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate how student engagement changes over time."""
        df['week'] = df['timestamp'].dt.isocalendar().week
        weekly_engagement = df.groupby('week').agg({
            'is_question': 'mean',
            'shows_confusion': 'mean',
            'is_followup': 'mean',
            'sentiment': 'mean'
        })
        
        return {
            'question_trend': stats.linregress(
                range(len(weekly_engagement)),
                weekly_engagement['is_question']
            ).slope,
            'confusion_trend': stats.linregress(
                range(len(weekly_engagement)),
                weekly_engagement['shows_confusion']
            ).slope,
            'follow_up_trend': stats.linregress(
                range(len(weekly_engagement)),
                weekly_engagement['is_followup']
            ).slope,
            'sentiment_trend': stats.linregress(
                range(len(weekly_engagement)),
                weekly_engagement['sentiment']
            ).slope
        }

    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on the analysis."""
        recommendations = []
        
        # Analyze difficulty distribution
        difficult_topics = [
            topic for topic, data in report['topics'].items()
            if data['insights'].difficulty_level in 
            (TopicDifficulty.DIFFICULT, TopicDifficulty.VERY_DIFFICULT)
        ]
        
        if difficult_topics:
            recommendations.append(
                f"Consider providing additional resources for challenging topics: {', '.join(difficult_topics)}"
            )
        
        # Analyze student engagement
        avg_engagement = np.mean([
            progress['questions_asked'] / progress['total_messages']
            for progress in report['student_progress'].values()
        ])
        
        if avg_engagement < 0.3:
            recommendations.append(
                "Implement more interactive elements to increase student engagement"
            )
        
        # Analyze temporal patterns
        peak_hours = list(report['temporal_analysis']['peak_activity_hours'].keys())
        recommendations.append(
            f"Consider scheduling additional support during peak activity hours: {peak_hours}"
        )
        
        # Analyze learning trends
        sentiment_trend = report['temporal_analysis']['learning_trends']['sentiment_trend']
        if sentiment_trend < 0:
            recommendations.append(
                "Review teaching approach to address declining student satisfaction"
            )
        
        return recommendations

if __name__ == "__main__":
    # Load chat history data
    with open("chat_history_corpus.json", "r", encoding="utf-8") as file:
        chat_history = json.load(file)
    
    # Initialize analytics system
    analytics = PreClassAnalytics()
    
    # Generate comprehensive report
    report = analytics.generate_comprehensive_report(chat_history)
    print(json.dumps(report, indent=2))