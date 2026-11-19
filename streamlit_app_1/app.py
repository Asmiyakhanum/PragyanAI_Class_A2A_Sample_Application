
import streamlit as st
import requests
import json
from datetime import datetime, timezone


# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="PragyanAI - A2A Agent Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==========================================
# 2. CUSTOM CSS
# ==========================================

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

</style>
""", unsafe_allow_html=True)


# ==========================================
# 3. HEADER
# ==========================================

st.markdown(
    '<div class="main-title">🤖 A2A Agent Dashboard</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Agent-to-Agent Protocol | Remote Agent Monitoring'
    '</div>',
    unsafe_allow_html=True
)

st.divider()


# ==========================================
# 4. SERVER CONFIGURATION
# ==========================================

DEFAULT_URL = "https://your-a2a-server.onrender.com"

try:
    SERVER_URL = st.secrets["A2A_SERVER_URL"]
except Exception:
    SERVER_URL = DEFAULT_URL


with st.sidebar:

    st.header("⚙️ Server Configuration")

    SERVER_URL = st.text_input(
        "A2A Server URL",
        value=SERVER_URL,
        help="Enter the public HTTPS URL of your A2A server"
    )

    SERVER_URL = SERVER_URL.strip().rstrip("/")

    st.caption("Agent Card endpoint")

    st.code(
        SERVER_URL + "/.well-known/agent-card.json"
        if SERVER_URL else "Not configured"
    )

    refresh = st.button(
        "🔄 Refresh Agent Status",
        use_container_width=True
    )

    st.divider()

    st.subheader("Technology Stack")

    st.markdown("""
    - Python
    - Streamlit
    - FastAPI
    - A2A Protocol
    - A2A Python SDK
    - JSON-RPC
    """)


# ==========================================
# 5. AGENT CARD DISCOVERY
# ==========================================

@st.cache_data(ttl=30)
def discover_agent(server_url):

    card_url = (
        server_url.rstrip("/")
        + "/.well-known/agent-card.json"
    )

    response = requests.get(
        card_url,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


if refresh:
    st.cache_data.clear()


# ==========================================
# 6. CHECK SERVER STATUS
# ==========================================

st.subheader("🌐 Remote A2A Server Status")

if not SERVER_URL:

    st.warning("Please configure your A2A Server URL.")

    st.stop()


try:

    with st.spinner("Connecting to A2A Server..."):

        agent = discover_agent(SERVER_URL)

    server_online = True

    st.success("🟢 A2A Agent Server is Online")

except requests.exceptions.Timeout:

    server_online = False
    agent = None

    st.error("Connection timeout. Server took too long to respond.")

except requests.exceptions.ConnectionError:

    server_online = False
    agent = None

    st.error("Unable to connect to the A2A Server.")

except requests.exceptions.HTTPError as error:

    server_online = False
    agent = None

    st.error(f"HTTP Error: {error}")

except Exception as error:

    server_online = False
    agent = None

    st.error(f"Unexpected error: {error}")


# ==========================================
# 7. AGENT OVERVIEW
# ==========================================

if server_online:

    st.divider()

    st.subheader("📊 Agent Overview")

    agent_name = agent.get(
        "name",
        "Unknown Agent"
    )

    description = agent.get(
        "description",
        "No description available"
    )

    version = agent.get(
        "version",
        "Unknown"
    )

    skills = agent.get(
        "skills",
        []
    )

    capabilities = agent.get(
        "capabilities",
        {}
    )

    interfaces = agent.get(
        "supportedInterfaces",
        []
    )

    # Metrics

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
            version
        )

    with col4:
        st.metric(
            "Streaming",
            "Enabled" if capabilities.get(
                "streaming", False
            ) else "Disabled"
        )


    # ======================================
    # 8. AGENT INFORMATION
    # ======================================

    st.divider()

    st.subheader("🤖 Agent Information")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("### Agent Details")

        st.write("**Name:**", agent_name)

        st.write(
            "**Description:**",
            description
        )

        st.write(
            "**Version:**",
            version
        )

        st.write(
            "**URL:**",
            SERVER_URL
        )

    with col2:

        st.markdown("### Agent Capabilities")

        if capabilities:

            st.json(capabilities)

        else:

            st.info("No capabilities published.")


    # ======================================
    # 9. AGENT SKILLS
    # ======================================

    st.divider()

    st.subheader("🧠 Available Agent Skills")

    if skills:

        for index, skill in enumerate(skills, 1):

            with st.expander(
                f"Skill {index}: {skill.get('name', 'Unnamed')}",
                expanded=True
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

                examples = skill.get("examples", [])

                if examples:

                    st.write("**Examples:**")

                    for example in examples:
                        st.write(f"- {example}")

    else:

        st.info("No skills registered.")


    # ======================================
    # 10. PROTOCOL INFORMATION
    # ======================================

    st.divider()

    st.subheader("🔗 A2A Protocol Information")

    if interfaces:

        for interface in interfaces:

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
                    "**Endpoint:**",
                    interface.get("url", "N/A")
                )

    else:

        st.info(
            "No supported interfaces found in Agent Card."
        )


    # ======================================
    # 11. INPUT AND OUTPUT MODES
    # ======================================

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


    # ======================================
    # 12. RAW AGENT CARD
    # ======================================

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


    # ======================================
    # 13. SERVER INFORMATION
    # ======================================

    st.divider()

    st.subheader("🕒 Monitoring Information")

    col1, col2 = st.columns(2)

    with col1:

        st.write(
            "**Last Checked:**",
            datetime.now(
                timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S UTC")
        )

    with col2:

        st.write(
            "**Agent Card Endpoint:**"
        )

        st.code(
            SERVER_URL
            + "/.well-known/agent-card.json"
        )


else:

    st.warning(
        "Agent information is unavailable. "
        "Check whether the A2A backend is running "
        "and the Agent Card endpoint is accessible."
    )


# ==========================================
# 14. FOOTER
# ==========================================

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
