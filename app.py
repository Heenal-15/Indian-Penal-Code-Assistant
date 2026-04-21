import os
from dotenv import load_dotenv

from langchain_community.llms.ollama import Ollama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

from pinecone import Pinecone

from query_router import classify_query

# ----------------------------
# ENV SETUP
# ----------------------------
load_dotenv()
pinecone_api_key = os.getenv("PINECONE_API_KEY")

if not pinecone_api_key:
    raise ValueError("PINECONE_API_KEY not found in environment variables")

# ----------------------------
# LLM + EMBEDDINGS
# ----------------------------
llm = Ollama(model="llama3.2:3b")

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

# ----------------------------
# PINECONE SETUP
# ----------------------------
index_name = "indian-penal-code-and-laws"

pc = Pinecone(api_key=pinecone_api_key)

vectorstore = PineconeVectorStore(
    embedding=embeddings,
    index_name=index_name
)

retriever = vectorstore.as_retriever()

# ----------------------------
# SYSTEM PROMPT
# ----------------------------
base_instruction = """
You are an expert Indian legal assistant.

Rules:
- Use ONLY the provided context
- Be precise and structured
- If answer is not in context, say "I don't know"
"""

# ----------------------------
# ROUTER
# ----------------------------
def route_query(query: str):
    router_prompt = f"""
Classify this legal query into ONE category only:

- section_lookup
- punishment_query
- legal_status
- definition
- general_rag

Query: {query}

Return only the category name.
"""

    try:
        return llm.invoke(router_prompt).strip().lower()
    except:
        return classify_query(query)

# ----------------------------
# MAIN FUNCTION (RAG PIPELINE)
# ----------------------------
def get_assistance(query: str):

    # Step 1: routing
    route = route_query(query)

    # Step 2: retrieval from Pinecone (FAST)
    docs = retriever.get_relevant_documents(query)
    context = "\n\n".join([d.page_content for d in docs])

    # Step 3: reasoning
    if route == "general_rag":

        prompt = f"""
{base_instruction}

Context:
{context}

Question:
{query}

Answer:
"""

    elif route in ["punishment_query", "legal_status", "section_lookup"]:

        prompt = f"""
{base_instruction}

You are a legal reasoning assistant.

Question Type: {route}

Context:
{context}

Question:
{query}

Return structured response:
- Section (if applicable)
- Explanation
- Legal Outcome
- Key Notes

Answer:
"""

    else:

        prompt = f"""
{base_instruction}

Context:
{context}

Explain clearly:
{query}

Answer:
"""

    response = llm.invoke(prompt)

    return {
        "answer": response,
        "route": route,
        "references": [doc.page_content for doc in docs]
    }