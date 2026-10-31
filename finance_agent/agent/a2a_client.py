"""A2A client for the research agent."""

import json
import os
from urllib.request import Request, urlopen
from uuid import uuid4

def fetch_research_agent_card() -> dict:
    """Fetch the research agent's public Agent Card."""
    base_url = os.getenv(
        "RESEARCH_A2A_URL",
        "http://127.0.0.1:8001",
    ).rstrip("/")

    # §8.2: Discover the Agent Card at the well-known URI.
    request = Request(
        f"{base_url}/.well-known/agent-card.json",
        headers={"Accept": "application/json"},
    )
    with urlopen(request, timeout=5) as response:
        return json.load(response)

def select_research_interface(card: dict) -> dict:
    """Select the first HTTP+JSON v1.0 interface in the Agent Card."""

    # §8.3.2: Read supportedInterfaces in preference order and
    # choose the first transport this client supports.
    for interface in card.get("supportedInterfaces", []):
        if (
            interface.get("protocolBinding") == "HTTP+JSON"
            and interface.get("protocolVersion") == "1.0"
            and interface.get("url")
        ):
            return interface

    raise ValueError(
        "Research agent does not advertise an HTTP+JSON v1.0 interface."
    )

def build_research_request(question: str, interface: dict) -> dict:
    question = question.strip()
    if not question:
        raise ValueError("Research question is empty.")

    # §3.2.1 SendMessageRequest: include the required message.
    # §4.1.4 Message: give the client message its own ID and USER role.
    # §4.1.6 Part: send the question as text/plain content.
    
    request = {
        "message": {
            "messageId": str(uuid4()),
            "role": "ROLE_USER",
            "parts": [
                {"text": question, "mediaType": "text/plain"}
            ],
        },
    }

    # §8.3.2: if the selected interface declares a tenant,
    # send that exact tenant value with every request.
    if interface.get("tenant"):
        request["tenant"] = interface["tenant"]

    return request

def send_research_message(question: str) -> dict:
    card = fetch_research_agent_card()
    interface = select_research_interface(card)
    payload = build_research_request(question, interface)

    # §11.3.1: Send Message uses POST /message:send.
    endpoint = interface["url"].rstrip("/") + "/message:send"

    # §11.1 and §11.4: send the request as A2A JSON.
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/a2a+json",
            "Accept": "application/a2a+json",
            "A2A-Version": interface["protocolVersion"],
        },
        method="POST",
    )

    with urlopen(request, timeout=90) as response:
        return json.load(response)

def extract_research_answer(result: dict) -> str:
    # §3.1.1: this client expects the direct Message response
    # chosen for our research server.
    message = result.get("message")
    if not isinstance(message, dict):
        raise ValueError("Research agent did not return a direct Message.")

    # §4.1.4 Message; §4.1.6 Part:
    # A Message can contain multiple parts, so collect its text parts.
    parts = message.get("parts", [])
    answer = "\n".join(
        part["text"]
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ).strip()

    if not answer:
        raise ValueError("Research agent returned no text answer.")

    return answer

from urllib.error import HTTPError, URLError


def research_web(question: str) -> dict:
    """Research a public company or market question using the research agent.

    Args:
        question: The public information to research.
    """
    try:
        result = send_research_message(question)
        answer = extract_research_answer(result)
        return {"status": "success", "answer": answer}

    except HTTPError as exc:
        try:
            error = json.load(exc).get("error", {})
            detail = error.get("message", str(exc))
        except (ValueError, OSError):
            detail = str(exc)
        return {"status": "error", "message": f"Research agent: {detail}"}

    except (URLError, TimeoutError, ValueError, OSError) as exc:
        return {"status": "error", "message": str(exc)}