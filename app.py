import streamlit as st
import io
import re
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
- **CRITICAL**: Always cite the exact source filename for every piece of information provided. Use the format [Source: filename.ext].
- DO NOT answer from general knowledge. If the answer is not in the provided documents, state: "This information is not present in the provided records."
- Maintain a professional, regulatory-focused, and precise tone at all times."""

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; font-size: 13px; }

.stApp { background-color: #f0f4f8; color: #1e293b; }

#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    max-width: 100% !important;
}

/* ════ SIDEBAR ════ */
section[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #dde3ec !important;
    min-width: 290px !important;
    max-width: 290px !important;
}
section[data-testid="stSidebar"] > div {
    padding: 0 !important;
}

.sidebar-brand {
    padding: 22px 22px 16px 22px;
    border-bottom: 1px solid #eef1f6;
}
.sidebar-brand h1 {
    font-size: 0.9rem !important;
    font-weight: 800 !important;
    color: #0f172a !important;
    margin: 0 !important;
    letter-spacing: -0.02em;
}

.sidebar-section-label {
    font-size: 0.67rem;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    padding: 16px 18px 8px 18px;
    display: block;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #ffffff !important;
    border: 1.5px dashed #b8cce8 !important;
    border-radius: 14px !important;
    padding: 20px 14px !important;
    margin: 0 14px !important;
}
[data-testid="stFileUploader"] label { display: none !important; }
[data-testid="stFileUploader"] button {
    background-color: #1e4fa3 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    width: auto !important;
    height: auto !important;
    min-height: unset !important;
    padding: 7px 18px !important;
}
[data-testid="stFileUploader"] button:hover {
    background-color: #1a3f85 !important;
}

/* ── Queued file cards ── */
.file-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 9px;
    padding: 6px 10px;
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0 14px 5px 14px;
}
.file-name-text {
    font-size: 0.79rem;
    font-weight: 500;
    color: #0f172a;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.file-meta-text { font-size: 0.69rem; color: #94a3b8; }
.indexed-badge { color: #10b981 !important; font-weight: 600; }

/* ── Sidebar buttons ── */
.stButton > button {
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 0.75rem !important;
    transition: all 0.18s !important;
    height: 38px !important;
    width: 100% !important;
}

/* Process Documents */
[data-testid="stSidebar"] [data-testid="stButton"]:nth-of-type(1) > button {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 2px 8px rgba(37,99,235,0.28) !important;
}
[data-testid="stSidebar"] [data-testid="stButton"]:nth-of-type(1) > button:hover {
    box-shadow: 0 4px 14px rgba(37,99,235,0.38) !important;
}
[data-testid="stSidebar"] [data-testid="stButton"]:nth-of-type(1) > button:disabled {
    background: #e2e8f0 !important;
    color: #94a3b8 !important;
    box-shadow: none !important;
}

/* Clear Session */
[data-testid="stSidebar"] [data-testid="stButton"]:nth-of-type(2) > button {
    background: #ffffff !important;
    color: #374151 !important;
    border: 1.5px solid #d1d5db !important;
}
[data-testid="stSidebar"] [data-testid="stButton"]:nth-of-type(2) > button:hover {
    background: #f9fafb !important;
    border-color: #9ca3af !important;
}

/* ── Status pill ── */
.status-pill {
    display: block;
    text-align: center;
    padding: 7px 0;
    border-radius: 9999px;
    font-size: 0.69rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    border: 1.5px solid;
    margin: 0 14px;
}
.status-awaiting { border-color: #cbd5e1; color: #94a3b8; background: #f8fafc; }
.status-processing { border-color: #3b82f6; color: #2563eb; background: #eff6ff; }
.status-ready { border-color: #34d399; color: #059669; background: #ecfdf5; }

/* ════ MAIN HEADER ════ */
.main-header {
    background: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding: 12px 40px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: fixed;
    top: 0;
    left: 290px;
    right: 0;
    z-index: 1000;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.main-chat-container {
    padding-top: 70px;
}
.main-header h2 {
    font-size: 1.25rem;
    font-weight: 800;
    color: #0f172a;
    margin: 0;
    letter-spacing: -0.02em;
}
.main-header p { font-size: 0.8rem; color: #64748b; margin: 3px 0 0 0; }
.badge-row { display: flex; gap: 8px; }
.badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 12px;
    border-radius: 9999px;
    font-size: 0.69rem;
    font-weight: 600;
    border: 1.5px solid;
    background: white;
}
.badge-dev { border-color: #fbbf2460; color: #d97706; background: #fffbeb; }
.badge-gmp { border-color: #34d39960; color: #059669; background: #ecfdf5; }

/* ════ WELCOME CARDS ════ */
.step-cards-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 400px;
    padding: 20px;
}
.step-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 22px;
    max-width: 860px;
    width: 100%;
}
.step-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 36px 24px 30px;
    text-align: center;
    box-shadow: 0 2px 12px rgba(0,0,0,0.05);
    transition: box-shadow 0.2s, transform 0.2s;
}
.step-card:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.1); transform: translateY(-2px); }
.step-num {
    width: 46px; height: 46px; border-radius: 50%;
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: #ffffff; font-weight: 700; font-size: 1rem;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 18px auto;
    box-shadow: 0 4px 12px rgba(37,99,235,0.3);
}
.step-card h3 { color: #0f172a; font-size: 1rem; font-weight: 700; margin: 0 0 10px 0; }
.step-card p  { color: #64748b; font-size: 0.81rem; margin: 0; line-height: 1.6; }

/* ════ CHAT MESSAGES ════ */
.main-chat-content { padding-bottom: 110px; }
.chat-wrap { max-width: 820px; margin: 0 auto; padding: 32px 24px; }
.msg-row { display: flex; gap: 14px; margin-bottom: 20px; align-items: flex-start; }
.msg-row.user { flex-direction: row-reverse; }
.avatar {
    width: 34px; height: 34px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.85rem; flex-shrink: 0;
}
.avatar.bot  { background: #eff6ff; border: 1.5px solid #bfdbfe; }
.avatar.user { background: #f1f5f9; border: 1.5px solid #e2e8f0; }
.bubble {
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 0.8rem;
    line-height: 1.55;
    max-width: 85%;
}
.bubble.bot {
    background: #ffffff;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    border-top-left-radius: 4px;
}
.bubble.user {
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: #ffffff;
    border-top-right-radius: 4px;
    box-shadow: 0 2px 8px rgba(37,99,235,0.25);
}
.bubble.bot p { margin: 6px 0; }
.bubble.bot h2,.bubble.bot h3,.bubble.bot h4 { color:#0f172a; margin:12px 0 6px; font-weight:700; }
.bubble.bot code { background:#f1f5f9; color:#2563eb; padding:2px 6px; border-radius:4px; font-size:0.82rem; }
.bubble.bot blockquote { border-left:3px solid #bfdbfe; color:#64748b; padding-left:12px; margin:8px 0; font-style:italic; }
.bubble.bot ul,.bubble.bot ol { padding-left:20px; margin:6px 0; }
.bubble.bot li { margin-bottom:3px; }
.bubble.bot hr { border:none; border-top:1px solid #e2e8f0; margin:10px 0; }
.bubble.bot strong { color:#0f172a; }

/* ════ INPUT BAR ════ */
.input-bar-wrap {
    position: fixed;
    bottom: 0;
    left: 290px;
    right: 0;
    background: #ffffff;
    border-top: 1px solid #e2e8f0;
    padding: 14px 40px 16px 40px;
    z-index: 200;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.04);
}
.input-inner { max-width: 820px; margin: 0 auto; }

.stTextInput input {
    background: #f8fafc !important;
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    font-size: 0.85rem !important;
    color: #1e293b !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
.stTextInput input:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
    background: #ffffff !important;
}
.stTextInput input::placeholder { color: #94a3b8 !important; }

/* Sidebar Footer */
.sidebar-footer {
    position: fixed;
    bottom: 0;
    width: 290px;
    background: #ffffff;
    border-top: 1px solid #eef1f6;
    padding: 10px 0;
    z-index: 100;
}

/* Send button — target last column */
div[data-testid="column"]:last-child .stButton > button {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    color: white !important;
    border: none !important;
    width: 46px !important;
    height: 46px !important;
    border-radius: 12px !important;
    font-size: 1rem !important;
    padding: 0 !important;
    box-shadow: 0 2px 8px rgba(37,99,235,0.3) !important;
}
div[data-testid="column"]:last-child .stButton > button:disabled {
    background: #e2e8f0 !important;
    color: #94a3b8 !important;
    box-shadow: none !important;
}

/* Sidebar files container */
.sidebar-files-container {
    max-height: calc(100vh - 380px);
    overflow-y: auto;
    padding-bottom: 10px;
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #f8fafc; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "files": [],
        "status": "awaiting",
        "messages": [],
        "input_key": 0,   # incremented after each send to clear the input field
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ── Helpers ───────────────────────────────────────────────────────────────────
def format_size(n: int) -> str:
    if n < 1024:     return f"{n} B"
    if n < 1048576:  return f"{n/1024:.1f} KB"
    return f"{n/1048576:.1f} MB"

def detect_doc_type(name: str) -> str:
    lo = name.lower()
    if "bmr" in lo or "batch" in lo: return "BMR"
    if "capa" in lo:                  return "CAPA"
    if "sop" in lo:                   return "SOP"
    if "audit" in lo:                 return "Audit Report"
    if "deviation" in lo:             return "Deviation Report"
    return "Document"

def extract_text(name: str, content: bytes) -> str:
    ext = name.rsplit(".", 1)[-1].lower()
    try:
        if ext == "pdf":
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            parts = [p.extract_text() for p in reader.pages if p.extract_text()]
            return "\n\n".join(parts) or "[No text found in PDF]"
        if ext in ("txt", "csv"):
            try:    return content.decode("utf-8")
            except: return content.decode("latin-1")
        if ext == "docx":
            from docx import Document
            doc = Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        try:    return content.decode("utf-8")
        except: return f"[Could not extract text from {name}]"
    except Exception as e:
        return f"[Extraction error for {name}: {e}]"

def build_context(files: list) -> str:
    parts = []
    for f in files:
        doc_type = detect_doc_type(f["name"])
        text = f.get("extracted_text") or "[No text extracted]"
        truncated = text[:15000] + "\n...[truncated]" if len(text) > 15000 else text
        parts.append(f"### DOCUMENT: {f['name']} (Type: {doc_type}) ###\n{truncated}\n### END DOCUMENT: {f['name']} ###")
    return "\n\n".join(parts)

def call_groq(messages: list) -> str:
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=MODEL, messages=messages, temperature=0.3, max_tokens=1024,
    )
    return response.choices[0].message.content or "No response received."

def markdown_to_html(md: str) -> str:
    import html
    s = html.escape(md)
    s = re.sub(r'^### (.+)$', r'<h4>\1</h4>', s, flags=re.MULTILINE)
    s = re.sub(r'^## (.+)$',  r'<h3>\1</h3>', s, flags=re.MULTILINE)
    s = re.sub(r'^# (.+)$',   r'<h2>\1</h2>', s, flags=re.MULTILINE)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\*(.+?)\*',     r'<em>\1</em>', s)
    s = re.sub(r'_(.+?)_',       r'<em>\1</em>', s)
    s = re.sub(r'`([^`]+)`',     r'<code>\1</code>', s)
    s = re.sub(r'^&gt; (.+)$',   r'<blockquote>\1</blockquote>', s, flags=re.MULTILINE)

    # ── patterns extracted to avoid backslash-in-f-string error ──
    bullet_pat   = r'^[-*]\s+'
    numbered_pat = r'^\d+\.\s+'

    def list_block(match):
        items = match.group(0).splitlines()
        li = "".join(f"<li>{re.sub(bullet_pat, '', item)}</li>" for item in items)
        return f"<ul>{li}</ul>"
    s = re.sub(r'(^[-*] .+$\n?)+', list_block, s, flags=re.MULTILINE)

    def ol_block(match):
        items = match.group(0).splitlines()
        li = "".join(f"<li>{re.sub(numbered_pat, '', item)}</li>" for item in items)
        return f"<ol>{li}</ol>"
    s = re.sub(r'(^\d+\. .+$\n?)+', ol_block, s, flags=re.MULTILINE)

    s = re.sub(r'^---+$', r'<hr>', s, flags=re.MULTILINE)
    s = re.sub(r'\n{2,}', '</p><p>', s)
    s = re.sub(r'\n', '<br>', s)
    s = f"<p>{s}</p>"
    s = re.sub(r'<p>\s*</p>', '', s)
    return s

# ════════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="sidebar-brand"><h1>🛡️ PharmaDigi</h1></div>', unsafe_allow_html=True)
    st.markdown('<span class="sidebar-section-label">Upload Records</span>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        label="Upload pharmaceutical records",
        type=["pdf", "txt", "docx", "csv"],
        accept_multiple_files=True,
        key="uploader",
        help="BMR, SOP, CAPA, Audit Reports — PDF, TXT, DOCX, CSV · Max 200 MB",
        label_visibility="collapsed",
    )

    # Sync new uploads into session state
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
                if st.session_state.status == "ready":
                    st.session_state.status = "awaiting"

    # Queued file cards
    if st.session_state.files:
        st.markdown(
            f'<span class="sidebar-section-label">Queued ({len(st.session_state.files)})</span>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sidebar-files-container">', unsafe_allow_html=True)
        to_remove = []
        for i, f in enumerate(st.session_state.files):
            doc_type     = detect_doc_type(f["name"])
            indexed_html = '<span class="indexed-badge">✓ indexed</span>' if f["extracted_text"] else ""
            st.markdown(f"""
            <div class="file-card">
                <span style="font-size:1rem">📄</span>
                <div style="flex:1;min-width:0">
                    <div class="file-name-text">{f['name']}</div>
                    <div class="file-meta-text">{format_size(f['size'])} · {doc_type} {indexed_html}</div>
                </div>
            </div>""", unsafe_allow_html=True)
            if st.button("✕", key=f"del_{i}", help=f"Remove {f['name']}"):
                to_remove.append(i)
        st.markdown('</div>', unsafe_allow_html=True)
        for idx in reversed(to_remove):
            st.session_state.files.pop(idx)
        if to_remove:
            st.rerun()

    # Spacer to push buttons down
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)

    # Buttons and Status in Fixed Footer
    st.markdown('<div class="sidebar-footer">', unsafe_allow_html=True)
    with st.container():
        st.markdown("<div style='padding: 0 14px 6px 14px;'>", unsafe_allow_html=True)
        can_process = len(st.session_state.files) > 0 and st.session_state.status == "awaiting"
        btn_label   = "⏳  Extracting & Indexing…" if st.session_state.status == "processing" else "⚙️  Process Documents"
        if st.button(btn_label, disabled=not can_process, use_container_width=True, key="process_btn"):
            st.session_state.status = "processing"
            st.rerun()

        if st.button("🗑️  Clear Session", use_container_width=True, key="clear_btn"):
            st.session_state.files     = []
            st.session_state.messages  = []
            st.session_state.status    = "awaiting"
            st.session_state.input_key += 1
            st.rerun()

        # Status pill
        s         = st.session_state.status
        badge_cls = {"awaiting":"status-awaiting","processing":"status-processing","ready":"status-ready"}[s]
        badge_lbl = {"awaiting":"AWAITING RECORDS","processing":"EXTRACTING…","ready":"✓ AI READY"}[s]
        st.markdown(
            f'<div style="padding: 8px 0 16px 0;">'
            f'<span class="status-pill {badge_cls}">{badge_lbl}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# PROCESSING TRIGGER
# ════════════════════════════════════════════════════════════════════════════════
if st.session_state.status == "processing":
    updated = []
    for f in st.session_state.files:
        if not f["extracted_text"]:
            text = extract_text(f["name"], f["content"])
            updated.append({**f, "extracted_text": text})
        else:
            updated.append(f)
    st.session_state.files = updated

    summary_lines = []
    for f in updated:
        doc_type = detect_doc_type(f["name"])
        preview  = (f["extracted_text"] or "")[:120].replace("\n", " ") + "…"
        summary_lines.append(
            f"- **{f['name']}** — Classified as: `{doc_type}` ({format_size(f['size'])})\n  _Preview: {preview}_"
        )

    intake_msg = (
        f"### 📋 Document Intake & Extraction Complete\n\n"
        f"I've extracted and indexed **{len(updated)}** document{'s' if len(updated)>1 else ''}:\n\n"
        + "\n".join(summary_lines)
        + "\n\n---\n\n"
        "**Ready for AI-powered compliance analysis.** You can now ask me:\n\n"
        '- _"Summarize the critical process parameters from the BMR."_\n'
        '- _"Were there any deviations flagged in the batch record?"_\n'
        '- _"What was the root cause and corrective action in the CAPA?"_\n'
        '- _"Walk me through SOP step 4.2."_'
    )
    st.session_state.messages = [{"role": "assistant", "content": intake_msg}]
    st.session_state.status   = "ready"
    st.rerun()

# ════════════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="main-chat-container">', unsafe_allow_html=True)
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

# ── Welcome screen or chat history ───────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
    <div class="step-cards-wrap">
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

# ════════════════════════════════════════════════════════════════════════════════
# CHAT INPUT  ← dynamic key resets field after every send
# ════════════════════════════════════════════════════════════════════════════════
is_ready    = st.session_state.status == "ready"
placeholder = (
    "Ask about deviations, CPPs, corrective actions…"
    if is_ready
    else "Upload and process pharmaceutical records first…"
)

st.markdown('<div class="input-bar-wrap"><div class="input-inner">', unsafe_allow_html=True)

with st.form(key=f"chat_form_{st.session_state.input_key}", clear_on_submit=False):
    col1, col2 = st.columns([12, 1])
    with col1:
        user_text = st.text_input(
            label="query",
            placeholder=placeholder,
            disabled=not is_ready,
            label_visibility="collapsed",
        )
    with col2:
        send = st.form_submit_button(
            "➤",
            disabled=not is_ready,
        )
st.markdown("</div></div>", unsafe_allow_html=True)

# ── Handle send ───────────────────────────────────────────────────────────────
if send and is_ready and (user_text or "").strip():
    query = user_text.strip()
    st.session_state.messages.append({"role": "user", "content": query})

    doc_context      = build_context(st.session_state.files)
    system_with_docs = (
        f"{SYSTEM_PROMPT}\n\n---\n\n"
        f"You have access to the following pharmaceutical documents:\n\n{doc_context}"
    )
    history = [{"role": "system", "content": system_with_docs}]
    for m in st.session_state.messages[-7:-1]:
        history.append({"role": m["role"], "content": m["content"]})
    history.append({"role": "user", "content": query})

    with st.spinner("🔍 Analyzing documents…"):
        try:
            reply = call_groq(history)
        except Exception as e:
            reply = f"⚠️ **Error communicating with AI:** {e}"

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.session_state.input_key += 1   # ← increment clears the text input on rerun
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True) # closing main-chat-container
