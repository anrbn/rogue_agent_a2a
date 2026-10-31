import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _request(path: str, payload: dict | None = None) -> dict:
    base_url = os.environ.get("FINANCE_API_URL", "http://127.0.0.1:8000").rstrip("/")
    token = os.environ.get("FINANCE_API_TOKEN", "northstar-local-dev-token")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        base_url + path,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST" if body is not None else "GET",
    )
    try:
        with urlopen(request, timeout=5) as response:
            return json.load(response)
    except HTTPError as exc:
        try:
            message = json.load(exc).get("error", "API request failed")
        except (ValueError, OSError):
            message = "API request failed"
        return {"status": "error", "message": message}
    except (URLError, TimeoutError):
        return {"status": "error", "message": "Finance API unavailable. Start the web server and try again."}


def get_profile() -> dict:
    """Get the account holder name and available cash from the finance API."""
    return _request("/api/agent/profile")


def get_portfolio() -> dict:
    """Get cash, holdings, portfolio value, and stock quotes from the finance API."""
    return _request("/api/agent/portfolio")


def buy_stock(symbol: str, quantity: int) -> dict:
    """Buy a positive whole number of shares of a watchlist symbol.

    Args:
        symbol: Stock ticker, such as NVDA.
        quantity: Number of whole shares to buy.
    """
    return _request("/api/agent/buy", {"symbol": symbol, "quantity": quantity})


def sell_stock(symbol: str, quantity: int) -> dict:
    """Sell a positive whole number of owned shares.

    Args:
        symbol: Stock ticker, such as NVDA.
        quantity: Number of whole shares to sell.
    """
    return _request("/api/agent/sell", {"symbol": symbol, "quantity": quantity})
