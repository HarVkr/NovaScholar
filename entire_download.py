import streamlit as st
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
import os

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


def get_collection_data(paper_type: str):
    """
    Fetch all documents from the specified collection based on paper type.
    """
    try:
        # Determine collection name based on paper type
        collection_name = paper_type.replace(" ", "_").lower()
        doc_collection = db[collection_name]

        # Get all documents
        docs = list(doc_collection.find())

        # Convert ObjectId to string
        for doc in docs:
            doc["_id"] = str(doc["_id"])

        return docs
    except Exception as e:
        st.error(f"Database Error: {str(e)}")
        return None


def main():
    st.title("MongoDB Collection Download")
    st.write("Download all documents from the selected research paper collection")

    # Dropdown to select the type of research paper
    paper_type = st.selectbox(
        "Select type of research paper:",
        [
            "Review Based Paper",
            "Opinion/Perspective Based Paper",
            "Empirical Research Paper",
            "Research Paper (Other)",
        ],
    )

    if st.button("Fetch Data"):
        with st.spinner("Retrieving documents from MongoDB..."):
            docs = get_collection_data(paper_type)

            if docs:
                # Convert to DataFrame
                df = pd.DataFrame(docs)
                # Convert lists to comma-separated strings for consistency
                for col in df.columns:
                    if df[col].apply(lambda x: isinstance(x, list)).any():
                        df[col] = df[col].apply(
                            lambda x: (
                                ", ".join(map(str, x)) if isinstance(x, list) else x
                            )
                        )
                st.success(
                    f"Successfully retrieved {len(df)} documents from '{paper_type}' collection."
                )
                st.dataframe(df)

                # Provide option to download the data as CSV
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{paper_type.replace(' ', '_').lower()}_papers.csv",
                    mime="text/csv",
                )
            else:
                st.warning(f"No documents found in the '{paper_type}' collection.")


if __name__ == "__main__":
    main()
