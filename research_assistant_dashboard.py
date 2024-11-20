import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Document,
    GPTVectorStoreIndex,
)
from bson import ObjectId
import requests
import openai
import numpy as np
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from llama_index.embeddings.openai import OpenAIEmbedding
from typing import List, Dict

# Initialize Perplexity API and OpenAI API
load_dotenv()
perplexity_api_key = os.getenv("PERPLEXITY_KEY")
openai.api_key = os.getenv("OPENAI_KEY")

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["novascholar_db"]
research_papers_collection = db["research_papers"]


def fetch_perplexity_data(api_key, topic):
    """
    Fetch research papers data from Perplexity API with proper formatting
    """
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}",
    }

    # Structured prompt to get properly formatted response
    messages = [
        {
            "role": "system",
            "content": """You are a research paper retrieval expert. For the given topic, return exactly 10 research papers in the following format:
            Title: Paper Title
            Authors: Author 1, Author 2
            Year: YYYY
            Content: Detailed paper content with abstract and key findings
            URL: DOI or paper URL
            """,
        },
        {"role": "user", "content": f"Find 10 research papers about: {topic}"},
    ]

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
        response = client.chat.completions.create(
            model="llama-3.1-sonar-small-128k-chat",  # Use the best Perplexity model
            messages=messages,
        )

        # Extract and validate response
        content = response.choices[0].message.content
        st.write("Fetched Data:", content)  # Debugging line to check the fetched data

        return content

    except Exception as e:
        st.error(f"Failed to fetch data from Perplexity API: {str(e)}")
        return ""


def split_and_vectorize_papers(content: str) -> List[Dict]:
    """Split and vectorize papers using OpenAI embeddings"""
    papers = content.split("\n\n")

    # Initialize OpenAI client
    # client = OpenAI()  # Uses api_key from environment variable
    vectors = []

    for paper in papers:
        try:
            # Get embedding using OpenAI's API directly
            response = openai.embeddings.create(
                model="text-embedding-ada-002", input=paper, encoding_format="float"
            )

            # Extract embedding from response
            embedding = response.data[0].embedding

            vectors.append(
                {"content": paper, "vector": embedding, "timestamp": datetime.utcnow()}
            )

        except Exception as e:
            st.error(f"Error vectorizing paper: {str(e)}")
            continue

    return vectors


def store_papers_in_mongodb(papers):
    """Store papers with vectors in MongoDB"""
    try:
        for paper in papers:
            # Prepare MongoDB document
            mongo_doc = {
                "content": paper["content"],
                "vector": paper["vector"],
                "created_at": datetime.utcnow(),
            }

            # Insert into MongoDB
            db.papers.update_one(
                {"content": paper["content"]}, {"$set": mongo_doc}, upsert=True
            )

        st.success(f"Stored {len(papers)} papers in database")
        return True
    except Exception as e:
        st.error(f"Error storing papers: {str(e)}")


def get_research_papers(query):
    """
    Get and store research papers with improved error handling
    """
    # Fetch papers from Perplexity
    content = fetch_perplexity_data(perplexity_api_key, query)

    if not content:
        return []

    # Split and vectorize papers
    papers = split_and_vectorize_papers(content)

    # Store papers in MongoDB
    if store_papers_in_mongodb(papers):
        return papers
    else:
        st.warning("Failed to store papers in database, but returning fetched results")
        return papers


def analyze_research_gaps(papers):
    """
    Analyze research gaps with improved prompt and error handling
    """
    if not papers:
        return "No papers provided for analysis"

    # Prepare paper summaries for analysis
    paper_summaries = "\n\n".join(
        [
            f"Key Findings: {paper['content'][:500]}..."
            # f"Title: {paper['title']}\nYear: {paper['year']}\nKey Findings: {paper['content'][:500]}..."
            for paper in papers
        ]
    )

    headers = {
        "Authorization": f"Bearer {perplexity_api_key}",
        "Content-Type": "application/json",
    }

    data = {
        "messages": [
            {
                "role": "system",
                "content": "You are a research analysis expert. Identify specific research gaps and future research directions based on the provided papers. Format your response with clear sections: Current State, Identified Gaps, and Future Directions.",
            },
            {
                "role": "user",
                "content": f"Analyze these papers and identify research gaps:\n\n{paper_summaries}",
            },
        ]
    }

    try:
        client = OpenAI(
            api_key=perplexity_api_key, base_url="https://api.perplexity.ai"
        )
        response = client.chat.completions.create(
            model="llama-3.1-sonar-small-128k-chat",  # Use the best Perplexity model
            messages=data["messages"],
        )
        return response.choices[0].message.content

    except Exception as e:
        st.error(f"Failed to analyze research gaps: {str(e)}")
        return "Error analyzing research gaps"


