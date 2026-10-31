"""A small LangChain agent using Gemini's built-in Google Search tool."""

import argparse
import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


def build_agent():
    model = ChatGoogleGenerativeAI(
        model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
        vertexai=False,
    )
    return model.bind_tools([{"google_search": {}}])


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Ask a web-searching agent a question.")
    parser.add_argument("question", nargs="*", help="Question to answer")
    args = parser.parse_args()
    question = " ".join(args.question).strip() or input("Question: ").strip()
    if not question:
        parser.error("Please enter a question.")

    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        parser.error("Set GOOGLE_API_KEY in your environment or .env file.")

    response = build_agent().invoke(
        "Search the web for this question and answer briefly using what you find. "
        "If the search does not support an answer, say so. "
        "Return only the answer, without a sources section. Question: " + question
    )
    answer = "\n".join(
        block["text"] for block in response.content_blocks if block.get("type") == "text"
    )
    print(answer or str(response.content))


if __name__ == "__main__":
    main()
