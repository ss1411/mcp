# Streamlit based chatbot for computer products customer support.
# What it does:
# 1. Answer generic computer usage questions.
# 2. Call into the MCP server via a generic support_query tool when user input suggests it, and then condition its answer on the returned JSON

import json
import asyncio
from typing import Dict, Any, List

import streamlit as st

from llm_client import LLMClient
from mcp_client import MCPClient


st.set_page_config(page_title="Computer Support Chatbot", page_icon="💻")


def init_state():
    if "messages" not in st.session_state:
        st.session_state.messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You are a friendly, precise customer support assistant for a company "
                    "that sells computer products like monitors, printers, and accessories. "
                    "Use tools when needed to look up product details, order status, or warranty info. "
                    "Always explain things clearly and keep answers concise."
                ),
            }
        ]


def render_header():
    st.title("💻 Computer Products Support Chatbot")
    st.caption(
        "Demo customer support assistant using OpenAI GPT‑4o‑mini and an MCP server "
        "for product/order tools."
    )


def score_tool(tool: Dict[str, Any], user_message: str) -> float:
    """
    Very simple relevance scoring based on keyword overlap
    between the tool description/name and the user query.
    In a more advanced version, you could call the LLM to pick a tool.
    """
    name = tool.get("name", "").lower()
    desc = tool.get("description", "").lower()
    text = f"{name} {desc}"

    query = user_message.lower()
    score = 0.0

    keywords = [
        ("order", ["order", "shipping", "delivery", "status"]),
        ("product", ["monitor", "printer", "keyboard", "speakers", "spec", "specification", "compatibility"]),
        ("warranty", ["warranty", "guarantee"]),
        ("ticket", ["issue", "problem", "ticket", "support"]),
    ]

    for _, kws in keywords:
        if any(k in query for k in kws) and any(k in text for k in kws):
            score += 1.0

    # Fallback: small score if any query word appears in name/description
    if score == 0.0:
        for word in query.split():
            if word in text:
                score += 0.1

    return score


async def async_call_mcp(user_message: str, mcp_client: MCPClient) -> str:
    """
    Async helper to:
    1) list available tools from the MCP server
    2) choose the most relevant tool for the user query
    3) call that tool via Streamable HTTP
    Returns a JSON string of the tool result, or "" if no good tool is found.
    """
    # Heuristic: only bother with tools if the query is likely to need backend data.
    triggers = ["order", "status", "warranty", "monitor", "printer", "ticket",
                "shipping", "delivery", "specification", "compatibility",
                "problem", "issue", "support", "guarantee", "keyboard", "speakers",
                "mouse", "headset"]
    if not any(t in user_message.lower() for t in triggers):
        return ""

    try:
        # 1) Ask MCP server what tools are available
        available_tools = await mcp_client.list_tools()  # you already have this implemented
        print(f"Available tools: {available_tools}")
        if not available_tools:
            return ""

        # 2) Score tools and pick the best one
        best_tool = None
        best_score = 0.0
        for tool in available_tools:
            s = score_tool(tool, user_message)
            if s > best_score:
                best_score = s
                best_tool = tool

        # If nothing scores above 0, skip tool call
        if not best_tool or best_score <= 0.0:
            return ""

        tool_name = best_tool["name"]

        # 3) Call the selected tool
        result = await mcp_client.call_tool(
            tool_name=tool_name,
            arguments={"query": user_message},
        )

        return json.dumps(
            {
                "selected_tool": tool_name,
                "tool_result": result,
            }
        )
    except Exception as e:
        return f"Tool call failed with error: {e}"



def main():
    init_state()
    render_header()

    # Sidebar: configuration
    with st.sidebar:
        st.subheader("Configuration")
        st.markdown("Set your secrets as environment variables:")
        st.code("OPENAI_API_KEY=sk-...\nMCP_SERVER_URL=https://vipfapwm3x.us-east-1.awsapprunner.com/mcp")
        st.markdown("These should be added in the Hugging Face Space settings under **Secrets**.")

        if st.button("Clear conversation"):
            st.session_state.messages = st.session_state.messages[:1]  # keep system

    # Chat history display
    for m in st.session_state.messages:
        if m["role"] == "system":
            continue
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_input = st.chat_input("Describe your issue or question...")
    if user_input:
        # Show user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # MCP + LLM processing
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                llm = LLMClient()
                mcp = MCPClient()

                tool_context = asyncio.run(async_call_mcp(user_input, mcp))

                # Augment conversation with a tool context system message if present
                messages_for_llm = list(st.session_state.messages)
                if tool_context:
                    messages_for_llm.append(
                        {
                            "role": "system",
                            "content": ("Tool results for this user query (JSON): "
                                f"{tool_context}. "
                                "Use this information when answering. If tool failed, "
                                "explain limitations briefly."
                            ),
                        }
                    )

                answer = llm.chat(messages_for_llm)
                st.markdown(answer)
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )


if __name__ == "__main__":
    main()