def create_research_paper(gaps, topic, papers):
    """
    Create a research paper that addresses the identified gaps using Perplexity API
    """
    full_texts = "\n\n".join([paper["content"] for paper in papers])
    headers = {
        "Authorization": f"Bearer {perplexity_api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "messages": [
            {
                "role": "system",
                "content": "You are a research paper generation expert. Create a comprehensive research paper that addresses the identified gaps based on the provided papers. Format your response with clear sections: Introduction, Literature Review, Methodology, Results, Discussion, Conclusion, and References.",
            },
            {
                "role": "user",
                "content": f"Create a research paper on the topic '{topic}' that addresses the following research gaps:\n\n{gaps}\n\nBased on the following papers:\n\n{full_texts}",
            },
        ]
    }
    try:
        client = OpenAI(
            api_key=perplexity_api_key, base_url="https://api.perplexity.ai"
        )
        response = client.chat.completions.create(
            model="llama-3.1-sonar-small-128k-chat",  # Use the best Perplexity model
            messages=data["messages"],
        )
        return response.choices[0].message.content

    except Exception as e:
        st.error(f"Failed to create research paper: {str(e)}")
        return "Error creating research paper"


def cosine_similarity(vec1, vec2):
    """Calculate the cosine similarity between two vectors"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def display_research_assistant_dashboard():
    """Display research assistant dashboard"""
    # Initialize session state for recommendations
    if "recommendations" not in st.session_state:
        st.session_state.recommendations = None
    if "vectors" not in st.session_state:
        st.session_state.vectors = None
    if "generated_paper" not in st.session_state:
        st.session_state.generated_paper = None

    # Sidebar
    with st.sidebar:
        st.title(f"Welcome, {st.session_state.username}")
        if st.button("Logout", use_container_width=True):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

    # Main content
    st.title("Research Paper Recommendations")
    search_query = st.text_input("Enter research topic:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Get Research Papers"):
            if search_query:
                with st.spinner("Fetching recommendations..."):
                    st.session_state.recommendations = get_research_papers(search_query)
                    st.session_state.vectors = [
                        paper["vector"] for paper in st.session_state.recommendations
                    ]
                    st.markdown(
                        "\n\n".join(
                            [
                                f"**{i+1}.**\n{paper['content']}"
                                # f"**{i+1}. {paper['title']}**\n{paper['content']}"
                                for i, paper in enumerate(
                                    st.session_state.recommendations
                                )
                            ]
                        )
                    )
            else:
                st.warning("Please enter a search query")
    with col2:
        if st.button("Analyze Research Gaps"):
            if st.session_state.recommendations:
                with st.spinner("Analyzing research gaps..."):
                    gaps = analyze_research_gaps(st.session_state.recommendations)
                    st.session_state.generated_paper = create_research_paper(
                        gaps, search_query, st.session_state.recommendations
                    )
                    st.markdown("### Potential Research Gaps")
                    st.markdown(gaps)
            else:
                st.warning("Please get research papers first")

    if st.button("Save and Vectorize"):
        if st.session_state.generated_paper:
            try:
                # Initialize OpenAI client

                # Get embedding for generated paper
                response = openai.embeddings.create(
                    model="text-embedding-ada-002",
                    input=st.session_state.generated_paper,
                    encoding_format="float",
                )
                generated_vector = response.data[0].embedding

                # Calculate similarities with stored vectors
                similarities = [
                    calculate_cosine_similarity(generated_vector, paper_vector)
                    for paper_vector in st.session_state.vectors
                ]

                # Display results
                st.markdown("### Generated Research Paper")
                st.markdown(st.session_state.generated_paper)

                st.markdown("### Cosine Similarities with Original Papers")
                for i, similarity in enumerate(similarities):
                    st.metric(
                        f"Paper {i+1}",
                        value=f"{similarity:.3f}",
                        help="Cosine similarity (1.0 = identical, 0.0 = completely different)",
                    )

            except Exception as e:
                st.error(f"Error during vectorization: {str(e)}")
        else:
            st.warning("Please analyze research gaps first")


# Run the dashboard
if __name__ == "__main__":
    display_research_assistant_dashboard()


