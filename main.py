import streamlit as st
from difflib import SequenceMatcher

from db_operations import (
    list_history_from_db,
    delete_history_from_db,
    save_query_to_db,
)
from app import get_assistance

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(
    page_title="Indian Penal Code Assistant",
    layout="wide",
    page_icon="⚖️"
)

# ----------------------------
# STYLES
# ----------------------------
st.markdown(
    """
    <style>
    .title {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        font-weight: bold;
    }
    .subtitle {
        font-size: 1.25rem;
        color: #555;
        text-align: center;
        margin-top: -10px;
    }
    .footer {
        font-size: 0.9rem;
        color: #888;
        text-align: center;
        margin-top: 20px;
    }
    .sidebar-section {
        margin-bottom: 20px;
        border-bottom: 1px solid #ddd;
        padding-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------------------
# INIT SESSION STATE
# ----------------------------
if "history" not in st.session_state:
    res = list_history_from_db()
    st.session_state.history = res.get("result", []) if res.get("status") == "success" else []

if "selected_question" not in st.session_state:
    st.session_state.selected_question = None

if "references" not in st.session_state:
    st.session_state.references = []   # FIX: always list

# ----------------------------
# HEADER
# ----------------------------
col1, col2 = st.columns([4, 1])

with col1:
    st.markdown('<div class="title">⚖️ Indian Penal Code Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Your AI assistant for Indian legal queries</div>', unsafe_allow_html=True)

# ----------------------------
# SIDEBAR HISTORY
# ----------------------------
with st.sidebar:
    st.markdown('<div class="sidebar-section"><b>Recently Asked Questions</b></div>', unsafe_allow_html=True)

    for idx, entry in enumerate(st.session_state.history, start=1):
        qid = entry["ID"]
        question = entry["Question"]

        if st.button(f"{idx}. {question}", key=f"q_{qid}"):
            st.session_state.selected_question = entry

# ----------------------------
# SELECTED QUESTION VIEW
# ----------------------------
st.markdown("### Query Assistant")

if st.session_state.selected_question:
    entry = st.session_state.selected_question

    st.write(f"#### Selected Question: {entry['Question']}")
    st.write(f"**Answer:** {entry['Answer']}")

    if st.button("Delete This Question"):
        delete_history_from_db(entry["ID"])

        st.session_state.history = [
            h for h in st.session_state.history
            if h["ID"] != entry["ID"]
        ]

        st.session_state.selected_question = None
        st.success("Deleted successfully!")

# ----------------------------
# NEW QUESTION INPUT
# ----------------------------
st.markdown("### Ask a New Question")

user_input = st.text_input(
    "Enter your query about Indian law:",
    placeholder="E.g., What is the punishment for theft under IPC?"
)

if user_input:

    with st.spinner("Agent is thinking..."):

        db_response = list_history_from_db()
        history = db_response.get("result", []) if db_response.get("status") == "success" else []

        # fuzzy duplicate check
        existing = [
            r for r in history
            if SequenceMatcher(
                None,
                r["Question"].lower().strip(),
                user_input.lower().strip()
            ).ratio() > 0.85
        ]

        # ----------------------------
        # NEW QUERY
        # ----------------------------
        if not existing:

            response = get_assistance(user_input.strip())

            answer = response["answer"]
            route = response.get("route", "unknown")
            references = response.get("references", [])

            # FIX: ensure references is always list
            if isinstance(references, str):
                references = [references]

            st.session_state.references = references

            save_query_to_db(user_input, answer, references)

            st.markdown("#### Answer")
            st.write(answer)

            st.session_state.history = list_history_from_db().get("result", [])

        # ----------------------------
        # EXISTING QUERY
        # ----------------------------
        else:
            result = existing[0]

            st.markdown("#### Answer (from history)")
            st.write(result["Answer"])

            refs = result.get("References", [])

            # FIX: safety check
            if isinstance(refs, str):
                refs = [refs]

            st.session_state.references = refs

# ----------------------------
# REFERENCES
# ----------------------------
if st.session_state.references:

    # FIX: safety check again (double protection)
    refs = st.session_state.references
    if isinstance(refs, str):
        refs = [refs]

    if st.button("Show Related Information"):
        st.markdown("#### Related Information")

        for i, doc in enumerate(refs):
            st.markdown(f"**Reference {i+1}:**")
            st.write(doc)
            st.write("---")

# ----------------------------
# FOOTER
# ----------------------------
st.markdown(
    '<div class="footer">© 2026 Indian Penal Code Assistant</div>',
    unsafe_allow_html=True
)