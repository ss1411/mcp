# tests/test_basic.py
import json
import asyncio
import types

import pytest

from llm_client import LLMClient
from mcp_client import MCPClient
from app import score_tool, async_call_mcp


EMAIL_PIN_FIXTURES = [
    ("donaldgarcia@example.net", "7912"),
    ("michellejames@example.com", "1520"),
    ("laurahenderson@example.org", "1488"),
    ("spenceamanda@example.org", "2535"),
    ("glee@example.net", "4582"),
    ("williamsthomas@example.net", "4811"),
    ("justin78@example.net", "9279"),
    ("jason31@example.com", "1434"),
    ("samuel81@example.com", "4257"),
    ("williamleon@example.net", "9928"),
]


def test_llm_client_init_no_key(monkeypatch):
    """
    Ensure LLMClient fails fast if OPENAI_API_KEY is not set.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        LLMClient()


def test_llm_message_format():
    """
    Basic shape/serialization test for LLM messages
    (no network call).
    """
    messages = [
        {"role": "system", "content": "You are a test assistant."},
        {"role": "user", "content": "Hello!"},
    ]
    dumped = json.dumps(messages)
    assert '"role": "user"' in dumped
    assert '"content": "Hello!"' in dumped


def test_score_tool_keyword_matching():
    """
    Check that score_tool gives higher score to more relevant tools
    for a given user query.
    """
    user_query = "What is the warranty on my printer order?"
    tool_order = {"name": "order_status", "description": "Check order and shipping status"}
    tool_warranty = {"name": "warranty_info", "description": "Warranty details for products"}
    tool_misc = {"name": "faq_search", "description": "General FAQs"}

    s_order = score_tool(tool_order, user_query)
    s_warranty = score_tool(tool_warranty, user_query)
    s_misc = score_tool(tool_misc, user_query)

    # At least one of the targeted tools should score higher than misc.
    assert max(s_order, s_warranty) >= s_misc


@pytest.mark.asyncio
async def test_async_call_mcp_selects_tool_and_returns_json(monkeypatch):
    """
    Test async_call_mcp with a fake MCPClient:
    - list_tools returns a few tools
    - call_tool returns a dummy payload
    Ensure the final result is JSON containing selected_tool and tool_result.
    """
    class FakeMCPClient:
        async def list_tools(self):
            # Simulate typical MCP list_tools response shape.
            return [
                {"name": "order_status", "description": "Order and shipping status"},
                {"name": "warranty_info", "description": "Warranty information"},
            ]

        async def call_tool(self, tool_name, arguments):
            return {
                "tool": tool_name,
                "arguments": arguments,
                "dummy": True,
            }

    # Use one of the test user emails and PIN in the query
    email, pin = EMAIL_PIN_FIXTURES[0]
    user_query = f"My order seems delayed, email {email}, PIN {pin}"

    fake_client = FakeMCPClient()

    result_str = await async_call_mcp(user_query, fake_client)
    # Should be valid JSON
    data = json.loads(result_str)

    assert "selected_tool" in data
    assert "tool_result" in data
    assert data["tool_result"]["dummy"] is True
    assert data["tool_result"]["arguments"]["query"] == user_query


def test_email_pin_fixtures_format():
    """
    Simple sanity check on provided email/PIN fixtures.
    """
    for email, pin in EMAIL_PIN_FIXTURES:
        assert "@" in email and "." in email.split("@")[-1]
        assert pin.isdigit()
        assert len(pin) == 4
