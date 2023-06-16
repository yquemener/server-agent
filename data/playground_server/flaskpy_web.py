import json
import sqlite3
from flask import Flask, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

import configuration as C

global app

auth = HTTPBasicAuth()
WHITELISTED_ROUTES = []
users = {
    "user": generate_password_hash(C.HTTP_PASSWORD)
}

global app
app = Flask(__name__)


@app.before_request
def require_auth():
    # check if the route requires authentication
    if request.path not in WHITELISTED_ROUTES:
        auth.login_required()


@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username

