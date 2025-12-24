# mcp

# Computer Products Support Chatbot (Demo)

Prototype customer-support chatbot for a company selling computer products (monitors, printers, etc.).  
The app uses:

- **OpenAI GPT-4o-mini** as the LLM.[web:19]
- A **Model Context Protocol (MCP) Streamable HTTP server** at `https://vipfapwm3x.us-east-1.awsapprunner.com/mcp` for access to internal tools such as product lookup, order status, or ticket creation.
- **Streamlit** for the web UI, deployed on **Hugging Face Spaces**.

---

## Tech stack

- Python 3.10+
- Streamlit (UI)
- OpenAI Python SDK (`openai`)[web:13]
- httpx (HTTP client for MCP)
- pydantic (structuring responses if needed)

---

## Design choices

- **Single-page Streamlit app**: Simplifies deployment to Hugging Face and provides a native chat UI via `st.chat_message` and `st.chat_input`.
- **LLM wrapper (`LLMClient`)**: Encapsulates GPT-4o-mini usage so model or parameters can be changed without touching UI code.[web:19]
- **MCP wrapper (`MCPClient`)**: Separates HTTP transport from business logic. The MCP server is responsible for implementing domain-specific tools.
- **Heuristic tool routing**: The first version uses keyword triggers to decide when to call MCP. In a more advanced version, the LLM could select tools via function-calling.

---

## Setup instructions (local)

1. **Clone & install**
```
git clone <this-repo-url>
cd <this-repo>
python -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Set environment variables:
```
export OPENAI_API_KEY=sk-...
export MCP_SERVER_URL=https://vipfapwm3x.us-east-1.awsapprunner.com/mcp
```

3. Run the app:
```
streamlit run app.py
```

The app will be available at `http://localhost:8501`.

4. **Run tests**
```
pip install pytest
pytest
```

5. HuggingFace Deployment:

