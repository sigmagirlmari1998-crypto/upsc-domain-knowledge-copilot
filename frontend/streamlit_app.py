import streamlit as st
from pypdf import PdfReader
from docx import Document
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
import sys
import os

# --- project path setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)
from app.gemini_utils import ask_gemini

from backend.db import init_db
from backend.corpus_manager import save_document, load_corpus_data
from backend.memory import (
    add_message,
    get_history,
    clear_history,
    format_memory_for_prompt
)

from frontend.ui_auth import render_auth_gate, render_logout
from frontend.ui_corpus import render_corpus_sidebar

init_db()

st.title("UPSC Domain Knowledge Co-Pilot")

user = render_auth_gate()

if not user:
    st.stop()

render_logout(user)

active_corpus = render_corpus_sidebar(user)

if not active_corpus:
    st.info("Create or select a corpus from the sidebar to begin.")
    st.stop()

st.caption(
    f"Active corpus: {active_corpus['name']}"
)

# Chat History Display

db_history = get_history(active_corpus["id"])

st.session_state.chat_history = []

pair = {}

for m in db_history:

    if m["role"] == "user":

        pair = {
            "question": m["content"]
        }

    elif (
        m["role"] == "assistant"
        and "question" in pair
    ):

        pair["answer"] = m["content"]

        st.session_state.chat_history.append(pair)

        pair = {}

if st.session_state.chat_history:

    st.subheader("💬 Previous Questions")

    for i, chat in enumerate(
        reversed(st.session_state.chat_history),
        start=1
    ):

        with st.expander(
            f"Q{i}: {chat['question'][:80]}"
        ):

            st.write("**Question:**")
            st.write(chat["question"])

            st.write("**Answer:**")
            st.write(chat["answer"])

# ---------------- SIDEBAR ----------------

st.sidebar.header("⚙️ Retrieval Settings")

top_k = st.sidebar.slider(
    "Top-K chunks",
    1,
    15,
    8
)

sim_threshold = st.sidebar.slider(
    "Similarity threshold",
    0.0,
    1.0,
    0.35,
    0.01
)

st.sidebar.header("📝 Answer Settings")

answer_mode = st.sidebar.selectbox(
    "Answer Mode",
    [
        "UPSC Mode",
        "Short Answer",
        "Detailed Answer",
        "Notes Mode"
    ]
)

st.sidebar.header("🐞 Debug Settings")

show_chunks = st.sidebar.checkbox(
    "Show Retrieved Chunks",
    value=True
)

debug_retrieval = st.sidebar.checkbox(
    "Debug Retrieval",
    value=False
)

st.sidebar.header("📊 Statistics")

stats_box = st.sidebar.empty()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if st.sidebar.button("🗑️ Clear Chat"):

    clear_history(active_corpus["id"])

    st.session_state.chat_history = []

    st.rerun()

# ---------------------------------------------------------------------------
# Model & helpers
# ---------------------------------------------------------------------------
@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")


model = load_model()


def create_embeddings(docs):
    return model.encode(docs)


def chunk_text(text, chunk_size=1200):

    paragraphs = text.split("\n")

    chunks = []
    current_chunk = ""

    for para in paragraphs:

        if len(current_chunk) + len(para) < chunk_size:
            current_chunk += para + "\n"

        else:
            chunks.append(current_chunk)
            current_chunk = para + "\n"

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def clean_text(text):

    text = re.sub(
        r'https?\s*:\s*/\s*/\S+',
        '',
        text
    )

    text = re.sub(
        r'[ \t]+',
        ' ',
        text
    )

    text = re.sub(
        r'\n{3,}',
        '\n\n',
        text
    )

    return text.strip()

def reformulate_query(q):

    q = re.sub(
        r"\s+",
        " ",
        q
    )

    return q.strip()

def build_prompt(context, question, mode):

    base = f"""
You are an expert UPSC mentor.

Use the context as PRIMARY source.

If the context contains insufficient information,
clearly mention:

"Additional information beyond uploaded documents:"

and then provide relevant UPSC knowledge.

Context:
{context}

Question:
{question}
"""

    if mode == "Short Answer":
        return base + """
Give only a crisp 3-4 line answer.
Do not use outside information.
"""

    elif mode == "Detailed Answer":
        return base + """
1. Direct answer
2. Detailed explanation
3. Facts
4. Statistics
5. Significance for India
6. UPSC relevance
Do not use outside information.
"""

    elif mode == "Notes Mode":
        return base + """
Create revision notes.

Sections:
- Key Facts
- Important Terms
- Prelims Nuggets
- Mains Keywords

Use only context.
"""

    else:
        return base + """
1. Give a 2-3 line direct answer first.
2. Explain in bullet points.
3. Include important facts.
4. Include key statistics if available.
5. Mention significance for India.
6. Mention UPSC Prelims relevance.
7. Mention UPSC Mains relevance.
8. Do not use information outside context.
"""

