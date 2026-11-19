
import streamlit as st
import requests
import json
from datetime import datetime, timezone
from urllib.parse import urlparse


# =====================================================
# 1. PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="PragyanAI - A2A Agent Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
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

.metric-card {
    background-color: rgba(128,128,128,0.08);
    padding: 18px;
    border-radius: 12px;
    border: 1px solid rgba(128,128,128,0.2);
}

.status-online {
    color: #16A34A;
    font-weight: bold;
}

.status-offline {
    color: #DC2626;
    font-weight: bold;
}

.small-text {
    font-size: 12px;
    color: gray;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# 3. HEADER
# =====================================================

st.markdown(
    '<div class="main-title">🤖 A2A Agent Dashboard</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Agent-to-Agent Protocol | Remote Agent Monitoring | '
    'Agent Discovery | JSON-RPC'
    '</div>',
    unsafe_allow_html=True
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

if "health_data" not in st.session_state:
    st.session_state.health_data = None

if "last_checked" not in st.session_state:
    st.session_state.last_checked = None


# =====================================================
# 5. SIDEBAR
# =====================================================

with st.sidebar:

    st.header("⚙️ Server Configuration")

    SERVER_URL = st.text_input(
        "A2A Server URL",
        value=st.session_state.server_url,
        help="Enter the public HTTPS URL of your A2A server"
    ).strip().rstrip("/")

    st.session_state.server_url = SERVER_URL

    HEALTH_URL = SERVER_URL + "/health"

    CARD_URL = (
        SERVER_URL
        + "/.well-known/agent-card.json"
    )

    st.caption("Health endpoint")
    st.code(HEALTH_URL)

    st.caption("Agent Card endpoint")
    st.code(CARD_URL)

    st.caption("JSON-RPC endpoint")
    st.code("/")

    refresh = st.button(
        "🔄 Refresh Agent Status",
        use_container_width=True
    )

    st.divider()

    st.subheader("Technology Stack")

    st.markdown("""
    - Python
    - Streamlit
    - Starlette / FastAPI
    - A2A Protocol
    - A2A Python SDK
    - JSON-RPC 2.0
    - HTTPX / Requests
    - Render Cloud
    """)

    st.divider()

    st.caption("PragyanAI | Agent Monitoring Platform")


# =====================================================
# 6. VALIDATE SERVER URL
# =====================================================

def validate_server_url(url):

    parsed = urlparse(url)

    if parsed.scheme not in ["http", "https"]:
        raise ValueError(
            "Server URL must begin with http:// or https://"
        )

    if not parsed.netloc:
        raise ValueError("Invalid server URL.")

    if parsed.username or parsed.password:
        raise ValueError(
            "Credentials should not be embedded in the URL."
        )

    return True


if not SERVER_URL:

    st.warning("Please configure your A2A Server URL.")

    st.stop()

try:

    validate_server_url(SERVER_URL)

except ValueError as error:

    st.error(str(error))

    st.stop()


# =====================================================
# 7. HTTP SESSION
# =====================================================

@st.cache_resource
def get_http_session():

    session = requests.Session()

    session.headers.update({
        "User-Agent": "PragyanAI-A2A-Dashboard/1.0"
    })

    return session


http = get_http_session()


# =====================================================
# 8. SERVER HEALTH CHECK
# =====================================================

def check_server_health(server_url):

    url = server_url + "/health"

    response = http.get(
        url,
        timeout=(10, 30)
    )

    response.raise_for_status()

    return response.json()


# =====================================================
# 9. AGENT CARD DISCOVERY
# =====================================================

@st.cache_data(ttl=30, show_spinner=False)
def discover_agent(server_url):

    card_url = (
        server_url
        + "/.well-known/agent-card.json"
    )

    response = requests.get(
        card_url,
        timeout=(10, 30),
        headers={
            "User-Agent": "PragyanAI-A2A-Dashboard/1.0"
        }
    )

    response.raise_for_status()

    card = response.json()

    if not isinstance(card, dict):
        raise ValueError(
            "Agent Card response is not a valid JSON object."
        )

    if not card.get("name"):
        raise ValueError(
            "Agent Card does not contain an agent name."
        )

    return card


# =====================================================
# 10. JSON-RPC ENDPOINT VALIDATION
# =====================================================

def get_jsonrpc_interfaces(agent):

    interfaces = agent.get(
        "supportedInterfaces",
        []
    )

    return [
        interface
        for interface in interfaces
        if interface.get(
            "protocolBinding", ""
        ).upper() == "JSONRPC"
    ]


def test_advertised_endpoint(interface):

    endpoint = interface.get("url", "").rstrip("/")

    if not endpoint:

        return {
            "success": False,
            "message": "JSON-RPC endpoint URL is missing."
        }

    parsed = urlparse(endpoint)

    if parsed.scheme not in ["http", "https"] or not parsed.netloc:

        return {
            "success": False,
            "message": "Invalid advertised endpoint URL."
        }

    # The health endpoint belongs to the service root.
    # A custom JSON-RPC path may differ from the root URL.

    health_url = (
        f"{parsed.scheme}://{parsed.netloc}/health"
    )

    try:

        response = requests.get(
            health_url,
            timeout=(10, 30)
        )

        response.raise_for_status()

        return {
            "success": True,
            "endpoint": endpoint,
            "health_url": health_url,
            "status_code": response.status_code,
            "health_data": response.json()
        }

    except requests.exceptions.RequestException as error:

        return {
            "success": False,
            "endpoint": endpoint,
            "health_url": health_url,
            "message": str(error)
        }


# =====================================================
# 11. REFRESH CACHE
# =====================================================

if refresh:

    discover_agent.clear()

    st.session_state.agent_card = None
    st.session_state.health_data = None

    st.rerun()


# =====================================================
# 12. SERVER STATUS
# =====================================================

st.subheader("🌐 Remote A2A Server Status")

server_online = False
agent = None
health = None

col1, col2 = st.columns([1, 2])

with col1:

    st.write("**Configured Server**")

    st.code(SERVER_URL)

with col2:

    st.write("**Current Monitoring Time**")

    st.write(
        datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    )


# =====================================================
# 13. HEALTH AND DISCOVERY
# =====================================================

try:

    with st.spinner("Checking A2A server..."):

        health = check_server_health(SERVER_URL)

    st.session_state.health_data = health

    server_online = (
        health.get("status", "").lower() == "healthy"
    )

except requests.exceptions.Timeout:

    st.error(
        "Health check timed out. "
        "Render server may be sleeping or unavailable."
    )

except requests.exceptions.ConnectionError:

    st.error(
        "Cannot establish a connection to the Render server."
    )

except requests.exceptions.HTTPError as error:

    st.error(
        f"Health endpoint returned HTTP error: {error}"
    )

except Exception as error:

    st.error(
        f"Health check error: {error}"
    )


# =====================================================
# 14. AGENT CARD DISCOVERY
# =====================================================

if server_online:

    try:

        with st.spinner("Discovering remote agent..."):

            agent = discover_agent(SERVER_URL)

        st.session_state.agent_card = agent

        st.session_state.last_checked = (
            datetime.now(timezone.utc)
            .strftime("%Y-%m-%d %H:%M:%S UTC")
        )

    except Exception as error:

        st.error(
            f"Agent Card discovery failed: {error}"
        )

        agent = None


# =====================================================
# 15. SERVER METRICS
# =====================================================

if server_online:

    st.success("🟢 A2A Agent Server is Online")

    agent = agent or {}

    skills = agent.get("skills", [])

    capabilities = agent.get(
        "capabilities",
        {}
    )

    interfaces = agent.get(
        "supportedInterfaces",
        []
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Server Status",
            "ONLINE"
        )

    with col2:

        st.metric(
            "Agent Skills",
            len(skills)
        )

    with col3:

        st.metric(
            "Agent Version",
            agent.get("version", "Unknown")
        )

    with col4:

        st.metric(
            "Streaming",
            "Enabled"
            if capabilities.get("streaming", False)
            else "Disabled"
        )

    st.divider()

    # =================================================
    # 16. AGENT INFORMATION
    # =================================================

    st.subheader("🤖 Agent Information")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("### Agent Details")

        st.write(
            "**Name:**",
            agent.get("name", "Unknown Agent")
        )

        st.write(
            "**Description:**",
            agent.get(
                "description",
                "No description available"
            )
        )

        st.write(
            "**Version:**",
            agent.get("version", "Unknown")
        )

        st.write(
            "**Server URL:**",
            SERVER_URL
        )

        st.write(
            "**Protocol Version:**",
            agent.get("protocolVersion", "Unknown")
        )

    with col2:

        st.markdown("### Agent Capabilities")

        if capabilities:

            st.json(capabilities)

        else:

            st.info("No capabilities published.")


    # =================================================
    # 17. AGENT SKILLS
    # =================================================

    st.divider()

    st.subheader("🧠 Available Agent Skills")

    if skills:

        for index, skill in enumerate(skills, 1):

            with st.expander(
                f"Skill {index}: "
                f"{skill.get('name', 'Unnamed')}",
                expanded=False
            ):

                st.write(
                    "**Skill ID:**",
                    skill.get("id", "N/A")
                )

                st.write(
                    "**Name:**",
                    skill.get("name", "N/A")
                )

                st.write(
                    "**Description:**",
                    skill.get("description", "N/A")
                )

                st.write(
                    "**Tags:**",
                    ", ".join(skill.get("tags", []))
                )

                examples = skill.get(
                    "examples", []
                )

                if examples:

                    st.write("**Examples:**")

                    for example in examples:

                        st.write(f"- {example}")

                st.write(
                    "**Input Modes:**",
                    skill.get("inputModes", [])
                )

                st.write(
                    "**Output Modes:**",
                    skill.get("outputModes", [])
                )

    else:

        st.info("No skills registered.")


    # =================================================
    # 18. A2A PROTOCOL INFORMATION
    # =================================================

    st.divider()

    st.subheader("🔗 A2A Protocol Information")

    if interfaces:

        for index, interface in enumerate(
            interfaces, 1
        ):

            with st.expander(
                f"Interface {index}: "
                f"{interface.get('protocolBinding', 'Unknown')}",
                expanded=True
            ):

                col1, col2 = st.columns(2)

                with col1:

                    st.write(
                        "**Protocol Binding:**",
                        interface.get(
                            "protocolBinding", "N/A"
                        )
                    )

                    st.write(
                        "**Protocol Version:**",
                        interface.get(
                            "protocolVersion", "N/A"
                        )
                    )

                with col2:

                    st.write(
                        "**Endpoint:**"
                    )

                    st.code(
                        interface.get("url", "N/A")
                    )

    else:

        st.warning(
            "No supported interfaces found in Agent Card."
        )


    # =================================================
    # 19. JSON-RPC ENDPOINT DIAGNOSTICS
    # =================================================

    st.divider()

    st.subheader("🔌 JSON-RPC Endpoint Diagnostics")

    jsonrpc_interfaces = get_jsonrpc_interfaces(
        agent
    )

    if jsonrpc_interfaces:

        for interface in jsonrpc_interfaces:

            endpoint = interface.get("url", "")

            st.write(
                "**Advertised JSON-RPC URL:**"
            )

            st.code(endpoint)

            if endpoint.rstrip("/") != SERVER_URL.rstrip("/"):

                st.warning(
                    "The advertised JSON-RPC URL differs "
                    "from the configured server URL. "
                    "Verify that it is intentional and reachable."
                )

            if st.button(
                "Test Advertised Endpoint",
                key=f"test_endpoint_{endpoint}"
            ):

                with st.spinner(
                    "Testing advertised service..."
                ):

                    result = test_advertised_endpoint(
                        interface
                    )

                if result["success"]:

                    st.success(
                        "Advertised endpoint service is reachable."
                    )

                    st.json(result["health_data"])

                else:

                    st.error(
                        "Advertised endpoint health check failed."
                    )

                    st.code(
                        result.get("message", "Unknown error")
                    )

    else:

        st.error(
            "No JSON-RPC interface found. "
            "The client cannot use JSON-RPC until the Agent "
            "Card advertises a supported interface."
        )


    # =================================================
    # 20. INPUT AND OUTPUT MODES
    # =================================================

    st.divider()

    st.subheader("📨 Supported Input / Output")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("**Input Modes**")

        for mode in agent.get(
            "defaultInputModes", []
        ):

            st.success(mode)

    with col2:

        st.markdown("**Output Modes**")

        for mode in agent.get(
            "defaultOutputModes", []
        ):

            st.info(mode)


    # =================================================
    # 21. COMPLETE AGENT CARD
    # =================================================

    st.divider()

    st.subheader("📄 Raw Agent Card JSON")

    with st.expander(
        "View Complete Agent Card",
        expanded=False
    ):

        st.json(agent)

        st.download_button(
            label="⬇️ Download Agent Card",
            data=json.dumps(
                agent,
                indent=4
            ),
            file_name="agent_card.json",
            mime="application/json"
        )


    # =================================================
    # 22. MONITORING INFORMATION
    # =================================================

    st.divider()

    st.subheader("🕒 Monitoring Information")

    col1, col2 = st.columns(2)

    with col1:

        st.write(
            "**Last Successful Discovery:**",
            st.session_state.last_checked or "N/A"
        )

    with col2:

        st.write("**Agent Card Endpoint**")

        st.code(
            SERVER_URL
            + "/.well-known/agent-card.json"
        )


else:

    st.error("🔴 A2A Server is Unavailable")

    st.warning(
        "Agent information is unavailable. "
        "Check Render deployment, server health and "
        "the configured URL."
    )


# =====================================================
# 23. FOOTER
# =====================================================

st.divider()

st.markdown(
    """
    <div style="text-align:center; color:gray;">
        <b>PRAGYANAI</b><br>
        Agent-to-Agent Communication Platform<br>
        Built using Python + Streamlit + A2A Protocol
    </div>
    """,
    unsafe_allow_html=True
)

