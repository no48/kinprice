from hmac import compare_digest

from flask import current_app
from flask_httpauth import HTTPBasicAuth

auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username, password):
    expected_user = current_app.config["BASIC_AUTH_USERNAME"]
    expected_pass = current_app.config["BASIC_AUTH_PASSWORD"]
    if compare_digest(username, expected_user) and compare_digest(password, expected_pass):
        return username
    return None


def protect(blueprint):
    @blueprint.before_request
    @auth.login_required
    def _require_auth():
        pass
