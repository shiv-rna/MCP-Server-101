import json
import os

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import httpx
from bs4 import BeautifulSoup

load_dotenv()

mcp = FastMCP("docs")

USER_AGENT = "docs-app/1.0"
SERPER_URL = "https://google.serper.dev/search"

docs_urls = {
    "langchain": "python.langchain.com/docs",
    "llama-index": "docs.llamaindex.ai/en/stable",
    "openai": "platform.openai.com/docs",
}

async def search_web(query: str) -> dict | None:
    """
    Perform a web search using the Serper.dev API for a given query.

    Args:
        query (str): The search query string.

    Returns:
        dict | None: A dictionary containing the search results (up to 2),
        or an empty result if the request fails or times out.
    """
    payload = json.dumps({"q": query, "num": 2})

    headers = {
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url=SERPER_URL, headers=headers, data=payload, timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            return{"organic": []}


async def fetch_url(url: str) -> str | None:
    """
    Fetch the content of a webpage and extract its visible text.

    Args:
        url (str): The URL of the webpage to fetch.

    Returns:
        str | None: The visible text content of the page, or an error message
        in case of a timeout.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout= 30.0)
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text()
            return text
        except httpx.TimeoutException:
            return "Timeout error"


@mcp.tool()
async def get_docs(query: str, library: str):
    """
    Search the documentation for a given query within a specific library.

    This tool uses web search constrained to the documentation domain of the
    selected library and extracts visible textual content from the top results.

    Args:
        query (str): The documentation query (e.g., 'Chroma DB').
        library (str): The library name ('langchain', 'openai', or 'llama-index').

    Returns:
        str: Extracted text content from the matched documentation page,
        or a message indicating no results were found.

    Raises:
        ValueError: If the specified library is not supported.
    """
    # Function docstring is important as it explains the LLM about the mcp tool
    if library not in docs_urls:
        raise ValueError(f"Library {library} is not supported")

    query = f"site:{docs_urls[library]} {query}"
    results = await search_web(query)

    if len(results["organic"]) == 0:
        return "No results found"

    text = ""
    for result in results["organic"]:
        text += await fetch_url(result["link"])
        return text

if __name__ == "__main__":
    mcp.run(transport="stdio")
