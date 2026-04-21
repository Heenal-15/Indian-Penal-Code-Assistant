"""
enhanced_main.py
─────────────────
Drop-in upgrade for main.py.
Imports existing modules unchanged; adds memory, confidence, bookmarks, theme.
Run with:  streamlit run enhanced_main.py
"""

import streamlit as st
from pathlib import Path

# ── Existing modules (unchanged) ──────────────────────────────────────────────
from db_operations import (
    list_history_from_db,
    save_query_to_db,
    delete_history_from_db,
)
from app import get_assistance, generate_embeddings

# ── New memory + agent enhancements ───────────────────────────────────────────
from memory_agent import (
    ConversationMemory,
    AgentThinkingLog,
    BookmarkManager,
    get_assistance_with_memory,
    generate_session_summary,
    get_route_meta,
)

# ── Try to grab the LLM for memory-aware rewrites (optional) ─────────────────
try:
    from app import llm as _llm
except ImportError:
    _llm = None

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IPC Legal Assistant",
    layout="wide",
    page_icon="⚖️",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# INJECT CSS
# ─────────────────────────────────────────────────────────────────────────────
css_path = Path(__file__).parent / "styles.css"
if css_path.exists():
    css_text = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "history":           [],
        "selected_question": None,
        "memory":            ConversationMemory(max_turns=6),
        "thinking_log":      AgentThinkingLog(),
        "bookmarks":         BookmarkManager(),
        "chat_messages":     [],  # [{role, content, meta}]
        "dark_mode":         False,
        "last_result":       None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

_init_state()

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _load_history():
    resp = list_history_from_db()
    return resp.get("result", []) if resp["status"] == "success" else []

def _html(content: str):
    st.markdown(content, unsafe_allow_html=True)

def _confidence_html(score: int) -> str:
    color = "#2E7D32" if score >= 70 else "#E65100" if score >= 40 else "#B71C1C"
    return f"""
<div style="margin:8px 0">
  <div style="display:flex;justify-content:space-between;font-size:0.78rem;color:#7A7A7A;margin-bottom:4px">
    <span>Answer Confidence</span>
    <span style="font-weight:600;color:{color}">{score}%</span>
  </div>
  <div class="confidence-bar">
    <div class="confidence-fill" style="width:{score}%;background:linear-gradient(90deg,{color},{color}99)"></div>
  </div>
</div>"""

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    _html('<div class="sidebar-title">⚖️ IPC Assistant</div>')

    # ── Theme toggle ──
    dark = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)
    if dark != st.session_state.dark_mode:
        st.session_state.dark_mode = dark
        st.rerun()

    st.divider()

    # ── Stats ──
    st.session_state.history = _load_history()
    total = len(st.session_state.history)
    session_turns = len(st.session_state.memory.turns) // 2

    col_a, col_b = st.columns(2)
    with col_a:
        _html(f'<div style="text-align:center"><div style="font-size:1.6rem;font-weight:700;color:#E2C97E">{total}</div><div style="font-size:0.7rem;color:rgba(255,255,255,0.5);letter-spacing:0.08em">TOTAL</div></div>')
    with col_b:
        _html(f'<div style="text-align:center"><div style="font-size:1.6rem;font-weight:700;color:#E2C97E">{session_turns}</div><div style="font-size:0.7rem;color:rgba(255,255,255,0.5);letter-spacing:0.08em">SESSION</div></div>')

    st.divider()

    # ── History ──
    _html('<div style="font-size:0.72rem;letter-spacing:0.1em;color:rgba(255,255,255,0.4);margin-bottom:8px">RECENT QUERIES</div>')

    for idx, entry in enumerate(reversed(st.session_state.history[-15:]), 1):
        label = f"{idx}. {entry['Question'][:40]}{'…' if len(entry['Question']) > 40 else ''}"
        if st.button(label, key=f"hist_{entry['ID']}"):
            st.session_state.selected_question = entry
            st.rerun()

    st.divider()

    # ── Bookmarks ──
    bookmarks = st.session_state.bookmarks.get_all()
    if bookmarks:
        _html('<div style="font-size:0.72rem;letter-spacing:0.1em;color:rgba(255,255,255,0.4);margin-bottom:8px">⭐ BOOKMARKS</div>')
        for b in bookmarks:
            label = b["Question"][:38] + ("…" if len(b["Question"]) > 38 else "")
            if st.button(f"★ {label}", key=f"bm_{b['ID']}"):
                st.session_state.selected_question = b
                st.rerun()

    st.divider()

    # ── Controls ──
    if st.button("🗑️ Clear Memory"):
        st.session_state.memory.clear()
        st.session_state.chat_messages = []
        st.success("Memory cleared")

    if st.button("📊 Session Summary"):
        summary = generate_session_summary(st.session_state.memory, _llm)
        st.info(summary)

    if st.button("⚙️ Generate Embeddings"):
        with st.spinner("Building vector index…"):
            msg = generate_embeddings()
            st.success(msg)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────────────────────────────────────

