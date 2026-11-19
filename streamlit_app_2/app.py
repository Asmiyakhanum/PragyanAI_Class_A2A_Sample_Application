
import streamlit as st
import asyncio
import httpx
import json

from datetime import datetime, timezone
from urllib.parse import urlparse

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
    page_title="PragyanAI - A2A Remote Agent Client",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =====================================================
# 2. CUSTOM CSS
# =====================================================

st.markdown("""
<style>

.main-title {
    font-size: 32px;
    font-weight: 700;
    color: #2563EB;
}

.subtitle {
    font-size: 15px;
    color: gray;
}

.status-online {
    color: #16A34A;
    font-weight: bold;
}

.status-offline {
    color: #DC2626;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# 3. HEADER
# =====================================================

st.markdown(
    '<div class="main-title">🚀 A2A Remote Agent Client</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'PragyanAI | Agent-to-Agent Communication | '
    'Remote Agent Discovery and Messaging'
    '</div>',
    unsafe_allow_html=True,
)

st.divider()


# =====================================================
# 4. SERVER CONFIGURATION
# =====================================================

DEFAULT_URL = "https://your-a2a-server.onrender.com"

try:

    SECRET_URL = st.secrets["A2A_SERVER_URL"]

except Exception:

    SECRET_URL = DEFAULT_URL


if "server_url" not in st.session_state:

    st.session_state.server_url = SECRET_URL


if "agent_card" not in st.session_state:

    st.session_state.agent_card = None


if "conversation" not in st.session_state:

    st.session_state.conversation = []


if "last_health" not in st.session_state:

    st.session_state.last_health = None


if "last_response" not in st.session_state:

    st.session_state.last_response = None


# =====================================================
# 5. SIDEBAR CONFIGURATION
# =====================================================

with st.sidebar:

    st.header("⚙️ A2A Configuration")

    SERVER_URL = st.text_input(
        "A2A Server URL",
        value=st.session_state.server_url,
        help="Enter your public Render server URL.",
    ).strip().rstrip("/")

    st.session_state.server_url = SERVER_URL

    st.divider()

    st.markdown("### Server Endpoints")

    st.caption("Health")

    st.code(
        SERVER_URL + "/health"
        if SERVER_URL else "Not configured"
    )

    st.caption("Agent Card")

    st.code(
        SERVER_URL + "/.well-known/agent-card.json"
        if SERVER_URL else "Not configured"
    )

    st.caption("JSON-RPC")

    st.code("/")

    st.divider()

    if st.button(
        "🔄 Clear Conversation",
        use_container_width=True,
    ):

        st.session_state.conversation = []

        st.session_state.last_response = None

        st.rerun()

    if st.button(
        "🔄 Reset Agent",
        use_container_width=True,
    ):

        st.session_state.agent_card = None

        st.session_state.last_health = None

        st.rerun()

    st.divider()

    st.markdown("### Technology Stack")

    st.markdown("""
    - Python
    - Streamlit
    - A2A Python SDK
    - HTTPX
    - JSON-RPC 2.0
    - Starlette
    - Render Cloud
    """)


# =====================================================
# 6. GENERIC OBJECT CONVERSION
# =====================================================

def safe_value(obj, field, default=None):

    """
    Safely read a field from either a dictionary
    or an SDK object.
    """

    if obj is None:
        return default

    if isinstance(obj, dict):

        return obj.get(field, default)

    return getattr(obj, field, default)


def to_plain_data(obj):

    """
    Convert SDK objects to JSON-compatible values.

    Supports dictionaries, Pydantic objects,
    dataclasses and ordinary Python objects.
    """

    if obj is None:
        return None

    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, dict):

        return {
            str(key): to_plain_data(value)
            for key, value in obj.items()
        }

    if isinstance(obj, (list, tuple)):

        return [
            to_plain_data(item)
            for item in obj
        ]

    if hasattr(obj, "model_dump"):

        return to_plain_data(
            obj.model_dump(
                mode="json",
                exclude_none=True,
            )
        )

    if hasattr(obj, "dict") and callable(obj.dict):

        try:

            return to_plain_data(obj.dict())

        except Exception:
            pass

    if hasattr(obj, "__dict__"):

        return {
            key: to_plain_data(value)
            for key, value in vars(obj).items()
            if not key.startswith("_")
        }

    return str(obj)


# =====================================================
# 7. VALIDATE SERVER URL
# =====================================================

def validate_server_url(url):

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):

        raise ValueError(
            "Server URL must start with http:// or https://"
        )

    if not parsed.netloc:

        raise ValueError("Invalid server URL.")

    return True


# =====================================================
# 8. HEALTH CHECK
# =====================================================

async def check_server_health(server_url):

    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
    ) as http_client:

        response = await http_client.get(
            server_url + "/health"
        )

        response.raise_for_status()

        return response.json()


# =====================================================
# 9. AGENT DISCOVERY
# =====================================================

async def discover_agent(server_url):

    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
    ) as http_client:

        resolver = A2ACardResolver(
            httpx_client=http_client,
            base_url=server_url,
        )

        card = await resolver.get_agent_card()

        return card


# =====================================================
# 10. EXTRACT AGENT INFORMATION
# =====================================================

def get_agent_information(card):

    name = safe_value(
        card,
        "name",
        "Unknown Agent",
    )

    description = safe_value(
        card,
        "description",
        "No description available.",
    )

    version = safe_value(
        card,
        "version",
        "Unknown",
    )

    capabilities = safe_value(
        card,
        "capabilities",
        {},
    )

    skills = safe_value(
        card,
        "skills",
        [],
    )

    interfaces = safe_value(
        card,
        "supported_interfaces",
        [],
    )

    input_modes = safe_value(
        card,
        "default_input_modes",
        [],
    )

    output_modes = safe_value(
        card,
        "default_output_modes",
        [],
    )

    return {
        "name": name,
        "description": description,
        "version": version,
        "capabilities": to_plain_data(capabilities) or {},
        "skills": skills or [],
        "interfaces": interfaces or [],
        "input_modes": input_modes or [],
        "output_modes": output_modes or [],
    }


# =====================================================
# 11. GET JSON-RPC ENDPOINT
# =====================================================

def get_jsonrpc_url(card):

    interfaces = safe_value(
        card,
        "supported_interfaces",
        [],
    )

    for interface in interfaces:

        protocol = safe_value(
            interface,
            "protocol_binding",
            "",
        )

        if str(protocol).upper() == "JSONRPC":

            endpoint = safe_value(
                interface,
                "url",
                "",
            )

            if endpoint:
                return endpoint.rstrip("/")

    raise ValueError(
        "No JSON-RPC interface found in the Agent Card."
    )


# =====================================================
# 12. ENDPOINT DIAGNOSTICS
# =====================================================

async def test_jsonrpc_service(card):

    endpoint = get_jsonrpc_url(card)

    parsed = urlparse(endpoint)

    health_url = (
        f"{parsed.scheme}://{parsed.netloc}/health"
    )

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
            "health_url": health_url,
            "health": response.json(),
            "status_code": response.status_code,
        }


# =====================================================
# 13. EXTRACT RESPONSE TEXT
# =====================================================

def extract_text_from_response(response):

    """
    Extract text from A2A Task, Message or response events.
    """

    data = to_plain_data(response)

    collected = []

    def walk(value):

        if isinstance(value, dict):

            text_value = value.get("text")

            if (
                isinstance(text_value, str)
                and text_value.strip()
            ):

                collected.append(
                    text_value.strip()
                )

            for key, item in value.items():

                if key != "text":
                    walk(item)

        elif isinstance(value, list):

            for item in value:
                walk(item)

    walk(data)

    unique = list(dict.fromkeys(collected))

    if unique:

        return "\n\n".join(unique)

    return json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
    )


# =====================================================
# 14. SEND A2A MESSAGE
# =====================================================

async def send_a2a_message(question, card):

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(120.0),
        follow_redirects=True,
    ) as http_client:

        config = ClientConfig(
            streaming=False,
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

            async for response in client.send_message(
                request
            ):

                response_text = extract_text_from_response(
                    response
                )

                if response_text:

                    responses.append(response_text)

            if not responses:

                return (
                    "The A2A server did not return "
                    "a readable text response."
                )

            return "\n\n".join(
                dict.fromkeys(responses)
            )

        finally:

            await client.close()


# =====================================================
# 15. SERVER STATUS
# =====================================================

st.subheader("🌐 Remote A2A Server Status")

if not SERVER_URL:

    st.warning(
        "Please configure the A2A Server URL."
    )

    st.stop()

try:

    validate_server_url(SERVER_URL)

except ValueError as error:

    st.error(str(error))

    st.stop()


col1, col2 = st.columns([2, 1])

with col1:

    st.write("**Server URL**")

    st.code(SERVER_URL)

with col2:

    if st.button(
        "Check Server Health",
        use_container_width=True,
    ):

        try:

            health = asyncio.run(
                check_server_health(SERVER_URL)
            )

            st.session_state.last_health = health

            st.success("Server is online!")

        except Exception as error:

            st.error(
                f"Health check failed: {error}"
            )


if st.session_state.last_health:

    st.json(
        st.session_state.last_health
    )


# =====================================================
# 16. DISCOVER REMOTE AGENT
# =====================================================

st.divider()

st.subheader("1. Discover Remote Agent")

if st.button(
    "🔍 Discover Agent",
    type="primary",
    use_container_width=False,
):

    try:

        with st.spinner(
            "Connecting to remote A2A agent..."
        ):

            card = asyncio.run(
                discover_agent(SERVER_URL)
            )

        st.session_state.agent_card = card

        st.success(
            "Agent discovered successfully!"
        )

    except Exception as error:

        st.session_state.agent_card = None

        st.error(
            f"Agent discovery failed: {error}"
        )


# =====================================================
# 17. REMOTE AGENT INFORMATION
# =====================================================

card = st.session_state.agent_card

if card:

    info = get_agent_information(card)

    st.divider()

    st.subheader("2. Remote Agent Information")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("### Agent Details")

        st.write(
            "**Agent Name**"
        )

        st.success(info["name"])

        st.write(
            "**Description**"
        )

        st.write(info["description"])

        st.write(
            "**Version**"
        )

        st.write(info["version"])

    with col2:

        st.markdown("### Agent Capabilities")

        capabilities = info["capabilities"]

        if capabilities:

            st.json(capabilities)

        else:

            st.info(
                "No capabilities published."
            )


    # =================================================
    # 18. AGENT SKILLS
    # =================================================

    st.divider()

    st.subheader("3. Available Agent Skills")

    if info["skills"]:

        for index, skill in enumerate(
            info["skills"],
            1,
        ):

            with st.expander(
                f"Skill {index}: "
                f"{safe_value(skill, 'name', 'Unnamed Skill')}"
            ):

                st.write(
                    "**Skill ID:**",
                    safe_value(skill, "id", "N/A")
                )

                st.write(
                    "**Description:**",
                    safe_value(skill, "description", "N/A")
                )

                st.write(
                    "**Tags:**",
                    safe_value(skill, "tags", [])
                )

                st.write(
                    "**Examples:**",
                    safe_value(skill, "examples", [])
                )

    else:

        st.info("No skills registered.")


    # =================================================
    # 19. SUPPORTED INTERFACES
    # =================================================

    st.divider()

    st.subheader("4. A2A Protocol Interfaces")

    if info["interfaces"]:

        for interface in info["interfaces"]:

            protocol = safe_value(
                interface,
                "protocol_binding",
                "Unknown",
            )

            endpoint = safe_value(
                interface,
                "url",
                "Unknown",
            )

            version = safe_value(
                interface,
                "protocol_version",
                "Unknown",
            )

            with st.expander(
                f"Protocol: {protocol}",
                expanded=True,
            ):

                st.write(
                    "**Protocol Binding:**",
                    protocol,
                )

                st.write(
                    "**Protocol Version:**",
                    version,
                )

                st.write(
                    "**Endpoint:**"
                )

                st.code(endpoint)

    else:

        st.warning(
            "No supported interfaces found."
        )


    # =================================================
    # 20. JSON-RPC CONNECTION TEST
    # =================================================

    st.divider()

    st.subheader("5. JSON-RPC Endpoint Diagnostics")

    try:

        jsonrpc_url = get_jsonrpc_url(card)

        st.write(
            "**Advertised JSON-RPC URL:**"
        )

        st.code(jsonrpc_url)

        if jsonrpc_url != SERVER_URL:

            st.warning(
                "Advertised JSON-RPC URL differs from "
                "the configured server URL. Verify it."
            )

        if st.button(
            "Test Advertised Endpoint",
            use_container_width=True,
        ):

            try:

                with st.spinner(
                    "Testing remote service..."
                ):

                    result = asyncio.run(
                        test_jsonrpc_service(card)
                    )

                st.success(
                    "Advertised service is reachable."
                )

                st.json(result)

            except Exception as error:

                st.error(
                    f"Endpoint test failed: {error}"
                )

    except Exception as error:

        st.error(str(error))


    # =================================================
    # 21. INPUT / OUTPUT MODES
    # =================================================

    st.divider()

    st.subheader("6. Supported Input / Output")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("**Input Modes**")

        for mode in info["input_modes"]:

            st.success(mode)

    with col2:

        st.markdown("**Output Modes**")

        for mode in info["output_modes"]:

            st.info(mode)


    # =================================================
    # 22. RAW AGENT CARD
    # =================================================

    st.divider()

    st.subheader("7. Complete Agent Card")

    with st.expander(
        "View Agent Card JSON"
    ):

        card_data = to_plain_data(card)

        st.json(card_data)

        st.download_button(
            "Download Agent Card",
            data=json.dumps(
                card_data,
                indent=4,
                ensure_ascii=False,
            ),
            file_name="pragyanai_agent_card.json",
            mime="application/json",
        )


    # =================================================
    # 23. CHAT INTERFACE
    # =================================================

    st.divider()

    st.subheader("8. Communicate with Remote Agent")

    st.caption(
        "Send messages to the remote A2A agent."
    )

    # Render previous conversation

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

                    st.session_state.last_response = result

                    st.session_state.conversation.append({
                        "role": "assistant",
                        "content": result,
                    })

                except httpx.ConnectError as error:

                    st.error(
                        "Cannot connect to the advertised "
                        "JSON-RPC endpoint."
                    )

                    st.code(str(error))

                    st.warning(
                        "Verify the supportedInterfaces URL "
                        "in the Agent Card and the Render server."
                    )

                except httpx.TimeoutException as error:

                    st.error(
                        "A2A request timed out."
                    )

                    st.code(str(error))

                except httpx.HTTPStatusError as error:

                    st.error(
                        f"HTTP Error: {error.response.status_code}"
                    )

                    st.code(
                        error.response.text[:2000]
                    )

                except Exception as error:

                    st.error(
                        f"A2A communication failed: {error}"
                    )

                    st.exception(error)


else:

    st.info(
        "Discover the remote agent to view its information "
        "and start A2A communication."
    )


# =====================================================
# 24. MONITORING INFORMATION
# =====================================================

st.divider()

st.subheader("9. Client Monitoring")

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "Conversation Messages",
        len(st.session_state.conversation)
    )

with col2:

    st.write("**Last Client Activity**")

    st.write(
        datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    )


# =====================================================
# 25. FOOTER
# =====================================================

st.divider()

st.markdown(
    """
    <div style="text-align:center; color:gray;">
        <b>PRAGYANAI</b><br>
        Agent-to-Agent Communication Platform<br>
        Streamlit + Python + A2A SDK + Render
    </div>
    """,
    unsafe_allow_html=True,
)
