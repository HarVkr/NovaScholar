import json
import typing_extensions as typing
import google.generativeai as genai
from typing import List, Dict, Any
import numpy as np
from collections import defaultdict

from dotenv import load_dotenv
import os
import pymongo
from pymongo import MongoClient

load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_KEY')

class EngagementMetrics(typing.TypedDict):
    participation_level: str  # "high" | "medium" | "low"
    question_quality: str     # "advanced" | "intermediate" | "basic"
    concept_understanding: str  # "strong" | "moderate" | "needs_improvement"

class StudentInsight(typing.TypedDict):
    student_id: str
    performance_level: str  # "high_performer" | "average" | "at_risk"
    struggling_topics: list[str]
    engagement_metrics: EngagementMetrics

class TopicInsight(typing.TypedDict):
    topic: str
    difficulty_level: float  # 0 to 1
    student_count: int
    common_issues: list[str]
    key_misconceptions: list[str]

class RecommendedAction(typing.TypedDict):
    action: str
    priority: str  # "high" | "medium" | "low"
    target_group: str  # "all_students" | "specific_students" | "faculty"
    reasoning: str
    expected_impact: str

class ClassDistribution(typing.TypedDict):
    high_performers: float
    average_performers: float
    at_risk: float

class CourseHealth(typing.TypedDict):
    overall_engagement: float  # 0 to 1
    critical_topics: list[str]
    class_distribution: ClassDistribution

class InterventionMetrics(typing.TypedDict):
    immediate_attention_needed: list[str]  # student_ids
    monitoring_required: list[str]  # student_ids

class AnalyticsResponse(typing.TypedDict):
    topic_insights: list[TopicInsight]
    student_insights: list[StudentInsight]
    recommended_actions: list[RecommendedAction]
    course_health: CourseHealth
    intervention_metrics: InterventionMetrics



