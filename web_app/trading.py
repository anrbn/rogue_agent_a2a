"""Persistent paper-trading operations shared by the web UI and future agent."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("FINANCE_DB_PATH", Path(__file__).with_name("trading.db")))
STOCKS = [
    {"symbol": "NVDA", "name": "NVIDIA", "price_cents": 13742, "change": 2.84},
    {"symbol": "AAPL", "name": "Apple", "price_cents": 23218, "change": 1.12},
    {"symbol": "MSFT", "name": "Microsoft", "price_cents": 41875, "change": -0.46},
    {"symbol": "GOOGL", "name": "Alphabet", "price_cents": 17623, "change": 0.89},
    {"symbol": "AMZN", "name": "Amazon", "price_cents": 19456, "change": 1.37},
    {"symbol": "TSLA", "name": "Tesla", "price_cents": 24131, "change": -1.62},
]
QUOTES = {stock["symbol"]: stock for stock in STOCKS}


class TradeError(ValueError):
    """A trade failed validation."""


@contextmanager
def _connect():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS account (id INTEGER PRIMARY KEY, name TEXT NOT NULL, cash_cents INTEGER NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS positions (symbol TEXT PRIMARY KEY, quantity INTEGER NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY, side TEXT NOT NULL, symbol TEXT NOT NULL, quantity INTEGER NOT NULL, price_cents INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        if not db.execute("SELECT 1 FROM account WHERE id = 1").fetchone():
            db.execute("INSERT INTO account VALUES (1, 'Demo Investor', 1000000)")
            db.executemany("INSERT INTO positions VALUES (?, ?)", [("NVDA", 4), ("AAPL", 2), ("MSFT", 1)])


def get_profile():
    """Return the demo account profile and available cash."""
    init_db()
    with _connect() as db:
        row = db.execute("SELECT name, cash_cents FROM account WHERE id = 1").fetchone()
    return {"name": row["name"], "cash": row["cash_cents"] / 100, "account_type": "paper"}


def get_portfolio():
    """Return current positions and their value at fixed demo prices."""
    init_db()
    with _connect() as db:
        positions = {row["symbol"]: row["quantity"] for row in db.execute("SELECT symbol, quantity FROM positions WHERE quantity > 0")}
        cash_cents = db.execute("SELECT cash_cents FROM account WHERE id = 1").fetchone()[0]
    invested_cents = sum(QUOTES[symbol]["price_cents"] * quantity for symbol, quantity in positions.items())
    return {"holdings": positions, "cash": cash_cents / 100, "invested": invested_cents / 100, "total_value": (cash_cents + invested_cents) / 100}


def _trade(side, symbol, quantity):
    init_db()
    if not isinstance(symbol, str):
        raise TradeError("Choose a valid stock symbol.")
    symbol = symbol.upper()
    if symbol not in QUOTES:
        raise TradeError("Choose a stock from the watchlist.")
    if type(quantity) is not int or quantity <= 0:
        raise TradeError("Enter a positive whole number of shares.")
    if quantity > 1_000_000:
        raise TradeError("Order is too large.")
    cost_cents = QUOTES[symbol]["price_cents"] * quantity
    with _connect() as db:
        db.execute("BEGIN IMMEDIATE")
        cash_cents = db.execute("SELECT cash_cents FROM account WHERE id = 1").fetchone()[0]
        row = db.execute("SELECT quantity FROM positions WHERE symbol = ?", (symbol,)).fetchone()
        held = row[0] if row else 0
        if side == "buy":
            if cost_cents > cash_cents:
                raise TradeError("Not enough buying power.")
            db.execute("UPDATE account SET cash_cents = cash_cents - ? WHERE id = 1", (cost_cents,))
            db.execute("INSERT INTO positions(symbol, quantity) VALUES (?, ?) ON CONFLICT(symbol) DO UPDATE SET quantity = quantity + excluded.quantity", (symbol, quantity))
        else:
            if quantity > held:
                raise TradeError("Not enough shares to sell.")
            db.execute("UPDATE account SET cash_cents = cash_cents + ? WHERE id = 1", (cost_cents,))
            db.execute("UPDATE positions SET quantity = quantity - ? WHERE symbol = ?", (quantity, symbol))
        db.execute("INSERT INTO trades(side, symbol, quantity, price_cents) VALUES (?, ?, ?, ?)", (side, symbol, quantity, QUOTES[symbol]["price_cents"]))
    return {"side": side, "symbol": symbol, "quantity": quantity, "price": QUOTES[symbol]["price_cents"] / 100, "total": cost_cents / 100, "status": "filled", "account_type": "paper"}


def buy_stock(symbol: str, quantity: int):
    """Buy whole shares of a watchlist stock in the paper account."""
    return _trade("buy", symbol, quantity)


def sell_stock(symbol: str, quantity: int):
    """Sell owned whole shares of a watchlist stock in the paper account."""
    return _trade("sell", symbol, quantity)


def get_state():
    return {"stocks": [{"symbol": s["symbol"], "name": s["name"], "price": s["price_cents"] / 100, "change": s["change"]} for s in STOCKS], "profile": get_profile(), "portfolio": get_portfolio()}
