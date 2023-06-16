"""
playground_web.py

This script sets up the main Flask application and routes for the app.
The Flask app is set up to be modular, with each page served by a separate python script file.

Each script file is placed in the 'pages' directory. These scripts are automatically
imported and their routes are registered to the Flask app.

The server runs on port 5481.

Usage:
    (in this file's directory):
    flask --app playground_web run  --debug -p 5481

    It will start th webserver in debug mode which makes it restart as soon as a file has been changed in the hierarchy
"""
import json

from flask import Flask, request
import os
import importlib
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
for module in os.listdir('pages'):
    if module == '__init__.py' or module[-3:] != '.py':
        continue
    importlib.import_module('pages.' + module[:-3])


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

@app.route('/routes_served')
def routes_served():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(str(rule))
    return json.dumps(routes)