# ---------------------------------------------------------------------------
# SINGLE ingestion pipeline -> list of {source, page, text}
# ---------------------------------------------------------------------------
def ingest_document(uploaded_file, min_chunk_len=100):
    file_type = uploaded_file.name.split(".")[-1].lower()

    documents = []

    def add_chunks(raw_text, page_label):
        for chunk in chunk_text(clean_text(raw_text)):
            if len(chunk.strip()) < min_chunk_len:
                continue
            documents.append({
                "source": uploaded_file.name,
                "page": page_label,
                "text": chunk,
            })

    if file_type == "pdf":
        reader = PdfReader(uploaded_file)
        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""

            page_text = re.sub(
            r'(\w)-\s+(\w)',
            r'\1\2',
            page_text
            )

            page_text = re.sub(
            r'([A-Z])\s+([A-Z])',
            r'\1\2',
            page_text
            )

            add_chunks(page_text, page_num)

    elif file_type == "docx":
        doc = Document(uploaded_file)
        body = "\n".join(p.text for p in doc.paragraphs)
        add_chunks(body, "Section")

    elif file_type in ("txt", "md"):
        body = uploaded_file.read().decode("utf-8", errors="ignore")
        add_chunks(body, "Section")

    print(
        "DOCUMENTS CREATED:", 
        uploaded_file.name,
        len(documents)
        ) 

    return documents


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

uploaded_files = st.file_uploader(
    "Upload your Document",
    type=["pdf", "docx", "txt", "md"],
    accept_multiple_files = True,
)

documents = []
doc_embeddings = None

if uploaded_files:              ## Process every uploaded file and merge chunks into a single list
    
        for uploaded_file in uploaded_files: 
            documents.extend(ingest_document(uploaded_file))

        if not documents:
            st.warning("No readable text found in this document.")
        else:
            doc_texts = [d["text"] for d in documents]
            doc_embeddings = create_embeddings(doc_texts)

            # Save uploaded files into active corpus

        for uploaded_file in uploaded_files:

            file_chunks = [
                d
            for d in documents
                if d["source"] == uploaded_file.name
            ]

            if not file_chunks:
               continue

            indices = [
               i
                for i, d in enumerate(documents)
                if d["source"] == uploaded_file.name
            ]

            file_embeddings = doc_embeddings[indices]

            save_document(
                active_corpus["id"],
                uploaded_file.name,
                file_chunks,
                file_embeddings
            )

        # Reload full corpus from database

        saved_docs, saved_embs = load_corpus_data(
            active_corpus["id"]
        )

        if saved_docs:

            documents = saved_docs

            doc_texts = [
                d["text"]
               for d in documents
            ]

            doc_embeddings = saved_embs

        stats_box.markdown(
            f"""
        **Documents:** {len(uploaded_files)}

        **Chunks:** {len(documents)}
        """
        )

        pages = {
            (d["source"], d["page"])
            for d in documents
        }

        with st.expander("📚 Corpus Statistics", expanded=True):

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Files",
                len(uploaded_files)
            )

            c2.metric(
                "Pages/Sections",
                len(pages)
            )

            c3.metric(
                "Chunks",
                len(documents)
            )

        from collections import Counter

        with st.expander("🗂️ Upload Summary"):

            counts = Counter(
                d["source"]
                for d in documents
            )

            for file_name, chunk_count in counts.items():

                st.write(
                    f"• {file_name} — {chunk_count} chunks"
                )

        st.subheader("📊 Chunk Distribution")

        for file_name, chunk_count in counts.items():

            st.write(
                f"{file_name}: {chunk_count} chunks"
            )        

        st.success(
            f"{len(uploaded_files)} document(s) loaded successfully!"
        )

        st.write(
            "Files:",
            ", ".join(f.name for f in uploaded_files)
        )

        st.write(
            "Total chunks:",
            len(documents)
        )

        st.write(
            "Embedding vectors:",
            len(doc_embeddings)
        )

        st.text_area(
            "Extracted Text (preview)",
            "\n\n".join(doc_texts)[:5000],
            height=300,
        )

