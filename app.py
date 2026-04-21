import os
from dotenv import load_dotenv

from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

from pinecone import Pinecone, ServerlessSpec
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from query_router import classify_query  # optional fallback router

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
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# ----------------------------
# PINECONE SETUP
# ----------------------------
index_name = "indian-penal-code-and-laws"

pc = Pinecone(api_key=pinecone_api_key)

if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=384,
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

vectorstore = PineconeVectorStore(
    embedding=embeddings,
    index_name=index_name
)

retriever = vectorstore.as_retriever()

# ----------------------------
# PROMPT DESIGN
# ----------------------------
base_instruction = """
You are an expert Indian legal assistant.

Rules:
- Use ONLY the provided context
- Be precise and structured
- If answer is not in context, say "I don't know"
"""

legal_prompt = ChatPromptTemplate.from_template("""
{base_instruction}

Context:
{context}

Question:
{input}

Answer:
""")

# ----------------------------
# EMBEDDING GENERATION
# ----------------------------
def generate_embeddings():
    loader = PyPDFLoader("./data/Indian_Penal_Code_Book.pdf")
    documents = loader.load()

    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    ).split_documents(documents)

    PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=index_name
    )

    return "Embeddings created successfully!"

# ----------------------------
# AGENT ROUTER (LLM-BASED)
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
        route = llm.invoke(router_prompt).strip().lower()
        return route
    except:
        # fallback if LLM fails
        return classify_query(query)

# ----------------------------
# MAIN AGENT FUNCTION
# ----------------------------
def get_assistance(query: str):
    
    # Step 1: Decide route (agent brain)
    route = route_query(query)

    # Step 2: Retrieve context ONCE
    docs = retriever.get_relevant_documents(query)
    context = "\n".join([d.page_content for d in docs])

    # Step 3: Route-based reasoning
    if route == "general_rag":

        final_prompt = legal_prompt.format(
            base_instruction=base_instruction,
            context=context,
            input=query
        )

        response = llm.invoke(final_prompt)

    elif route in ["punishment_query", "legal_status", "section_lookup"]:

        structured_prompt = f"""
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
"""

        response = llm.invoke(structured_prompt)

    else:

        response = llm.invoke(
            f"{base_instruction}\n\nContext:\n{context}\n\nExplain clearly:\n{query}"
        )

    # Step 4: Return structured output
    return {
        "answer": response,
        "route": route,
        "references": [doc.page_content for doc in docs]
    }