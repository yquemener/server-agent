"""
app.py

This script sets up the main Flask application and routes for the app.
The Flask app is set up to be modular, with each page served by a separate python script file.

Each script file is placed in the 'pages' directory. These scripts are automatically
imported and their routes are registered to the Flask app.

The server runs on port 5481.

Usage:
    This script is meant to be run by the run.py script for hot-reloading.
    It can also be run directly with `python app.py` for regular execution.
"""

from flask import Flask
import os
import importlib


def create_app():
    app = Flask(__name__)

    for module in os.listdir('pages'):
        if module == '__init__.py' or module[-3:] != '.py':
            continue
        importlib.import_module('pages.' + module[:-3])

    return app


if __name__ == "__main__":
    app = create_app()
    print("Playground server running")
    app.run(port=5481)
