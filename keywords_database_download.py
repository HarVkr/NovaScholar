import streamlit as st
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import json
import re

# 1. Load environment variables
load_dotenv()
MONGODB_URI = os.getenv(
    "MONGODB_UR",
    "mongodb+srv://milind:05july60@cluster0.d6mld.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
)
# 2. Create MongoDB connection
client = MongoClient(MONGODB_URI)
db = client["novascholar_db"]
collection = db["research_papers"]


def convert_mixed_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert any columns that contain lists into comma-separated strings
    in order to ensure consistent data types for CSV export.
    """
    for col in df.columns:
        if any(isinstance(val, list) for val in df[col].dropna()):
            df[col] = df[col].apply(
                lambda x: (
                    ", ".join(map(str, x))
                    if isinstance(x, list)
                    else (str(x) if pd.notna(x) else "")
                )
            )
    return df


def filter_and_export_collection_to_csv(keyword: str, doc_collection=None):
    """
    Find documents in the given collection with a matching keyword
    in the 'Keywords' field, export them to CSV, and return the DataFrame
    and CSV filename.
    """
    # Use the default 'research_papers' collection if none provided
    if doc_collection is None:
        doc_collection = collection

    docs = list(doc_collection.find({"Keywords": {"$regex": keyword, "$options": "i"}}))
    if docs:
        df = pd.DataFrame(docs)
        df = convert_mixed_columns(df)
        csv_filename = "papers_filtered_export.csv"
        df.to_csv(csv_filename, index=False)
        return df, csv_filename
    else:
        # Return an empty DataFrame if no documents found
        return pd.DataFrame(), None


def main():
    # st.set_page_config(page_title="Filter and Export Papers", layout="wide")
    st.title("Filter and Export Papers by Keyword")

    # Let user select the paper type
    paper_type = st.selectbox(
        "Select type of research paper:",
        [
            "Review Based Paper",
            "Opinion/Perspective Based Paper",
            "Empirical Research Paper",
            "Research Paper (Other)",
        ],
    )

    # 5. Let user enter the keyword to filter
    keyword_input = st.text_input(
        "Enter the exact keyword to filter papers by 'Keywords' field:"
    )

    # When user clicks button, use the collection for the selected paper type
    if st.button("Export Filtered Papers to CSV"):
        with st.spinner("Exporting filtered documents..."):
            try:
                # Determine dynamic collection based on paper type
                collection_name = paper_type.replace(" ", "_").lower()
                doc_collection = db[collection_name]

                df, csv_filename = filter_and_export_collection_to_csv(
                    keyword_input, doc_collection
                )
                if not df.empty and csv_filename:
                    st.success(
                        f"Successfully exported filtered papers to {csv_filename}!"
                    )
                    st.write("Preview of the filtered DataFrame:")
                    st.dataframe(df)
                else:
                    st.warning("No matching documents found for that keyword.")
            except Exception as e:
                st.error(f"Error exporting filtered papers: {str(e)}")


if __name__ == "__main__":
    main()
