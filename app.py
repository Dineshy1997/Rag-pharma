import streamlit as st
import io
import csv
import re
import time
from groq import Groq

# ── Page config must be first Streamlit call ──────────────────────────────────
st.set_page_config(
    page_title="PharmaDigi – Pharmaceutical Compliance AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ─────────────────────────────────────────────────────────────────
GROQ_API_KEY = "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"
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a Senior Pharmaceutical Compliance Agent with deep expertise in GMP, FDA 21 CFR Part 211, ICH guidelines, and pharmaceutical manufacturing regulations.

Your responsibilities:
- Analyze Batch Manufacturing Records (BMR), Standard Operating Procedures (SOP), CAPA reports, and Audit Reports.
- Extract and summarize Critical Process Parameters (CPPs), Critical Quality Attributes (CQAs), and deviation events.
- For CAPAs: clearly distinguish Root Cause Analysis vs. Corrective Actions vs. Preventive Actions.
- For SOPs: provide numbered step-by-step guidance when asked procedural questions.
- Flag any values outside "Acceptable Range" defined in the document with ⚠️ DEVIATION ALERT.
- Always cite which document and section your answer is derived from.
- Do not fabricate data. If the answer is not in the provided documents, state: "This information is not present in the provided records."
- Maintain a professional, regulatory-focused, and precise tone at all times."""

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* === Reset & base === */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* === App background === */
.stApp {
    background-color: #f8fafc;
    color: #1e293b;
}

/* === Hide default streamlit elements === */
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    max-width: 100% !important;
}

/* === Sidebar === */
section[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
    min-width: 280px !important;
    max-width: 300px !important;
}
section[data-testid="stSidebar"] > div { padding: 0 !important; }

/* === Sidebar header === */
.sidebar-logo {
    background: #ffffff;
    padding: 24px 20px 20px 20px;
    border-bottom: 1px solid #f1f5f9;
}
.sidebar-logo h1 {
    font-size: 1.3rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
    margin: 0 !important;
}

/* === Main header === */
.main-header {
    background: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding: 20px 40px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 100;
}
.main-header h2 {
    font-size: 1.35rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0;
}
.main-header p {
    font-size: 0.85rem;
    color: #64748b;
    margin: 2px 0 0 0;
}
.badge-row { display: flex; gap: 10px; }
.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 600;
    border: 1px solid;
    background: white;
}
.badge-dev { border-color: #3b82f640; color: #2563eb; }
.badge-gmp { border-color: #10b98140; color: #059669; }

/* === Step cards === */
.step-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
    max-width: 900px;
    margin: auto;
    padding: 100px 20px;
}
.step-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 32px 24px;
    text-align: center;
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
}
.step-num {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #2563eb;
    color: #ffffff;
    font-weight: 700;
    font-size: 0.95rem;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 16px auto;
}
.step-card h3 { color: #0f172a; font-size: 1rem; font-weight: 600; margin: 0 0 10px 0; }
.step-card p { color: #64748b; font-size: 0.82rem; margin: 0; line-height: 1.5; }

/* === Chat messages === */
.chat-wrap { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
.msg-row { display: flex; gap: 16px; margin-bottom: 24px; align-items: flex-start; }
.msg-row.user { flex-direction: row-reverse; }
.avatar {
    width: 36px; height: 36px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.9rem; flex-shrink: 0;
}
.avatar.bot { background: #eff6ff; color: #2563eb; }
.avatar.user { background: #f1f5f9; color: #64748b; }
.bubble {
    border-radius: 12px;
    padding: 14px 18px;
    font-size: 0.92rem;
    line-height: 1.6;
    max-width: 80%;
}
.bubble.bot { background: #ffffff; color: #1e293b; border: 1px solid #e2e8f0; box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05); }
.bubble.user { background: #2563eb; color: #ffffff; }

/* === File item area in sidebar === */
.sidebar-content { padding: 20px; }
.sidebar-label {
    font-size: 0.7rem;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
}

/* === File item card === */
.file-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
}
.file-card .file-icon { color: #2563eb; font-size: 1.1rem; }
.file-card .file-name { font-size: 0.82rem; font-weight: 500; color: #0f172a; }
.file-card .file-meta { font-size: 0.72rem; color: #94a3b8; }
.indexed { color: #10b981 !important; font-weight: 600; }

/* === Status badge === */
.status-badge-container {
    padding: 20px;
    border-top: 1px solid #f1f5f9;
    background: white;
}
.status-pill {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    border: 1px solid;
    text-align: center;
    width: 100%;
}
.status-awaiting { border-color: #e2e8f0; color: #64748b; background: white; }
.status-processing { border-color: #2563eb; color: #2563eb; background: white; }
.status-ready { border-color: #10b981; color: #059669; background: white; }

/* === Input area === */
.input-area {
    background: #ffffff;
    border-top: 1px solid #e2e8f0;
    padding: 24px 40px;
    display: flex;
    justify-content: center;
}
.input-container {
    max-width: 800px;
    width: 100%;
    display: flex;
    gap: 12px;
}

/* === Streamlit button overrides === */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s;
    height: 42px !important;
    width: 100% !important;
}

div[data-testid="stSidebar"] button[key="process_btn"] {
    background-color: #7dabdb !important;
    color: white !important;
    border: none !important;
}
div[data-testid="stSidebar"] button[key="clear_btn"] {
    background-color: white !important;
    color: #475569 !important;
    border: 1px solid #e2e8f0 !important;
}

/* Input / Send button */
.stTextInput input {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
    font-size: 0.9rem !important;
}
.stTextInput input:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 2px rgb(37 99 235 / 0.1) !important;
}

button[key="send_btn"] {
    background-color: #7dabdb !important;
    color: white !important;
    border: none !important;
    width: 42px !important;
    height: 42px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    border-radius: 10px !important;
}

/* === File uploader === */
[data-testid="stFileUploader"] {
    background: #ffffff !important;
    border: 1px dashed #7dabdb !important;
    border-radius: 12px !important;
    padding: 30px 20px !important;
}
[data-testid="stFileUploader"] label { display: none; }
.upload-placeholder {
    text-align: center;
    color: #64748b;
}
.upload-placeholder i { font-size: 2rem; color: #2563eb; margin-bottom: 12px; }

/* === Scrollbar === */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #f8fafc; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }

/* Chat content padding */
.main-chat-content { padding-bottom: 120px; }

/* Markdown Styling in Light Theme */
.bubble.bot p { margin: 8px 0; }
.bubble.bot h1, .bubble.bot h2, .bubble.bot h3, .bubble.bot h4 {
    color: #0f172a; margin: 16px 0 8px; font-weight: 700;
}
.bubble.bot code {
    background: #f1f5f9;
    color: #2563eb;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.85rem;
    font-family: 'JetBrains Mono', monospace;
}
.bubble.bot blockquote {
    border-left: 4px solid #e2e8f0;
    color: #64748b;
    padding-left: 16px;
    margin: 12px 0;
    font-style: italic;
}
.bubble.bot ul, .bubble.bot ol { padding-left: 20px; margin: 8px 0; }
.bubble.bot li { margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
def _init_state():
    if "files" not in st.session_state:
        st.session_state.files = []
    if "status" not in st.session_state:
        st.session_state.status = "awaiting"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""

_init_state()

# ── Helpers ───────────────────────────────────────────────────────────────────
def format_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    return f"{n/(1024*1024):.1f} MB"

def detect_doc_type(name: str) -> str:
    lo = name.lower()
    if "bmr" in lo or "batch" in lo:   return "BMR"
    if "capa" in lo:                    return "CAPA"
    if "sop" in lo:                     return "SOP"
    if "audit" in lo:                   return "Audit Report"
    if "deviation" in lo:               return "Deviation Report"
    return "Document"

def extract_text(name: str, content: bytes) -> str:
    ext = name.rsplit(".", 1)[-1].lower()
    try:
        if ext == "pdf":
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            parts = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
            return "\n\n".join(parts) or "[No text found in PDF]"

        if ext in ("txt", "csv"):
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content.decode("latin-1")

        if ext == "docx":
            from docx import Document
            doc = Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

        try:
            return content.decode("utf-8")
        except Exception:
            return f"[Could not extract text from {name}]"

    except Exception as e:
        return f"[Extraction error for {name}: {e}]"

def build_context(files: list) -> str:
    parts = []
    for f in files:
        doc_type = detect_doc_type(f["name"])
        text = f.get("extracted_text") or "[No text extracted]"
        truncated = text[:6000] + "\n...[truncated]" if len(text) > 6000 else text
        parts.append(f"=== {doc_type}: {f['name']} ===\n{truncated}")
    return "\n\n".join(parts)

def call_groq(messages: list) -> str:
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=1024,
    )
    return response.choices[0].message.content or "No response received."

def markdown_to_html(md: str) -> str:
    """Minimal markdown → HTML for chat bubbles (headings, bold, code, bullets, blockquote)."""
    import html
    s = html.escape(md)

    # ### Headings
    s = re.sub(r'^### (.+)$', r'<h4>\1</h4>', s, flags=re.MULTILINE)
    s = re.sub(r'^## (.+)$', r'<h3>\1</h3>', s, flags=re.MULTILINE)
    s = re.sub(r'^# (.+)$', r'<h2>\1</h2>', s, flags=re.MULTILINE)

    # Bold & italic
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
    s = re.sub(r'_(.+?)_', r'<em>\1</em>', s)

    # Inline code
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)

    # Blockquote
    s = re.sub(r'^&gt; (.+)$', r'<blockquote>\1</blockquote>', s, flags=re.MULTILINE)

    # ── FIX: extract regex patterns into variables to avoid backslash in f-string ──

    # Bullet lists (lines starting with - or *)
    bullet_prefix = r'^[-*]\s+'
    def list_block(match):
        items = match.group(0).splitlines()
        li = "".join(f"<li>{re.sub(bullet_prefix, '', item)}</li>" for item in items)
        return f"<ul>{li}</ul>"
    s = re.sub(r'(^[-*] .+$\n?)+', list_block, s, flags=re.MULTILINE)

    # Numbered lists
    numbered_prefix = r'^\d+\.\s+'
    def ol_block(match):
        items = match.group(0).splitlines()
        li = "".join(f"<li>{re.sub(numbered_prefix, '', item)}</li>" for item in items)
        return f"<ol>{li}</ol>"
    s = re.sub(r'(^\d+\. .+$\n?)+', ol_block, s, flags=re.MULTILINE)

    # Horizontal rule
    s = re.sub(r'^---+$', r'<hr>', s, flags=re.MULTILINE)

    # Paragraphs: double newlines
    s = re.sub(r'\n{2,}', '</p><p>', s)
    s = re.sub(r'\n', '<br>', s)
    s = f"<p>{s}</p>"

    # Clean up empty p tags
    s = re.sub(r'<p>\s*</p>', '', s)
    return s

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <span class="shield">🛡️</span>
        <h1>PharmaDigi</h1>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.7rem;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:0.08em;margin:0 0 10px 4px'>Upload Records</p>", unsafe_allow_html=True)

    uploaded = st.file_uploader(
        label="Drag & drop or browse",
        type=["pdf", "txt", "docx", "csv"],
        accept_multiple_files=True,
        key="uploader",
        help="BMR, SOP, CAPA, Audit Reports — PDF, TXT, DOCX, CSV (max 200 MB)",
    )

    # Sync uploaded files into session_state
    if uploaded:
        existing_names = {f["name"] for f in st.session_state.files}
        for uf in uploaded:
            if uf.name not in existing_names:
                st.session_state.files.append({
                    "name": uf.name,
                    "size": uf.size,
                    "content": uf.read(),
                    "extracted_text": None,
                })
                st.session_state.status = "awaiting"

    # File queue
    if st.session_state.files:
        st.markdown(f"<p style='font-size:0.7rem;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:0.08em;margin:12px 0 8px 4px'>Queued ({len(st.session_state.files)})</p>", unsafe_allow_html=True)
        to_remove = []
        for i, f in enumerate(st.session_state.files):
            doc_type = detect_doc_type(f["name"])
            indexed_html = '<span class="indexed">✓ indexed</span>' if f["extracted_text"] else ""
            st.markdown(f"""
            <div class="file-card">
                <span class="file-icon">📄</span>
                <div style="flex:1;min-width:0">
                    <div class="file-name" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{f['name']}</div>
                    <div class="file-meta">{format_size(f['size'])} · {doc_type} {indexed_html}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("✕", key=f"del_{i}", help=f"Remove {f['name']}"):
                to_remove.append(i)
        for idx in reversed(to_remove):
            st.session_state.files.pop(idx)
        if to_remove:
            st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Process button
    can_process = len(st.session_state.files) > 0 and st.session_state.status == "awaiting"
    if st.button(
        "⏳ Extracting & Indexing…" if st.session_state.status == "processing" else "⚙️ Process Documents",
        disabled=not can_process,
        use_container_width=True,
        key="process_btn",
    ):
        st.session_state.status = "processing"
        st.rerun()

    # Clear session
    if st.button("🗑️ Clear Session", use_container_width=True, key="clear_btn"):
        st.session_state.files = []
        st.session_state.messages = []
        st.session_state.status = "awaiting"
        st.session_state.user_input = ""
        st.rerun()

    # Status badge
    s = st.session_state.status
    badge_cls = {"awaiting": "status-awaiting", "processing": "status-processing", "ready": "status-ready"}[s]
    badge_label = {"awaiting": "AWAITING RECORDS", "processing": "EXTRACTING…", "ready": "✓ AI READY"}[s]
    st.markdown(f'<div class="status-badge"><span class="status-pill {badge_cls}">{badge_label}</span></div>', unsafe_allow_html=True)

# ── Processing trigger (runs after rerun) ────────────────────────────────────
if st.session_state.status == "processing":
    updated = []
    for f in st.session_state.files:
        if not f["extracted_text"]:
            text = extract_text(f["name"], f["content"])
            updated.append({**f, "extracted_text": text})
        else:
            updated.append(f)
    st.session_state.files = updated

    doc_summary_parts = []
    for f in updated:
        doc_type = detect_doc_type(f["name"])
        preview = (f["extracted_text"] or "")[:120].replace("\n", " ") + "…"
        doc_summary_parts.append(
            f"- **{f['name']}** — Classified as: `{doc_type}` ({format_size(f['size'])})\n  _Preview: {preview}_"
        )
    doc_summary = "\n".join(doc_summary_parts)

    intake_msg = (
        f"### 📋 Document Intake & Extraction Complete\n\n"
        f"I've extracted and indexed **{len(updated)}** document{'s' if len(updated) > 1 else ''}:\n\n"
        f"{doc_summary}\n\n---\n\n"
        f"**Ready for AI-powered compliance analysis.** You can now ask me:\n\n"
        f'- _"Summarize the critical process parameters from the BMR."_\n'
        f'- _"Were there any deviations flagged in the batch record?"_\n'
        f'- _"What was the root cause and corrective action in the CAPA?"_\n'
        f'- _"Walk me through SOP step 4.2."_'
    )
    st.session_state.messages = [{"role": "assistant", "content": intake_msg}]
    st.session_state.status = "ready"
    st.rerun()

# ── Main area ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <div>
        <h2>Pharmaceutical Compliance</h2>
        <p>Ask questions about BMRs, SOPs, CAPAs &amp; Audit Reports</p>
    </div>
    <div class="badge-row">
        <span class="badge badge-dev">⚠️ Deviation Alerts</span>
        <span class="badge badge-gmp">🛡️ GMP Compliant</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Chat area
if not st.session_state.messages:
    st.markdown("""
    <div class="step-cards">
        <div class="step-card">
            <div class="step-num">1</div>
            <h3>Upload Records</h3>
            <p>Drop BMR, SOP, CAPA, or Audit PDFs into the sidebar.</p>
        </div>
        <div class="step-card">
            <div class="step-num">2</div>
            <h3>AI Extraction</h3>
            <p>Groq AI extracts and indexes all text from your documents.</p>
        </div>
        <div class="step-card">
            <div class="step-num">3</div>
            <h3>Ask Questions</h3>
            <p>Query compliance data, deviations, corrective actions &amp; more.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown('<div class="main-chat-content">', unsafe_allow_html=True)
    chat_html = '<div class="chat-wrap">'
    for msg in st.session_state.messages:
        if msg["role"] == "assistant":
            content_html = markdown_to_html(msg["content"])
            chat_html += f"""
            <div class="msg-row">
                <div class="avatar bot">🤖</div>
                <div class="bubble bot">{content_html}</div>
            </div>"""
        else:
            import html as _html
            safe = _html.escape(msg["content"]).replace("\n", "<br>")
            chat_html += f"""
            <div class="msg-row user">
                <div class="avatar user">👤</div>
                <div class="bubble user">{safe}</div>
            </div>"""
    chat_html += "</div>"
    st.markdown(chat_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Chat input ────────────────────────────────────────────────────────────────
is_ready = st.session_state.status == "ready"
placeholder = (
    "Ask about deviations, CPPs, corrective actions…"
    if is_ready
    else "Upload and process pharmaceutical records first…"
)

with st.container():
    col1, col2 = st.columns([10, 1])
    with col1:
        user_text = st.text_input(
            label="Ask a question",
            placeholder=placeholder,
            disabled=not is_ready,
            label_visibility="collapsed",
            key="chat_input",
        )
    with col2:
        send = st.button("➤", disabled=not is_ready or not (user_text or "").strip(), key="send_btn")

if (send or (user_text and user_text != st.session_state.get("_last_input", ""))) and is_ready and user_text.strip():
    st.session_state["_last_input"] = user_text

    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_text.strip()})

    # Build Groq request
    doc_context = build_context(st.session_state.files)
    system_with_docs = f"{SYSTEM_PROMPT}\n\n---\n\nYou have access to the following pharmaceutical documents:\n\n{doc_context}"

    history = [{"role": "system", "content": system_with_docs}]
    # Last 6 messages as context
    for m in st.session_state.messages[-7:-1]:
        history.append({"role": m["role"], "content": m["content"]})
    history.append({"role": "user", "content": user_text.strip()})

    with st.spinner("🔍 Analyzing documents…"):
        try:
            reply = call_groq(history)
        except Exception as e:
            reply = f"⚠️ **Error communicating with AI:** {e}"

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
