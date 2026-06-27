# UPSC Domain Knowledge Co-Pilot

## Overview

UPSC Domain Knowledge Co-Pilot is a Retrieval-Augmented Generation (RAG) application designed to help UPSC aspirants interact with domain-specific documents through natural language questions.

The system allows users to upload study material, create document corpora, perform semantic search, and receive AI-generated answers grounded in uploaded content.

---

## Features

* User Authentication (Signup/Login)
* Corpus Management

  * Create corpus
  * Select corpus
  * Delete corpus
* Multi-document Upload

  * PDF
  * DOCX
  * TXT
  * Markdown
* Automatic Text Extraction
* Intelligent Chunking
* Embedding Generation using Sentence Transformers
* Semantic Search using Cosine Similarity
* Retrieval-Augmented Generation (RAG)
* Gemini-powered Answer Generation
* Persistent Chat Memory
* Source Citation Display
* Retrieval Metrics Dashboard
* Answer Export

  * TXT
  * Markdown

---

## Tech Stack

### Frontend

* Streamlit

### Backend

* Python
* SQLAlchemy
* SQLite

### AI & NLP

* Sentence Transformers
* Scikit-Learn
* Google Gemini API

### Document Processing

* PyPDF
* Python-Docx

---

## Project Structure

upsc-copilot/

├── app/

├── backend/

├── frontend/

├── requirements.txt

├── README.md

└── .gitignore

---

## Installation

1. Clone the repository

2. Create a virtual environment

3. Install dependencies

4. Create a .env file and add:

GEMINI_API_KEY=YOUR_API_KEY

5. Run the application:

streamlit run frontend/streamlit_app.py

---

## Usage

1. Register or login
2. Create a corpus
3. Upload UPSC study material
4. Ask questions
5. View AI-generated answers with sources
6. Export answers if needed

---

## Future Improvements

* Hybrid Search (BM25 + Vector Search)
* Advanced Reranking
* Multi-document Comparison
* UPSC-specific Evaluation Metrics
* Cloud Deployment
* Admin Dashboard

---

## Author

Mari

UPSC Domain Knowledge Co-Pilot Project
