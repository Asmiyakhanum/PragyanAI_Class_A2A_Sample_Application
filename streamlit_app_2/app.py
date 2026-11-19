
import streamlit as st
import asyncio
import httpx
import uuid
import json

from a2a.client import (
    A2ACardResolver,
    ClientConfig,
    create_client,
)

from a2a.helpers import (
    new_text_message,
    get_artifact_text,
    get_message_text,
)

from a2a.types import (
    Role,
    SendMessageRequest,
    TaskState,
)


# =====================================================
# 1. STREAMLIT CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="PragyanAI A2A Client",
    page_icon="🚀",
    layout="wide",
)

st.title("🚀 PragyanAI – A2A Remote Agent Client")

st.caption(
    "Discover remote agents, send messages and "
    "communicate through the A2A protocol."
)


# =====================================================
# 2. SERVER CONFIGURATION
# =====================================================

try:
    SERVER_URL = st.secrets["A2A_SERVER_URL"].strip().rstrip("/")
except Exception:
    st.error(
        "A2A_SERVER_URL is missing from Streamlit Secrets."
    )
    st.stop()


# =====================================================
# 3. SESSION STATE
# =====================================================

if "agent_card" not in st.session_state:
    st.session_state.agent_card = None

if "conversation" not in st.session_state:
    st.session_state.conversation = []

if "server_health" not in st.session_state:
    st.session_state.server_health = None


# =====================================================
# 4. UTILITY FUNCTIONS
# =====================================================

def extract_agent_interfaces(card):

    interfaces = []

    for interface in card.supported_interfaces:

        interfaces.append({
            "protocol": interface.protocol_binding,
            "url": interface.url,
            "version": interface.protocol_version,
        })

    return interfaces


def extract_task_response(task):

    output = []

    # Extract task state
    try:
        state = TaskState.Name(task.status.state)
        output.append(f"Task Status: {state}")
    except Exception:
        pass

    # Extract task artifacts
    for artifact in task.artifacts:

        try:
            artifact_text = get_artifact_text(
                artifact,
                delimiter="\n"
            )

            if artifact_text:
                output.append(artifact_text)

        except Exception:
            for part in artifact.parts:

                try:
                    if part.HasField("text"):
                        output.append(part.text)
                except Exception:
                    pass

    # Extract status message, if available
    try:
        if task.status.HasField("message"):

            status_text = get_message_text(
                task.status.message,
                delimiter="\n"
            )

            if status_text:
                output.append(status_text)

    except Exception:
        pass

    return "\n".join(output)


def extract_response(chunk):

    # Case 1: Direct message response
    if chunk.HasField("message"):

        return get_message_text(
            chunk.message,
            delimiter="\n"
        )

    # Case 2: Complete task response
    if chunk.HasField("task"):

        return extract_task_response(
            chunk.task
        )

    # Case 3: Artifact update
    if chunk.HasField("artifact_update"):

        return get_artifact_text(
            chunk.artifact_update.artifact,
            delimiter="\n"
        )

    # Case 4: Status update
    if chunk.HasField("status_update"):

        status = chunk.status_update.status

        try:
            state = TaskState.Name(status.state)
        except Exception:
            state = str(status.state)

        message = ""

        try:
            if status.HasField("message"):
                message = get_message_text(
                    status.message,
                    delimiter="\n"
                )
        except Exception:
            pass

        return f"Task Status: {state}\n{message}"

    return ""


# =====================================================
# 5. SERVER HEALTH CHECK
# =====================================================

async def check_server_health():

    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
    ) as http_client:

        response = await http_client.get(
            f"{SERVER_URL}/health"
        )

        response.raise_for_status()

        return response.json()


# =====================================================
# 6. DISCOVER REMOTE AGENT
# =====================================================

async def discover_agent():

    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
    ) as http_client:

        resolver = A2ACardResolver(
            httpx_client=http_client,
            base_url=SERVER_URL,
        )

        card = await resolver.get_agent_card()

        return card


# =====================================================
# 7. SEND A2A MESSAGE
# =====================================================

async def send_a2a_message(question, card):

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(120.0),
        follow_redirects=True,
    ) as http_client:

        # Force JSON-RPC transport.
        # Reuse this HTTP client for the A2A request.

        config = ClientConfig(
            streaming=False,
            supported_protocol_bindings=["JSONRPC"],
            httpx_client=http_client,
        )

        client = await create_client(
            agent=card,
            client_config=config,
        )

        try:

            message = new_text_message(
                question,
                role=Role.ROLE_USER,
            )

            request = SendMessageRequest(
                message=message
            )

            responses = []

            async for chunk in client.send_message(request):

                result = extract_response(chunk)

                if result:
                    responses.append(result)

            if not responses:
                return (
                    "The A2A server responded, "
                    "but no text response or artifact was returned."
                )

            return "\n\n".join(responses)

        finally:

            await client.close()


# =====================================================
# 8. SIDEBAR – SERVER SETTINGS
# =====================================================

