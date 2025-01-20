import streamlit as st
import pandas as pd
import PyPDF2
import io
import os
from dotenv import load_dotenv
import requests
import time

# Load environment variables
load_dotenv()
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

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
        "Applications": "What are the potential applications of this research:"
    }
    
    prompt = f"{prompts[category]}\n\nPaper text: {text[:5000]}"  # Limit text to avoid token limits
    return call_perplexity_api(prompt)

def main():
    st.title("Research Paper Analysis Tool")
    
    # File uploader
    uploaded_files = st.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("Process Papers"):
            # Initialize progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialize results dictionary
            results = []
            
            # Define categories
            categories = [
                "Summarized Abstract", "Results", "Summarized Introduction", 
                "Methods Used", "Literature Survey", "Limitations", 
                "Contributions", "Practical Implications", "Objectives",
                "Findings", "Future Research", "Dependent Variables",
                "Independent Variables", "Dataset", "Problem Statement",
                "Challenges", "Applications"
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
                    progress = (i * len(categories) + j + 1) / (len(uploaded_files) * len(categories))
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
                mime="text/csv"
            )
            
            # Display results in the app
            st.subheader("Analysis Results")
            st.dataframe(df)
            
            status_text.text("Processing complete!")
            progress_bar.progress(1.0)

if __name__ == "__main__":
    main()