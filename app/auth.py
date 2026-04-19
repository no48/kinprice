from flask import current_app
from flask_httpauth import HTTPBasicAuth

auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username, password):
    if (
        username == current_app.config["BASIC_AUTH_USERNAME"]
        and password == current_app.config["BASIC_AUTH_PASSWORD"]
    ):
        return username
    return None
