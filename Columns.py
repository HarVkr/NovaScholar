
import streamlit as st
import pandas as pd
import PyPDF2
import io
import os
from dotenv import load_dotenv
import requests
import time
from mistralai import Mistral
from typing import List, Dict
from fpdf import FPDF

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL = "https://api.mistral.ai/v1/completions"

# Initialize the Mistral client
client = Mistral(api_key=MISTRAL_API_KEY)

def call_mistral_api(prompt: str) -> str:
    """Call Mistral AI with a prompt, return the text response if successful."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]
    tools = []  # Add any tools if necessary

    try:
        # Make the API call
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=messages,
            tools=tools,
            tool_choice="any",
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"API Error: {str(e)}")
        return ""

def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Process the DataFrame and return a DataFrame with analysis results."""
    print("Processing DataFrame...")
    # Initialize results dictionary
    results = []

    # Process each column starting from the third column
    for i, column in enumerate(df.columns[2:], start=2):
        print(f"Processing column: {column}")
        # Extract text from column and attach values from the first and second columns
        text = " ".join(
            f"Column1-{row[df.columns[0]]}, Column2-{row[df.columns[1]]}, {value}"
            for _, row in df.iterrows()
            for value in [row[column]]
            if pd.notna(value)
        )

        # Generate prompt
        prompt = f"You are a Professional Researcher and Analyser with 10 yrs of Experience. Find details and Elaborate on Top Trends,Patterns ,Highlight Theories and Method in this topic.Support your answer with rightful evidence of corresponding DOI/SrNo and Frequency(how many times same topic repeated and in which papers):Make sure to limit the answer within 400 words ({column}):\n\n{text}"
        
        # Call Mistral API
        result1 = call_mistral_api(prompt)
        prompt1=f"""This result was the reponse of an earlier prompt Result -{result1}, Fact check the result with my original data -({column}):\n\n{text}. Return the refined Result(after careful fact checking and finding adequate evidence within the original data) , Make sure the meaning/structure of the Result doesnt change,only false/low evidence statements get eliminated.Limit the response to 400 words.MAKE SURE THERE IS NO CONTEXT CHANGE AND MEANING REMAINS SAME JUST WITH GOOD EVIDENCE AND REFINED RESULT. """
        result=call_mistral_api(prompt1)
        results.append({"Column": column, "Result": result})

    # Create DataFrame from results
    results_df = pd.DataFrame(results)
    print("DataFrame processing complete.")
    return results_df

def split_dataframe(df: pd.DataFrame, max_rows: int = 52) -> List[pd.DataFrame]:
    """
    Split a DataFrame into multiple smaller DataFrames, each having a maximum of `max_rows` rows.
    
    Args:
        df (pd.DataFrame): The original DataFrame to be split.
        max_rows (int): The maximum number of rows for each smaller DataFrame (excluding the header row).
    
    Returns:
        List[pd.DataFrame]: A list of smaller DataFrames.
    """
    print("Splitting DataFrame...")
    # Calculate the number of splits needed
    num_splits = (len(df) + max_rows - 1) // max_rows
    
    # Split the DataFrame
    split_dfs = [df.iloc[i * max_rows:(i + 1) * max_rows].reset_index(drop=True) for i in range(num_splits)]
    print(f"DataFrame split into {len(split_dfs)} parts.")
    return split_dfs

def generate_professional_review(df1: pd.DataFrame) -> str:
    """
    Generate a professional literature review, trends analysis, TSM/ADO analysis, gaps, theories, and frameworks
    based on DOI and Serial Number as key value pairs.
    
    Args:
        df1 (pd.DataFrame): The first DataFrame.
        df2 (pd.DataFrame): The second DataFrame.
    
    Returns:
        str: The generated analysis text.
    """
    print("Generating professional review...")
    # Concatenate DataFrames
    

    # Convert the concatenated DataFrame to a string format suitable for the prompt
    context = df1.to_string(index=True)
    
    # Generate a single prompt for the analysis
    prompt = f"""Generate a professional literature review, trends analysis, TCM ADO (Theories,Context,Method ,Ancedents,Decisions,Outcomes), gaps, theories, and frameworks
    based on the following data , If you find evidence as proper DOI make sure you analyze the whole
    table with more DOI,Serial No and find more evidence.Always give supporting evidence for your literature review,TCM ADO analysis,trends ,frameworks,
    check DOIs and find more evidence as inference again.Make sure the review is as professional as possible.Limit the answer to 500 words and only highlight the most imp trends with supporting evidence of DOI/SrNo and frequency(how many papers used that and top 2 DOI of that),Limit it to 500 words.Make sure all important details/frequently repeating trends/methods are highlighted.:\n\n{context}."""
  

    # Call Mistral API
    result = call_mistral_api(prompt)
    print("Professional review generated.")
    return result