# Load saved corpus when no new uploads

if not uploaded_files:

    saved_docs, saved_embs = load_corpus_data(
        active_corpus["id"]
    )

    if saved_docs:

        documents = saved_docs

        doc_texts = [
            d["text"]
            for d in documents
        ]

        doc_embeddings = saved_embs

        stats_box.markdown(
            f"**Chunks:** {len(documents)}"
        )        

question = st.text_input("Ask a question from the documents")


# ---------------------------------------------------------------------------
# Semantic search + Gemini answer
# ---------------------------------------------------------------------------
if question and doc_embeddings is not None and len(documents) > 0:

    question_embedding = model.encode([question])
    similarities = cosine_similarity(question_embedding, doc_embeddings)[0]
    top_indices = np.argsort(
    similarities
    )[::-1][:top_k]

    st.success("Top Relevant Results")

    context = ""
    citations = []  # list of (source, page)

    for idx in top_indices:

        score = float(similarities[idx])

        if debug_retrieval:

            st.write(
               f"Similarity: {score:.3f} | "
               f"{documents[idx]['source']}"
            )

        if score < sim_threshold:
            continue

        doc = documents[idx]

        citations.append(
            (doc["source"], doc["page"])
        )

        context += doc["text"] + "\n\n"

        rank = len(citations)

        query_words = question.lower().split()

        best_pos = -1

        for word in query_words:

            pos = doc["text"].lower().find(word)

            if pos != -1:
                best_pos = pos
                break

        if best_pos == -1:

            start = 0
            end = min(len(doc["text"]), 800)

        else:

            start = max(0, best_pos - 200)
            end = min(len(doc["text"]), best_pos + 600)

        if show_chunks:

            with st.expander(
                f"[{rank}] {doc['source']} | Page {doc['page']} | Score {score:.2f}"
            ):

                st.write(
                    doc["text"][start:end]
                )

                if debug_retrieval:

                    st.caption(
                        f"Chunk Index: {idx}"
                    )       

    if not context:
        st.error("No sufficiently relevant content found.")
    else:
        st.subheader("Combined Context")
        st.write(context[:3000])

        clean_q = reformulate_query(question)

        retrieved_count = len(citations)

        avg_similarity = (
            np.mean(
               [   
                   similarities[i]
                   for i in top_indices
                   if similarities[i] >= sim_threshold
                ]
            )
            if retrieved_count > 0
            else 0
        )

        with st.expander("📈 Retrieval Metrics"):

            c1, c2, c3 = st.columns(3)

            c1.metric(
               "Retrieved Chunks",
                retrieved_count
            )

            c2.metric(
                "Average Similarity",
                f"{avg_similarity:.2f}"
            )

            c3.metric(
                "Total Corpus Chunks",
                len(documents)
            )

            coverage = (
                retrieved_count / len(documents)
            ) * 100

            st.metric(
                "Corpus Coverage %",
                f"{coverage:.2f}%"
            )

        memory_block = format_memory_for_prompt(
            active_corpus["id"]
        )

        prompt = build_prompt(
            memory_block + "\n" + context,
            clean_q,
            answer_mode
        )

        with st.spinner("Generating answer..."):
            answer = ask_gemini(prompt)

            add_message(
                active_corpus["id"],
                "user",
                question
            )

            add_message(
                active_corpus["id"],
                "assistant",
                answer
            )

            st.session_state.chat_history.append(
        {
            "question": question,
            "answer": answer
        }  
      ) 

        st.subheader("AI Answer")
        st.write(answer)

        col1, col2 = st.columns(2)

        with col1:
            st.download_button(
                "⬇ Download TXT",
                answer,
                file_name="upsc_answer.txt",
                mime="text/plain"
            )

        with col2:
            st.download_button(
                "⬇ Download Markdown",
                f"# UPSC Answer\n\n{answer}",
                file_name="upsc_answer.md",
                mime="text/markdown"
            )

        st.subheader("Sources")
        seen = []
        for source, page in citations:
            label = f"{source} — Page {page}" if page != "Section" else f"{source} — Section"
            if label not in seen:
                seen.append(label)
        for label in seen:
            st.write("•", label)