with st.sidebar:

    st.header("⚙️ A2A Configuration")

    st.write("**Server URL**")

    st.code(SERVER_URL)

    if st.button(
        "🔍 Check Server Health",
        use_container_width=True,
    ):

        try:

            health = asyncio.run(
                check_server_health()
            )

            st.session_state.server_health = health

            st.success("Server is online!")

            st.json(health)

        except httpx.RequestError as e:

            st.error(
                f"Network connection failed: {str(e)}"
            )

        except Exception as e:

            st.error(
                f"Health check failed: {str(e)}"
            )

    if st.button(
        "🔄 Clear Conversation",
        use_container_width=True,
    ):

        st.session_state.conversation = []

        st.rerun()


# =====================================================
# 9. AGENT DISCOVERY
# =====================================================

st.subheader("1. Discover Remote Agent")

col1, col2 = st.columns([1, 2])

with col1:

    discover_button = st.button(
        "🔍 Discover Agent",
        type="primary",
        use_container_width=True,
    )

with col2:

    st.caption(
        "Fetch the remote Agent Card and inspect "
        "the advertised communication endpoint."
    )


if discover_button:

    try:

        with st.spinner("Discovering remote agent..."):

            card = asyncio.run(
                discover_agent()
            )

            st.session_state.agent_card = card

        st.success("Agent discovered successfully!")

    except httpx.RequestError as e:

        st.error(
            f"Agent discovery network error: {str(e)}"
        )

    except Exception as e:

        st.error(
            f"Agent discovery failed: {str(e)}"
        )


# =====================================================
# 10. DISPLAY AGENT CARD
# =====================================================

card = st.session_state.agent_card

if card:

    st.divider()

    st.subheader("2. Agent Information")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("**Agent Name**")

        st.write(card.name)

        st.markdown("**Description**")

        st.write(card.description)

        st.markdown("**Version**")

        st.write(card.version)

    with col2:

        st.markdown("**Capabilities**")

        st.json({
            "streaming": card.capabilities.streaming,
            "push_notifications": (
                card.capabilities.push_notifications
            ),
        })

        st.markdown("**Supported Interfaces**")

        st.json(
            extract_agent_interfaces(card)
        )

    # Verify the endpoint advertised by the Agent Card.

    interfaces = extract_agent_interfaces(card)

    jsonrpc_interfaces = [
        item for item in interfaces
        if item["protocol"] == "JSONRPC"
    ]

    if jsonrpc_interfaces:

        advertised_url = (
            jsonrpc_interfaces[0]["url"].rstrip("/")
        )

        st.markdown("**JSON-RPC Endpoint**")

        st.code(advertised_url)

        if advertised_url != SERVER_URL:

            st.warning(
                "The Agent Card advertises a different "
                "JSON-RPC URL from A2A_SERVER_URL. "
                "Verify that the advertised URL is publicly "
                "accessible and points to your Render service."
            )

    else:

        st.error(
            "No JSON-RPC interface was found in the Agent Card."
        )


# =====================================================
# 11. CHAT INTERFACE
# =====================================================

st.divider()

st.subheader("3. Communicate with Remote Agent")

if not card:

    st.info(
        "Discover the remote agent before sending a message."
    )

else:

    for item in st.session_state.conversation:

        with st.chat_message(item["role"]):

            st.markdown(item["content"])

    question = st.chat_input(
        "Enter your message to the remote agent..."
    )

    if question:

        st.session_state.conversation.append({
            "role": "user",
            "content": question,
        })

        with st.chat_message("user"):

            st.markdown(question)

        with st.chat_message("assistant"):

            with st.spinner(
                "Remote A2A agent is processing..."
            ):

                try:

                    result = asyncio.run(
                        send_a2a_message(
                            question,
                            card,
                        )
                    )

                    st.markdown(result)

                    st.session_state.conversation.append({
                        "role": "assistant",
                        "content": result,
                    })

                except httpx.ConnectError as e:

                    error_message = (
                        "Could not connect to the A2A JSON-RPC "
                        "endpoint. Check the Agent Card URL, "
                        "Render service availability and logs.\n\n"
                        f"Technical details: {str(e)}"
                    )

                    st.error(error_message)

                except httpx.TimeoutException:

                    error_message = (
                        "The A2A request timed out. "
                        "The server may be sleeping, overloaded "
                        "or taking too long to process."
                    )

                    st.error(error_message)

                except httpx.HTTPStatusError as e:

                    error_message = (
                        f"HTTP Error: {e.response.status_code}\n\n"
                        f"Response: {e.response.text[:2000]}"
                    )

                    st.error(error_message)

                except Exception as e:

                    error_message = (
                        f"A2A communication failed: {str(e)}"
                    )

                    st.error(error_message)

                    st.exception(e)

                else:

                    st.success("A2A response received!")

# =====================================================
# 12. FOOTER
# =====================================================

st.divider()

st.caption(
    "PragyanAI | Agent-to-Agent Communication Demo | "
    "Streamlit + A2A SDK + Render"
)

