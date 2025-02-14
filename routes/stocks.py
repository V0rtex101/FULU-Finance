from flask import Blueprint, request, redirect, render_template, session

from services.db import buy_stock, sell_stock, get_history, get_user_portfolio, get_user_by_id
from utils.decorators import login_required
from utils.helpers import lookup, apology, usd

stocks_bp = Blueprint("stocks"
                      , __name__,
                      url_prefix="/stocks",
                      template_folder="templates")


@stocks_bp.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks = get_user_portfolio(session["user_id"])
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

    user = get_user_by_id(session["user_id"])
    cash = float(user.cash)
    total += cash

    cash = usd(cash)
    total = usd(total)
    return render_template("index.html", stocks=portfolio, cash=cash, total=total)


@stocks_bp.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        stock_info = lookup(symbol)

        if not stock_info:
            return apology("INVALID SYMBOL", 400)

        try:
            buy_stock(session["user_id"], symbol, int(shares), stock_info["price"])
        except Exception as e:
            return apology(str(e), 400)

        return redirect("/")
    else:
        return render_template("buy.html")


@stocks_bp.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        stock_info = lookup(symbol)

        if not symbol:
            return apology("MISSING SYMBOL", 400)

        if not shares:
            return apology("MISSING SHARES", 400)

        if shares < 1:
            return apology("INVALID SHARES", 400)

        try:
            sell_stock(session["user_id"], symbol, shares, stock_info["price"])
        except ValueError as e:
            return apology(str(e), 400)

        return redirect("/")


@stocks_bp.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":
        symbol = request.form.get("symbol")

        stock_info = lookup(symbol)
        if not stock_info:
            return apology("INVALID SYMBOL", 400)

        return render_template("quoted.html",
                               companyName=stock_info["name"],
                               symbol=stock_info["symbol"],
                               price=usd(stock_info["price"]))
    else:
        return render_template("quote.html")


@stocks_bp.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = get_history(session["user_id"])
    return render_template("history.html", transactions=transactions, usd=usd)
