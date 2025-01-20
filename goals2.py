import streamlit as st
from typing import List, Dict
import httpx
from pathlib import Path
import os
from dotenv import load_dotenv
import json
import numpy as np
from pymongo import MongoClient
from openai import OpenAI
from datetime import datetime
import asyncio
import pandas as pd

# Load environment variables
load_dotenv()
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_KEY")
MONGODB_URI = os.getenv("MONGO_URI")
OPENAI_API_KEY = os.getenv("OPENAI_KEY")

# Initialize MongoDB client
client = MongoClient(MONGODB_URI)
db = client["document_analysis"]
vectors_collection = db["document_vectors"]

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)


class GoalAnalyzer:
    def __init__(self):
        self.api_key = PERPLEXITY_API_KEY
        self.base_url = "https://api.perplexity.ai/chat/completions"

    def clean_json_string(self, content: str) -> str:
        """Clean and extract valid JSON from string"""
        # Remove markdown formatting
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1]

        # Find the JSON object boundaries
        start_idx = content.find("{")
        end_idx = content.rfind("}") + 1

        if start_idx != -1 and end_idx > 0:
            content = content[start_idx:end_idx]

        # Clean up common issues
        content = content.strip()
        content = content.replace("\n", "")
        content = content.replace("'", '"')

        return content

    async def get_perplexity_analysis(self, text: str, goal: str) -> Dict:
        """Get analysis from Perplexity API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        prompt = f"""
        Analyze the following text in context of the goal: {goal}
        
        Text: {text}
        
        Provide analysis in the following JSON format:
        {{
            "themes": ["theme1", "theme2"],
            "subthemes": {{"theme1": ["subtheme1", "subtheme2"], "theme2": ["subtheme3"]}},
            "keywords": ["keyword1", "keyword2"],
            "relevance_score": 0-100
        }}
        """

        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "model": "llama-3.1-sonar-small-128k-chat",  # Updated to supported model
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an AI assistant that analyzes documents and provides structured analysis.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 1024,
                }

                # Debug info using expander
                with st.expander("Debug Info", expanded=False):
                    st.write("Request payload:", payload)

                response = await client.post(
                    self.base_url, headers=headers, json=payload, timeout=30.0
                )

                # Debug response info
                with st.expander("Response Info", expanded=False):
                    st.write("Response status:", response.status_code)
                    st.write("Response headers:", dict(response.headers))
                    st.write("Response content:", response.text)

                if response.status_code != 200:
                    error_detail = (
                        response.json() if response.content else "No error details"
                    )
                    raise Exception(
                        f"API returned status code {response.status_code}. Details: {error_detail}"
                    )

                result = response.json()
                content = (
                    result.get("choices", [{}])[0].get("message", {}).get("content", "")
                )

                # Clean and parse JSON
                cleaned_content = self.clean_json_string(content)

                try:
                    analysis = json.loads(cleaned_content)

                    # Validate required fields
                    required_fields = [
                        "themes",
                        "subthemes",
                        "keywords",
                        "relevance_score",
                    ]
                    for field in required_fields:
                        if field not in analysis:
                            analysis[field] = [] if field != "relevance_score" else 0

                    return analysis

                except json.JSONDecodeError as e:
                    st.error(f"JSON parsing error: {str(e)}")
                    st.error(f"Failed content: {cleaned_content}")
                    return {
                        "themes": ["Error parsing themes"],
                        "subthemes": {"Error": ["Failed to parse subthemes"]},
                        "keywords": ["parsing-error"],
                        "relevance_score": 0,
                    }

        except Exception as e:
            st.error(f"API Error: {str(e)}")
            return None

    def extract_text_from_file(self, file) -> str:
        """Extract text content from uploaded file"""
        try:
            text = ""
            file_type = file.type

            if file_type == "text/plain":
                text = file.getvalue().decode("utf-8")
            elif file_type == "application/pdf":
                import PyPDF2

                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text()
            elif (
                file_type
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ):
                import docx

                doc = docx.Document(file)
                text = " ".join([paragraph.text for paragraph in doc.paragraphs])

            return text
        except Exception as e:
            st.error(f"Error extracting text: {str(e)}")
            return ""


class DocumentVectorizer:
    def __init__(self):
        self.model = "text-embedding-ada-002"
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client["document_analysis"]
        self.vectors_collection = self.db["document_vectors"]

        # Create vector search index if it doesn't exist
        try:
            self.vectors_collection.create_index(
                [("vector", "2dsphere")],  # Changed to 2dsphere for vector indexing
                {
                    "vectorSearchConfig": {
                        "dimensions": 1536,  # OpenAI embedding dimensions
                        "similarity": "cosine",
                    }
                },
            )
        except Exception as e:
            st.warning(f"Vector index may already exist")

    def get_embedding(self, text: str) -> list:
        """Get embedding vector for text using OpenAI"""
        try:
            response = openai_client.embeddings.create(model=self.model, input=text)
            return response.data[0].embedding
        except Exception as e:
            st.error(f"Error getting embedding: {str(e)}")
            return None

    # Add this method to DocumentVectorizer class
    def vector_exists(self, doc_name: str) -> bool:
        """Check if vector exists for document"""
        return self.vectors_collection.count_documents({"name": doc_name}) > 0

    # Update store_vector method in DocumentVectorizer class
    def store_vector(self, doc_name: str, vector: list, text: str, goal: str = None):
        """Store document/goal vector in MongoDB using upsert"""
        try:
            vector_doc = {
                "name": doc_name,
                "vector": vector,
                "text": text,
                "type": "document" if goal is None else "goal",
                "goal": goal,
                "updated_at": datetime.utcnow(),
            }

            # Use update_one with upsert
            self.vectors_collection.update_one(
                {"name": doc_name},
                {"$set": vector_doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
                upsert=True,
            )

        except Exception as e:
            st.error(f"Error storing vector: {str(e)}")

    # Update vector_search method in DocumentVectorizer class
    def vector_search(self, query_vector: List[float], limit: int = 5) -> List[Dict]:
        """Search for similar documents using vector similarity"""
        try:
            # Get all documents
            documents = list(self.vectors_collection.find({"type": "document"}))

            # Calculate similarities
            similarities = []
            for doc in documents:
                similarity = self.calculate_similarity(query_vector, doc["vector"])
                similarities.append(
                    {
                        "name": doc["name"],
                        "text": doc["text"],
                        "similarity": similarity,  # Keep as float
                        "similarity_display": f"{similarity*100:.1f}%",  # Add display version
                    }
                )

            # Sort by similarity and get top k
            sorted_docs = sorted(
                similarities,
                key=lambda x: x["similarity"],  # Sort by float value
                reverse=True,
            )[:limit]

            return sorted_docs

        except Exception as e:
            st.error(f"Vector search error: {str(e)}")
            return []

    def find_similar_documents(self, text: str, limit: int = 5) -> List[Dict]:
        """Find similar documents for given text"""
        vector = self.get_embedding(text)
        if vector:
            return self.vector_search(vector, limit)
        return []

    def calculate_similarity(self, vector1: list, vector2: list) -> float:
        """Calculate cosine similarity between two vectors"""
        return np.dot(vector1, vector2) / (
            np.linalg.norm(vector1) * np.linalg.norm(vector2)
        )


def display_analysis_results(analysis: Dict):
    """Display analysis results in Streamlit UI"""
    if not analysis:
        return

    # Display Themes
    st.subheader("Themes")
    for theme in analysis.get("themes", []):
        with st.expander(f"🎯 {theme}"):
            # Display subthemes for this theme
            subthemes = analysis.get("subthemes", {}).get(theme, [])
            if subthemes:
                st.write("**Subthemes:**")
                for subtheme in subthemes:
                    st.write(f"- {subtheme}")

    # Display Keywords
    st.subheader("Keywords")
    keywords = analysis.get("keywords", [])
    st.write(" | ".join([f"🔑 {keyword}" for keyword in keywords]))

    # Display Relevance Score
    score = analysis.get("relevance_score", 0)
    st.metric("Relevance Score", f"{score}%")


def display_analyst_dashboard():
    st.title("Multi-Goal Document Analysis")

    with st.sidebar:
        st.markdown("### Input Section")
        tab1, tab2 = st.tabs(["Document Analysis", "Similarity Search"])
        # tab1, tab2 = st.tabs(["Document Analysis", "Similarity Search"])

        with tab1:
            # Multiple goals input
            num_goals = st.number_input("Number of goals:", min_value=1, value=1)
            goals = []
            for i in range(num_goals):
                goal = st.text_area(f"Goal {i+1}:", key=f"goal_{i}", height=100)
                if goal:
                    goals.append(goal)

            uploaded_files = st.file_uploader(
                "Upload documents",
                accept_multiple_files=True,
                type=["txt", "pdf", "docx"],
            )
            analyze_button = (
                st.button("Analyze Documents") if goals and uploaded_files else None
            )

        with tab2:
            # Keep existing similarity search tab
            search_text = st.text_area("Enter text to find similar documents:")
            search_limit = st.slider("Number of results", 1, 10, 5)
            search_button = st.button("Search Similar") if search_text else None

        if st.button("Logout", use_container_width=True):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

    if analyze_button:
        analyzer = GoalAnalyzer()
        vectorizer = DocumentVectorizer()

        # Store vectors
        doc_vectors = {}
        goal_vectors = {}

        # Process goals first
        with st.spinner("Processing goals..."):
            for i, goal in enumerate(goals):
                vector = vectorizer.get_embedding(goal)
                if vector:
                    goal_vectors[f"Goal {i+1}"] = vector
                    vectorizer.store_vector(f"Goal {i+1}", vector, goal, goal)

        # Process documents
        with st.spinner("Processing documents..."):
            for file in uploaded_files:
                st.markdown(f"### Analysis for {file.name}")

                if vectorizer.vector_exists(file.name):
                    st.info(f"Vector already exists for {file.name}")
                    existing_doc = vectorizer.vectors_collection.find_one(
                        {"name": file.name}
                    )
                    doc_vectors[file.name] = existing_doc["vector"]
                else:
                    text = analyzer.extract_text_from_file(file)
                    if not text:
                        st.warning(f"Could not extract text from {file.name}")
                        continue

                    vector = vectorizer.get_embedding(text)
                    if vector:
                        doc_vectors[file.name] = vector
                        vectorizer.store_vector(file.name, vector, text)

                # Display goal similarities
                st.subheader("Goal Relevance Scores")
                col1, col2 = st.columns([1, 2])

                with col1:
                    for goal_name, goal_vector in goal_vectors.items():
                        similarity = (
                            vectorizer.calculate_similarity(
                                doc_vectors[file.name], goal_vector
                            )
                            * 100
                        )
                        st.metric(f"{goal_name}", f"{similarity:.1f}%")

                with col2:
                    # Get analysis for all goals combined
                    analysis = asyncio.run(
                        analyzer.get_perplexity_analysis(text, " | ".join(goals))
                    )
                    display_analysis_results(analysis)

                st.divider()

            # Document similarity matrix
            if len(doc_vectors) > 1:
                st.markdown("### Document Similarity Matrix")
                files = list(doc_vectors.keys())
                similarity_matrix = []

                for file1 in files:
                    row = []
                    for file2 in files:
                        similarity = vectorizer.calculate_similarity(
                            doc_vectors[file1], doc_vectors[file2]
                        )
                        row.append(similarity)
                    similarity_matrix.append(row)

                df = pd.DataFrame(similarity_matrix, columns=files, index=files)
                st.dataframe(df.style.background_gradient(cmap="RdYlGn"))

                # Add goal-document similarity matrix
                st.markdown("### Goal-Document Similarity Matrix")
                goal_doc_matrix = []
                goal_names = list(goal_vectors.keys())

                for file in files:
                    row = []
                    for goal in goal_names:
                        similarity = vectorizer.calculate_similarity(
                            doc_vectors[file], goal_vectors[goal]
                        )
                        row.append(similarity)
                    goal_doc_matrix.append(row)

                df_goals = pd.DataFrame(
                    goal_doc_matrix, columns=goal_names, index=files
                )
                st.dataframe(df_goals.style.background_gradient(cmap="RdYlGn"))

    # Keep existing similarity search functionality
    elif search_button:
        vectorizer = DocumentVectorizer()
        with st.spinner("Searching similar documents..."):
            query_vector = vectorizer.get_embedding(search_text)
            if query_vector:
                similar_docs = vectorizer.vector_search(query_vector, search_limit)

                if similar_docs:
                    st.markdown("### Similar Documents Found")

                    # Create DataFrame with numeric similarities
                    df = pd.DataFrame(similar_docs)

                    # Apply gradient to numeric column
                    styled_df = df[["name", "similarity"]].style.background_gradient(
                        cmap="RdYlGn", subset=["similarity"]
                    )

                    # Format display after styling
                    styled_df = styled_df.format({"similarity": "{:.1%}"})

                    st.dataframe(styled_df)

                    # Show document contents
                    for doc in similar_docs:
                        with st.expander(
                            f"📄 {doc['name']} (Similarity: {doc['similarity_display']})"
                        ):
                            st.text(
                                doc["text"][:20] + "..."
                                if len(doc["text"]) > 20
                                else doc["text"]
                            )
                else:
                    st.info("No similar documents found")
            else:
                st.error("Could not process search query")


def main():
    st.title("Multi-Goal Document Analysis")

    with st.sidebar:
        st.markdown("### Input Section")
        tab1, tab2 = st.tabs(["Document Analysis", "Similarity Search"])
        # tab1, tab2 = st.tabs(["Document Analysis", "Similarity Search"])

        with tab1:
            # Multiple goals input
            num_goals = st.number_input("Number of goals:", min_value=1, value=1)
            goals = []
            for i in range(num_goals):
                goal = st.text_area(f"Goal {i+1}:", key=f"goal_{i}", height=100)
                if goal:
                    goals.append(goal)

            uploaded_files = st.file_uploader(
                "Upload documents",
                accept_multiple_files=True,
                type=["txt", "pdf", "docx"],
            )
            analyze_button = (
                st.button("Analyze Documents") if goals and uploaded_files else None
            )

        with tab2:
            # Keep existing similarity search tab
            search_text = st.text_area("Enter text to find similar documents:")
            search_limit = st.slider("Number of results", 1, 10, 5)
            search_button = st.button("Search Similar") if search_text else None

    if analyze_button:
        analyzer = GoalAnalyzer()
        vectorizer = DocumentVectorizer()

        # Store vectors
        doc_vectors = {}
        goal_vectors = {}

        # Process goals first
        with st.spinner("Processing goals..."):
            for i, goal in enumerate(goals):
                vector = vectorizer.get_embedding(goal)
                if vector:
                    goal_vectors[f"Goal {i+1}"] = vector
                    vectorizer.store_vector(f"Goal {i+1}", vector, goal, goal)

        # Process documents
        with st.spinner("Processing documents..."):
            for file in uploaded_files:
                st.markdown(f"### Analysis for {file.name}")

                if vectorizer.vector_exists(file.name):
                    st.info(f"Vector already exists for {file.name}")
                    existing_doc = vectorizer.vectors_collection.find_one(
                        {"name": file.name}
                    )
                    doc_vectors[file.name] = existing_doc["vector"]
                else:
                    text = analyzer.extract_text_from_file(file)
                    if not text:
                        st.warning(f"Could not extract text from {file.name}")
                        continue

                    vector = vectorizer.get_embedding(text)
                    if vector:
                        doc_vectors[file.name] = vector
                        vectorizer.store_vector(file.name, vector, text)

                # Display goal similarities
                st.subheader("Goal Relevance Scores")
                col1, col2 = st.columns([1, 2])

                with col1:
                    for goal_name, goal_vector in goal_vectors.items():
                        similarity = (
                            vectorizer.calculate_similarity(
                                doc_vectors[file.name], goal_vector
                            )
                            * 100
                        )
                        st.metric(f"{goal_name}", f"{similarity:.1f}%")

                with col2:
                    # Get analysis for all goals combined
                    analysis = asyncio.run(
                        analyzer.get_perplexity_analysis(text, " | ".join(goals))
                    )
                    display_analysis_results(analysis)

                st.divider()

            # Document similarity matrix
            if len(doc_vectors) > 1:
                st.markdown("### Document Similarity Matrix")
                files = list(doc_vectors.keys())
                similarity_matrix = []

                for file1 in files:
                    row = []
                    for file2 in files:
                        similarity = vectorizer.calculate_similarity(
                            doc_vectors[file1], doc_vectors[file2]
                        )
                        row.append(similarity)
                    similarity_matrix.append(row)

                df = pd.DataFrame(similarity_matrix, columns=files, index=files)
                st.dataframe(df.style.background_gradient(cmap="RdYlGn"))

                # Add goal-document similarity matrix
                st.markdown("### Goal-Document Similarity Matrix")
                goal_doc_matrix = []
                goal_names = list(goal_vectors.keys())

                for file in files:
                    row = []
                    for goal in goal_names:
                        similarity = vectorizer.calculate_similarity(
                            doc_vectors[file], goal_vectors[goal]
                        )
                        row.append(similarity)
                    goal_doc_matrix.append(row)

                df_goals = pd.DataFrame(
                    goal_doc_matrix, columns=goal_names, index=files
                )
                st.dataframe(df_goals.style.background_gradient(cmap="RdYlGn"))

    # Keep existing similarity search functionality
    elif search_button:
        vectorizer = DocumentVectorizer()
        with st.spinner("Searching similar documents..."):
            query_vector = vectorizer.get_embedding(search_text)
            if query_vector:
                similar_docs = vectorizer.vector_search(query_vector, search_limit)

                if similar_docs:
                    st.markdown("### Similar Documents Found")

                    # Create DataFrame with numeric similarities
                    df = pd.DataFrame(similar_docs)

                    # Apply gradient to numeric column
                    styled_df = df[["name", "similarity"]].style.background_gradient(
                        cmap="RdYlGn", subset=["similarity"]
                    )

                    # Format display after styling
                    styled_df = styled_df.format({"similarity": "{:.1%}"})

                    st.dataframe(styled_df)

                    # Show document contents
                    for doc in similar_docs:
                        with st.expander(
                            f"📄 {doc['name']} (Similarity: {doc['similarity_display']})"
                        ):
                            st.text(
                                doc["text"][:20] + "..."
                                if len(doc["text"]) > 20
                                else doc["text"]
                            )
                else:
                    st.info("No similar documents found")
            else:
                st.error("Could not process search query")


if __name__ == "__main__":
    main()
