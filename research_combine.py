import streamlit as st
import os
import json
import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from typing import Dict, Any

# Load environment variables
load_dotenv()
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
MONGODB_URI = os.getenv(
    "MONGODB_UR",
    "mongodb+srv://milind:05july60@cluster0.d6mld.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
)

# MongoDB setup
client = MongoClient(MONGODB_URI)
db = client["novascholar_db"]
collection = db["research_papers"]


def search_papers(topic: str, num_papers: int) -> str:
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }

    prompt = f"""Find {num_papers} recent research papers about {topic}.
    Return ONLY a valid JSON array with the following structure for each paper, no additional text:
    [
        {{
            "Title": "paper title",
            "Publication": "publication name",
            "Journal_Conference": "venue name",
            "Abstract": "abstract text",
            "Keywords": "key terms",
            "Author": "author names",
            "Date_of_Publication": "publication date",
            "Intro": "introduction summary",
            "Literature_Review": "literature review summary",
            "Research_Models_Used": "models description", 
            "Methodology": "methodology description",
            "Discussion": "discussion summary",
            "Future_Scope": "future work",
            "Theory": "theoretical framework",
            "Independent_Variables": "list of variables",
            "nof_Independent_Variables": 0,
            "Dependent_Variables": "list of variables",
            "nof_Dependent_Variables": 0,
            "Control_Variables": "list of variables",
            "nof_Control_Variables": 0,
            "Extraneous_Variables": "list of variables",
            "nof_Extraneous_Variables": 0
        }}
    ]"""

    payload = {
        "model": "llama-3.1-sonar-small-128k-chat",
        "messages": [
            {
                "role": "system",
                "content": "You are a research paper analyzer that returns only valid JSON arrays.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }

    try:
        response = requests.post(PERPLEXITY_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

        # Clean response and ensure it's valid JSON
        content = content.strip()
        if not content.startswith("["):
            content = content[content.find("[") :]
        if not content.endswith("]"):
            content = content[: content.rfind("]") + 1]

        # Validate JSON
        papers = json.loads(content)
        if not isinstance(papers, list):
            raise ValueError("Response is not a JSON array")

        # Insert into MongoDB
        if papers:
            collection.insert_many(papers)
            return content
        return "[]"

    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON response: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None


import research22
import keywords_database_download
import new_keywords
import infranew
import loldude
import new_research_paper
import research3
import entire_download


def main():
    st.set_page_config(page_title="Research Papers", layout="wide")

    st.title("Research Papers")

    # Sidebar radio
    option = st.sidebar.radio(
        "Select an option",
        [
            "Search Papers",
            "Upload Paper",
            "Single Keyword Search",
            "Multiple Keywords Search",
            "Knowledge Graph",
            "Cosine Similarity",
            "Paper Generator",
            "Paper from Topic",
            "Download Entire Corpus",
        ],
    )

    if option == "Search Papers":
        st.subheader("Search and Store Papers")

        topic = st.text_input("Enter research topic")
        num_papers = st.number_input(
            "Number of papers", min_value=1, max_value=10, value=5
        )

        if st.button("Search and Store"):
            if topic:
                with st.spinner(f"Searching and storing papers about {topic}..."):
                    results = search_papers(topic, num_papers)
                    if results:
                        st.success(
                            f"Successfully stored {num_papers} papers in MongoDB"
                        )
                        # Display results
                        papers = json.loads(results)
                        for paper in papers:
                            with st.expander(paper["Title"]):
                                for key, value in paper.items():
                                    if key != "Title":
                                        st.write(f"**{key}:** {value}")
            else:
                st.warning("Please enter a research topic")

        # Add MongoDB connection status
        if st.sidebar.button("Check Database Connection"):
            try:
                client.admin.command("ping")
                print(MONGODB_URI)
                st.sidebar.success("Connected to MongoDB")
            except Exception as e:
                st.sidebar.error(f"MongoDB Connection Error: {str(e)}")
    elif option == "Single Keyword Search":
        keywords_database_download.main()
    elif option == "Multiple Keywords Search":
        new_keywords.main()
    elif option == "Knowledge Graph":
        infranew.main()
    elif option == "Cosine Similarity":
        loldude.main()
    elif option == "Paper Generator":
        new_research_paper.main()
    elif option == "Paper from Topic":
        research3.main()
    elif option == "Download Entire Corpus":
        entire_download.main()
    else:
        # st.subheader("Blank Page")
        # st.write("This is a placeholder for alternative content.")
        research22.main()


if __name__ == "__main__":
    main()
