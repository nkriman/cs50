import os
import time
import requests
from flask import redirect, render_template, request, session
import json
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# Update Nomics database in the background
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


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Update Nomics database in the background
    bg = backgroundDB()
    # Display table with current user stocks, numbers of shares, current price, total vale of holding
    portfolio = db.execute("SELECT * from portfolio where user_id=?", session["user_id"])
    # update price of shares in portfolio
    for i in portfolio:
        t1 = db.execute("SELECT max(t) as t from nomics WHERE symbol =?", i["symbol"])
        t2 = t1[0]["t"]
        p1 = db.execute("SELECT price, change from nomics WHERE symbol =? and t=?", i["symbol"], t2)
        new_price = p1[0]["price"]
        change = round(p1[0]["change"] * 100 , 2)
        db.execute("UPDATE portfolio SET price=?, change=? WHERE user_id =? and symbol =?", new_price, change, session["user_id"], i["symbol"])
    portfolio = db.execute("SELECT * from portfolio where user_id=?", session["user_id"])
    rows = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
    # Display users current cash balance
    if len(rows) != 1:
        return apology("User session error", 403)
    user_cash = rows[0]["cash"]
    # Calculate total portfolio value
    rows2 = db.execute("SELECT SUM(price*quantity) as value from portfolio where user_id=?", session["user_id"])
    #if len(rows2) != 1:
        # return apology("User session error", 403)
    if rows2[0]["value"] is None:
        pvalue = 0
    else:
        pvalue = rows2[0]["value"]
    return render_template("index.html", portfolio=portfolio, cash=int(user_cash), value=int(pvalue))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # 3rd

    # IF POST: purchase STOCK if user can afford it (query DB, compare price x shares), add tables
    if request.method == "POST":
        quote_result = lookup(request.form.get("symbol"))
        if quote_result is None:
            return apology("symbol does not exist", 403)
        else:
            # return render_template("quote_result.html", quote_result=quote_result)
            # get name
            name = quote_result["name"]
            # get symbol price
            price = quote_result["price"]
            # get quantity
            quantity = request.form.get("shares")
            # calculate price x quantity
            pxq = price * float(quantity)
            # query user cash
            rows = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
            if len(rows) != 1:
                return apology("User session error", 403)
            user_cash = rows[0]["cash"]
            # if pxq > cash : error
            if pxq > float(user_cash):
                return apology("cash insufficient", 403)
            else:
                # update user cash (original cash - pxq)
                db.execute("UPDATE users SET cash=? WHERE id = ?", user_cash - pxq, session["user_id"])
                rows_pf = db.execute("SELECT * FROM portfolio WHERE symbol = ? AND user_id=?",
                                     request.form.get("symbol"), session["user_id"])

                # if symbol not in list of user shares:
                if len(rows_pf) == 0:
                    # register symbol, quantity
                    db.execute("INSERT INTO portfolio (symbol, quantity, price, user_id, name) VALUES (?, ?, ?, ?, ?)",
                               request.form.get("symbol"), quantity, price, session["user_id"], name)
                # else:
                elif len(rows_pf) == 1:
                    # update symbol quantity
                    db.execute("UPDATE portfolio SET quantity=? WHERE user_id = ? and symbol = ?",
                               rows_pf[0]["quantity"] + int(quantity), session["user_id"], request.form.get("symbol"))
                else:
                    return apology("Portfolio DB error", 403)

            # register transaction in history DB
            # Source https://www.programiz.com/python-programming/datetime/current-datetime
            db.execute("INSERT INTO history (symbol, transaction_type, quantity, datetime, price, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                       request.form.get("symbol"), "BUY", quantity, datetime.now(), price, session["user_id"])
            return redirect("/")
    # If GET: display form to buy
    else:


        return render_template("buy.html")


@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def changepassword():

    # When form submited via POST, insert into users table
    if request.method == "POST":

        rows = db.execute("select hash from users where id=?", session["user_id"])
        realoph = rows[0]["hash"]
        # Ensure username was submitted
        if not check_password_hash(realoph, request.form.get("old_password")):
            return apology("incorrect current password", 403)
        if not request.form.get("old_password"):
            return apology("must provide current password", 403)
        if request.form.get("new_password") != request.form.get("confirmation"):
            return apology("password does not match", 403)
        # Ensure password was submitted
        elif not request.form.get("new_password"):
            return apology("must provide password", 403)

        else:
            pwhash = generate_password_hash(request.form.get("new_password"))
            db.execute("UPDATE users SET hash=? WHERE id =? ", pwhash, session["user_id"])
            # Redirect user to home page
            return redirect("/")

    # Check for invalid inputs (eg. user already registered, password does not match)
    # Hash the user's password and store in DB
    # User reached route via GET (as by clicking a link or via redirect)

    # When requested via GET, should display registration form
    else:
        return render_template("changepassword.html")
    # return apology("TODO")

@app.route("/leaderboard")
@login_required
def leaderboard():
    """Show leaderboard of all users"""

    # Display table with current user stocks, numbers of shares, current price, total vale of holding
    portfolio = db.execute("SELECT * from portfolio")
    # update price of shares in portfolio
    for i in portfolio:
        time.sleep(1)
        share = lookup(i["symbol"])
        new_price = share["price"]
        change = round(float(share["1d"]) * 100 , 2)
        db.execute("UPDATE portfolio SET price=?, change=change WHERE symbol =?", new_price, change, i["symbol"])
    # portfolio = db.execute("SELECT * from portfolio")
    points = db.execute("SELECT username, cash + SUM(price*quantity),  as points FROM users INNER JOIN portfolio on id=user_id group by username")

    # Display users current cash balance
    # Calculate total portfolio value
    # value = db.execute("SELECT SUM(price*quantity) as value, user_id from portfolio group by user_id")
    #if len(rows2) != 1:
        # return apology("User session error", 403)

    return render_template("leaderboard.html", points=points)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # 6th
    # Query tables for history of transactions
    history = db.execute("select * from history where user_id=?", session["user_id"])
    # Display table listing row by row of every buy and sell
    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # 2nd OK
    if request.method == "POST":
        quote_result = lookup(request.form.get("symbol"))
        if quote_result is None:
             return apology("symbol does not exist", 400)
        else:
            return render_template("quote_result.html", quote_result=quote_result)
    # If GET: display form to request a stock quote
    else:
        return render_template("quote.html")
    # If POST: lookup using lookup function (see helpers.py) and display the results. If there is no stock, error (apology)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # 1st OK
    # When form submited via POST, insert into users table
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("password does not match", 400)
        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username does not exist
        if len(rows) != 0:
            return apology("user already registered", 400)
        else:
            pwhash = generate_password_hash(request.form.get("password"))
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get("username"), pwhash)
            rows_registered = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
            # Remember which user has logged in
            session["user_id"] = rows_registered[0]["id"]

            # Redirect user to home page
            return redirect("/")

    # Check for invalid inputs (eg. user already registered, password does not match)
    # Hash the user's password and store in DB
    # User reached route via GET (as by clicking a link or via redirect)

    # When requested via GET, should display registration form
    else:
        return render_template("register.html")
    # return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # 5th
    # GET: display form to sell
    # If GET: display form to buy
    if request.method == "GET":

        sym_row = db.execute("SELECT symbol FROM portfolio WHERE user_id=?", session["user_id"])
        symbols = [d['symbol'] for d in sym_row]
        return render_template("sell.html", symbols=symbols)
        # Require that a user input a stock’s symbol, implemented as a select menu whose name is symbol

        # Render an apology if the user fails to select a stock or if (somehow, once submitted) the user does not own any shares of that stock.
        # Require that a user input a number of shares, implemented as a text field whose name is shares.
        # Render an apology if the input is not a positive integer or if the user does not own that many shares of the stock.
        # When a sale is complete, redirect the user back to the index page.

    # Submit the user’s input via POST to /sell.
    # POST: sell number of shares, update the users cash (error check), update tables
    else:
        sym_row = db.execute("SELECT symbol FROM portfolio WHERE user_id=?", session["user_id"])
        symbols = [d['symbol'] for d in sym_row]
        symbol = request.form.get("symbol")
        q = request.form.get("shares")
        rows = db.execute("SELECT quantity FROM portfolio WHERE user_id=? AND symbol=?",
                          session["user_id"], request.form.get("symbol"))
        if len(rows) != 1:
            return apology("DB error", 403)
        quantity = rows[0]["quantity"]
        if not symbol:
            return apology("Please select a symbol", 400)
        # else if q is void:
            # return apology("Please enter number of shares", 403)
        if symbol not in symbols:
            return apology("THOU SHALL NOT HACK", 403)
        if int(q) <= 0:
            return apology("Enter positive number of shares", 400)
        if int(q) > int(quantity):
            return apology("Not enough shares", 400)
        else:
            share = lookup(symbol)
            new_price = share["price"]
            db.execute("UPDATE portfolio SET price=? WHERE user_id =? and symbol =?", new_price, session["user_id"], symbol)
            # update quantity in portfolio = original q - q
            if quantity - int(q) > 0:
                db.execute("UPDATE portfolio SET quantity=? WHERE user_id = ? and symbol = ?",
                           quantity - int(q), session["user_id"], symbol)
            if quantity == int(q):
                db.execute("DELETE FROM portfolio WHERE user_id = ? and symbol = ?", session["user_id"], symbol)
            # calculate new price x q
            value = float(q) * new_price
            # update cash in users = original cash + newprice x q
            rows2 = db.execute("SELECT cash from users where id = ?", session["user_id"])
            orig_cash = rows2[0]["cash"]
            db.execute("UPDATE users SET cash=? WHERE id = ?", orig_cash + value, session["user_id"])
            db.execute("INSERT INTO history (symbol, transaction_type, quantity, datetime, price, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                       symbol, "SELL", q, datetime.now(), new_price, session["user_id"])
            return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