# Dark mode body class injection
if st.session_state.dark_mode:
    _html('<script>document.body.setAttribute("data-theme","dark")</script>')

# ── Header ───────────────────────────────────────────────────────────────────
_html("""
<div class="ipc-header">
  <div class="ipc-title">Indian Penal Code Assistant</div>
  <div class="ipc-subtitle">AI-powered legal research · Powered by Retrieval-Augmented Generation</div>
</div>
""")

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_chat, tab_history, tab_bookmarks = st.tabs(["💬 Ask a Question", "📋 Query History", "⭐ Bookmarks"])

# ╔══════════════════════════════════════════════════════╗
# ║  TAB 1 — CHAT / ASK                                 ║
# ╚══════════════════════════════════════════════════════╝
with tab_chat:

    # Show selected question context (from sidebar click)
    if st.session_state.selected_question:
        entry = st.session_state.selected_question
        _html('<div class="section-header">📌 <span>Selected Query</span></div>')

        _html(f"""
        <div class="answer-card">
          <div class="answer-label">Question</div>
          <div class="answer-text" style="font-weight:600">{entry['Question']}</div>
        </div>
        """)

        _html(f"""
        <div class="answer-card">
          <div class="answer-label">Stored Answer</div>
          <div class="answer-text">{entry['Answer']}</div>
        </div>
        """)

        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("🗑️ Delete", key="del_selected"):
                delete_history_from_db(entry["ID"])
                st.session_state.history = _load_history()
                st.session_state.selected_question = None
                st.success("Deleted.")
                st.rerun()
        with col2:
            bookmarked = st.session_state.bookmarks.is_bookmarked(entry["ID"])
            label = "★ Saved" if bookmarked else "☆ Bookmark"
            if st.button(label, key="bm_selected"):
                if bookmarked:
                    st.session_state.bookmarks.remove(entry["ID"])
                else:
                    st.session_state.bookmarks.add(entry)
                st.rerun()
        with col3:
            if st.button("✕ Dismiss", key="dismiss_selected"):
                st.session_state.selected_question = None
                st.rerun()

        _html('<div class="ornamental-divider">✦ ✦ ✦</div>')

    # ── Conversation Memory Display ───────────────────────────────────────────
    if st.session_state.chat_messages:
        _html('<div class="section-header">🗂️ <span>Conversation</span></div>')
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                _html(f"""
                <div class="chat-bubble-user">
                  {msg['content']}
                  <div class="chat-meta">You · {msg.get('time','')}</div>
                </div>""")
            else:
                meta = msg.get("meta", {})
                route_info = get_route_meta(meta.get("route", ""))
                conf = meta.get("confidence", 0)
                _html(f"""
                <div class="chat-bubble-assistant">
                  {msg['content']}
                  <div class="chat-meta" style="display:flex;gap:12px;margin-top:8px">
                    <span>{route_info.get('icon','')} {route_info.get('label','')}</span>
                    <span>Confidence: {conf}%</span>
                    <span>Assistant · {msg.get('time','')}</span>
                  </div>
                </div>""")

    # ── Input ─────────────────────────────────────────────────────────────────
    _html('<div class="section-header">⚖️ <span>Ask a Question</span></div>')

    user_input = st.text_input(
        "",
        placeholder="E.g., What is the punishment for theft under IPC Section 379?",
        label_visibility="collapsed"
    )

    col_ask, col_clear = st.columns([3, 1])
    with col_ask:
        ask_clicked = st.button("⚖️ Get Legal Advice", key="ask_btn", use_container_width=True)
    with col_clear:
        if st.button("🧹 New Topic", key="clear_btn", use_container_width=True):
            st.session_state.memory.clear()
            st.session_state.chat_messages = []
            st.session_state.last_result = None
            st.rerun()

    if ask_clicked and user_input.strip():
        now = __import__("datetime").datetime.now().strftime("%H:%M")

        # ── Check DB cache ────────────────────────────────────────────────────
        all_records = _load_history()
        cached = [
            r for r in all_records
            if r["Question"].strip().lower() == user_input.strip().lower()
        ]

        if cached:
            cached_result = cached[0]
            st.session_state.chat_messages.append({
                "role": "user", "content": user_input, "time": now
            })
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": cached_result["Answer"] + "\n\n*_(Answer retrieved from history)_*",
                "time": now,
                "meta": {"route": "general_rag", "confidence": 85}
            })
            st.session_state.memory.add("user", user_input)
            st.session_state.memory.add("assistant", cached_result["Answer"][:400])
            st.session_state.last_result = {
                "answer": cached_result["Answer"],
                "route": "general_rag",
                "confidence": 85,
                "references": cached_result.get("References", []),
                "from_cache": True
            }
            st.rerun()

        else:
            # ── Agent call with thinking steps ───────────────────────────────
            thinking_placeholder = st.empty()

            with st.spinner(""):
                # Show thinking steps progressively
                thinking_log = st.session_state.thinking_log

                def _show_thinking(steps):
                    html_steps = "".join([
                        f'<div class="thinking-step"><span class="step-icon">{s["icon"]}</span>{s["message"]}</div>'
                        for s in steps
                    ])
                    thinking_placeholder.markdown(
                        f'<div style="margin:12px 0">{html_steps}</div>',
                        unsafe_allow_html=True
                    )

                result = get_assistance_with_memory(
                    query=user_input,
                    memory=st.session_state.memory,
                    thinking_log=thinking_log,
                    get_assistance_fn=get_assistance,
                    llm=_llm
                )

                _show_thinking(thinking_log.get_steps())

            thinking_placeholder.empty()

            # ── Save to DB ────────────────────────────────────────────────────
            save_query_to_db(user_input, result["answer"], result.get("references", []))
            st.session_state.history = _load_history()

            # ── Add to chat ───────────────────────────────────────────────────
            st.session_state.chat_messages.append({
                "role": "user", "content": user_input, "time": now
            })
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": result["answer"],
                "time": now,
                "meta": {
                    "route": result.get("route", ""),
                    "confidence": result.get("confidence", 0)
                }
            })
            st.session_state.last_result = result
            st.rerun()

    # ── Last Result Detail Panel ──────────────────────────────────────────────
    if st.session_state.last_result:
        result = st.session_state.last_result
        route_info = get_route_meta(result.get("route", ""))
        confidence = result.get("confidence", 0)

        st.divider()

        # Route + confidence row
        col_route, col_conf = st.columns([2, 3])
        with col_route:
            _html(f"""
            <div style="display:flex;align-items:center;gap:8px">
              <div class="route-badge">
                {route_info.get('icon','')} {route_info.get('label','')}
              </div>
              {'<span style="font-size:0.75rem;color:#7A7A7A;margin-left:6px">From cache</span>' if result.get("from_cache") else ''}
            </div>
            """)
        with col_conf:
            _html(_confidence_html(confidence))

        # References expander
        refs = result.get("references", [])
        if refs:
            with st.expander(f"📚 Legal References ({len(refs)} sections retrieved)", expanded=False):
                for i, doc in enumerate(refs, 1):
                    _html(f"""
                    <div class="ref-card">
                      <div class="ref-number">REF {i}</div>
                      {doc[:500]}{'…' if len(doc) > 500 else ''}
                    </div>
                    """)

