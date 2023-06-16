import json
import os

import requests
from flask import render_template, Blueprint
import sqlite3
import configuration as C
from tools.tool import Tool


class FlaskModule(Tool):
    def __init__(self, root_path, url_root, db_name):
        super().__init__()
        self.root_path = root_path
        self.url_root = url_root
        self.db_name = db_name
        self.file_path = self.root_path + "/flaskpy_web.py"

        # Initialize necessary directories
        os.makedirs(self.root_path, exist_ok=True)
        for dir_name in self.directories:
            os.makedirs(os.path.join(self.root_path, dir_name), exist_ok=True)

    def execute_query(self, json_obj):
        required = ["content", "summary"]
        query_summary = "Modifying the main web server script"
        for r in required:
            if r not in json_obj:
                return str(query_summary), f"Error: {r} not specified"
        query_summary = json_obj["summary"]
        content = json_obj["content"]
        with open(self.file_path, 'w') as f:
            f.write(content)
        self.history.append((query_summary, "success"))
        return query_summary, "success"

    def context(self):
        return {"py_script": open(self.file_path).read(),
                "db_name": self.db_name}
