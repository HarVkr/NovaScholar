import streamlit as st
import pandas as pd
import networkx as nx
from bokeh.models import HoverTool
from bokeh.plotting import figure, from_networkx
import requests
import json
import google.generativeai as genai

PERPLEXITY_API_KEY = "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"
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


def extract_edges(keywords):
    keywords = [kw.strip() for kw in keywords.split(",")]
    edges = [
        (keywords[i], keywords[j])
        for i in range(len(keywords))
        for j in range(i + 1, len(keywords))
    ]
    return edges


def create_knowledge_graph(data):
    G = nx.Graph()

    for _, row in data.iterrows():
        words = []
        for col in data.columns:
            if pd.notnull(row[col]):
                # Convert to string and handle numeric values
                cell_value = str(row[col]).strip()
                if cell_value:
                    words.extend(cell_value.split())

        if words:
            edges = extract_edges(",".join(words))
            G.add_edges_from(edges)

            for word in words:
                word = word.strip()
                if word not in G:
                    G.add_node(word, title=word, value=len(word))

    return G


def render_graph_bokeh(G):
    plot = figure(
        title="Interactive Knowledge Graph",
        x_range=(-1.5, 1.5),
        y_range=(-1.5, 1.5),
        tools="pan,wheel_zoom,box_zoom,reset,tap",
        active_scroll="wheel_zoom",
    )
    plot.add_tools(HoverTool(tooltips="@index"))

    graph_renderer = from_networkx(G, nx.spring_layout, scale=1, center=(0, 0))

    graph_renderer.node_renderer.glyph.size = 10
    graph_renderer.node_renderer.glyph.fill_color = "blue"
    graph_renderer.node_renderer.glyph.line_color = "black"

    graph_renderer.edge_renderer.glyph.line_width = 1
    graph_renderer.edge_renderer.glyph.line_color = "gray"

    plot.renderers.append(graph_renderer)

    return plot


import re


def search_papers(topic: str, num_papers: int) -> list:
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }

    prompt = f"""Find {num_papers} recent research papers about {topic}.
    Return ONLY a valid JSON array with the following structure for each paper:
    [
        {{
            "Title": "paper title",
            "Abstract": "abstract text",
            "Keywords": "key terms"
        }}
    ]"""

    payload = {
        "model": "llama-3.1-sonar-small-128k-chat",
        "messages": [
            {
                "role": "system",
                "content": "You are a research paper analyzer that returns valid JSON arrays.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }

    try:
        response = requests.post(PERPLEXITY_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

        # Clean response to ensure valid JSON
        content = content.strip()
        if not content.startswith("["):
            content = content[content.find("[") :]
        if not content.endswith("]"):
            content = content[: content.rfind("]") + 1]

        # Remove any trailing commas before closing brackets
        content = re.sub(r",\s*]", "]", content)
        content = re.sub(r",\s*}", "}", content)

        papers = json.loads(content)
        if not isinstance(papers, list):
            raise ValueError("Response is not a JSON array")
        return papers
    except requests.exceptions.RequestException as e:
        st.error(f"API Request Error: {str(e)}")
        return []
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON response: {str(e)}")
        st.error(f"Response content: {response.text}")
        return []
    except ValueError as e:
        st.error(f"Error: {str(e)}")
        return []


import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://api.openai.com/v1/engines/davinci-codex/completions"


def call_gemini_api(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "max_tokens": 150,
        "temperature": 0.7,
    }

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Gemini API Error: {str(e)}")
        return ""


def generate_gaps_paragraph(gaps):
    prompt = f"Generate a brief paragraph about the gaps in the research based on the following gaps: {', '.join(gaps)}"
    return call_gemini_api(prompt)


def generate_insights(G, topic):
    papers = search_papers(topic, 5)
    if papers:
        st.write("### Research Insights from Perplexity API")
        for paper in papers:
            st.write(f"**Title:** {paper['Title']}")
            st.write(f"**Abstract:** {paper['Abstract']}")
            st.write(f"**Keywords:** {paper['Keywords']}")
            st.write("---")

    nodes = list(G.nodes(data=True))
    insights = {}
    insights["Strong Points"] = [
        n for n, d in nodes if G.degree(n) > len(G.nodes) * 0.1
    ]
    insights["Weak Points"] = [n for n, d in nodes if G.degree(n) < len(G.nodes) * 0.05]
    insights["Gaps"] = [n for n, d in nodes if len(list(nx.neighbors(G, n))) == 0]

    st.write("### Graph-Based Insights")
    st.write("**Strong Points:**", insights["Strong Points"])
    st.write("**Weak Points:**", insights["Weak Points"])
    st.write("**Gaps:**", insights["Gaps"])

    if insights["Gaps"]:
        with st.spinner("Generating insights about gaps..."):
            gaps_paragraph = generate_gaps_paragraph(insights["Gaps"])
            if gaps_paragraph:
                st.write("### Gaps in Research")
                st.write(gaps_paragraph)


def main():
    st.title("Advanced Interactive Knowledge Graph")
    st.write(
        "Upload a CSV file to generate a fully interactive and insightful knowledge graph."
    )

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        try:
            data = pd.read_csv(uploaded_file)
            st.write("Preview of the uploaded data:")
            st.dataframe(data.head())

            G = create_knowledge_graph(data)

            st.write("Generated Knowledge Graph:")
            plot = render_graph_bokeh(G)
            st.bokeh_chart(plot, use_container_width=True)

            topic = st.text_input(
                "Enter a topic for additional insights:", "knowledge graphs"
            )
            if topic:
                generate_insights(G, topic)

        except Exception as e:
            st.error(f"An error occurred while processing the file: {e}")
    else:
        st.info("Please upload a CSV file to get started.")


if __name__ == "__main__":
    main()
