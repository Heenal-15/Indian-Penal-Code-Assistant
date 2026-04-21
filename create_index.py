from dotenv import load_dotenv
import os

from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

# ----------------------------
# SETUP
# ----------------------------
load_dotenv()
pinecone_api_key = os.getenv("PINECONE_API_KEY")

index_name = "indian-penal-code-and-laws"

pc = Pinecone(api_key=pinecone_api_key)

# ----------------------------
# CHECK IF ALREADY INDEXED
# ----------------------------
index = pc.Index(index_name)
stats = index.describe_index_stats()

if stats["total_vector_count"] > 0:
    print("Index already exists. Skipping embedding creation.")
    exit()

# ----------------------------
# LOAD DATA
# ----------------------------
loader = PyPDFLoader("./data/Indian_Penal_Code_Book.pdf")
documents = loader.load()

chunks = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
).split_documents(documents)

# ----------------------------
# EMBEDDINGS MODEL
# ----------------------------
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

# ----------------------------
# UPLOAD TO PINECONE
# ----------------------------
PineconeVectorStore.from_documents(
    documents=chunks,
    embedding=embeddings,
    index_name=index_name
)

print("Embedding + indexing complete")