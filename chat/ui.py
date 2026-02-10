import json
import os
import sys
import streamlit as st

# Allow `streamlit run chat/ui.py` from repo root (or anywhere)
# by ensuring the repository root is on sys.path so `import chat.*` works.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from chat.services.mcp_client import MCPClient, MCPToolsError
from chat.services.ollama_client import OllamaClient
from chat.orchestrator.agent import (
    detect_intent,
    execute_tool_calls,
    build_context_from_executions,
    answer_from_context,
)


st.set_page_config(page_title="Elastic MCP Log Assistant", layout="wide")
st.title("🔎 Elastic MCP Log Assistant")

# Initialize clients once per session
@st.cache_resource
def get_clients():
    return MCPClient(), OllamaClient()

mcp, ollama = get_clients()

# Session state for chat history
if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.header("Options")
    show_debug = st.checkbox("Show tool calls + MCP results", value=True)
    max_context_chars = st.slider("Max MCP context chars to send to LLM", 5_000, 80_000, 25_000, step=1_000)
    st.caption("Tip: reduce context size if responses become slow or too long.")

    if st.button("🧹 Clear chat"):
        st.session_state.history = []
        st.rerun()

# Input
question = st.text_input("Ask a question about your logs:", placeholder="e.g., how many errors per route in last 2 hours?")
ask_btn = st.button("Ask")

def trim_context(text: str, max_chars: int) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    # Keep head + tail so the model gets structure + most recent rows
    head = text[: int(max_chars * 0.6)]
    tail = text[-int(max_chars * 0.4):]
    return head + "\n\n... [truncated] ...\n\n" + tail

if ask_btn and question.strip():
    user_q = question.strip()

    # Store user message
    st.session_state.history.append({"role": "user", "content": user_q})

    with st.spinner("Fetching MCP tools..."):
        try:
            tools = mcp.fetch_tools_normalized()
        except MCPToolsError as e:
            st.session_state.history.append({"role": "assistant", "content": f"❌ MCP tools error: {e}"})
            st.rerun()

    # 1) Detect intent
    with st.spinner("Detecting intent (LLM)..."):
        raw_intent, intent = detect_intent(question=user_q, tools=tools, ollama=ollama)

    if not (intent and intent.get("tool_calls")):
        msg = "❌ Could not parse tool_calls from the LLM.\n\nRaw LLM output:\n" + (raw_intent or "")
        st.session_state.history.append({"role": "assistant", "content": msg})
        st.rerun()

    # Debug: show tool calls
    if show_debug:
        st.subheader("🧰 Tool calls")
        for i, tc in enumerate(intent["tool_calls"], 1):
            st.markdown(f"**{i}. {tc.get('name','?')}**")
            st.code(json.dumps(tc.get("arguments") or {}, indent=2, ensure_ascii=False), language="json")

    # 2) Execute tool calls
    with st.spinner("Executing tool calls against MCP..."):
        try:
            executions = execute_tool_calls(intent=intent, mcp_client=mcp)
        except MCPToolsError as e:
            st.session_state.history.append({"role": "assistant", "content": f"❌ MCP execution error: {e}"})
            st.rerun()

    if not executions:
        st.session_state.history.append({"role": "assistant", "content": "No tool calls were executed."})
        st.rerun()

    # Debug: show results
    if show_debug:
        st.subheader("📦 MCP results")
        for i, ex in enumerate(executions, 1):
            st.markdown(f"**Result #{i}: {ex.get('name','?')}**")
            st.code(ex.get("extracted_text") or "", language="text")

    # 3) Build context → Ask for final answer
    context = build_context_from_executions(executions)
    context = trim_context(context, max_context_chars)

    with st.spinner("Generating final answer (LLM)..."):
        final_answer = answer_from_context(question=user_q, context=context, ollama=ollama)

    st.session_state.history.append({"role": "assistant", "content": final_answer})
    st.rerun()

# Render chat history
st.subheader("💬 Conversation")
for msg in st.session_state.history:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"**Assistant:** {msg['content']}")