class NovaScholarAnalytics:
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(model_name)
        
    def _create_analytics_prompt(self, chat_histories: List[Dict], all_topics: List[str]) -> str:
        """Creates a structured prompt for Gemini to analyze chat histories."""
        # Prompt 1: 
        # return f"""Analyze these student chat histories for a university course and provide detailed analytics.

        # Context:
        # - These are pre-class chat interactions between students and an AI tutor
        # - Topics covered: {', '.join(all_topics)}

        # Chat histories: {json.dumps(chat_histories, indent=2)}

        # Return the analysis in JSON format matching this exact schema:
        # {AnalyticsResponse.__annotations__}

        # Ensure all numeric values are between 0 and 1 (accuracy upto 3 decimal places) where applicable.

        # Important analysis guidelines:
        # 1. Identify topics where students show confusion or ask multiple follow-up questions
        # 2. Look for patterns in question types and complexity
        # 3. Analyze response understanding based on follow-up questions
        # 4. Consider both explicit and implicit signs of difficulty
        # 5. Focus on concept relationships and prerequisite understanding"""

        # Prompt 2: 
        # return f"""Analyze the provided student chat histories for a university course and generate concise, actionable analytics.  

        # Context:  
        # - Chat histories: {json.dumps(chat_histories, indent=2)}
        # - These are pre-class interactions between students and an AI tutor aimed at identifying learning difficulties and improving course delivery.  
        # - Topics covered: {', '.join(all_topics)}.  

        # Your task is to extract key insights that will help faculty address challenges effectively and enhance learning outcomes.  

        # Output Format:  
        # 1. Topics where students face significant difficulties:  
        # - Provide a ranked list of topics where the majority of students are struggling, based on the frequency and nature of their questions or misconceptions.  
        # - Include the percentage of students who found each topic challenging.  

        # 2. AI-recommended actions for faculty:  
        # - Suggest actionable steps to address the difficulties identified in each critical topic.  
        # - Specify the priority of each action (high, medium, low) based on the urgency and impact.  
        # - Explain the reasoning behind each recommendation and its expected impact on student outcomes.  

        # 3. Student-specific analytics (focusing on at-risk students):  
        # - Identify students categorized as "at-risk" based on their engagement levels, question complexity, and recurring struggles.  
        # - For each at-risk student, list their top 3 struggling topics and their engagement metrics (participation level, concept understanding).  
        # - Provide personalized recommendations for improving their understanding.  

        # Guidelines for Analysis:  
        # - Focus on actionable and concise insights rather than exhaustive details.  
        # - Use both explicit (e.g., direct questions) and implicit (e.g., repeated follow-ups) cues to identify areas of difficulty.  
        # - Prioritize topics with higher difficulty scores or more students struggling.  
        # - Ensure numerical values (e.g., difficulty levels, percentages) are between 0 and 1 where applicable.  

        # The response must be well-structured, concise, and highly actionable for faculty to implement improvements effectively."""  

        # Prompt 3:
        return f"""Analyze the provided student chat histories for a university course and generate concise, actionable analytics.
        Context:
        - Chat histories: {json.dumps(chat_histories, indent=2)}
        - These are pre-class interactions between students and an AI tutor aimed at identifying learning difficulties and improving course delivery.
        - Topics covered: {', '.join(all_topics)}.

        Your task is to provide detailed analytics that will help faculty address challenges effectively and enhance learning outcomes.

        Output Format (strictly follow this JSON structure):
        {{
        "topic_wise_insights": [
            {{
            "topic": "<string>",
            "struggling_percentage": <number between 0 and 1>,
            "key_issues": ["<string>", "<string>", ...],
            "key_misconceptions": ["<string>", "<string>", ...],
            "recommended_actions": {{
                "description": "<string>",
                "priority": "high|medium|low",
                "expected_outcome": "<string>"
            }}
            }}
        ],
        "ai_recommended_actions": [
        {{
            "action": "<string>",
            "priority": "high|medium|low",
            "reasoning": "<string>",
            "expected_outcome": "<string>",
            "pedagogy_recommendations": {{
                "methods": ["<string>", "<string>", ...],
                "resources": ["<string>", "<string>", ...],
                "expected_impact": "<string>"
            }}
        }}
        ],
        "student_analytics": [
            {{
            "student_id": "<string>",
            "engagement_metrics": {{
                "participation_level": <number between 0 and 1>,
                "concept_understanding": "strong|moderate|needs_improvement",
                "question_quality": "advanced|intermediate|basic"
            }},
            "struggling_topics": ["<string>", "<string>", ...],
            "personalized_recommendation": "<string>"
            }}
        ]
        }}

        Guidelines for Analysis:
        - Focus on actionable and concise insights rather than exhaustive details.
        - Use both explicit (e.g., direct questions) and implicit (e.g., repeated follow-ups) cues to identify areas of difficulty.
        - Prioritize topics with higher difficulty scores or more students struggling.
        - Ensure numerical values (e.g., difficulty levels, percentages) are between 0 and 1 where applicable.
        - Make sure to include **All** i.e. **every single student** in the analysis, not just a subset.
        - for the ai_recommended_actions:
            - Prioritize pedagogy recommendations for critical topics with the high difficulty scores or struggling percentages.
            - For each action:
                - Include specific teaching methods (e.g., interactive discussions or quizzes, problem-based learning, practical examples etc).
                - Recommend supporting resources (e.g., videos, handouts, simulations).
                - Provide reasoning for the recommendation and the expected outcomes for student learning.
                - Example:
                - **Action:** Conduct an interactive problem-solving session on "<Topic Name>".
                - **Reasoning:** Students showed difficulty in applying concepts to practical problems.
                - **Expected Outcome:** Improved practical understanding and application of the topic.
                - **Pedagogy Recommendations:**
                    - **Methods:** Group discussions, real-world case studies.
                    - **Resources:** Online interactive tools, relevant case studies, video walkthroughs.
                    - **Expected Impact:** Enhance conceptual clarity by 40% and practical application by 30%. 

        The response must adhere strictly to the above JSON structure, with all fields populated appropriately."""

    
    def _calculate_class_distribution(self, analytics: Dict) -> Dict:
        """Calculate the distribution of students across performance levels."""
        try:
            total_students = len(analytics.get("student_insights", []))
            if total_students == 0:
                return {
                    "high_performers": 0,
                    "average_performers": 0,
                    "at_risk": 0
                }
            
            distribution = defaultdict(int)
            
            for student in analytics.get("student_insights", []):
                performance_level = student.get("performance_level", "average")
                # Map performance levels to our three categories
                if performance_level in ["excellent", "high", "high_performer"]:
                    distribution["high_performers"] += 1
                elif performance_level in ["struggling", "low", "at_risk"]:
                    distribution["at_risk"] += 1
                else:
                    distribution["average_performers"] += 1
            
            # Convert to percentages
            return {
                level: count/total_students 
                for level, count in distribution.items()
            }
        except Exception as e:
            print(f"Error calculating class distribution: {str(e)}")
            return {
                "high_performers": 0,
                "average_performers": 0,
                "at_risk": 0
            }

    def _identify_urgent_cases(self, analytics: Dict) -> List[str]:
        """Identify students needing immediate attention."""
        try:
            urgent_cases = []
            for student in analytics.get("student_insights", []):
                student_id = student.get("student_id")
                if not student_id:
                    continue
                    
                # Check multiple risk factors
                risk_factors = 0
                
                # Factor 1: Performance level
                if student.get("performance_level") in ["struggling", "at_risk", "low"]:
                    risk_factors += 1
                    
                # Factor 2: Number of struggling topics
                if len(student.get("struggling_topics", [])) >= 2:
                    risk_factors += 1
                    
                # Factor 3: Engagement metrics
                engagement = student.get("engagement_metrics", {})
                if (engagement.get("participation_level") == "low" or 
                    engagement.get("concept_understanding") == "needs_improvement"):
                    risk_factors += 1
                
                # If student has multiple risk factors, add to urgent cases
                if risk_factors >= 2:
                    urgent_cases.append(student_id)
            
            return urgent_cases
        except Exception as e:
            print(f"Error identifying urgent cases: {str(e)}")
            return []

    def _identify_monitoring_cases(self, analytics: Dict) -> List[str]:
        """Identify students who need monitoring but aren't urgent cases."""
        try:
            monitoring_cases = []
            urgent_cases = set(self._identify_urgent_cases(analytics))
            
            for student in analytics.get("student_insights", []):
                student_id = student.get("student_id")
                if not student_id or student_id in urgent_cases:
                    continue
                
                # Check monitoring criteria
                monitoring_needed = False
                
                # Criterion 1: Has some struggling topics but not enough for urgent
                if len(student.get("struggling_topics", [])) == 1:
                    monitoring_needed = True
                    
                # Criterion 2: Medium-low engagement
                engagement = student.get("engagement_metrics", {})
                if engagement.get("participation_level") == "medium":
                    monitoring_needed = True
                    
                # Criterion 3: Recent performance decline
                if student.get("performance_level") == "average":
                    monitoring_needed = True
                
                if monitoring_needed:
                    monitoring_cases.append(student_id)
            
            return monitoring_cases
        except Exception as e:
            print(f"Error identifying monitoring cases: {str(e)}")
            return []

    def _identify_critical_topics(self, analytics: Dict) -> List[str]:
        """
        Identify critical topics that need attention based on multiple factors.
        Returns a list of topic names that are considered critical.
        """
        try:
            critical_topics = []
            topics = analytics.get("topic_insights", [])
            
            for topic in topics:
                if not isinstance(topic, dict):
                    continue
                    
                # Initialize score for topic criticality
                critical_score = 0
                
                # Factor 1: High difficulty level
                difficulty_level = topic.get("difficulty_level", 0)
                if difficulty_level > 0.7:
                    critical_score += 2
                elif difficulty_level > 0.5:
                    critical_score += 1
                    
                # Factor 2: Number of students struggling
                student_count = topic.get("student_count", 0)
                total_students = len(analytics.get("student_insights", []))
                if total_students > 0:
                    struggle_ratio = student_count / total_students
                    if struggle_ratio > 0.5:
                        critical_score += 2
                    elif struggle_ratio > 0.3:
                        critical_score += 1
                        
                # Factor 3: Number of common issues
                if len(topic.get("common_issues", [])) > 2:
                    critical_score += 1
                    
                # Factor 4: Number of key misconceptions
                if len(topic.get("key_misconceptions", [])) > 1:
                    critical_score += 1
                
                # If topic exceeds threshold, mark as critical
                if critical_score >= 3:
                    critical_topics.append(topic.get("topic", "Unknown Topic"))
            
            return critical_topics
            
        except Exception as e:
            print(f"Error identifying critical topics: {str(e)}")
            return []

    def _calculate_engagement(self, analytics: Dict) -> Dict:
        """
        Calculate detailed engagement metrics across all students.
        Returns a dictionary with engagement statistics.
        """
        try:
            total_students = len(analytics.get("student_insights", []))
            if total_students == 0:
                return {
                    "total_students": 0,
                    "overall_score": 0,
                    "engagement_distribution": {
                        "high": 0,
                        "medium": 0,
                        "low": 0
                    },
                    "participation_metrics": {
                        "average_topics_per_student": 0,
                        "active_participants": 0
                    }
                }
            
            engagement_levels = defaultdict(int)
            total_topics_engaged = 0
            active_participants = 0
            
            for student in analytics.get("student_insights", []):
                # Get engagement metrics
                metrics = student.get("engagement_metrics", {})
                
                # Calculate participation level
                participation = metrics.get("participation_level", "low").lower()
                engagement_levels[participation] += 1
                
                # Count topics student is engaged with
                topics_count = len(student.get("struggling_topics", []))
                total_topics_engaged += topics_count
                
                # Count active participants (students engaging with any topics)
                if topics_count > 0:
                    active_participants += 1
            
            # Calculate overall engagement score (0-1)
            weighted_score = (
                (engagement_levels["high"] * 1.0 + 
                engagement_levels["medium"] * 0.6 + 
                engagement_levels["low"] * 0.2) / total_students
            )
            
            return {
                "total_students": total_students,
                "overall_score": round(weighted_score, 2),
                "engagement_distribution": {
                    level: count/total_students 
                    for level, count in engagement_levels.items()
                },
                "participation_metrics": {
                    "average_topics_per_student": round(total_topics_engaged / total_students, 2),
                    "active_participants_ratio": round(active_participants / total_students, 2)
                }
            }
            
        except Exception as e:
            print(f"Error calculating engagement: {str(e)}")
            return {
                "total_students": 0,
                "overall_score": 0,
                "engagement_distribution": {
                    "high": 0,
                    "medium": 0,
                    "low": 0
                },
                "participation_metrics": {
                    "average_topics_per_student": 0,
                    "active_participants_ratio": 0
                }
            }

    def _process_gemini_response(self, response: str) -> Dict:
        """Process and validate Gemini's response."""
        # try:
        #     analytics = json.loads(response)
        #     return self._enrich_analytics(analytics)
        # except json.JSONDecodeError as e:
        #     print(f"Error decoding Gemini response: {e}")
        #     return self._fallback_analytics()
        try:
            # Parse JSON response
            analytics = json.loads(response)
            
            # Validate required fields exist
            required_fields = {
                "topic_insights": [],
                "student_insights": [],
                "recommended_actions": []
            }
            
            # Ensure all required fields exist with default values
            for field, default_value in required_fields.items():
                if field not in analytics or not analytics[field]:
                    analytics[field] = default_value
            
            # Now enrich the validated analytics
            return self._enrich_analytics(analytics)
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error processing Gemini response: {str(e)}")
            print(f"Raw response: {response}")
            return self._fallback_analytics()

    def _enrich_analytics(self, analytics: Dict) -> Dict:
        """Add derived insights and metrics to the analytics."""
        # Add overall course health metrics
        analytics["course_health"] = {
            "overall_engagement": self._calculate_engagement(analytics),
            "critical_topics": self._identify_critical_topics(analytics),
            "class_distribution": self._calculate_class_distribution(analytics)
        }
        
        # Add intervention urgency scores
        analytics["intervention_metrics"] = {
            "immediate_attention_needed": self._identify_urgent_cases(analytics),
            "monitoring_required": self._identify_monitoring_cases(analytics)
        }
        
        return analytics

    def _calculate_engagement(self, analytics: Dict) -> Dict:
        # """Calculate overall engagement metrics."""
        # total_students = len(analytics["student_insights"])
        # engagement_levels = defaultdict(int)
        
        # for student in analytics["student_insights"]:
        #     engagement_levels[student["engagement_metrics"]["participation_level"]] += 1
            
        # return {
        #     "total_students": total_students,
        #     "engagement_distribution": {
        #         level: count/total_students 
        #         for level, count in engagement_levels.items()
        #     }
        # }
        """Calculate overall engagement metrics with defensive programming."""
        try:
            total_students = len(analytics.get("student_insights", []))
            if total_students == 0:
                return {
                    "total_students": 0,
                    "engagement_distribution": {
                        "high": 0,
                        "medium": 0,
                        "low": 0
                    }
                }
            
            engagement_levels = defaultdict(int)
            
            for student in analytics.get("student_insights", []):
                metrics = student.get("engagement_metrics", {})
                level = metrics.get("participation_level", "low")
                engagement_levels[level] += 1
                
            return {
                "total_students": total_students,
                "engagement_distribution": {
                    level: count/total_students 
                    for level, count in engagement_levels.items()
                }
            }
        except Exception as e:
            print(f"Error calculating engagement: {str(e)}")
            return {
                "total_students": 0,
                "engagement_distribution": {
                    "high": 0,
                    "medium": 0,
                    "low": 0
                }
            }

    def _identify_critical_topics(self, analytics: Dict) -> List[Dict]:
        # """Identify topics needing immediate attention."""
        # return [
        #     topic for topic in analytics["topic_insights"]
        #     if topic["difficulty_level"] > 0.7 or 
        #     len(topic["common_issues"]) > 2
        # ]
        """Identify topics needing immediate attention with defensive programming."""
        try:
            return [
                topic for topic in analytics.get("topic_insights", [])
                if topic.get("difficulty_level", 0) > 0.7 or 
                len(topic.get("common_issues", [])) > 2
            ]
        except Exception as e:
            print(f"Error identifying critical topics: {str(e)}")
            return []

    def generate_analytics(self, chat_histories: List[Dict], all_topics: List[str]) -> Dict:
        # Method 1: (caused key 'student_insights' error): 
        # """Main method to generate analytics from chat histories."""
        # # Preprocess chat histories
        # processed_histories = self._preprocess_chat_histories(chat_histories)
        
        # # Create and send prompt to Gemini
        # prompt = self._create_analytics_prompt(processed_histories, all_topics)
        # response = self.model.generate_content(
        #     prompt, 
        #     generation_config=genai.GenerationConfig(
        #         response_mime_type="application/json",
        #         response_schema=AnalyticsResponse
        #     )
        # )
        
        # # # Process and enrich analytics
        # # analytics = self._process_gemini_response(response.text)
        # # return analytics
        # # Process, validate, and enrich the response
        # analytics = self._process_gemini_response(response.text)
    
        # # Then cast it to satisfy the type checker
        # return typing.cast(AnalyticsResponse, analytics)

        # Method 2 (possible fix): 
        # """Main method to generate analytics with better error handling."""
        # try:
        #     processed_histories = self._preprocess_chat_histories(chat_histories)
        #     prompt = self._create_analytics_prompt(processed_histories, all_topics)
            
        #     response = self.model.generate_content(
        #         prompt,
        #         generation_config=genai.GenerationConfig(
        #             response_mime_type="application/json",
        #             temperature=0.15
        #             # response_schema=AnalyticsResponse
        #         )
        #     )
            
        #     if not response.text:
        #         print("Empty response from Gemini")
        #         return self._fallback_analytics()
                
        #     # analytics = self._process_gemini_response(response.text)
        #     # return typing.cast(AnalyticsResponse, analytics)
        #     # return response.text;
        #     analytics = json.loads(response.text)
        #     return analytics
        
        # except Exception as e:
        #     print(f"Error generating analytics: {str(e)}")
        #     return self._fallback_analytics()


        # Debugging code: 
        """Main method to generate analytics with better error handling."""
        try:
            # Debug print for input validation
            print("Input validation:")
            print(f"Chat histories: {len(chat_histories)} entries")
            print(f"Topics: {all_topics}")

            if not chat_histories or not all_topics:
                print("Missing required input data")
                return self._fallback_analytics()

            # Debug the preprocessing step
            try:
                processed_histories = self._preprocess_chat_histories(chat_histories)
                print("Successfully preprocessed chat histories")
            except Exception as preprocess_error:
                print(f"Error in preprocessing: {str(preprocess_error)}")
                return self._fallback_analytics()

            # Debug the prompt creation
            try:
                prompt = self._create_analytics_prompt(processed_histories, all_topics)
                print("Successfully created prompt")
                print("Prompt preview:", prompt[:200] + "...") # Print first 200 chars
            except Exception as prompt_error:
                print(f"Error in prompt creation: {str(prompt_error)}")
                return self._fallback_analytics()

            # Rest of the function remains the same
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.15
                )
            )
            
            if not response.text:
                print("Empty response from Gemini")
                return self._fallback_analytics()
                
            analytics = json.loads(response.text)
            return analytics
            
        except Exception as e:
            print(f"Error generating analytics: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print("Full traceback:", traceback.format_exc())
            return self._fallback_analytics()

    def _preprocess_chat_histories(self, chat_histories: List[Dict]) -> List[Dict]:
        # """Preprocess chat histories to focus on relevant information."""
        # processed = []
        
        # for chat in chat_histories:
        #     print(str(chat["user_id"]))
        #     processed_chat = {
        #         "user_id": str(chat["user_id"]),
        #         "messages": [
        #             {
        #                 "prompt": msg["prompt"],
        #                 "response": msg["response"]
        #             }
        #             for msg in chat["messages"]
        #         ]
        #     }
        #     processed.append(processed_chat)
            
        # return processed

        # Code 2: 
        """Preprocess chat histories to focus on relevant information."""
        processed = []
        
        for chat in chat_histories:
            # Convert ObjectId to string if it's an ObjectId
            user_id = str(chat["user_id"]["$oid"]) if isinstance(chat["user_id"], dict) and "$oid" in chat["user_id"] else str(chat["user_id"])
            
            try:
                processed_chat = {
                    "user_id": user_id,
                    "messages": [
                        {
                            "prompt": msg["prompt"],
                            "response": msg["response"]
                        }
                        for msg in chat["messages"]
                    ]
                }
                processed.append(processed_chat)
                print(f"Successfully processed chat for user: {user_id}")
            except Exception as e:
                print(f"Error processing chat for user: {user_id}")
                print(f"Error details: {str(e)}")
                continue
                
        return processed

    def _fallback_analytics(self) -> Dict:
        # """Provide basic analytics in case of LLM processing failure."""
        # return {
        #     "topic_insights": [],
        #     "student_insights": [],
        #     "recommended_actions": [
        #         {
        #             "action": "Review analytics generation process",
        #             "priority": "high",
        #             "target_group": "system_administrators",
        #             "reasoning": "Analytics generation failed",
        #             "expected_impact": "Restore analytics functionality"
        #         }
        #     ]
        # }
        """Provide comprehensive fallback analytics that match our schema."""
        return {
            "topic_insights": [],
            "student_insights": [],
            "recommended_actions": [
                {
                    "action": "Review analytics generation process",
                    "priority": "high",
                    "target_group": "system_administrators",
                    "reasoning": "Analytics generation failed",
                    "expected_impact": "Restore analytics functionality"
                }
            ],
            "course_health": {
                "overall_engagement": 0,
                "critical_topics": [],
                "class_distribution": {
                    "high_performers": 0,
                    "average_performers": 0,
                    "at_risk": 0
                }
            },
            "intervention_metrics": {
                "immediate_attention_needed": [],
                "monitoring_required": []
            }
        }
    
# if __name__ == "__main__":
#     # Example usage
    
    
#     analytics_generator = NovaScholarAnalytics()
#     analytics = analytics_generator.generate_analytics(chat_histories, all_topics)
#     print(json.dumps(analytics, indent=2))