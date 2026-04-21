def retrieve_context(retriever, query):
    docs = retriever.get_relevant_documents(query)

    if not isinstance(docs, list):
        docs = [docs]

    return docs


def format_answer(llm_response, route=None):

    cleaned = llm_response.strip()

    return {
        "answer": cleaned,
        "route": route,
        "confidence": "high" if route in ["punishment_query", "section_lookup"] else "medium"
    }