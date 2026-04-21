# Indian-Penal-Code-Assistant
⚖️ Indian Penal Code Assistant is an AI-powered application designed to assist users with legal queries related to the Indian Penal Code (IPC). The app provides quick answers, detailed explanations, and related references for various laws. It also allows users to update or delete their query history for efficient management.

# Features
  # Query Assistance 
  - Enter any legal query, and the AI will provide a detailed answer.
  - If the query exists in the database, the answer is retrieved instantly without reprocessing.
  - References are included to offer additional context.
    
  # Query History
  - Displays a list of recently asked questions in the sidebar.
  - Allows users to revisit previously answered queries.
    
  # Query Updation and Deletion
  - Update the question and retrieve a revised answer.
  - Delete unwanted or irrelevant queries from the history.
    
  # Embedding Generation
  - Generate embeddings for the underlying dataset for efficient query retrieval.


# Technologies Used
  # Backend
  - ```SQLite```: For storing query history, answers, and references.
  - ```Python```: Core programming language.
  - ```LangChain```: Used for chaining AI model queries and database operations.
  - ```Pinecone DB```: For efficient vector-based retrieval of embeddings.

  # Frontend
  - ```Streamlit```: For building a user-friendly, interactive interface.

  # AI Model 
  - ```LLaMA 3```: Powered by Ollama, providing advanced natural language processing capabilities.


# Usage
  # Query Assistance
  - Enter your legal question in the input box.
  - If the query exists in the database, the answer is retrieved from there.
  - If not, the AI processes the query, generates an answer, and stores it in the database for future reference.

  # Query Management
  - Update a Query: Select a query from the sidebar, modify it, and retrieve the revised answer.
  - Delete a Query: Remove unwanted queries directly from the sidebar.

  # References
  - Click "Show Related Information" to view detailed references related to your query.
  

# Acknowledgments
- Streamlit for the interactive UI framework.
- LangChain for efficient AI integrations.
- Ollama for the LLaMA 3 model.
