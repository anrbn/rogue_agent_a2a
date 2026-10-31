r"""A clean terminal chat for the Northstar ADK agent.

Run from the agent folder: .\.venv\Scripts\python.exe chat.py
"""

import asyncio
import logging
import os
import sys
import uuid
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=r"\[EXPERIMENTAL\].*", category=UserWarning)
logging.getLogger("google.adk").setLevel(logging.ERROR)

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(Path(__file__).with_name(".env"))
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")

from agent.agent import root_agent

console = Console()


async def ask(runner: Runner, session_id: str, message: str) -> str:
    """Return the agent's final answer for one message."""
    content = types.Content(role="user", parts=[types.Part(text=message)])
    answer = ""
    async for event in runner.run_async(user_id="local_user", session_id=session_id, new_message=content):

        for call in event.get_function_calls():
            console.print(f"[dim]Tool called: {call.name} args={call.args!r}[/]")

        for response in event.get_function_responses():
            console.print(f"[dim]Tool finished: {response.name}[/]")
            if response.name == "research_web":
                console.print(f"[dim]Research result: {response.response!r}[/]")

        if event.is_final_response() and event.content:
            answer = "\n".join(part.text for part in event.content.parts if part.text)
    return answer or "I couldn't produce a response. Please try again."


async def main() -> int:
    if not os.environ.get("GOOGLE_API_KEY"):
        console.print("[bold red]Missing GOOGLE_API_KEY.[/]")
        console.print("Add it to [cyan]agent/.env[/] before starting chat.")
        return 1

    runner = Runner(
        agent=root_agent,
        app_name="northstar_cli",
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    session_id = uuid.uuid4().hex

    console.print(Panel.fit(
        "[bold bright_cyan]NORTHSTAR[/]\n[dim]Stock portfolio assistant[/]",
        border_style="bright_cyan",
    ))
    console.print("[dim]Ask about your account or portfolio, or request a trade. Type /help for commands.[/]")

    try:
        while True:
            try:
                message = (await asyncio.to_thread(
                    console.input, "\n[bold bright_blue]You >[/] "
                )).strip()
            except EOFError:
                console.print("\n[dim]Goodbye.[/]")
                return 0

            if not message:
                continue
            if message.lower() in {"/exit", "/quit", "exit", "quit"}:
                console.print("[dim]Goodbye.[/]")
                return 0
            if message.lower() == "/help":
                console.print("[cyan]/new[/] New chat  [cyan]/help[/] Commands  [cyan]/exit[/] Quit")
                continue
            if message.lower() == "/new":
                session_id = uuid.uuid4().hex
                console.print("[dim]Started a new chat. Your portfolio is unchanged.[/]")
                continue

            try:
                with console.status("[green]Northstar is thinking...[/]", spinner="dots"):
                    reply = await ask(runner, session_id, message)
                console.print(Panel(Markdown(reply), title="Northstar", border_style="green"))
            except Exception as exc:
                console.print(Panel(str(exc), title="Request failed", border_style="red"))
    finally:
        await runner.close()


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye.[/]")
