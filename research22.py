# if __name__ == "__main__":
#     main()
import streamlit as st
import google.generativeai as genai
from typing import Dict, Any
import PyPDF2
import io
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import json
import re

# --------------------------------------------------------------------------------
# 1. Environment Setup
# --------------------------------------------------------------------------------
load_dotenv()
# MongoDB
MONGODB_URI = os.getenv("MONGODB_URI")
# Gemini
GEMINI_KEY = os.getenv("GEMINI_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_KEY)


# --------------------------------------------------------------------------------
# 2. Database Connection
# --------------------------------------------------------------------------------
def create_db_connection():
    """
    Create MongoDB connection and return the 'papers' collection.
    """
    try:
        client = MongoClient(MONGODB_URI)
        db = client["novascholar_db"]  # Database name
        collection = db["research_papers"]  # Collection name
        # Ping to confirm connection
        client.admin.command("ping")
        return db
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        return None


# --------------------------------------------------------------------------------
# 3. PDF Text Extraction
# --------------------------------------------------------------------------------
def extract_text_from_pdf(pdf_file) -> str:
    """
    Extract all text from a PDF.
    """
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return ""


# --------------------------------------------------------------------------------
# 4. Gemini Response Helper
# --------------------------------------------------------------------------------
def get_gemini_response(prompt: str) -> str:
    """
    Sends a prompt to Google's Gemini model and returns the response text.
    Adjust this function as needed for your generative AI usage.
    """
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Gemini API Error: {str(e)}")
        return ""


# --------------------------------------------------------------------------------
# 5. Basic Info Extraction
# --------------------------------------------------------------------------------
def extract_basic_info(text: str) -> Dict[str, str]:
    """
    Extract title, publication, journal/conference, abstract, keywords, author, and date from the paper text.
    Return a dictionary with these fields.
    """
    prompt = f"""
    Extract the following fields from the research paper text below:

    Title
    Publication
    Journal_Conference
    Abstract
    Keywords
    Author
    Date_of_Publication

    Paper text:
    {text}

    Return them in this format:
    Title: ...
    Publication: ...
    Journal_Conference: ...
    Abstract: ...
    Keywords: ...
    Author: ...
    Date_of_Publication: ...
    """
    response = get_gemini_response(prompt)
    if not response:
        return {}
    info = {}
    lines = response.split("\n")
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    return info


# --------------------------------------------------------------------------------
# 6. Content Sections Extraction
# --------------------------------------------------------------------------------
def extract_content_sections(text: str) -> Dict[str, str]:
    """
    Extract expanded sections: Intro, Literature_Review, Research_Models_Used,
    Methodology, Discussion, Future_Scope, Theory.
    """
    prompt = f"""Please extract these sections from the research paper:
    1. Introduction
    2. Literature Review
    3. Research Models Used
    4. Methodology
    5. Discussion
    6. Future Scope
    7. Theory

    Paper text: {text}
    
    Return in this exact format without any additional text or explanations also make sure 
    no data should be empty (at least 10-15 words) and it should be meaningful:
    Intro: <text>
    Literature_Review: <text>
    Research_Models_Used: <text>
    Methodology: <text>
    Discussion: <text>
    Future_Scope: <text>
    Theory: <text>
    """
    response = get_gemini_response(prompt)
    if not response:
        return {}
    sections = {}
    lines = response.split("\n")
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            sections[key.strip()] = value.strip()
    return sections


# --------------------------------------------------------------------------------
# 7. Variables Extraction
# --------------------------------------------------------------------------------
def extract_variables(text: str) -> Dict[str, Any]:
    """
    Extract variable data: Independent_Variables, nof_Independent_Variables,
    Dependent_Variables, nof_Dependent_Variables, Control_Variables,
    Extraneous_Variables, nof_Control_Variables, nof_Extraneous_Variables
    """
    prompt = f"""From the paper text, extract the following fields:
    1. Independent_Variables
    2. nof_Independent_Variables
    3. Dependent_Variables
    4. nof_Dependent_Variables
    5. Control_Variables
    6. Extraneous_Variables
    7. nof_Control_Variables
    8. nof_Extraneous_Variables

    Return them in this format:
    Independent_Variables: <list>
    nof_Independent_Variables: <integer>
    Dependent_Variables: <list>
    nof_Dependent_Variables: <integer>
    Control_Variables: <list>
    Extraneous_Variables: <list>
    nof_Control_Variables: <integer>
    nof_Extraneous_Variables: <integer>

    Paper text: {text}
    """
    response = get_gemini_response(prompt)
    if not response:
        return {}
    variables = {}
    lines = response.split("\n")
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            # Attempt to convert to integer where appropriate
            clean_key = key.strip()
            clean_value = value.strip()
            if clean_key.startswith("nof_"):
                try:
                    variables[clean_key] = int(clean_value)
                except ValueError:
                    # fallback if it's not an integer
                    variables[clean_key] = 0
            else:
                variables[clean_key] = clean_value
    return variables


# --------------------------------------------------------------------------------
# 8. Utility to ensure no empty fields (example logic)
# --------------------------------------------------------------------------------
def ensure_non_empty_values(data: Dict[str, Any], fallback_text: str) -> Dict[str, Any]:
    """
    Ensure each extracted field has meaningful content. If empty, fill with default text.
    """
    for k, v in data.items():
        if not v or len(str(v).split()) < 3:  # example check for minimal words
            data[k] = f"No sufficient data found for {k}. Could not parse."
    return data


# --------------------------------------------------------------------------------
# 9. Processing the Paper
# --------------------------------------------------------------------------------
# def process_paper(text: str) -> Dict[str, Any]:
#     """
#     Orchestrate calls to extract basic info, content sections, and variables.
#     Return a dictionary containing all the fields with consistent naming.
#     """
#     with st.spinner("Extracting basic information..."):
#         basic_info = extract_basic_info(text)
#         basic_info = ensure_non_empty_values(basic_info, text)

#     with st.spinner("Extracting content sections..."):
#         content_sections = extract_content_sections(text)
#         content_sections = ensure_non_empty_values(content_sections, text)

#     with st.spinner("Extracting variables..."):
#         variables_info = extract_variables(text)
#         variables_info = ensure_non_empty_values(variables_info, text)

#     # Create a single dictionary with all fields
#     paper_doc = {
#         "Title": basic_info.get("Title", ""),
#         "Publication": basic_info.get("Publication", ""),
#         "Journal_Conference": basic_info.get("Journal_Conference", ""),
#         "Abstract": basic_info.get("Abstract", ""),
#         "Keywords": basic_info.get("Keywords", ""),
#         "Author": basic_info.get("Author", ""),
#         "Date_of_Publication": basic_info.get("Date_of_Publication", ""),
#         "Intro": content_sections.get("Intro", ""),
#         "Literature_Review": content_sections.get("Literature_Review", ""),
#         "Research_Models_Used": content_sections.get("Research_Models_Used", ""),
#         "Methodology": content_sections.get("Methodology", ""),
#         "Discussion": content_sections.get("Discussion", ""),
#         "Future_Scope": content_sections.get("Future_Scope", ""),
#         "Theory": content_sections.get("Theory", ""),
#         "Independent_Variables": variables_info.get("Independent_Variables", ""),
#         "nof_Independent_Variables": variables_info.get("nof_Independent_Variables", 0),
#         "Dependent_Variables": variables_info.get("Dependent_Variables", ""),
#         "nof_Dependent_Variables": variables_info.get("nof_Dependent_Variables", 0),
#         "Control_Variables": variables_info.get("Control_Variables", ""),
#         "Extraneous_Variables": variables_info.get("Extraneous_Variables", ""),
#         "nof_Control_Variables": variables_info.get("nof_Control_Variables", 0),
#         "nof_Extraneous_Variables": variables_info.get("nof_Extraneous_Variables", 0),
#     }

#     return paper_doc

# filepath: /c:/Users/acer/OneDrive/Documents/GitHub/res-cor/research22.py
# ...existing code continues...

# --------------------------------------------------------------------------------
# 3. Paper Type Attributes
# --------------------------------------------------------------------------------
PAPER_TYPE_ATTRIBUTES = {
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


# --------------------------------------------------------------------------------
# 4. Extract Paper Fields
# --------------------------------------------------------------------------------
def extract_paper_fields(text: str, paper_type: str) -> Dict[str, Any]:
    """
    Use Gemini to extract fields based on the paper type attributes,
    then return a dictionary of extracted fields.
    """
    if paper_type not in PAPER_TYPE_ATTRIBUTES:
        st.error("Invalid paper type selected.")
        return {}

    selected_attrs = PAPER_TYPE_ATTRIBUTES[paper_type]
    prompt = f"""
    Extract the following fields from the research paper text below:

    {", ".join(selected_attrs)}

    Paper text:
    {text}

    Return them in this JSON format strictly, with no extra text:
    [
        {{
            {", ".join([f'"{attr}": "value"' for attr in selected_attrs])}
        }}
    ]
    """

    try:
        response = get_gemini_response(prompt)
        if not response:
            st.error("No response from Gemini.")
            return {}

        # Clean up any text around JSON
        # Clean up any text around JSON
        raw_text = response.strip()

        # Find start and end of JSON
        json_start = raw_text.find("[")
        json_end = raw_text.rfind("]") + 1
        json_str = raw_text[json_start:json_end]

        # Try removing trailing commas, extra quotes, etc.
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*\]", "]", json_str)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            st.warning(f"Fixing JSON errors: {str(e)}")
            # As a last-resort attempt, remove anything after the last curly bracket
            bracket_pos = json_str.rfind("}")
            if bracket_pos != -1:
                json_str = json_str[: bracket_pos + 1]
            # Try again
            data = json.loads(json_str)

        if isinstance(data, list) and len(data) > 0:
            return data[0]
        else:
            st.error("Gemini did not return a valid JSON array.")
            return {}
    except Exception as e:
        st.error(f"Error in Gemini extraction: {str(e)}")
        return {}


