import new_research_paper
import research3
import entire_download
import streamlit as st
import os
import json
import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from typing import Dict, Any
import research22
import keywords_database_download
import new_keywords
import infranew
import loldude
import new_research_paper
import research3
import entire_download
import sciclone
import extract

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


def search_papers(topic: str, num_papers: int, paper_type: str) -> str:
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }

    attributes = {
        "Review Based Paper": [
            "Title",
            "Publication",
            "Journal_Conference",
            "Abstract",
            "Keywords",
            "Author",
            "Date_of_Publication",
            "Intro",
            "Literature_Review",
            "Body",
            "Protocol",
            "Search String",
            "Included Studies",
            "Data Collection and Analysis Methods",
            "Data Extraction Table",
            "Synthesis and Analysis",
            "Conclusion",
            "Limitations",
            "Results",
            "References",
            "Risk of Bias Assessment",
        ],
        "Opinion/Perspective Based Paper": [
            "Title",
            "Publication",
            "Journal_Conference",
            "Abstract",
            "Keywords",
            "Author",
            "Date_of_Publication",
            "Intro",
            "Literature_Review",
            "Introduction",
            "Body",
            "Results and Discussion",
            "Conclusion",
            "References",
        ],
        "Empirical Research Paper": [
            "Title",
            "Publication",
            "Journal_Conference",
            "Abstract",
            "Keywords",
            "Author",
            "Date_of_Publication",
            "Intro",
            "Literature_Review",
            "Introduction",
            "Body",
            "Methodology",
            "Participants",
            "Survey Instrument",
            "Data Collection",
            "Data Analysis",
            "Results and Discussion",
            "Conclusion",
            "References",
        ],
        "Research Paper (Other)": [
            "Title",
            "Publication",
            "Journal_Conference",
            "Abstract",
            "Keywords",
            "Author",
            "Date_of_Publication",
            "Intro",
            "Literature_Review",
            "Research_Models_Used",
            "Methodology",
            "Discussion",
            "Future_Scope",
            "Theory",
            "Independent_Variables",
            "nof_Independent_Variables",
            "Dependent_Variables",
            "nof_Dependent_Variables",
            "Control_Variables",
            "Extraneous_Variables",
            "nof_Control_Variables",
            "nof_Extraneous_Variables",
        ],
    }

    selected_attributes = attributes[paper_type]
    prompt = f"""Find {num_papers} recent research papers about {topic}.
    Return ONLY a valid JSON array with the following structure for each paper, no additional text:
    [{{
        {", ".join([f'"{attr}": "value"' for attr in selected_attributes])}
    }}]"""

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
        collection = db[paper_type.replace(" ", "_").lower()]
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


def display_research_assistant_dashboard():
    #st.set_page_config(page_title="Research Papers", layout="wide")

   # st.title("Research Papers")

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
            "Research Copilot",
            "Research Paper Analysis Tool",
        ],
    )

    if option == "Search Papers":
        st.subheader("Search and Store Papers")

        topic = st.text_input("Enter research topic")
        num_papers = st.number_input(
            "Number of papers", min_value=1, max_value=10, value=5
        )
        paper_type = st.selectbox(
            "Select type of research paper",
            [
                "Review Based Paper",
                "Opinion/Perspective Based Paper",
                "Empirical Research Paper",
                "Research Paper (Other)",
            ],
        )

        if st.button("Search and Store"):
            if topic:
                with st.spinner(f"Searching and storing papers about {topic}..."):
                    results = search_papers(topic, num_papers, paper_type)
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
    elif option == "Research Copilot":
        sciclone.main()
    elif option == "Research Paper Analysis Tool":
        extract.main()
    else:
        research22.main()


if __name__ == "__main__":
    display_research_assistant_dashboard()
