import streamlit as st
from db_operations import * 
from app import *

st.set_page_config(page_title="Indian Penal Code Assistant", layout="wide", page_icon="⚖️")

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
    """, unsafe_allow_html=True
)

col1, col2 = st.columns([4, 1])  
with col1:
    st.markdown('<div class="title">⚖️ Indian Penal Code Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Your AI assistant for Indian legal queries</div>', unsafe_allow_html=True)

with col2:
    if st.button("Generate Embeddings"):
        with st.spinner("Generating embeddings..."):
            response = generate_embeddings()
            st.success(response)

with st.sidebar:
    st.markdown('<div class="sidebar-section"><b>Recently Asked Questions</b></div>', unsafe_allow_html=True)
    
    if 'history' not in st.session_state:
        history = list_history_from_db()
        if history['status'] == 'success':
            st.session_state.history = history.get('result', [])
        else:
            st.session_state.history = []

    for idx, entry in enumerate(st.session_state.history, start=1):
        question = entry['Question']
        answer = entry['Answer']
        question_id = entry['ID']
        references = entry['References']
        
        if st.button(f"{idx}. {question}", key=f"question_{question_id}"):
            st.session_state.selected_question = question
            st.session_state.selected_answer = answer
            st.session_state.selected_id = question_id

st.markdown("### Query Assistant")

if 'selected_question' in st.session_state:
    selected_question = st.session_state.selected_question
    selected_answer = st.session_state.selected_answer
    question_id = st.session_state.selected_id
    
    st.write(f"#### Selected Question: {selected_question}")
    st.write(f"**Answer:** {selected_answer}")

    updated_question = st.text_input("Update Question", value=selected_question)
    if updated_question != selected_question:
        with st.spinner("Retrieving updated answer..."):
            updated_answer, updated_references = get_assistance(updated_question)
        
        st.write(f"**Updated Answer:** {updated_answer}")
        
        if st.button("Save Updated Question and Answer"):
            update_history_in_db(question_id, updated_question, updated_answer, updated_references)

            st.session_state.selected_question = updated_question
            st.session_state.selected_answer = updated_answer

            st.session_state.history = list_history_from_db()['result']
            st.success("Question and answer updated successfully!")

    if st.button("Delete this Question"):
        delete_history_from_db(question_id)
        del st.session_state.selected_question
        del st.session_state.selected_answer

        st.session_state.history = list_history_from_db()['result']
        st.success("Question deleted successfully!")

st.markdown("### Ask a New Question")
input_text = st.text_input("Enter your query about Indian law:", placeholder="E.g., What is the punishment for theft under IPC?")
if input_text:
    with st.spinner("Retrieving information..."):
        db_response = list_history_from_db(condition= f"question='{input_text}'")
            
        if len(db_response.get('result', [])) == 0:
            response, references = get_assistance(input_text.strip())
            save_query_to_db(input_text, response.get('answer', 'No answer found'), references)
            
            st.markdown("#### Answer:")
            st.write(response.get('answer', "No response available."))
            st.session_state.references = references

        else:
            result = db_response.get('result', [])[0]
            response, references = result.get('Answer'), result.get('References')

            st.markdown("#### Answer:")
            st.write(response)
            st.session_state.references = references

        if 'references' in st.session_state and st.session_state.references:
            if st.button("Show Related Information"):
                st.markdown("#### Related Information:")
                for i, doc in enumerate(st.session_state.references):
                    st.markdown(f"**Reference {i+1}:**")
                    st.write(doc)
                    st.write("---")

st.markdown('<div class="footer">© 2025 Indian Penal Code Assistant </div>', unsafe_allow_html=True)
