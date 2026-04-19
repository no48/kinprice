from flask import Flask
from flask_httpauth import HTTPBasicAuth

from app.config import Config

auth = HTTPBasicAuth()


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(Config)

    @auth.verify_password
    def verify_password(username, password):
        if (
            username == app.config["BASIC_AUTH_USERNAME"]
            and password == app.config["BASIC_AUTH_PASSWORD"]
        ):
            return username
        return None

    from app.routes import bp

    if not getattr(bp, "_auth_attached", False):
        @bp.before_request
        @auth.login_required
        def require_auth():
            pass

        bp._auth_attached = True

    app.register_blueprint(bp, url_prefix=app.config["URL_PREFIX"])

    return app
