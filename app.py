import os
from sqlalchemy import create_engine, text
from flask import Flask, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session
from dotenv import load_dotenv
import redis

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Makes environmental variables available
load_dotenv()

# Custom filter
app.jinja_env.filters["usd"] = usd

# Set the secret key to sign the session
app.secret_key = os.environ.get("SECRET_KEY")

# Configure Redis
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

# Redis connection 
REDIS_URL = os.environ.get("REDIS_URL")
app.config["SESSION_REDIS"] = redis.from_url(REDIS_URL)

# Initialize the session
Session(app)

# Get Neon database URL
DATABASE_URL = os.environ.get("DATABASE_URL")

# Configure engine
engine = create_engine(DATABASE_URL, echo=True)


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
    with engine.connect() as db:
        results = db.execute(text("SELECT * FROM portfolio WHERE user_id = :user_id"), {"user_id": session["user_id"]})
        stocks = results.fetchall()
    total = 0
    portfolio = []
    for stock in stocks:
        stock_dict = {"user_id": stock.user_id, "symbol": stock.symbol, "shares": stock.shares}
        price = float(lookup(stock_dict["symbol"])["price"])
        stock_dict["price"] = usd(price)
        stock_total = price * int(stock_dict["shares"])
        stock_dict["total"] = usd(stock_total)
        total += stock_total
        portfolio.append(stock_dict)

    with engine.connect() as db:
        user = db.execute(text("SELECT * FROM users WHERE id = :user_id"), {"user_id": session["user_id"]}).fetchone()
    cash = float(user.cash)
    total += cash

    cash = usd(cash)
    total = usd(total)
    return render_template("index.html", stocks=portfolio, cash=cash, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        stockInfo = lookup(symbol)

        if not symbol:
            return apology("MISSING SYMBOL", 400)
        if not shares:
            return apology("MISSING SHARES", 400)
        if not shares.isdigit() or isinstance(eval(shares), float) or int(shares) < 1:
            return apology("INVALID SHARES", 400)
        if not stockInfo:
            return apology("INVALID SYMBOL", 400)

        with engine.connect() as db:
            cash = db.execute(text("SELECT cash FROM users WHERE id = :user_id"), {"user_id": session["user_id"]}).fetchone().cash
            total_cost = int(shares) * stockInfo["price"]

            if total_cost <= float(cash):
                db.execute(text(
                    "INSERT INTO history (user_id, type, symbol, shares, shareprice) VALUES (:user_id, :type, :symbol, :shares, :shareprice)"),
                    {"user_id": session["user_id"], "type": "buy", "symbol": stockInfo["symbol"], "shares": shares, "shareprice": stockInfo["price"]}
                )

                db.execute(text("UPDATE users SET cash = cash - :cost WHERE id = :user_id"),
                        {"cost": total_cost, "user_id": session["user_id"]})

                db.execute(text("""
                    INSERT INTO portfolio (user_id, symbol, shares)
                    VALUES (:user_id, :symbol, :shares)
                    ON CONFLICT(user_id, symbol) DO UPDATE 
                    SET shares = portfolio.shares + EXCLUDED.shares
                """), {"user_id": session["user_id"], "symbol": stockInfo["symbol"], "shares": shares})

                db.commit()
            else:
                return apology("INSUFFICIENT FUNDS", 400)

        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    with engine.connect() as db:
        transactions = db.execute(text("SELECT * FROM history WHERE user_id = :user_id"), {"user_id": session["user_id"]}).fetchall()
    return render_template("history.html", transactions=transactions, usd=usd)


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
        with engine.connect() as db:
            row = db.execute(text(
                "SELECT * FROM users WHERE username = :username"), {"username": request.form.get("username")}
            ).fetchone()

            # Ensure username exists and password is correct
            if not row or not check_password_hash(
                row.hash, request.form.get("password")
            ):
                return apology("invalid username and/or password", 403)

            # Remember which user has logged in
            session["user_id"] = row.id

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

    if request.method == "POST":
        symbol = request.form.get("symbol")

        stockInfo = lookup(symbol)
        if not stockInfo:
            return apology("INVALID SYMBOL", 400)

        return render_template("quoted.html", companyName=stockInfo["name"], symbol=stockInfo["symbol"], price=usd(stockInfo["price"]))
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            return apology("Please provide username", 400)

        # Ensure password was submitted
        elif not password or not confirmation or password != confirmation:
            return apology("Both passwords must match", 400)

        # Query database for username
        try:
            hashed = generate_password_hash(password)
            with engine.connect() as db:
                db.execute(text("INSERT INTO users (username, hash) VALUES (:username, :hash)"), {"username": username, "hash": hashed})
                db.commit()
        except ValueError:
            return apology("Username already exists :(", 400)

        return redirect("/welcome")
    else:
        return render_template("register.html") 


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")

        if not symbol:
            return apology("MISSING SYMBOL", 400)

        shares = request.form.get("shares")

        if not shares:
            return apology("MISSING SHARES", 400)

        shares = int(shares)
        if shares < 1:
            return apology("INVALID SHARES", 400)

        with engine.connect() as db:
            # Fetch the number of shares the user owns for the given symbol
            owned_shares = db.execute(
                text("SELECT shares FROM portfolio WHERE user_id = :user_id AND symbol = :symbol"),
                {"user_id": session["user_id"], "symbol": symbol.upper()},
            ).fetchone()

            if not owned_shares:
                return apology("SYMBOL NOT FOUND", 400)

            owned_shares = int(owned_shares.shares)

            # Check if the user is trying to sell more shares than they own
            if owned_shares < shares:
                return apology("NOT ENOUGH SHARES", 400)

            # Fetch the stock price
            stockInfo = lookup(symbol)
            proceeds = stockInfo["price"] * shares

            # Update the user's cash
            db.execute(
                text("UPDATE users SET cash = cash + :cash WHERE id = :user_id"),
                {"cash": proceeds, "user_id": session["user_id"]},
            )

            # Record the transaction in the history table
            db.execute(
                text("INSERT INTO history (user_id, type, symbol, shares, shareprice) VALUES (:user_id, :type, :symbol, :shares, :shareprice)"),
                {
                    "user_id": session["user_id"],
                    "type": "sell",
                    "symbol": stockInfo["symbol"],
                    "shares": -shares,  # Negative to indicate selling
                    "shareprice": stockInfo["price"],
                },
            )

            # Update the portfolio: If shares become zero, delete the record
            remaining_shares = owned_shares - shares
            if remaining_shares == 0:
                db.execute(
                    text("DELETE FROM portfolio WHERE user_id = :user_id AND symbol = :symbol"),
                    {"user_id": session["user_id"], "symbol": symbol.upper()},
                )
            else:
                db.execute(
                    text("UPDATE portfolio SET shares = shares - :shares WHERE user_id = :user_id AND symbol = :symbol"),
                    {"shares": shares, "user_id": session["user_id"], "symbol": symbol.upper()},
                )

            db.commit()

        return redirect("/")
    else:
        with engine.connect() as db:
            stocks = db.execute(text("SELECT symbol FROM portfolio WHERE user_id = :user_id"), {"user_id": session["user_id"]}).fetchall()
        return render_template("sell.html", stocks=stocks)



@app.route("/change", methods=["GET", "POST"])
def change():
    if request.method == "POST":
        username = request.form.get("username")
        if not username:
            return apology("MISSING USERNAME")

        old = request.form.get("old")
        if not old:
            return apology("PROVIDE PREVIOUS PASSWORD")

        new = request.form.get("new")
        if not new:
            return apology("ENTER NEW PASSWORD")

        if old == new:
            return apology("CANNOT USE SAME PASSWORD")

        with engine.connect() as db:
            info = db.execute(text("SELECT * FROM users WHERE username = :username"), {"username": username}).fetchone()
            hashed = info["hash"]

            if not check_password_hash(hashed, old):
                return apology("INCORRECT PASSWORD ENTERED")
            else:
                db.execute(text("UPDATE users SET hash = :hash WHERE username = :username"),
                        {"hash": generate_password_hash(new), "username": username})

        return redirect("/")
    else:
        return render_template("password.html")
    

@app.route("/welcome")
def welcome():
    return render_template("welcome.html")
    

if __name__ == "__main__":
    app.run(debug=True)
