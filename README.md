# 🤖 RAG Chatbot — Groq + LangChain + Streamlit

A production-ready Retrieval-Augmented Generation (RAG) chatbot that lets you chat with your documents using Groq's blazing-fast inference.

---

## ✨ Features

| Feature | Detail |
|---|---|
| **Document types** | PDF, TXT, DOCX, CSV |
| **Multi-file** | Upload several files at once |
| **LLM backend** | Groq (llama3-8b, llama3-70b, mixtral, gemma2) |
| **Embeddings** | `all-MiniLM-L6-v2` (runs locally, free) |
| **Vector store** | FAISS (in-memory, no server needed) |
| **Memory** | Conversational buffer — remembers context |
| **Sources** | Shows which chunks were used per answer |

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get a Groq API key
- Visit [console.groq.com](https://console.groq.com)
- Create a free account and generate an API key

### 3. Run the app
```bash
streamlit run app.py
```

### 4. Use the chatbot
1. Paste your **Groq API key** in the sidebar
2. Choose a **model**
3. **Upload** one or more documents
4. Click **Process Documents**
5. Start **chatting**!

---

## 🏗️ Architecture

```
User Upload
    │
    ▼
Document Loader (PyPDF / TextLoader / Docx2txt / CSV)
    │
    ▼
RecursiveCharacterTextSplitter  (chunk_size=1000, overlap=200)
    │
    ▼
HuggingFace Embeddings (all-MiniLM-L6-v2)
    │
    ▼
FAISS Vector Store
    │
    ▼ (top-4 chunks retrieved)
ConversationalRetrievalChain
    │
    ▼
Groq LLM  →  Answer + Sources
```

---

## 📁 Project Structure

```
rag_chatbot/
├── app.py            # Main Streamlit application
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

---

## 🔧 Configuration

All configuration is done via the sidebar UI:
- **Groq API Key** — your personal key
- **Model** — choose speed vs. capability
- **Documents** — drag & drop to upload

---

## 📝 Notes

- Embeddings run **locally** on CPU — no extra API key needed
- The vector store is **in-memory**; re-upload if you refresh the page
- For large documents, processing may take 30–60 seconds
