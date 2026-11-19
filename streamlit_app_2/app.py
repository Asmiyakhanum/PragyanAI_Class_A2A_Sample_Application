
import streamlit as st
import asyncio
import httpx
import json

from a2a.client import (
    A2ACardResolver,
    ClientConfig,
    create_client,
)

from a2a.helpers import new_text_message

from a2a.types import (
    Role,
    SendMessageRequest,
)


# =====================================================
# 1. PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="PragyanAI A2A Client",
    page_icon="🚀",
    layout="wide",
)

st.title("🚀 PragyanAI – A2A Remote Agent Client")

st.caption(
    "Discover a remote agent, send messages and "
    "receive responses using the A2A protocol."
)


# =====================================================
# 2. SERVER CONFIGURATION
# =====================================================

try:

    SERVER_URL = (
        st.secrets["A2A_SERVER_URL"]
        .strip()
        .rstrip("/")
    )

except Exception:

    st.error(
        "A2A_SERVER_URL is missing from Streamlit Secrets."
    )

    st.stop()


HEALTH_URL = f"{SERVER_URL}/health"
AGENT_CARD_URL = (
    f"{SERVER_URL}/.well-known/agent-card.json"
)


# =====================================================
# 3. SESSION STATE
# =====================================================

if "agent_card" not in st.session_state:
    st.session_state.agent_card = None

if "conversation" not in st.session_state:
    st.session_state.conversation = []

if "agent_discovered" not in st.session_state:
    st.session_state.agent_discovered = False


# =====================================================
# 4. HEALTH CHECK
# =====================================================

async def check_server_health():

    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
    ) as http_client:

        response = await http_client.get(
            HEALTH_URL
        )

        response.raise_for_status()

        return response.json()


# =====================================================
# 5. AGENT DISCOVERY
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
# 6. GENERIC A2A RESPONSE EXTRACTION
# =====================================================

def extract_text_from_response(response):

    """
    Extract text from A2A response models.

    Handles nested task artifacts, message parts
    and status messages.
    """

    if hasattr(response, "model_dump"):

        data = response.model_dump(
            mode="json",
            exclude_none=True,
        )

    elif isinstance(response, dict):

        data = response

    else:

        return str(response)

    collected = []

    def walk(value):

        if isinstance(value, dict):

            # A2A text part
            if (
                isinstance(value.get("text"), str)
                and value.get("text").strip()
            ):

                collected.append(
                    value["text"].strip()
                )

            for key, item in value.items():

                if key != "text":
                    walk(item)

        elif isinstance(value, list):

            for item in value:
                walk(item)

    walk(data)

    # Remove duplicate text entries
    unique_text = list(dict.fromkeys(collected))

    if unique_text:

        return "\n\n".join(unique_text)

    return json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
    )


# =====================================================
# 7. GET JSON-RPC ENDPOINT
# =====================================================

def get_jsonrpc_url(card):

    interfaces = getattr(
        card,
        "supported_interfaces",
        [],
    )

    for interface in interfaces:

        if (
            interface.protocol_binding.upper()
            == "JSONRPC"
        ):

            return interface.url.rstrip("/")

    raise ValueError(
        "Agent Card does not advertise a JSON-RPC interface."
    )


# =====================================================
# 8. TEST ADVERTISED ENDPOINT
# =====================================================

async def test_advertised_endpoint(card):

    endpoint = get_jsonrpc_url(card)

    # The server's health route is at the service root,
    # not at the JSON-RPC path if a custom path is used.
    if endpoint == SERVER_URL:

        health_url = f"{SERVER_URL}/health"

    else:

        health_url = f"{endpoint}/health"

    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
    ) as http_client:

        response = await http_client.get(
            health_url
        )

        response.raise_for_status()

        return {
            "endpoint": endpoint,
            "health": response.json(),
        }


# =====================================================
# 9. SEND A2A MESSAGE
# =====================================================

async def send_a2a_message(question, card):

    endpoint = get_jsonrpc_url(card)

    # Create HTTP client used by the A2A SDK.
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(120.0),
        follow_redirects=True,
    ) as http_client:

        config = ClientConfig(
            streaming=False,
            httpx_client=http_client,
        )

        # Client uses the URL advertised in Agent Card.
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

            async for response in client.send_message(
                request
            ):

                text = extract_text_from_response(
                    response
                )

                if text:
                    responses.append(text)

            if not responses:

                return (
                    "The server responded, but no "
                    "text content was returned."
                )

            return "\n\n".join(responses)

        finally:

            await client.close()


# =====================================================
# 10. SIDEBAR
# =====================================================

