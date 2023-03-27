import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

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

# User ID for the user currently logged in

# user_id = session.get("user_id")


@app.route("/")
@login_required
def index():

    stockvalues = []
    user_id = session.get("user_id")
    """Show portfolio of stocks"""
    stocks = db.execute("SELECT * FROM stocks WHERE userid = ?", user_id)
    selectedcash = db.execute("SELECT * FROM users WHERE id = ?", user_id)
    cash = selectedcash[0]["cash"]

    totalvalue = 0
    i = 0
    while i < len(stocks):
        x = lookup(stocks[i]["symbol"])
        y = x["price"]
        totalvalue = totalvalue + stocks[i]["shares"] * y
        stockvalues.append(y)

        i = i + 1
    return render_template("index.html", cash=cash, stocks=stocks, stockvalues=stockvalues, totalvalue=totalvalue)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    user_id = session.get("user_id")
    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("Please enter a valid stock", 400)

        if not request.form.get("shares"):
            return apology("Please enter a valid amount of shares", 400)

        if not request.form.get("symbol"):
            return apology("Please enter a valid symbol", 400)

        stock = lookup(request.form.get("symbol"))

        try:
            quant = int(request.form.get("shares"))
        except ValueError:
            return apology("Shares must be a positive integer", 400)

        if stock == None:
            return apology("Stock invalid", 400)

        if quant < 1:
            return apology("Please choose a valid amount of shares")

        cost = stock["price"] * quant
        usercash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        cash = usercash[0]["cash"]
        symbol = stock["symbol"]

        stockname = stock["name"]
        newcash = cash - cost

        # Ensure user has enough cash to make purchase
        if cost > cash:
            return apology("Not enough funds")

        else:

            if len(db.execute("SELECT * FROM stocks WHERE userid = ? AND stockname = ?", user_id, stockname)) == 1:

                row = db.execute("SELECT * FROM stocks WHERE userid = ? AND stockname = ?", user_id, stockname)

                currentshares = row[0]["shares"]

                newshares = currentshares + quant

                db.execute("UPDATE stocks SET shares = ? WHERE userid = ? AND stockname = ?", newshares, user_id, stockname)

                db.execute("UPDATE users SET cash = ? WHERE id = ?", newcash, session["user_id"])

                db.execute("INSERT INTO transactions (userid, type, stockid, quantity, value) VALUES (?, ?, ?, ?, ?)",
                           user_id, "BUY", stockname, quant, cost)

                return redirect("/")

            else:

                db.execute("INSERT INTO stocks (userid, shares, stockname, symbol) VALUES (?, ?, ?, ?)",
                           user_id, quant, stockname, symbol)

                db.execute("UPDATE users SET cash = ? WHERE id = ?", newcash, session["user_id"])

                db.execute("INSERT INTO transactions (userid, type, stockid, quantity, value) VALUES (?, ?, ?, ?, ?)",
                           user_id, "BUY", symbol, quant, cost)

            return redirect("/")

    else:

        """Buy shares of stock"""
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute("SELECT * FROM transactions WHERE userid = ?", session.get("user_id"))
    return render_template("history.html", transactions=transactions)


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

    if request.method == "POST":

        stock = lookup(request.form.get("symbol"))

        # Ensure stock requested is valid
        if not request.form.get("symbol"):
            return apology("Please enter a valid stock", 400)

        if lookup(request.form.get("symbol")) == None:
            return apology("Stock invalid", 400)

        if not request.form.get("symbol"):
            return apology("Please enter a valid symbol", 400)

        """Return Stock quote."""
        return render_template("quoted.html", stock=stock)

    """Get stock quote."""
    return render_template("quote.html")


@app.route("/quoted", methods=["POST"])
@login_required
def quoted():

    stock = lookup(request.form.get("symbol"))

    # Ensure stock requested is valid
    if not request.form.get("symbol"):
        return apology("Please enter a valid stock", 400)

    if lookup(request.form.get("symbol")) == None:
        return apology("Stock invalid")

    if not request.form.get("symbol"):
        return apology("Please enter a valid symbol", 400)

    """Return Stock quote."""
    return render_template("quoted.html", stock=stock)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Stores the information the user submitted
        username = request.form.get("username")
        password = request.form.get("password")
        password2 = request.form.get("confirmation")
        email = request.form.get("email")

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Checks if both passwords submitted by the user match
        if password != password2:
            return apology("Passwords do not match")

        else:

            # hash the password #
            hashed = generate_password_hash(password)

            # See if username already exists
            users = db.execute("SELECT * FROM users WHERE username = ?", username)
            print(users)

            if len(users) > 0:
                return apology("Username already exists, please select another username", 400)

            else:
                # Insert user into the database and redicrects them to the login page
                db.execute("INSERT into users (username, hash, email) VALUES(?, ?, ?)", username, hashed, email)
                return apology("Thanks for registering, please log in now", 200)

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    rows = db.execute("SELECT * FROM stocks WHERE userid = ?", session.get("user_id"))

    if request.method == "POST":
        # Get data from user input
        symbol = request.form.get("symbol")

        quantity = float(request.form.get("shares"))

        # check if user has selected a share
        if symbol == None:
            return apology("Please select a share you own")

        currentStock = lookup(symbol)

        shares = db.execute("SELECT shares FROM stocks WHERE userid = ? AND symbol = ?", session.get("user_id"), symbol)
        ownedshares = shares[0]["shares"]

        # check if user has sold positive value of shares
        if quantity < 1:
            return apology("Can't sell less than 0.01 Shares")

        # check if user owns enough shares to cover the sale
        if quantity > ownedshares:
            return apology("You tried to sell more shares than you own")

        newshares = ownedshares - quantity

        value = currentStock["price"]

        user = db.execute("SELECT * FROM users WHERE id = ?", session.get("user_id"))

        userCash = user[0]["cash"]

        newCash = userCash + value * quantity

        # If user has sold all their shares, remove from current shares held
        if newshares == 0:
            # Delete shares
            db.execute("DELETE FROM stocks WHERE userid = ? AND symbol = ?", session.get("user_id"), symbol)
            # Add to Transactions
            db.execute("INSERT INTO transactions (userid, type, stockid, quantity, value) VALUES (?, ?, ?, ?, ?)",
                       session.get("user_id"), "SELL", symbol, quantity, value)
            # Update total Cash
            db.execute("UPDATE users SET cash = ? WHERE id = ?", newCash, session.get("user_id"))
            return redirect("/")

        # Update the number of shares, cash and transactions
        else:
            db.execute("UPDATE stocks SET shares = ? WHERE userid = ? AND symbol = ?", newshares, session.get("user_id"), symbol)
            db.execute("INSERT INTO transactions (userid, type, stockid, quantity, value) VALUES (?, ?, ?, ?, ?)",
                       session.get("user_id"), "SELL", symbol, quantity, value)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", newCash, session.get("user_id"))

            return redirect("/")

    else:

        return render_template("sell.html", rows=rows)


@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():

    if request.method == "POST":

        cashRequest = float(request.form.get("cash"))

        user = db.execute("SELECT * FROM users WHERE id = ?", session.get("user_id"))

        userCash = user[0]["cash"]

        newCash = userCash + cashRequest

        db.execute("UPDATE users SET cash = ? WHERE id = ?", newCash, session.get("user_id"))

        return redirect("/")
    else:

        return render_template("addcash.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
