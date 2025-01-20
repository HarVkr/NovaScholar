import streamlit as st
import requests
import PyPDF2
from typing import Optional, Dict, List
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET
import re
from datetime import datetime
import time
from dotenv import load_dotenv
import os
import pandas as pd

# Load environment variables
load_dotenv()
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
SAPLING_API_KEY = os.getenv("SAPLING_API_KEY")


def call_perplexity_api(prompt: str) -> str:
    """Call Perplexity AI with a prompt, return the text response if successful."""
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama-3.1-sonar-small-128k-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }

    try:
        response = requests.post(PERPLEXITY_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return ""


def extract_text_from_pdf(pdf_file):
    """Extract text content from a PDF file."""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text


def analyze_paper(text: str, category: str) -> str:
    """Generate a prompt and get analysis for a specific category."""
    prompts = {
        "Summarized Abstract": "Extract and summarize the abstract from this research paper:",
        "Results": "What are the main results and findings from this research paper:",
        "Summarized Introduction": "Summarize the introduction section of this research paper:",
        "Methods Used": "What are the main methods and methodologies used in this research:",
        "Literature Survey": "Summarize the literature review or related work from this paper:",
        "Limitations": "What are the limitations mentioned in this research:",
        "Contributions": "What are the main contributions of this research:",
        "Practical Implications": "What are the practical implications of this research:",
        "Objectives": "What are the main objectives of this research:",
        "Findings": "What are the key findings from this research:",
        "Future Research": "What future research directions are suggested in this paper:",
        "Dependent Variables": "What are the dependent variables studied in this research:",
        "Independent Variables": "What are the independent variables studied in this research:",
        "Dataset": "What dataset(s) were used in this research:",
        "Problem Statement": "What is the main problem statement or research question:",
        "Challenges": "What challenges were faced or addressed in this research:",
        "Applications": "What are the potential applications of this research:",
    }

    prompt = f"{prompts[category]}\n\nPaper text: {text[:5000]}"  # Limit text to avoid token limits
    return call_perplexity_api(prompt)


class ResearchAssistant:
    def __init__(self, perplexity_key: str):
        self.perplexity_key = perplexity_key

    def chat_with_pdf(self, pdf_text: str, query: str) -> Dict:
        chunks = self._split_text(pdf_text)
        relevant_chunks = self._get_relevant_chunks(chunks, query)

        prompt = f"Context from PDF:\n\n{relevant_chunks}\n\nQuestion: {query}"
        response_text = call_perplexity_api(prompt)
        return {"choices": [{"message": {"content": response_text}}]}

    def generate_literature_review(self, topic: str) -> Dict:
        try:
            # Search arXiv for papers
            papers = self._search_arxiv(topic)
            if not papers:
                return {"error": "No papers found on the topic"}

            # Format paper information
            papers_summary = "\n\n".join(
                [
                    f"Paper: {p['title']}\nAuthors: {', '.join(p['authors'])}\nSummary: {p['summary']}"
                    for p in papers
                ]
            )

            prompt = f"""Generate a comprehensive literature review on '{topic}'. Based on these papers:

            {papers_summary}

            Structure the review as follows:
            1. Introduction and Background
            2. Current Research Trends
            3. Key Findings and Themes
            4. Research Gaps
            5. Future Directions"""

            response_text = call_perplexity_api(prompt)
            return {"choices": [{"message": {"content": response_text}}]}
        except Exception as e:
            return {"error": f"Literature review generation failed: {str(e)}"}

    def ai_writer(self, outline: str, references: List[str]) -> Dict:
        prompt = f"""Write a research paper following this structure:
        
        Outline:
        {outline}
        
        References to incorporate:
        {json.dumps(references)}
        
        Instructions:
        - Follow academic writing style
        - Include appropriate citations
        - Maintain logical flow
        - Include introduction and conclusion"""

        response_text = call_perplexity_api(prompt)
        return {"choices": [{"message": {"content": response_text}}]}

    def refine_response(self, response: str, column: str) -> str:
        prompt = f"""Refine the following response to fit the '{column}' column in a research paper CSV format:
        
        Response: {response}
        
        Ensure the response is clear, concise, and fits the context of the column."""

        refined_response = call_perplexity_api(prompt)
        return refined_response

    def paraphrase(self, text: str) -> Dict:
        prompt = f"""Paraphrase the following text while:
        - Maintaining academic tone
        - Preserving key meaning
        - Improving clarity
        
        Text: {text}"""

        response_text = call_perplexity_api(prompt)
        return {"choices": [{"message": {"content": response_text}}]}

    def generate_citation(self, paper_info: Dict, style: str = "APA") -> Dict:
        prompt = f"""Generate a {style} citation for:
        Title: {paper_info['title']}
        Authors: {', '.join(paper_info['authors'])}
        Year: {paper_info['year']}
        
        Follow exact {style} format guidelines."""

        response_text = call_perplexity_api(prompt)
        return {"citation": response_text}

    def detect_ai_content(self, text: str) -> Dict:
        prompt = f"""You are an AI content detector. Analyze the text for:
        1. Writing style consistency
        2. Language patterns
        3. Contextual coherence
        4. Common AI patterns
        Provide a clear analysis with confidence level.
        
        Text: {text}"""

        response = requests.post(
            "https://api.sapling.ai/api/v1/aidetect",
            json={"key": SAPLING_API_KEY, "text": text},
        )
        st.info(
            "A score from 0 to 1 will be returned, with 0 indicating the maximum confidence that the text is human-written, and 1 indicating the maximum confidence that the text is AI-generated."
        )

        if response.status_code == 200:
            return {"choices": [{"message": {"content": response.json()}}]}
        else:
            return {
                "error": f"Sapling API Error: {response.status_code} - {response.text}"
            }

    def _split_text(self, text: str) -> List[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", ". ", " ", ""]
        )
        return splitter.split_text(text)

    def _get_relevant_chunks(self, chunks: List[str], query: str) -> str:
        # Simple keyword-based relevance scoring
        query_words = set(query.lower().split())
        scored_chunks = []

        for chunk in chunks:
            chunk_words = set(chunk.lower().split())
            score = len(query_words.intersection(chunk_words))
            scored_chunks.append((score, chunk))

        scored_chunks.sort(reverse=True)
        return "\n\n".join(chunk for _, chunk in scored_chunks[:3])

    def _search_arxiv(self, topic: str) -> List[Dict]:
        try:
            query = "+AND+".join(topic.split())
            url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=5"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return self._parse_arxiv_response(response.text)
        except Exception as e:
            print(f"arXiv search failed: {str(e)}")
            return []

    def _parse_arxiv_response(self, response_text: str) -> List[Dict]:
        try:
            root = ET.fromstring(response_text)
            papers = []
            for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                paper = {
                    "id": entry.find("{http://www.w3.org/2005/Atom}id").text,
                    "title": entry.find(
                        "{http://www.w3.org/2005/Atom}title"
                    ).text.strip(),
                    "summary": entry.find(
                        "{http://www.w3.org/2005/Atom}summary"
                    ).text.strip(),
                    "authors": [
                        author.find("{http://www.w3.org/2005/Atom}name").text.strip()
                        for author in entry.findall(
                            "{http://www.w3.org/2005/Atom}author"
                        )
                    ],
                    "published": entry.find(
                        "{http://www.w3.org/2005/Atom}published"
                    ).text[:10],
                }
                papers.append(paper)
            return papers
        except Exception as e:
            print(f"arXiv response parsing failed: {str(e)}")
            return []


def main():
    # st.set_page_config(page_title="Research Assistant", layout="wide")
    st.title("Research Copilot")

    if not PERPLEXITY_API_KEY:
        st.warning("Perplexity API key not found in environment variables.")
        return

    assistant = ResearchAssistant(PERPLEXITY_API_KEY)

    tabs = st.tabs(
        [
            "Chat with PDF",
            "Literature Review",
            "AI Writer",
            "Extract Data",
            "Paraphraser",
            "Citation Generator",
            "AI Detector",
        ]
    )

    with tabs[0]:  # Chat with PDF
        st.header("Chat with PDF")

        # File uploader with clear button
        col1, col2 = st.columns([3, 1])
        with col1:
            uploaded_file = st.file_uploader("Upload PDF", type="pdf", key="pdf_chat")
        with col2:
            if st.button("Clear PDF"):
                st.session_state.pop("pdf_text", None)
                st.rerun()

        if uploaded_file:
            if "pdf_text" not in st.session_state:
                with st.spinner("Processing PDF..."):
                    reader = PyPDF2.PdfReader(uploaded_file)
                    st.session_state.pdf_text = ""
                    for page in reader.pages:
                        st.session_state.pdf_text += page.extract_text()
                    st.success("PDF processed successfully!")

            query = st.text_input("Ask a question about the PDF")
            if query:
                with st.spinner("Analyzing..."):
                    response = assistant.chat_with_pdf(st.session_state.pdf_text, query)
                    if "error" in response:
                        st.error(response["error"])
                    else:
                        st.write(response["choices"][0]["message"]["content"])

    with tabs[1]:  # Literature Review
        st.header("Literature Review")
        topic = st.text_input("Enter research topic")
        if st.button("Generate Review") and topic:
            with st.spinner("Generating literature review..."):
                review = assistant.generate_literature_review(topic)
                if "error" in review:
                    st.error(review["error"])
                else:
                    st.write(review["choices"][0]["message"]["content"])

    with tabs[2]:  # AI Writer
        st.header("AI Writer")
        outline = st.text_area("Enter paper outline")
        references = st.text_area("Enter references (one per line)")
        if st.button("Generate Paper") and outline:
            with st.spinner("Writing paper..."):
                paper = assistant.ai_writer(outline, references.split("\n"))
                if "error" in paper:
                    st.error(paper["error"])
                else:
                    st.write(paper["choices"][0]["message"]["content"])

    with tabs[3]:  # Extract Data
        st.header("Extract Data")

        uploaded_files = st.file_uploader(
            "Upload multiple PDF  files", type="pdf", accept_multiple_files=True
        )

        if uploaded_files:
            if st.button("Process Papers"):
                # Initialize progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Initialize results dictionary
                results = []

                # Define categories
                categories = [
                    "Summarized Abstract",
                    "Results",
                    "Summarized Introduction",
                    "Methods Used",
                    "Literature Survey",
                    "Limitations",
                    "Contributions",
                    "Practical Implications",
                    "Objectives",
                    "Findings",
                    "Future Research",
                    "Dependent Variables",
                    "Independent Variables",
                    "Dataset",
                    "Problem Statement",
                    "Challenges",
                    "Applications",
                ]

                # Process each file
                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Processing {file.name}...")

                    # Extract text from PDF
                    text = extract_text_from_pdf(file)

                    # Initialize paper results
                    paper_results = {"Filename": file.name}

                    # Analyze each category
                    for j, category in enumerate(categories):
                        status_text.text(f"Processing {file.name} - {category}")
                        paper_results[category] = analyze_paper(text, category)

                        # Update progress
                        progress = (i * len(categories) + j + 1) / (
                            len(uploaded_files) * len(categories)
                        )
                        progress_bar.progress(progress)

                        # Add small delay to avoid API rate limits
                        time.sleep(1)

                    results.append(paper_results)

                # Create DataFrame
                df = pd.DataFrame(results)

                # Convert DataFrame to CSV
                csv = df.to_csv(index=False)

                # Create download button
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name="research_papers_analysis.csv",
                    mime="text/csv",
                )

                # Display results in the app
                st.subheader("Analysis Results")
                st.dataframe(df)

                status_text.text("Processing complete!")
                progress_bar.progress(1.0)

    with tabs[4]:  # Paraphraser
        st.header("Paraphraser")
        text = st.text_area("Enter text to paraphrase")
        if st.button("Paraphrase") and text:
            with st.spinner("Paraphrasing..."):
                result = assistant.paraphrase(text)
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.write(result["choices"][0]["message"]["content"])

    with tabs[5]:  # Citation Generator
        st.header("Citation Generator")
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Paper Title")
            authors = st.text_input("Authors (comma-separated)")
        with col2:
            year = st.text_input("Year")
            style = st.selectbox("Citation Style", ["APA", "MLA", "Chicago"])

        if st.button("Generate Citation") and title:
            with st.spinner("Generating citation..."):
                citation = assistant.generate_citation(
                    {
                        "title": title,
                        "authors": [a.strip() for a in authors.split(",")],
                        "year": year,
                    },
                    style,
                )
                if "error" in citation:
                    st.error(citation["error"])
                else:
                    st.code(citation["citation"], language="text")

    with tabs[6]:  # AI Detector
        st.header("AI Detector")
        text = st.text_area("Enter text to analyze")
        if st.button("Detect AI Content") and text:
            with st.spinner("Analyzing..."):
                result = assistant.detect_ai_content(text)
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.write(result["choices"][0]["message"]["content"])


if __name__ == "__main__":
    main()
