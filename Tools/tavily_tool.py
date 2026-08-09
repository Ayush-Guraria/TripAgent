from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()


def get_tavily_client():
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise EnvironmentError("TAVILY_API_KEY environment variable is not set. Please set it in .env or the shell.")
    return TavilyClient(api_key=api_key)


def tavily_search(query):
    client = get_tavily_client()
    response = client.search(
        query=query,
        max_results=5,
    )

    results = None
    if isinstance(response, dict):
        results = response.get("results")
    else:
        results = getattr(response, "results", None)

    if results is None:
        raise ValueError("Unexpected Tavily search response format; expected a dict or object with results.")

    result = []

    for i, r in enumerate(results):
        title = r.get("title", "No title")
        description = r.get("description", "No description")
        url = r.get("url", "No URL")
        snippet = r.get("context", "No snippet").strip()

        if len(snippet) > 300:
            snippet = snippet[:300].rsplit(" ", 1)[0] + "..."

        result.append(f"{i+1}. **{title}**\n{description}\nURL: {url}\nSnippet: {snippet}\n")

    return "\n\n".join(result)
        