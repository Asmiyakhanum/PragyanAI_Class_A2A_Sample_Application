
import streamlit as st
import asyncio
import httpx

from a2a.client import (
    A2ACardResolver,
    ClientConfig,
    create_client
)

from a2a.helpers import new_text_message

from a2a.types import (
    Role,
    SendMessageRequest
)

st.set_page_config(
    page_title="A2A Client",
    page_icon="🚀"
)

st.title("🚀 A2A Remote Agent Client")

SERVER_URL = st.secrets["A2A_SERVER_URL"]

@st.cache_resource
def get_agent_card():
    async def discover():
        async with httpx.AsyncClient(
            timeout=30
        ) as http_client:

            resolver = A2ACardResolver(
                httpx_client=http_client,
                base_url=SERVER_URL
            )

            return await resolver.get_agent_card()

    return asyncio.run(discover())


async def send_message(card, question):

    client = await create_client(
        agent=card,
        client_config=ClientConfig(
            streaming=False
        )
    )

    message = new_text_message(
        question,
        role=Role.ROLE_USER
    )

    request = SendMessageRequest(
        message=message
    )

    output = []

    try:
        async for result in client.send_message(request):

            if hasattr(result, "artifacts"):

                for artifact in result.artifacts:
                    for part in artifact.parts:
                        if part.root.kind == "text":
                            output.append(part.root.text)

    finally:
        await client.close()

    return "\n".join(output)


if st.button("Discover Remote Agent"):

    try:
        card = get_agent_card()

        st.success("Agent discovered!")

        st.write("Agent:", card.name)
        st.write("Description:", card.description)

    except Exception as e:
        st.error(str(e))


question = st.text_area(
    "Enter your message",
    "Hello from Streamlit A2A Client!"
)

if st.button("Send A2A Request"):

    try:
        card = get_agent_card()

        with st.spinner("Remote agent processing..."):

            result = asyncio.run(
                send_message(card, question)
            )

        st.success("Response received!")
        st.write(result)

    except Exception as e:
        st.error(f"A2A Error: {e}")
