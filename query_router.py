def classify_query(query: str) -> str:
    query = query.lower()

    if "section" in query:
        return "section_lookup"

    if "punishment" in query or "penalty" in query:
        return "punishment_query"

    if "bailable" in query or "cognizable" in query:
        return "legal_status"

    if "what is" in query:
        return "definition"

    return "general_rag"