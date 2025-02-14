from flask import Flask, render_template
from flask_session import Session

from startup.configs import Config
from utils.helpers import usd

# Configure application
app = Flask(__name__)
app.config.from_object(Config)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Initialize the session
Session(app)

# Import blueprints after initializing app to avoid circular imports
from startup.blueprint_registration import register_blueprints

# register_blueprints
register_blueprints(app)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def welcome():
    return render_template("welcome.html")


if __name__ == "__main__":
    app.run(debug=True)
