"""A2A SDK client for the research agent.

A2A specification: https://a2a-protocol.org/latest/specification/

Implemented sections:
- §3.1.1, §3.2.1: Send Message and SendMessageRequest
- §3.4.1, §3.4.3: contextId and Context Continuity
- §4.1.4–4.1.6: Message, Role, and Part
- §8.2, §8.3.2: Agent Card discovery and protocol selection
- §11.3.1: HTTP+JSON POST /message:send
"""

import os
from uuid import uuid4

import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import Message, Part, Role, SendMessageRequest
from a2a.utils.errors import A2AError
from google.adk.tools import ToolContext

_CONTEXT_KEY = "research_a2a_context_id"


async def research_web(question: str, tool_context: ToolContext) -> dict:
    """Research a public company or market question using the research agent.

    Args:
        question: The public information to research.
    """
    question = question.strip()
    if not question:
        return {"status": "error", "message": "Research question is empty."}

    base_url = os.getenv(
        "RESEARCH_A2A_URL", "http://127.0.0.1:8001"
    ).rstrip("/")

    # ADK session state keeps the A2A context separate for each Northstar chat.
    # A2A §3.4.3, Context Continuity: Include the server-issued contextId in subsequent Messages
    # to continue the same conversational context.
    context_id = tool_context.state.get(_CONTEXT_KEY)

    # A2A §4.1.4–4.1.6: each request is a new Message with a unique
    # messageId, ROLE_USER, and a text/plain Part.
    message = Message(
        message_id=str(uuid4()),
        role=Role.ROLE_USER,
        parts=[Part(text=question, media_type="text/plain")],
    )
    if context_id:
        message.context_id = context_id

    try:
        async with httpx.AsyncClient(timeout=90.0) as http:
            # A2A §8.2, §8.3.2: discover the Agent Card and select
            # its HTTP+JSON interface.
            factory = ClientFactory(
                ClientConfig(
                    httpx_client=http,
                    streaming=False,
                    supported_protocol_bindings=["HTTP+JSON"],
                )
            )
            client = await factory.create_from_url(base_url)

            # A2A §3.1.1, §3.2.1, §11.3.1: send a
            # SendMessageRequest using POST /message:send.
            # The SDK exposes the reply through an async iterator even
            # when the HTTP operation is non-streaming.
            reply = None
            async for event in client.send_message(
                SendMessageRequest(message=message)
            ):
                if event.HasField("message"):
                    reply = event.message
                    break

        # A2A §3.1.1: this research server returns a direct Message,
        # rather than a Task.
        if reply is None:
            raise ValueError("Research agent did not return a Message.")

        # A2A §3.4.1: a server Message includes a contextId.
        if not reply.context_id:
            raise ValueError("Research agent returned no contextId.")
        if context_id and reply.context_id != context_id:
            raise ValueError("Research agent changed the contextId.")

        # A2A §4.1.6: collect text from the reply's Parts.
        answer = "\n".join(
            part.text
            for part in reply.parts
            if part.WhichOneof("content") == "text"
        ).strip()
        if not answer:
            raise ValueError("Research agent returned no text answer.")

        # Save the server-issued ID for the next research_web call
        # in this ADK chat session.
        tool_context.state[_CONTEXT_KEY] = reply.context_id
        return {"status": "success", "answer": answer}

    except (A2AError, httpx.HTTPError, ValueError) as exc:
        return {"status": "error", "message": str(exc)}