import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = "88543daffd0ee6fbe5f6f8d07eac30ccc66d480b"
        # url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}"
        url = f"https://api.nomics.com/v1/currencies/ticker?key={api_key}&ids={urllib.parse.quote_plus(symbol)}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote[0]["name"],
            "price": float(quote[0]["price"]),
            "1d": quote[0]["1d"]["price_change_pct"],
            "symbol": quote[0]["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def backgroundDB():
    api_key = "88543daffd0ee6fbe5f6f8d07eac30ccc66d480b"

    url = f"https://api.nomics.com/v1/currencies/ticker?key={api_key}&ids=BTC,ETH,USDT,ADA,XRP,DOGE,DOT,ICP,BCH,USDC,UNI,LTC,LINK,XLM,SOL,MATIC,ETC,VET,THETA,TRX,FIL,EOS,XMR"
    response = requests.get(url)
    quote = response.json()
    for i in quote:
        try:
            symbol = i['id']
            price = float(i['price'])
            name = i['name']
            change = float(i['1d']['price_change_pct'])
            db.execute("INSERT INTO nomics (symbol, price, name, change) VALUES (?, ?, ?, ?)",
                                       symbol, price, name, change)
        except:
            db.execute("INSERT INTO nomics (symbol, price, name, change) VALUES (?, ?, ?, ?)",
                                   symbol, price, name, 0)
    return True
