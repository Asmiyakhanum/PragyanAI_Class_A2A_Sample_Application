
# server.py

import os
import uvicorn

from starlette.applications import Starlette

from a2a.server.request_handlers import (
    DefaultRequestHandler
)

from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes
)

from a2a.server.tasks import (
    InMemoryTaskStore
)

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill
)

from agent_executor import (
    HelloWorldAgentExecutor
)


# ==========================================
# 1. SERVER CONFIGURATION
# ==========================================

HOST = "0.0.0.0"

PORT = int(os.environ.get("PORT", "8001"))

PUBLIC_URL = os.environ.get(
    "A2A_PUBLIC_URL",
    f"http://127.0.0.1:{PORT}"
).rstrip("/")


# ==========================================
# 2. DEFINE AGENT SKILL
# ==========================================

hello_skill = AgentSkill(

    id="hello_world",

    name="Hello World",

    description=(
        "Accepts user messages and returns "
        "intelligent responses."
    ),

    tags=[
        "hello",
        "greeting",
        "conversation",
        "a2a"
    ],

    examples=[
        "Hello A2A Agent",
        "Explain Agent-to-Agent Protocol",
        "How do AI agents communicate?"
    ],

    input_modes=[
        "text/plain"
    ],

    output_modes=[
        "text/plain"
    ]
)


# ==========================================
# 3. CREATE AGENT CARD
# ==========================================

agent_card = AgentCard(

    name="PragyanAI Remote A2A Agent",

    description=(
        "A remote AI agent built using "
        "Python, A2A SDK and Streamlit."
    ),

    version="1.0.0",

    default_input_modes=[
        "text/plain"
    ],

    default_output_modes=[
        "text/plain"
    ],

    capabilities=AgentCapabilities(

        streaming=True,

        push_notifications=False

    ),

    supported_interfaces=[

        AgentInterface(

            protocol_binding="JSONRPC",

            url=PUBLIC_URL,

            protocol_version="1.0"

        )

    ],

    skills=[
        hello_skill
    ]
)


# ==========================================
# 4. CREATE A2A REQUEST HANDLER
# ==========================================

request_handler = DefaultRequestHandler(

    agent_executor=HelloWorldAgentExecutor(),

    task_store=InMemoryTaskStore(),

    agent_card=agent_card

)


# ==========================================
# 5. CREATE A2A ROUTES
# ==========================================

routes = []

# Agent Card discovery
routes.extend(
    create_agent_card_routes(agent_card)
)

# A2A JSON-RPC endpoint
routes.extend(
    create_jsonrpc_routes(
        request_handler,
        "/"
    )
)


# ==========================================
# 6. CREATE APPLICATION
# ==========================================

app = Starlette(
    routes=routes
)


# ==========================================
# 7. HEALTH CHECK
# ==========================================

@app.route("/health", methods=["GET"])
async def health(request):

    from starlette.responses import JSONResponse

    return JSONResponse({
        "status": "healthy",
        "agent": agent_card.name,
        "version": agent_card.version
    })


# ==========================================
# 8. START SERVER
# ==========================================

if __name__ == "__main__":

    print("Starting PragyanAI A2A Server...")

    print("Agent:", agent_card.name)

    print("Agent Card:", PUBLIC_URL +
          "/.well-known/agent-card.json")

    uvicorn.run(
        app,
        host=HOST,
        port=PORT
    )