# --------------------------------------------------------------------------------
# 5. Process Paper and Save
# --------------------------------------------------------------------------------
def process_paper(text: str, paper_type: str):
    """
    Extract paper fields based on paper type, then save to
    the corresponding MongoDB collection.
    """
    db = create_db_connection()
    if not db:
        return

    # Determine collection name
    collection_name = paper_type.replace(" ", "_").lower()
    collection = db[collection_name]

    # Extract fields
    extracted_data = extract_paper_fields(text, paper_type)
    if extracted_data:
        # Insert into MongoDB
        collection.insert_one(extracted_data)
        return extracted_data
    return {}


# --------------------------------------------------------------------------------
# 6. Streamlit UI for Paper Extraction
# --------------------------------------------------------------------------------
def main():
    # st.set_page_config(page_title="Extract Research Paper", layout="wide")
    st.title("Extract Research Paper")

    paper_type = st.selectbox(
        "Select type of research paper:",
        [
            "Review Based Paper",
            "Opinion/Perspective Based Paper",
            "Empirical Research Paper",
            "Research Paper (Other)",
        ],
    )

    uploaded_file = st.file_uploader("Upload a PDF or text file", type=["pdf", "txt"])

    if st.button("Extract & Save") and uploaded_file:
        try:
            # Read file content
            if uploaded_file.type == "application/pdf":
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text()
            else:
                text_content = uploaded_file.read().decode("utf-8", errors="replace")

            with st.spinner("Extracting fields..."):
                data = process_paper(text_content, paper_type)

            if data:
                st.success(
                    f"Paper extracted and saved to MongoDB in '{paper_type}' collection!"
                )
                st.write("Extracted fields:")
                st.json(data)

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")


# ...existing code (if any)...

if __name__ == "__main__":
    main()
