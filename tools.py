def retrieve_context(retriever, query):
    return retriever.get_relevant_documents(query)


def format_answer(llm_response):
    return llm_response