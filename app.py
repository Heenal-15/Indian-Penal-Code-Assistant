import os
import sys
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from pinecone import Pinecone, ServerlessSpec
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

parent_dir = os.path.abspath(os.path.join(os.path.dirname('langchain_token'), '..'))
sys.path.insert(0, parent_dir)
#from langchain_token import pinecone_api_key 
pinecone_api_key = os.getenv("PINECONE_API_KEY")
pinecone_api_key = 'pcsk_3jrKUv_TBc1wJ1ert9Lzyd5fBmnvxiT5MoFN61Lcgea7mGYnaUEcR3CmX9ReiJh6CgewZJ'
os.environ['PINECONE_API_KEY'] = pinecone_api_key

#setting embeddings_falg to False as embedddings are already taken and stored in the db

embeddings_flag = True



llm = Ollama(model='llama3.2:3b')
embeddings = HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')

index_name = 'indian-penal-code-and-laws'
pc = Pinecone(api_key=pinecone_api_key)

if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=384,
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )

prompt = ChatPromptTemplate.from_template(
    """
    You are an Indian law assistant and your work is to answer queries based on the context only. 
    If you don't know the answer or don't have the context, say "I don't know." and dont mention anything about context.
    Context: {context}
    Question: {input}
    Your Answer:
    """
)

def generate_embeddings():
    loader = PyPDFLoader('./data/Indian_Penal_Code_Book.pdf')
    if embeddings_flag:
        documents = loader.load()
        text_documents = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(documents)
        PineconeVectorStore.from_documents(text_documents, embedding=embeddings, index_name=index_name)
    return "Embeddings are ready!"

def get_assistance(input_text):
    document_chain = create_stuff_documents_chain(llm, prompt)
    retriever = PineconeVectorStore(embedding=embeddings, index_name=index_name).as_retriever()
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    response = retrieval_chain.invoke({"input": input_text})

    references = [doc.page_content for doc in response.get('context', [])]

    return response, references