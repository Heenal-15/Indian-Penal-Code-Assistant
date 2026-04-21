"""
memory_agent.py
───────────────
Adds conversation memory, enhanced agent reasoning, confidence scoring,
and bookmarks on TOP of the existing app.py / db_operations.py code.
Does NOT modify or re-implement those modules.
"""

import json
import re
from datetime import datetime
from typing import Optional


# ── CONVERSATION MEMORY ──────────────────────────────────────────────────────

class ConversationMemory:
    """
    Lightweight in-session memory.
    Keeps a rolling window of (user, assistant) turns so the LLM has context.
    """

    def __init__(self, max_turns: int = 6):
        self.turns: list[dict] = []
        self.max_turns = max_turns

    def add(self, role: str, content: str):
        self.turns.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().strftime("%H:%M")
        })
        # Keep only the last N turns (2 entries per turn = user + assistant)
        if len(self.turns) > self.max_turns * 2:
            self.turns = self.turns[-(self.max_turns * 2):]

    def get_context_block(self) -> str:
        """Return a formatted string of past conversation for the LLM prompt."""
        if not self.turns:
            return ""
        lines = ["--- Conversation History ---"]
        for t in self.turns:
            speaker = "User" if t["role"] == "user" else "Assistant"
            lines.append(f"{speaker}: {t['content']}")
        lines.append("--- End History ---")
        return "\n".join(lines)

    def clear(self):
        self.turns = []

    def to_list(self) -> list[dict]:
        return list(self.turns)


# ── AGENT THINKING STEPS ─────────────────────────────────────────────────────

class AgentThinkingLog:
    """Collects reasoning steps so the UI can show 'Agent Thinking...' stages."""

    def __init__(self):
        self.steps: list[dict] = []

    def add(self, icon: str, message: str):
        self.steps.append({"icon": icon, "message": message})

    def clear(self):
        self.steps = []

    def get_steps(self) -> list[dict]:
        return list(self.steps)


# ── CONFIDENCE SCORING ────────────────────────────────────────────────────────

def estimate_confidence(answer: str, docs: list) -> int:
    """
    Heuristic confidence score (0–100) based on:
    - Number of supporting docs retrieved
    - Whether the answer contains 'I don't know' style phrases
    - Answer length (too short = low confidence)
    """
    low_confidence_phrases = [
        "i don't know", "i do not know", "not mentioned",
        "not found", "no information", "cannot answer",
        "unclear", "not available"
    ]
    answer_lower = answer.lower()

    # Start at 70
    score = 70

    # Penalise if answer signals uncertainty
    for phrase in low_confidence_phrases:
        if phrase in answer_lower:
            score -= 25
            break

    # Reward for supporting docs
    score += min(len(docs) * 5, 20)

    # Penalise very short answers
    if len(answer.strip()) < 80:
        score -= 15

    # Reward for structured output markers (sections, bullets)
    if any(marker in answer for marker in ["Section", "•", "-", "1.", "Explanation"]):
        score += 5

    return max(10, min(score, 98))


# ── MEMORY-AWARE ASSISTANT ────────────────────────────────────────────────────

def get_assistance_with_memory(
    query: str,
    memory: ConversationMemory,
    thinking_log: AgentThinkingLog,
    get_assistance_fn,          # pass app.get_assistance directly
    llm=None                    # optional: pass the llm for follow-up rewrite
):
    """
    Wraps the existing get_assistance() with:
    1. Memory-augmented prompt rewriting (resolve pronouns / follow-ups)
    2. Agent thinking log
    3. Confidence estimation
    4. Memory update
    """
    thinking_log.clear()

    # ── Step 1: Rewrite query with memory context ──
    thinking_log.add("🔍", "Analysing query intent…")

    resolved_query = query
    if memory.turns and llm is not None:
        history_block = memory.get_context_block()
        rewrite_prompt = f"""
You are a legal query resolver. Given the conversation history below and a follow-up question,
rewrite the follow-up question as a fully self-contained legal query (resolve pronouns, fill context).
Return ONLY the rewritten question — no explanation.

{history_block}

Follow-up: {query}

Rewritten standalone question:"""
        try:
            rewritten = llm.invoke(rewrite_prompt).strip()
            if rewritten and len(rewritten) > 5:
                resolved_query = rewritten
                thinking_log.add("✏️", f"Query resolved: {resolved_query[:80]}…")
        except Exception:
            pass  # fallback to original

    # ── Step 2: Route classification ──
    thinking_log.add("🗂️", "Classifying query type…")

    # ── Step 3: Retrieve context ──
    thinking_log.add("📚", "Retrieving relevant legal sections…")

    # ── Step 4: Call the original agent ──
    thinking_log.add("⚖️", "Reasoning through legal context…")
    result = get_assistance_fn(resolved_query)

    # ── Step 5: Confidence ──
    thinking_log.add("📊", "Estimating answer confidence…")
    confidence = estimate_confidence(result["answer"], result.get("references", []))
    result["confidence"] = confidence
    result["resolved_query"] = resolved_query

    # ── Step 6: Update memory ──
    memory.add("user", query)
    memory.add("assistant", result["answer"][:600])  # truncate to save tokens

    thinking_log.add("✅", "Response ready.")
    return result


# ── BOOKMARKS ────────────────────────────────────────────────────────────────

class BookmarkManager:
    """Session-scoped bookmark store (survives re-renders, not across sessions)."""

    def __init__(self):
        self.bookmarks: list[dict] = []

    def add(self, entry: dict):
        ids = {b.get("ID") for b in self.bookmarks}
        if entry.get("ID") not in ids:
            self.bookmarks.append(entry)

    def remove(self, record_id: int):
        self.bookmarks = [b for b in self.bookmarks if b.get("ID") != record_id]

    def is_bookmarked(self, record_id: int) -> bool:
        return any(b.get("ID") == record_id for b in self.bookmarks)

    def get_all(self) -> list[dict]:
        return list(self.bookmarks)


# ── SESSION SUMMARY ────────────────────────────────────────────────────────────

def generate_session_summary(memory: ConversationMemory, llm=None) -> str:
    """Generate a short bullet-point summary of the session so far."""
    if not memory.turns or llm is None:
        return "No session activity yet."

    history_block = memory.get_context_block()
    prompt = f"""
Based on the conversation below, write a concise bullet-point summary (max 5 bullets)
of the key legal topics discussed. Be brief.

{history_block}

Summary:"""
    try:
        return llm.invoke(prompt).strip()
    except Exception:
        return "Session summary unavailable."


# ── ROUTE METADATA ────────────────────────────────────────────────────────────

ROUTE_META = {
    "section_lookup": {
        "label": "Section Lookup",
        "icon": "📜",
        "color": "#1A3360",
        "description": "Identifies specific IPC sections"
    },
    "punishment_query": {
        "label": "Punishment Query",
        "icon": "⚖️",
        "color": "#B71C1C",
        "description": "Details penalties and sentencing"
    },
    "legal_status": {
        "label": "Legal Status",
        "icon": "🔎",
        "color": "#1B5E20",
        "description": "Bailable / cognizable classification"
    },
    "definition": {
        "label": "Definition",
        "icon": "📖",
        "color": "#4A148C",
        "description": "Legal term definitions"
    },
    "general_rag": {
        "label": "General Query",
        "icon": "💬",
        "color": "#E8541A",
        "description": "General RAG retrieval"
    },
}

def get_route_meta(route: str) -> dict:
    return ROUTE_META.get(route, {
        "label": route.replace("_", " ").title(),
        "icon": "🔹",
        "color": "#0F2044",
        "description": ""
    })