def main():
    st.title("Research Corpus Synthesis Tool")

    # Logout button
    if st.button("Logout", use_container_width=True):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

    # File uploader
    uploaded_file = st.file_uploader("Upload CSV file", type="csv")

    if uploaded_file:
        if st.button("Process CSV"):
            print("CSV file uploaded.")
            # Initialize progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Read CSV file into DataFrame
            df = pd.read_csv(uploaded_file)
            print("CSV file read into DataFrame.")

            # Split DataFrame into smaller DataFrames
            split_dfs = split_dataframe(df, max_rows=52)

            # Initialize variable to concatenate all generated reviews
            concatenated_reviews = ""

            # Process each smaller DataFrame
            for i, split_df in enumerate(split_dfs):
                status_text.text(f"Processing part {i + 1} of {len(split_dfs)}")
                print(f"Processing part {i + 1} of {len(split_dfs)}")

                # Process the smaller DataFrame
                processed_df = process_dataframe(split_df)

                # Generate professional review
                review = generate_professional_review(processed_df)

                # Concatenate the generated review
                concatenated_reviews += review + "\n\n"

                # Update progress
                progress = (i + 1) / len(split_dfs)
                progress_bar.progress(progress)
                st.write(i)
                st.write(review)
                
               
                
               

            # Generate final analysis based on the concatenated reviews
            final_prompt = f"""
            Given is a consolidated research review of a huge number of research papers (evidence is DOI, Serial No). Perform this:
            Given as a context is a table of analyzing trends/frameworks analysis of a huge corpus of papers specific to the columns.
            Analyze the table properly and create a professional and accurate literature review (Ensure to cite DOI as evidence).

            Subheadings for Literature Review :
            1. Introduction
               ○ Overview of the main topic or concept.
               ○ Key research questions or objectives.
            2. Theoretical Foundations
               ○ Exploration of dominant theories related to the topic.
               ○ Domain-specific theoretical applications.
            3. Contextual Analysis
               ○ Geographic contexts and challenges.
               ○ Sectoral applications and digital infrastructure readiness.
            4. Methodological Approaches
               ○ Qualitative, quantitative, and mixed-methods approaches used in research.
            5. Discussion and Future Research
               ○ Current challenges and limitations.
               ○ Potential areas for future study.
            6. Conclusion
               ○ Summary of findings.
               ○ Implications and future directions.

            TCM-ADO Framework in Research Analysis and Literature Review:
            Theory
               Theoretical foundations driving the research.
               ● Focus on identifying and analyzing the conceptual models or frameworks that underpin the study.
               ● Establish the intellectual basis and rationale for the research direction.
            Context
               Situational and environmental factors shaping the research.
               ● Emphasis on geographic, sectoral, cultural, and infrastructural dimensions influencing the implementation or findings.
               ● Examples include urban versus rural settings, digital infrastructure readiness, or policy landscapes.
               ● Objective: To understand how external conditions impact the dynamics and applicability of the research.
            Method
               Research methodologies and analytical approaches utilized.
               ● Covers the selection of qualitative, quantitative, or mixed-method approaches, along with tools and techniques employed.
               ● Objective: To ensure methodological rigor and the validity of findings.
            Antecedents
            Pre-existing conditions enabling or constraining research or implementation.
            ● Includes factors such as technological infrastructure, stakeholder preparedness, and
            regulatory frameworks.
            ● To identify critical prerequisites that influence the starting point of the research or
            initiative.
            Decisions
            Strategic choices made throughout the implementation or research process.
            ● Involves critical decision points in areas like technology adoption, governance
            frameworks, and operational strategies.
            ● analyze how informed decision-making shapes the trajectory and success of the project.
            Outcomes
            Results and impacts observed as a consequence of the initiative or study.
            ● Evaluates direct and indirect contributions to the research objectives or broader societal
            goals.
            ● assess the effectiveness and long-term implications of the research or project outcomes.
            """

            final_result = call_mistral_api(final_prompt)
            print("Final analysis generated.")

            # Display the final result
            st.subheader("Final Analysis")
            st.write(final_result)

            status_text.text("Processing complete!")
            progress_bar.progress(1.0)
            print("Processing complete.")

if __name__ == "__main__":
    main()