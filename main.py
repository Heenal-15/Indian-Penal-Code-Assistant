import streamlit as st
from db_operations import *
from app import get_assistance, generate_embeddings

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
# HEADER
# ----------------------------
col1, col2 = st.columns([4, 1])

with col1:
    st.markdown('<div class="title">⚖️ Indian Penal Code Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Your AI assistant for Indian legal queries</div>', unsafe_allow_html=True)

with col2:
    if st.button("Generate Embeddings"):
        with st.spinner("Generating embeddings..."):
            msg = generate_embeddings()
            st.success(msg)

# ----------------------------
# SESSION STATE INIT
# ----------------------------
if "history" not in st.session_state:
    history = list_history_from_db()
    st.session_state.history = history.get("result", []) if history["status"] == "success" else []

if "selected_question" not in st.session_state:
    st.session_state.selected_question = None

if "messages" not in st.session_state:
    st.session_state.messages = []

# ----------------------------
# SIDEBAR HISTORY
# ----------------------------
with st.sidebar:
    st.markdown('<div class="sidebar-section"><b>Recently Asked Questions</b></div>', unsafe_allow_html=True)

    for idx, entry in enumerate(st.session_state.history, start=1):
        question = entry["Question"]
        question_id = entry["ID"]

        if st.button(f"{idx}. {question}", key=f"q_{question_id}"):
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

        st.session_state.history = list_history_from_db().get("result", [])
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

        # ❗ FIXED: no SQL string condition
        db_response = list_history_from_db()
        existing = [
            r for r in db_response.get("result", [])
            if r["Question"].strip().lower() == user_input.strip().lower()
        ]

        # ----------------------------
        # IF NOT IN DB → CALL AGENT
        # ----------------------------
        if len(existing) == 0:

            response = get_assistance(user_input.strip())

            answer = response["answer"]
            route = response["route"]
            references = response["references"]

            save_query_to_db(user_input, answer, references)

            st.success(f"Agent Route: {route}")

            st.markdown("#### Answer:")
            st.write(answer)

            st.session_state.history = list_history_from_db().get("result", [])

        # ----------------------------
        # IF ALREADY EXISTS
        # ----------------------------
        else:
            result = existing[0]

            st.markdown("#### Answer (from history):")
            st.write(result["Answer"])

            references = result["References"]

# ----------------------------
# REFERENCES VIEW
# ----------------------------
if "references" in locals() and references:

    if st.button("Show Related Information"):
        st.markdown("#### Related Information:")

        for i, doc in enumerate(references):
            st.markdown(f"**Reference {i+1}:**")
            st.write(doc)
            st.write("---")

# ----------------------------
# FOOTER
# ----------------------------
st.markdown(
    '<div class="footer">© 2025 Indian Penal Code Assistant</div>',
    unsafe_allow_html=True
)