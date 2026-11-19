
import os
import uvicorn

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)

from agent_executor import HelloWorldAgentExecutor


# --------------------------------------------------
# 1. SERVER CONFIGURATION
# --------------------------------------------------

PORT = int(os.environ.get("PORT", "8001"))

PUBLIC_URL = os.environ.get(
    "A2A_PUBLIC_URL",
    f"http://127.0.0.1:{PORT}"
).rstrip("/")


# --------------------------------------------------
# 2. DEFINE AGENT SKILL
# --------------------------------------------------

hello_skill = AgentSkill(
    id="hello_world",
    name="Hello World Agent",
    description=(
        "An A2A agent that receives user messages "
        "and returns intelligent responses."
    ),
    tags=[
        "hello",
        "greeting",
        "assistant",
        "A2A",
    ],
    examples=[
        "Hello",
        "Introduce yourself",
        "What can you do?",
        "Explain Agent-to-Agent communication",
    ],
)


# --------------------------------------------------
# 3. DEFINE AGENT CARD
# --------------------------------------------------

agent_card = AgentCard(
    name="PragyanAI Hello World Agent",
    description=(
        "A demonstration A2A agent hosted on Render. "
        "It receives messages from external A2A clients "
        "and returns responses."
    ),
    version="1.0.0",

    default_input_modes=[
        "text/plain",
    ],

    default_output_modes=[
        "text/plain",
    ],

    capabilities=AgentCapabilities(
        streaming=True,
        push_notifications=False,
    ),

    supported_interfaces=[
        AgentInterface(
            protocol_binding="JSONRPC",
            url=PUBLIC_URL,
            protocol_version="1.0",
        )
    ],

    skills=[
        hello_skill,
    ],
)


# --------------------------------------------------
# 4. INITIALIZE AGENT EXECUTOR
# --------------------------------------------------

agent_executor = HelloWorldAgentExecutor()


# --------------------------------------------------
# 5. INITIALIZE TASK STORE
# --------------------------------------------------

task_store = InMemoryTaskStore()


# --------------------------------------------------
# 6. INITIALIZE REQUEST HANDLER
# --------------------------------------------------

request_handler = DefaultRequestHandler(
    agent_executor=agent_executor,
    task_store=task_store,
    agent_card=agent_card,
)


# --------------------------------------------------
# 7. HEALTH CHECK ENDPOINT
# --------------------------------------------------

async def health(request):

    return JSONResponse({
        "status": "healthy",
        "service": "PragyanAI A2A Server",
        "agent": agent_card.name,
        "version": agent_card.version,
        "public_url": PUBLIC_URL,
    })


# --------------------------------------------------
# 8. REGISTER ROUTES
# --------------------------------------------------

routes = [

    # Health check
    Route(
        "/health",
        endpoint=health,
        methods=["GET"],
    ),

    # A2A Agent Card discovery
    *create_agent_card_routes(agent_card),

    # A2A JSON-RPC communication
    *create_jsonrpc_routes(
        request_handler,
        "/",
    ),
]


# --------------------------------------------------
# 9. CREATE STARLETTE APPLICATION
# --------------------------------------------------

app = Starlette(
    routes=routes,
)


# --------------------------------------------------
# 10. RUN SERVER LOCALLY
# --------------------------------------------------

if __name__ == "__main__":

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
    )
