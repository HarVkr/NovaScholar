import streamlit as st
import pandas as pd
import requests
import json
import os
from dotenv import load_dotenv

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


def generate_research_paper(df: pd.DataFrame) -> dict:
    """
    For each column in the DataFrame, generate a research paper section (200-500 words)
    that addresses the data in that column. Return a dict mapping column -> text.
    """
    paper_sections = {}
    for col in df.columns:
        # Convert all non-null rows in the column to strings and join them for context
        col_values = df[col].dropna().astype(str).tolist()
        # We'll truncate if this is huge
        sample_text = " | ".join(col_values[:50])  # limit to first 50 rows for brevity
        prompt = f"""
        Topic: {col}
        Data Sample: {sample_text}

        Generate a professional research paper section for the above column.
        The section should be at least 100 words and at most 150 words,
        focusing on key insights, challenges, and potential research angles.
        Integrate the data samples as context for the content.
        """
        section_text = call_perplexity_api(prompt)
        paper_sections[col] = section_text.strip() if section_text else ""
    return paper_sections


def format_paper(paper_dict: dict) -> str:
    """
    Format the generated paper into a Markdown string.
    Each column name is used as a heading, and the text is placed under it.
    """
    md_text = "# Generated Research Paper\n\n"
    for col, content in paper_dict.items():
        md_text += f"## {col}\n{content}\n\n"
    return md_text


def main():
    st.title("Corpus-based Research Paper Generator")

    uploaded_file = st.file_uploader("Upload CSV corpus file", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write("### Preview of Uploaded Data")
        st.dataframe(df.head())

        if st.button("Generate Research Paper"):
            st.info("Generating paper based on the columns of your corpus...")
            with st.spinner("Calling Perplexity AI..."):
                paper = generate_research_paper(df)
                if paper:
                    formatted_paper = format_paper(paper)
                    st.success("Research Paper Generated Successfully!")
                    st.write(formatted_paper)

                    st.download_button(
                        label="Download Paper as Markdown",
                        data=formatted_paper,
                        file_name="research_paper.md",
                        mime="text/markdown",
                    )
                else:
                    st.error(
                        "Paper generation failed. Please check Perplexity API key."
                    )


if __name__ == "__main__":
    main()