with st.sidebar:

    st.header("⚙️ A2A Server")

    st.write("Configured Server URL")

    st.code(SERVER_URL)

    st.divider()

    if st.button(
        "Check Server Health",
        use_container_width=True,
    ):

        try:

            health = asyncio.run(
                check_server_health()
            )

            st.success("Server is online!")

            st.json(health)

        except Exception as e:

            st.error(
                f"Health check failed: {str(e)}"
            )

    if st.button(
        "Clear Conversation",
        use_container_width=True,
    ):

        st.session_state.conversation = []

        st.rerun()


# =====================================================
# 11. DISCOVER REMOTE AGENT
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
        "Fetch the remote Agent Card from Render."
    )


if discover_button:

    try:

        with st.spinner(
            "Discovering remote agent..."
        ):

            card = asyncio.run(
                discover_agent()
            )

        st.session_state.agent_card = card
        st.session_state.agent_discovered = True

        st.success("Agent discovered successfully!")

    except Exception as e:

        st.session_state.agent_card = None
        st.session_state.agent_discovered = False

        st.error(
            f"Agent discovery failed: {str(e)}"
        )


# =====================================================
# 12. DISPLAY AGENT DETAILS
# =====================================================

card = st.session_state.agent_card

if card:

    st.divider()

    st.subheader("2. Remote Agent Information")

    col1, col2 = st.columns(2)

    with col1:

        st.write("**Agent Name**")

        st.success(card.name)

        st.write("**Description**")

        st.write(card.description)

        st.write("**Version**")

        st.write(card.version)

    with col2:

        st.write("**Agent Capabilities**")

        st.json(
            card.capabilities.model_dump(
                mode="json"
            )
        )

    # Display advertised interfaces
    st.write("**Supported Interfaces**")

    for interface in card.supported_interfaces:

        st.code(
            f"{interface.protocol_binding}: "
            f"{interface.url}"
        )

    # Display skills
    st.write("**Available Skills**")

    for skill in card.skills:

        with st.expander(skill.name):

            st.write(skill.description)

            st.write("Tags:", skill.tags)

            st.write("Examples:", skill.examples)


# =====================================================
# 13. ENDPOINT DIAGNOSTICS
# =====================================================

if card:

    st.divider()

    st.subheader("3. JSON-RPC Connection Diagnostics")

    if st.button(
        "Test Advertised Endpoint",
        use_container_width=True,
    ):

        try:

            with st.spinner(
                "Testing advertised endpoint..."
            ):

                result = asyncio.run(
                    test_advertised_endpoint(card)
                )

            st.success("Advertised endpoint is reachable!")

            st.write(
                "**JSON-RPC URL:**",
                result["endpoint"],
            )

            st.json(result["health"])

        except Exception as e:

            st.error(
                f"Advertised endpoint test failed: {str(e)}"
            )

            st.warning(
                "Check the URL advertised in the Agent Card "
                "and the Render deployment."
            )


# =====================================================
# 14. CHAT INTERFACE
# =====================================================

st.divider()

st.subheader("4. Communicate with Remote Agent")

if not card:

    st.info(
        "First click Discover Agent to connect to the "
        "remote A2A agent."
    )

else:

    # Display conversation history

    for item in st.session_state.conversation:

        with st.chat_message(item["role"]):

            st.markdown(item["content"])

    question = st.chat_input(
        "Enter your message to the remote agent..."
    )

    if question:

        # Add user message
        st.session_state.conversation.append({
            "role": "user",
            "content": question,
        })

        with st.chat_message("user"):

            st.markdown(question)

        with st.chat_message("assistant"):

            with st.spinner(
                "Remote agent is processing..."
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

                    st.error(
                        "Cannot connect to the JSON-RPC endpoint."
                    )

                    st.code(str(e))

                    st.info(
                        "Check whether the Agent Card advertises "
                        "the correct publicly accessible Render URL."
                    )

                except httpx.TimeoutException as e:

                    st.error(
                        "A2A request timed out."
                    )

                    st.code(str(e))

                except httpx.HTTPStatusError as e:

                    st.error(
                        f"HTTP error: {e.response.status_code}"
                    )

                    st.code(
                        e.response.text[:2000]
                    )

                except Exception as e:

                    st.error(
                        f"A2A communication failed: {str(e)}"
                    )

                    st.exception(e)


# =====================================================
# 15. FOOTER
# =====================================================

st.divider()

st.caption(
    "PragyanAI | A2A Remote Agent Client | "
    "Streamlit + Python + A2A SDK + Render"
)

