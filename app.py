import os
from dotenv import load_dotenv

from langchain_community.llms import Ollama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

from langgraph.graph import StateGraph
from typing import TypedDict, Optional, List

from query_router import classify_query
from tools import retrieve_context, format_answer

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
- Avoid long explanations unless required
- If answer is not in context, say "I don't know"
"""

# ----------------------------
# STATE
# ----------------------------
class State(TypedDict):
    query: str
    route: Optional[str]
    context: Optional[str]
    docs: Optional[List[str]]
    answer: Optional[str]

# ----------------------------
# ROUTER NODE
# ----------------------------
def router_node(state: State):
    query = state["query"]

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
        route = llm.invoke(router_prompt).strip().lower()
    except:
        route = classify_query(query)

    return {"route": route}

# ----------------------------
# RETRIEVAL NODE (IMPROVED)
# ----------------------------
def compress_reference(text: str) -> str:
    """
    NEW: makes references clean and readable
    """
    lines = text.split(".")
    summary = ". ".join(lines[:2])  # first 1–2 sentences only
    return summary.strip()


def retrieval_node(state: State):
    query = state["query"]

    docs = retrieve_context(retriever, query)

    if isinstance(docs, str):
        docs = [docs]

    clean_docs = []

    for d in docs:
        text = d.page_content if hasattr(d, "page_content") else str(d)
        text = text.strip()

        if len(text) > 50:
            clean_docs.append(compress_reference(text))  # 🔥 IMPROVED HERE

    context = "\n\n".join(clean_docs)

    return {
        "context": context,
        "docs": clean_docs
    }

# ----------------------------
# REASONING NODE
# ----------------------------
def reasoning_node(state: State):
    query = state["query"]
    context = state.get("context", "")
    route = state.get("route", "general_rag")

    if route == "general_rag":

        prompt = f"""
{base_instruction}

Context:
{context}

Question:
{query}

Answer briefly and clearly:
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
- Explanation (concise)
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

    raw_answer = llm.invoke(prompt)

    formatted = format_answer(raw_answer, route)

    return {
        "answer": formatted,
        "route": route,
        "context": context,
        "docs": state.get("docs", [])
    }

# ----------------------------
# GRAPH
# ----------------------------
graph = StateGraph(State)

graph.add_node("router", router_node)
graph.add_node("retrieve", retrieval_node)
graph.add_node("reason", reasoning_node)

graph.set_entry_point("router")

graph.add_edge("router", "retrieve")
graph.add_edge("retrieve", "reason")

graph.set_finish_point("reason")

app = graph.compile()

# ----------------------------
# MAIN FUNCTION
# ----------------------------
def get_assistance(query: str):

    result = app.invoke({
        "query": query
    })

    refs = result.get("docs", [])

    if isinstance(refs, str):
        refs = [refs]

    return {
        "answer": result["answer"],
        "route": result.get("route"),
        "references": refs
    }