from routes.auth import auth_bp
from routes.stocks import stocks_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(stocks_bp)
