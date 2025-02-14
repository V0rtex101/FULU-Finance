from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, DataError
from typing import Optional, Dict, List, Any
from werkzeug.security import check_password_hash, generate_password_hash

from app import app

engine = create_engine(app.config["MY_DATABASE_URL"], echo=True)


class DatabaseError(Exception):
    """Base exception for database-related errors."""
    pass


def execute_query(query: str, params: Optional[Dict] = None) -> Any:
    """Execute a SQL query and commit the transaction."""
    with engine.connect() as db:
        try:
            result = db.execute(text(query), params or {})
            db.commit()
            return result
        except IntegrityError as e:
            if "username" in str(e):
                raise ValueError("Username already exists")
            raise DatabaseError("Database integrity error")
        except DataError as e:
            raise DatabaseError("Invalid data provided")
        except Exception as e:
            raise DatabaseError(f"Database error: {str(e)}")


def fetch_one(query: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """Fetch a single row from the database."""
    with engine.connect() as db:
        result = db.execute(text(query), params or {}).fetchone()
        if not result:
            raise ValueError("User not found")
        return result


def fetch_all(query: str, params: Optional[Dict] = None) -> List[Dict]:
    """Fetch all rows from the database."""
    with engine.connect() as db:
        return db.execute(text(query), params or {}).fetchall()


def get_user_portfolio(user_id: int) -> List[Dict]:
    """Retrieve a user's portfolio."""
    return fetch_all(
        "SELECT * FROM portfolio WHERE user_id = :user_id",
        {"user_id": user_id}
    )


def register_user(username: str, password: str) -> None:
    """Register a new user."""
    hashed = generate_password_hash(password)
    try:
      print(execute_query(
            "INSERT INTO users (username, hash) VALUES (:username, :hash)",
            {
                "username": username,
                "hash": hashed}
        ))
    except ValueError:
        raise ValueError("Username already exists")


def get_user_by_id(user_id: int) -> Dict:
    """Retrieve a user by ID."""
    return fetch_one("SELECT * FROM users WHERE id = :user_id",
                     {"user_id": user_id})


def get_user(username: str, password: str) -> Dict:
    """Retrieve a user by username and validate their password."""
    user = fetch_one(
        "SELECT * FROM users WHERE username = :username",
        {"username": username}
    )

    print(password)
    if not user or not check_password_hash(user.hash, password):
        raise ValueError("Invalid username or password")
    return user


def update_user_password(username: str, new_password: str) -> None:
    """Update a user's password."""
    hashed = generate_password_hash(new_password)
    execute_query(
        "UPDATE users SET hash = :hash WHERE username = :username",
        {
            "hash": hashed,
            "username": username}
    )


def get_user_cash(user_id: int) -> float:
    """Retrieve a user's cash balance."""
    user = fetch_one(
        "SELECT cash FROM users WHERE id = :user_id",
        {"user_id": user_id}
    )
    return float(user["cash"])


def buy_stock(user_id: int, symbol: str, shares: int, price: float) -> None:
    """Buy shares of a stock."""
    total_cost = shares * price
    user_cash = get_user_cash(user_id)

    if total_cost > user_cash:
        raise ValueError("Insufficient funds")

    # Update user's cash
    execute_query(
        "UPDATE users SET cash = cash - :cost WHERE id = :user_id",
        {
            "cost": total_cost,
            "user_id": user_id}
    )

    # Record the transaction
    execute_query(
        """
        INSERT INTO history (user_id, type, symbol, shares, shareprice)
        VALUES (:user_id, :type, :symbol, :shares, :shareprice)
        """,
        {
            "user_id": user_id,
            "type": "buy",
            "symbol": symbol,
            "shares": shares,
            "shareprice": price}
    )

    # Update portfolio
    execute_query(
        """
        INSERT INTO portfolio (user_id, symbol, shares)
        VALUES (:user_id, :symbol, :shares)
        ON CONFLICT(user_id, symbol) DO UPDATE 
        SET shares = portfolio.shares + EXCLUDED.shares
        """,
        {
            "user_id": user_id,
            "symbol": symbol,
            "shares": shares
        }
    )


def sell_stock(user_id: int, symbol: str, shares: int, price: float) -> None:
    """Sell shares of a stock."""
    user_shares = fetch_one(
        "SELECT shares FROM portfolio WHERE user_id = :user_id AND symbol = :symbol",
        {
            "user_id": user_id,
            "symbol": symbol}
    )

    if not user_shares or int(user_shares["shares"]) < shares:
        raise ValueError("Not enough shares")

    proceeds = price * shares

    # Update user's cash
    execute_query(
        "UPDATE users SET cash = cash + :proceeds WHERE id = :user_id",
        {
            "proceeds": proceeds,
            "user_id": user_id}
    )

    # Record the transaction
    execute_query(
        """
        INSERT INTO history (user_id, type, symbol, shares, shareprice)
        VALUES (:user_id, :type, :symbol, :shares, :shareprice)
        """,
        {
            "user_id": user_id,
            "type": "sell",
            "symbol": symbol,
            "shares": -shares,
            "shareprice": price}
    )

    # Update portfolio
    remaining_shares = int(user_shares["shares"]) - shares
    if remaining_shares == 0:
        execute_query(
            "DELETE FROM portfolio WHERE user_id = :user_id AND symbol = :symbol",
            {
                "user_id": user_id,
                "symbol": symbol}
        )
    else:
        execute_query(
            "UPDATE portfolio SET shares = shares - :shares WHERE user_id = :user_id AND symbol = :symbol",
            {
                "shares": shares,
                "user_id": user_id,
                "symbol": symbol}
        )


def get_history(user_id, ):
    return fetch_all(
        "SELECT * FROM history WHERE user_id = :user_id",
        {"user_id": user_id}
    )