---
## Streamlit deployment (option 1 - chosen option)
1. create a streamlit community cloud account (use github for login)
2. Go to streamlit UI 
3. click on deploy (when you run your app, it's on the top right side)
4. Provide necessary info (github repo, app url, etc)
5. Your app is deployed

Here is the link to my steamlit deployment:
https://mcp-customer-support-chatbot.streamlit.app/


## Hugging Face Spaces deployment (option 2)

1. **Create a new Space**

- Go to [Hugging Face Spaces](https://huggingface.co/spaces) and click **New Space**.
- Choose **SDK: Streamlit**, pick a name, and create

2. **Push code**

- Either link a Git repo or upload files (`app.py`, `llm_client.py`, `mcp_client.py`, `requirements.txt`, `README.md`, `tests/`).

3. **Configure secrets**

- In the Space, go to **Settings → Repository secrets**.
- Add:
  - `OPENAI_API_KEY`: your OpenAI API key.
  - (Optional) `MCP_SERVER_URL`: override if the company changes the MCP endpoint.

4. **Build & run**

- Once the build completes, the Space will automatically start.
- Open the Space URL and interact with the chatbot.

Hugging Face automatically runs `pip install -r requirements.txt` and `streamlit run app.py` for Streamlit Spaces.

---

## Challenges and notes

- **MCP transport complexity**: Streamable HTTP supports bi-directional communication, notifications, and streaming, which can be complex to implement fully. 

A standard JSON‑RPC 2.0 request looks like this
```
{
  "jsonrpc": "2.0",
  "id": "some-unique-id",
  "method": "tool.call",
  "params": {
    "name": "support_query",
    "arguments": {
      "query": "Where is my order #123?"
    }
  }
}
```
- jsonrpc: always "2.0".
- id: any unique string/number used to correlate the response.
- method: the JSON‑RPC method name the MCP server expects. Many MCP servers use method names like "tools/call", "tool.call", or similar; check your server’s docs or OpenAPI/README.
- params: an object whose structure is defined by your MCP server. A common MCP pattern is {"name": "<tool_name>", "arguments": { ... }}

- **Deployment environment**: Spaces have limited resources; `gpt-4o-mini` is chosen for low latency and cost while still being strong enough for support tasks.
- **Secrets management**: API keys must be configured via environment variables or Space secrets, not hard-coded.

- Able to access available tools but facing issue in providing the most relevant tool to LLM as per user query
```
Available tools: {'tools': [{'name': 'list_products', 'description': 'List products with optional filters.\n\n    Args:\n        category: Filter by category (e.g., "Computers", "Monitors")\n        is_active: Filter by active status (True/False)\n\n    Returns:\n        Formatted string with products, one per line\n\n    Use cases:\n        - Browse inventory by category\n        - Check stock levels\n        - Find available products\n    ', 'inputSchema': {'properties': {'category': {'anyOf': [{'type': 'string'}, {'type': 'null'}], 'default': None, 'title': 'Category'}, 'is_active': {'anyOf': [{'type': 'boolean'}, {'type': 'null'}], 'default': None, 'title': 'Is Active'}}, 'title': 'list_productsArguments', 'type': 'object'}, 'outputSchema': {'properties': {'result': {'title': 'Result', 'type': 'string'}}, 'required': ['result'], 'title': 'list_productsOutput', 'type': 'object'}}, {'name': 'get_product', 'description': 'Get detailed product information by SKU.\n\n    Args:\n        sku: Product SKU (e.g., "COM-0001")\n\n    Returns:\n        Formatted product details\n\n    Raises:\n        ProductNotFoundError: If SKU doesn\'t exist\n\n    Use cases:\n        - Get current price\n        - Check inventory for specific item\n        - Verify product details before ordering\n    ', 'inputSchema': {'properties': {'sku': {'title': 'Sku', 'type': 'string'}}, 'required': ['sku'], 'title': 'get_productArguments', 'type': 'object'}, 'outputSchema': {'properties': {'result': {'title': 'Result', 'type': 'string'}}, 'required': ['result'], 'title': 'get_productOutput', 'type': 'object'}}, {'name': 'search_products', 'description': 'Search products by name or description.\n\n    Args:\n        query: Search term (case-insensitive, partial match)\n\n    Returns:\n        Formatted search results (same format as list_products)\n\n    Use cases:\n        - Find products by keyword\n        - Help customers discover items\n        - Natural language product lookup\n    ', 'inputSchema': {'properties': {'query': {'title': 'Query', 'type': 'string'}}, 'required': ['query'], 'title': 'search_productsArguments', 'type': 'object'}, 'outputSchema': {'properties': {'result': {'title': 'Result', 'type': 'string'}}, 'required': ['result'], 'title': 'search_productsOutput', 'type': 'object'}}, {'name': 'get_customer', 'description': "Get customer information by ID.\n\n    Args:\n        customer_id: Customer UUID\n\n    Returns:\n        Formatted customer details\n\n    Raises:\n        CustomerNotFoundError: If customer doesn't exist\n\n    Use cases:\n        - Look up customer details\n        - Verify shipping address\n        - Check customer role/permissions\n    ", 'inputSchema': {'properties': {'customer_id': {'title': 'Customer Id', 'type': 'string'}}, 'required': ['customer_id'], 'title': 'get_customerArguments', 'type': 'object'}, 'outputSchema': {'properties': {'result': {'title': 'Result', 'type': 'string'}}, 'required': ['result'], 'title': 'get_customerOutput', 'type': 'object'}}, {'name': 'verify_customer_pin', 'description': 'Verify customer identity with email and PIN.\n\n    Args:\n        email: Customer email address\n        pin: 4-digit PIN code\n\n    Returns:\n        Formatted customer details if verified\n\n    Raises:\n        CustomerNotFoundError: If email not found or PIN incorrect\n\n    Use cases:\n        - Authenticate customer before order placement\n        - Verify identity for account access\n        - Simple security check\n    ', 'inputSchema': {'properties': {'email': {'title': 'Email', 'type': 'string'}, 'pin': {'title': 'Pin', 'type': 'string'}}, 'required': ['email', 'pin'], 'title': 'verify_customer_pinArguments', 'type': 'object'}, 'outputSchema': {'properties': {'result': {'title': 'Result', 'type': 'string'}}, 'required': ['result'], 'title': 'verify_customer_pinOutput', 'type': 'object'}}, {'name': 'list_orders', 'description': 'List orders with optional filters.\n\n    Args:\n        customer_id: Filter by customer UUID\n        status: Filter by status (draft|submitted|approved|fulfilled|cancelled)\n\n    Returns:\n        Formatted order list\n\n    Use cases:\n        - View customer order history\n        - Track pending orders\n        - Analyze order patterns (autonomous agents)\n        - Find orders by status\n    ', 'inputSchema': {'properties': {'customer_id': {'anyOf': [{'type': 'string'}, {'type': 'null'}], 'default': None, 'title': 'Customer Id'}, 'status': {'anyOf': [{'type': 'string'}, {'type': 'null'}], 'default': None, 'title': 'Status'}}, 'title': 'list_ordersArguments', 'type': 'object'}, 'outputSchema': {'properties': {'result': {'title': 'Result', 'type': 'string'}}, 'required': ['result'], 'title': 'list_ordersOutput', 'type': 'object'}}, {'name': 'get_order', 'description': "Get detailed order information including items.\n\n    Args:\n        order_id: Order UUID\n\n    Returns:\n        Formatted order with line items\n\n    Raises:\n        OrderNotFoundError: If order doesn't exist\n\n    Use cases:\n        - View order details\n        - Check order contents\n        - Analyze what products are ordered together (cross-sell analysis)\n    ", 'inputSchema': {'properties': {'order_id': {'title': 'Order Id', 'type': 'string'}}, 'required': ['order_id'], 'title': 'get_orderArguments', 'type': 'object'}, 'outputSchema': {'properties': {'result': {'title': 'Result', 'type': 'string'}}, 'required': ['result'], 'title': 'get_orderOutput', 'type': 'object'}}, {'name': 'create_order', 'description': 'Create a new order with items.\n\n    Args:\n        customer_id: Customer UUID\n        items: List of items, each with:\n            - sku: str (product SKU, e.g., "MON-0054")\n            - quantity: int (must be > 0)\n            - unit_price: str (decimal as string)\n            - currency: str (default "USD")\n\n    Returns:\n        Formatted order confirmation\n\n    Raises:\n        CustomerNotFoundError: If customer doesn\'t exist\n        ProductNotFoundError: If any product SKU doesn\'t exist\n        InsufficientInventoryError: If quantity exceeds available stock\n\n    Use cases:\n        - Place new orders for customers\n        - Automatically decrements inventory (atomic)\n        - Validates all constraints before committing\n\n    Note:\n        Order starts in "submitted" status with "pending" payment\n    ', 'inputSchema': {'properties': {'customer_id': {'title': 'Customer Id', 'type': 'string'}, 'items': {'items': {'additionalProperties': True, 'type': 'object'}, 'title': 'Items', 'type': 'array'}}, 'required': ['customer_id', 'items'], 'title': 'create_orderArguments', 'type': 'object'}, 'outputSchema': {'properties': {'result': {'title': 'Result', 'type': 'string'}}, 'required': ['result'], 'title': 'create_orderOutput', 'type': 'object'}}]}
```

---

## Possible enhancements (if more time)

- Add a product selector / order ID input widget in the sidebar to structure queries to the MCP tools.
- Add conversation rating and feedback capture for improving support flows.
- Persist conversation history per user (e.g., via a small database or in-memory cache).
- Implement more robust tool-selection logic with LLM function-calling instead of keyword heuristics.
- Add automated tests with mocks for OpenAI and MCP servers to verify business flows end-to-end.

