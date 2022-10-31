import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]
    purchases_db = db.execute("SELECT symbol, SUM(shares) AS shares FROM purchases WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0", user_id)
    cash_db = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
    cash = cash_db[0]["cash"]

    portfolio = []
    totalsum = 0

    for row in purchases_db:
        stock = lookup(row['symbol'])
        sumshares = (stock["price"] * row["shares"])
        portfolio.append({"symbol": stock["symbol"], "name": stock["name"], "shares": row["shares"], "price": usd(stock["price"]), "total": usd(sumshares)})
        totalsum += stock["price"] * row["shares"]

    totalsum += cash

    return render_template("index.html", portfolio = portfolio, cash = usd(cash), total = usd(totalsum))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("must provide a symbol")
        stock = lookup(symbol.upper())
        if stock == None:
            return apology("symbol doesn't exist")
        shares = request.form.get("shares")
        if not shares.isdigit():
            return apology("must provide a valid number")

        transaction_cost = int(shares) * stock["price"]
        user_id = session["user_id"]
        user_balance = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        real_user_balance = user_balance[0]["cash"]
        date = datetime.datetime.now()
        if real_user_balance < transaction_cost:
            return apology("not enough money")
        updated_balance = real_user_balance - transaction_cost

        db.execute("UPDATE users SET cash = ? WHERE id = ?", updated_balance, user_id)

        db.execute("INSERT INTO purchases (user_id, price, symbol, shares, date) VALUES (?, ?, ?, ?, ?)", user_id, stock["price"], stock["symbol"], int(shares), date)

        flash ("Bought!")

        return redirect("/")




@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    transactions_db = db.execute("SELECT * FROM purchases WHERE user_id = ?", user_id)
    return render_template("history.html", transactions = transactions_db)

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
    if request.method == ("GET"):
        return render_template("quote.html")

    else:
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("must provide a symbol")
        quotedstock = lookup(symbol.upper())
        if quotedstock == None:
            return apology("symbol doesn't exist")
        return render_template("quoted.html", price = quotedstock["price"], symbol = quotedstock["symbol"], name = quotedstock["name"])


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("must provide username")
        if not password:
            return apology("must provide password")
        if not confirmation:
            return apology("must provide confirmation")
        if password != confirmation:
            return apology("passwords must match")

        encryptedpass = generate_password_hash(password)

        try:
            new_user = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, encryptedpass)
        except:
            return apology("user already exists")

        session["user_id"] = new_user

        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]
    if request.method == "GET" :
        symbols = db.execute("SELECT symbol, SUM(shares) AS shares FROM purchases WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0", user_id)
        return render_template("sell.html", symbols = symbols)
    else:
        cash_db = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        curr_cash = cash_db[0]["cash"]
        stock = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        symbol = lookup(stock.upper())
        selling_value = shares * symbol["price"]
        user_shares_db = db.execute("SELECT SUM(shares) AS shares FROM purchases WHERE user_id = ? and symbol = ? GROUP BY symbol", user_id, stock)
        user_shares = user_shares_db[0]["shares"]
        if shares < 0:
            return apology("must provide a valid number")
        if shares > user_shares:
            return apology("not enough shares")
        date = datetime.datetime.now()
        new_cash_balance = selling_value + curr_cash
        db.execute("UPDATE users SET cash = ? WHERE id = ?", new_cash_balance, user_id)
        db.execute("INSERT INTO purchases (user_id, price, symbol, shares, date) VALUES (?, ?, ?, ?, ?)", user_id, symbol["price"], stock, (-1)*shares, date)

        flash("Sold!")

        return redirect("/")


@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():

    if request.method == "GET":
        return render_template("deposit.html")
    else:
        valid_digit = request.form.get("deposit")
        if not valid_digit.isdigit():
            return apology("must provide a valid number")
        amount = int(request.form.get("deposit"))
        if amount < 100:
            return apology("Can not deposit less than 100")
        if not amount:
            return apology("Must input a number")
        user_id = session["user_id"]
        old_balance_db = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        old_balance = old_balance_db[0]["cash"]
        new_balance = old_balance + amount

        db.execute("UPDATE users SET cash = ? WHERE id = ?", new_balance, user_id)

        flash("Deposit was succesful!")

    return redirect("/")