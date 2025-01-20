import streamlit as st
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict

def load_and_preprocess_data(uploaded_file):
    """Load and preprocess the CSV data."""
    df = pd.read_csv(uploaded_file)
    # Combine relevant text fields for similarity comparison
    df['combined_text'] = df['Title'] + ' ' + df['Abstract'] + ' ' + df['Keywords']
    return df

def calculate_similarity_matrix(df):
    """Calculate cosine similarity matrix based on combined text."""
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(df['combined_text'])
    similarity_matrix = cosine_similarity(tfidf_matrix)
    return similarity_matrix

def find_similar_papers(similarity_matrix, df, threshold=0.7):
    """Find pairs of papers with similarity above threshold."""
    similar_pairs = []
    for i in range(len(similarity_matrix)):
        for j in range(i + 1, len(similarity_matrix)):
            similarity = similarity_matrix[i][j]
            if similarity >= threshold:
                similar_pairs.append({
                    'Paper 1': df.iloc[i]['Title'],
                    'Paper 2': df.iloc[j]['Title'],
                    'Similarity': similarity
                })
    return pd.DataFrame(similar_pairs)

def find_outliers(similarity_matrix, df, threshold=0.3):
    """Find papers with low average similarity to others."""
    avg_similarities = np.mean(similarity_matrix, axis=1)
    outliers = []
    for i, avg_sim in enumerate(avg_similarities):
        if avg_sim < threshold:
            outliers.append({
                'Title': df.iloc[i]['Title'],
                'Average Similarity': avg_sim
            })
    return pd.DataFrame(outliers)

def create_similarity_heatmap(similarity_matrix, df):
    """Create a heatmap of similarity matrix."""
    fig = go.Figure(data=go.Heatmap(
        z=similarity_matrix,
        x=df['Title'],
        y=df['Title'],
        colorscale='Viridis'
    ))
    fig.update_layout(
        title='Paper Similarity Heatmap',
        xaxis_tickangle=-45,
        height=800
    )
    return fig

def analyze_keywords(df):
    """Analyze keyword frequency across papers."""
    keyword_freq = defaultdict(int)
    for keywords in df['Keywords']:
        if isinstance(keywords, str):
            for keyword in keywords.split(','):
                keyword = keyword.strip()
                keyword_freq[keyword] += 1
    
    keyword_df = pd.DataFrame([
        {'Keyword': k, 'Frequency': v} 
        for k, v in keyword_freq.items()
    ]).sort_values('Frequency', ascending=False)
    
    return keyword_df

def main():
    st.title('Research Papers Similarity Analysis')
    
    uploaded_file = st.file_uploader("Upload your research papers CSV file", type=['csv'])
    
    if uploaded_file is not None:
        df = load_and_preprocess_data(uploaded_file)
        similarity_matrix = calculate_similarity_matrix(df)
        
        st.header('Document Similarity Analysis')
        
        # Similarity Heatmap
        st.subheader('Similarity Heatmap')
        heatmap = create_similarity_heatmap(similarity_matrix, df)
        st.plotly_chart(heatmap, use_container_width=True)
        
        # Similar Papers
        st.subheader('Similar Papers')
        similarity_threshold = st.slider('Similarity Threshold', 0.0, 1.0, 0.7)
        similar_papers = find_similar_papers(similarity_matrix, df, similarity_threshold)
        if not similar_papers.empty:
            st.dataframe(similar_papers)
        else:
            st.write("No papers found above the similarity threshold.")
        
        # Outliers
        st.subheader('Outlier Papers')
        outlier_threshold = st.slider('Outlier Threshold', 0.0, 1.0, 0.3)
        outliers = find_outliers(similarity_matrix, df, outlier_threshold)
        if not outliers.empty:
            st.dataframe(outliers)
        else:
            st.write("No outliers found below the threshold.")
        
        # Keyword Analysis
        st.header('Keyword Analysis')
        keyword_freq = analyze_keywords(df)
        if not keyword_freq.empty:
            fig = px.bar(keyword_freq, x='Keyword', y='Frequency',
                        title='Keyword Frequency Across Papers')
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        
        # Basic Statistics
        st.header('Basic Statistics')
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Papers", len(df))
            st.metric("Average Similarity", f"{np.mean(similarity_matrix):.2f}")
        with col2:
            st.metric("Unique Keywords", len(keyword_freq))
            st.metric("Max Similarity", f"{np.max(similarity_matrix[~np.eye(similarity_matrix.shape[0], dtype=bool)]):.2f}")

if __name__ == "__main__":
    main()