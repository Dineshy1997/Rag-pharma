import streamlit as st
import os
from pathlib import Path
import tempfile

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, Docx2txtLoader, CSVLoader
)
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import HumanMessage, AIMessage

st.set_page_config(page_title="RAG Chatbot", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"], p, h1, h2, h3, h4, h5, h6, span, div, input, button, select, textarea, label, a, li, td, th { font-family: 'Inter', sans-serif !important; }

/* Preserve Material Icons font for Streamlit icons */
span[data-testid="stIconMaterial"],
[data-testid="stSidebarCollapseButton"] span,
[data-testid="collapsedControl"] span,
.st-emotion-cache-1rtdyuf,
span[class*="icon"],
[data-testid="stExpander"] summary span[data-testid="stIconMaterial"] {
    font-family: 'Material Symbols Rounded', sans-serif !important;
}
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }
.block-container { padding-top: 2rem !important; }
.stApp { background: #f4f6fb; }

/* Keep sidebar toggle button visible */
button[data-testid="stSidebarCollapseButton"],
button[data-testid="collapsedControl"] {
    visibility: visible !important;
    opacity: 1 !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #6c63ff !important; color: white !important;
    border: none !important; border-radius: 10px !important;
    padding: 0.65rem 1.5rem !important; font-weight: 600 !important;
    font-size: 0.9rem !important; width: 100% !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: #5a52e0 !important;
    box-shadow: 0 6px 18px rgba(108,99,255,0.35) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:disabled { background: #c4c9d4 !important; transform: none !important; }

/* ── Inputs ── */
.stTextInput > div > div > input {
    border-radius: 10px !important; border: 1.5px solid #d1d5db !important;
    padding: 0.65rem 1rem !important; font-size: 0.9rem !important;
    background: #fafafa !important; color: #1a1d2e !important;
}
.stTextInput > div > div > input:focus {
    border-color: #6c63ff !important;
    box-shadow: 0 0 0 3px rgba(108,99,255,0.12) !important;
    background: #fff !important;
}
.stSelectbox > div > div { border-radius: 10px !important; border: 1.5px solid #d1d5db !important; }
.stTextInput label, .stSelectbox label { display: none !important; }

/* ── API Page ── */
.api-brand { font-size:.75rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:#6c63ff; margin-bottom:.5rem; }
.api-title { font-size:1.75rem; font-weight:700; color:#1a1d2e; margin-bottom:.4rem; line-height:1.2; }
.api-sub { font-size:.9rem; color:#6b7280; margin-bottom:2rem; line-height:1.5; }
.field-label { font-size:.78rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:#374151; margin-bottom:.4rem; margin-top:1.2rem; }
.field-hint { font-size:.75rem; color:#9ca3af; margin-top:.4rem; }
.divider { height:1px; background:#e8eaf0; margin:1.8rem 0; }
.info-box { background:#f9fafb; border:1px solid #e8eaf0; border-radius:10px; padding:1rem 1.2rem; margin-top:1.5rem; }
.info-box-label { font-size:.7rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:#9ca3af; margin-bottom:.4rem; }
.info-box-val { font-size:.82rem; color:#6b7280; line-height:1.7; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background:#ffffff; border-right:1px solid #e8eaf0; }
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span:not([data-testid="stIconMaterial"]),
section[data-testid="stSidebar"] div, section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] h4 { color:#1a1d2e !important; }
.sb-brand { font-size:1rem; font-weight:700; color:#6c63ff !important; letter-spacing:.02em; }
.sb-tag { font-size:.72rem; color:#9ca3af !important; }
.sb-section { font-size:.68rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:#9ca3af !important; margin:1.2rem 0 .6rem 0; }
.sb-divider { height:1px; background:#f0f2f7; margin:.8rem 0; }
.conf-box { background:#f4f6fb; border:1px solid #e8eaf0; border-radius:8px; padding:.55rem 1rem; font-size:.8rem; color:#374151; margin-bottom:.4rem; }
.conf-label { font-weight:600; color:#9ca3af; font-size:.68rem; text-transform:uppercase; letter-spacing:.04em; display:block; margin-bottom:2px; }
.doc-badge { background:#f4f6fb; border:1px solid #e8eaf0; border-radius:8px; padding:.42rem .9rem; font-size:.78rem; color:#374151 !important; margin:3px 0; display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.status-pill { display:inline-block; padding:4px 14px; border-radius:20px; font-size:.72rem; font-weight:700; letter-spacing:.05em; text-transform:uppercase; }
.pill-ready { background:#ecfdf5; color:#065f46 !important; border:1px solid #6ee7b7; }
.pill-pending { background:#fffbeb; color:#92400e !important; border:1px solid #fcd34d; }

/* ── Chat page ── */
.page-hdr { padding:1.3rem 1.6rem; background:white; border-radius:14px; border:1px solid #e8eaf0; margin-bottom:1.4rem; display:flex; align-items:center; justify-content:space-between; }
.page-hdr h2 { margin:0; font-size:1.25rem; font-weight:700; color:#1a1d2e; }
.page-hdr p { margin:0; font-size:.8rem; color:#9ca3af; margin-top:2px; }
.model-tag { background:#f0eeff; color:#6c63ff; padding:4px 12px; border-radius:20px; font-size:.73rem; font-weight:700; border:1px solid #ddd9ff; }
.chat-win { background:#fff; border:1px solid #e8eaf0; border-radius:14px; padding:1.4rem 1.6rem; min-height:380px; max-height:500px; overflow-y:auto; margin-bottom:1rem; }
.row-user { display:flex; justify-content:flex-end; margin-bottom:1rem; }
.bbl-user { background:#6c63ff; color:white; border-radius:14px 14px 2px 14px; padding:.7rem 1.1rem; max-width:72%; font-size:.88rem; line-height:1.55; box-shadow:0 3px 10px rgba(108,99,255,.2); }
.row-bot { display:flex; align-items:flex-start; gap:10px; margin-bottom:1rem; }
.bot-lbl { background:#f4f6fb; border:1px solid #e8eaf0; border-radius:6px; padding:3px 8px; font-size:.68rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:#6c63ff; white-space:nowrap; margin-top:4px; }
.bbl-bot { background:#f9fafb; color:#1a1d2e; border-radius:2px 14px 14px 14px; padding:.7rem 1.1rem; max-width:74%; font-size:.88rem; line-height:1.6; border:1px solid #e8eaf0; }
.empty-st { text-align:center; padding:3.5rem 2rem; }
.empty-title { font-size:.95rem; font-weight:600; color:#9ca3af; margin-bottom:.3rem; }
.empty-sub { font-size:.8rem; color:#c4c9d4; }
.src-box { background:#f4f6fb; border-left:3px solid #6c63ff; border-radius:0 8px 8px 0; padding:.5rem 1rem; margin:4px 0; font-size:.79rem; color:#374151; }
.src-name { font-weight:700; font-size:.72rem; text-transform:uppercase; letter-spacing:.04em; color:#1a1d2e; margin-bottom:2px; }
.step-card { background:white; border:1px solid #e8eaf0; border-radius:12px; padding:1.5rem 1.6rem; text-align:center; }
.step-num { display:inline-block; width:28px; height:28px; line-height:28px; border-radius:50%; background:#6c63ff; color:white; font-size:.75rem; font-weight:700; margin-bottom:.7rem; }
.step-title { font-size:.88rem; font-weight:700; color:#1a1d2e; margin-bottom:.3rem; }
.step-desc { font-size:.78rem; color:#9ca3af; line-height:1.5; }
</style>
""", unsafe_allow_html=True)

# ── Configuration ─────────────────────────────────────────────────────────────
GROQ_API_KEY = "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"
MODEL_NAME = "llama-3.3-70b-versatile"

# ── Session defaults ──────────────────────────────────────────────────────────
DEFAULTS = {
    "chat_history": [],       # list of {"role": "user"/"assistant", "content": str}
    "lc_history": [],         # list of LangChain HumanMessage/AIMessage for chain
    "vector_store": None,
    "qa_chain": None,
    "documents_loaded": [],
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Core functions ────────────────────────────────────────────────────────────
def load_document(f):
    suffix = Path(f.name).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(f.getvalue()); tmp_path = tmp.name
    loaders = {".pdf": PyPDFLoader, ".txt": TextLoader, ".docx": Docx2txtLoader, ".csv": CSVLoader}
    cls = loaders.get(suffix)
    if not cls: os.unlink(tmp_path); return None
    try: docs = cls(tmp_path).load()
    finally: os.unlink(tmp_path)
    for d in docs: d.metadata["source_name"] = f.name
    return docs

def build_vector_store(docs):
    chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(docs)
    emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})
    return FAISS.from_documents(chunks, emb)

def build_qa_chain(vs):
    llm = ChatGroq(groq_api_key=GROQ_API_KEY, model_name=MODEL_NAME, temperature=0.1, max_tokens=2048)
    retriever = vs.as_retriever(search_kwargs={"k": 4})

    # Prompt to rephrase question considering chat history
    condense_prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
        ("human", "Given the conversation above, rephrase the follow-up question to be standalone."),
    ])
    history_aware_retriever = create_history_aware_retriever(llm, retriever, condense_prompt)

    # Prompt to answer using retrieved context
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a precise AI assistant. Answer using only the provided context. "
         "If the answer is not in the context, state that clearly.\n\nContext:\n{context}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    combine_chain = create_stuff_documents_chain(llm, qa_prompt)
    return create_retrieval_chain(history_aware_retriever, combine_chain)

def render_chat():
    html = '<div class="chat-win">'
    for m in st.session_state.chat_history:
        if m["role"] == "user":
            html += f'<div class="row-user"><div class="bbl-user">{m["content"]}</div></div>'
        else:
            html += f'<div class="row-bot"><div class="bot-lbl">AI</div><div class="bbl-bot">{m["content"]}</div></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# ══════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown('<div class="sb-brand">Document Intelligence</div>', unsafe_allow_html=True)
        st.markdown('<div class="sb-section">Documents</div>', unsafe_allow_html=True)

        files = st.file_uploader("Upload", type=["pdf","txt","docx","csv"], accept_multiple_files=True, label_visibility="collapsed")

        if st.button("Process Documents", disabled=not files, key="process_btn"):
            with st.spinner("Building knowledge base..."):
                all_docs, names = [], []
                for f in files:
                    docs = load_document(f)
                    if docs: all_docs.extend(docs); names.append(f.name)
                if all_docs:
                    vs = build_vector_store(all_docs)
                    st.session_state.vector_store = vs
                    st.session_state.qa_chain = build_qa_chain(vs)
                    st.session_state.documents_loaded = names
                    st.session_state.chat_history = []
                    st.session_state.lc_history = []
                    st.success(f"{len(names)} document(s) indexed.")
                else:
                    st.error("No text could be extracted.")

        if st.session_state.documents_loaded:
            st.markdown('<div class="sb-section">Indexed Files</div>', unsafe_allow_html=True)
            for n in st.session_state.documents_loaded:
                st.markdown(f'<span class="doc-badge">{n}</span>', unsafe_allow_html=True)

        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
        if st.button("Clear Conversation", key="clear_btn"):
            st.session_state.chat_history = []
            st.session_state.lc_history = []
            st.rerun()

        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
        if st.session_state.qa_chain:
            st.markdown('<span class="status-pill pill-ready">Ready</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-pill pill-pending">Awaiting Documents</span>', unsafe_allow_html=True)

# ══════════════════════════════════════
# CHAT PAGE
# ══════════════════════════════════════
def page_chat():
    render_sidebar()

    st.markdown(f"""
    <div class="page-hdr">
        <div>
            <h2>Document Q&A</h2>
            <p>Ask questions about your uploaded documents</p>
        </div>
        <span class="model-tag">{MODEL_NAME}</span>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.qa_chain:
        c1, c2 = st.columns(2)
        for col, n, t, d in [
            (c1, "1", "Upload Documents", "Use the sidebar to upload PDF, TXT, DOCX, or CSV files."),
            (c2, "2", "Process and Chat",  "Click Process Documents, then type your question below."),
        ]:
            col.markdown(f'<div class="step-card"><div class="step-num">{n}</div><div class="step-title">{t}</div><div class="step-desc">{d}</div></div>', unsafe_allow_html=True)
        return

    # Process any pending query BEFORE rendering chat
    if "pending_query" in st.session_state and st.session_state.pending_query:
        q = st.session_state.pending_query
        st.session_state.pending_query = ""
        st.session_state.chat_history.append({"role": "user", "content": q})
        with st.spinner("Generating response..."):
            try:
                result = st.session_state.qa_chain.invoke({
                    "input": q,
                    "chat_history": st.session_state.lc_history,
                })
                answer = result.get("answer", "No answer found.")
                sources = result.get("context", [])
            except Exception as e:
                answer = f"Error: {str(e)}"; sources = []

        # Update LangChain message history
        st.session_state.lc_history.append(HumanMessage(content=q))
        st.session_state.lc_history.append(AIMessage(content=answer))

        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        if sources:
            seen, unique = set(), []
            for d in sources:
                k = (d.metadata.get("source_name", "Unknown"), d.page_content[:180])
                if k not in seen: seen.add(k); unique.append(k)
            st.session_state["last_sources"] = unique
        st.rerun()

    if st.session_state.chat_history:
        render_chat()
        if "last_sources" in st.session_state and st.session_state.last_sources:
            with st.expander(f"Source references ({len(st.session_state.last_sources)})", expanded=False):
                for name, snip in st.session_state.last_sources:
                    st.markdown(f'<div class="src-box"><div class="src-name">{name}</div>{snip}...</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="chat-win"><div class="empty-st"><div class="empty-title">Ready to answer questions</div><div class="empty-sub">Your documents have been indexed. Type a question below.</div></div></div>', unsafe_allow_html=True)

    if "input_key_counter" not in st.session_state:
        st.session_state.input_key_counter = 0

    col_in, col_btn = st.columns([5, 1])
    with col_in:
        user_input = st.text_input("q", placeholder="Ask a question about your documents...", label_visibility="collapsed", key=f"user_input_{st.session_state.input_key_counter}")
    with col_btn:
        send = st.button("Send", use_container_width=True, key="send_btn")

    if send and user_input.strip():
        st.session_state.pending_query = user_input.strip()
        st.session_state.input_key_counter += 1
        st.rerun()

# ── Router ────────────────────────────────────────────────────────────────────
page_chat()