# ╔══════════════════════════════════════════════════════╗
# ║  TAB 2 — HISTORY                                    ║
# ╚══════════════════════════════════════════════════════╝
with tab_history:
    _html('<div class="section-header">📋 <span>Query History</span></div>')

    history = _load_history()

    if not history:
        _html('<div class="info-box">ℹ️ No queries saved yet. Start asking legal questions!</div>')
    else:
        # Search filter
        search = st.text_input("🔍 Filter history", placeholder="Search questions…", key="hist_search")
        filtered = [
            e for e in reversed(history)
            if not search or search.lower() in e["Question"].lower()
        ]

        _html(f'<div style="font-size:0.82rem;color:#7A7A7A;margin-bottom:12px">{len(filtered)} result(s)</div>')

        for entry in filtered:
            with st.expander(f"❓ {entry['Question'][:80]}"):
                _html(f"""
                <div class="answer-card">
                  <div class="answer-label">Answer</div>
                  <div class="answer-text">{entry['Answer']}</div>
                </div>
                """)

                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("🗑️ Delete", key=f"del_h_{entry['ID']}"):
                        delete_history_from_db(entry["ID"])
                        st.rerun()
                with col2:
                    is_bm = st.session_state.bookmarks.is_bookmarked(entry["ID"])
                    bm_label = "★ Saved" if is_bm else "☆ Bookmark"
                    if st.button(bm_label, key=f"bm_h_{entry['ID']}"):
                        if is_bm:
                            st.session_state.bookmarks.remove(entry["ID"])
                        else:
                            st.session_state.bookmarks.add(entry)
                        st.rerun()

# ╔══════════════════════════════════════════════════════╗
# ║  TAB 3 — BOOKMARKS                                  ║
# ╚══════════════════════════════════════════════════════╝
with tab_bookmarks:
    _html('<div class="section-header">⭐ <span>Bookmarked Queries</span></div>')

    bookmarks = st.session_state.bookmarks.get_all()

    if not bookmarks:
        _html('<div class="info-box">ℹ️ No bookmarks yet. Star important queries from the History tab!</div>')
    else:
        for bm in bookmarks:
            with st.expander(f"★ {bm['Question'][:80]}"):
                _html(f"""
                <div class="answer-card">
                  <div class="answer-label">Answer</div>
                  <div class="answer-text">{bm['Answer']}</div>
                </div>
                """)
                if st.button("Remove Bookmark", key=f"rm_bm_{bm['ID']}"):
                    st.session_state.bookmarks.remove(bm["ID"])
                    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
_html("""
<div class="ipc-footer">
  <strong>Indian Penal Code Assistant</strong> · For informational purposes only · Not a substitute for professional legal advice<br>
  सत्यमेव जयते — Truth alone triumphs
</div>
""")