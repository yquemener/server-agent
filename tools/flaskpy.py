import json
import os

import requests
from flask import render_template, Blueprint
import sqlite3
import configuration as C
from tools.tool import Tool


class FlaskPyModule(Tool):
    def __init__(self, root_path, url_root, db_name):
        super().__init__()
        self.root_path = root_path
        self.url_root = url_root
        self.db_name = db_name
        self.file_path = self.root_path + "/flaskpy_web.py"

    def execute_query(self, new_content):
        query_summary = "Modifying the main web server script"
        with open(self.file_path, 'w') as f:
            f.write(new_content)
        self.history.append((query_summary, "success"))
        return query_summary, "success"

    def context(self):
        return {"py_script": open(self.file_path).read(),
                "db_name": self.db_name}
