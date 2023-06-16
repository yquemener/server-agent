import json
import os

import requests
from flask import render_template, Blueprint
import sqlite3
import configuration as C
from tools.tool import Tool


class FlaskModule(Tool):
    def __init__(self, root_path, url_root, flask_app, db_name):
        super().__init__()
        self.root_path = root_path
        self.directories = ['templates', 'static/css', 'static/html', 'pages']
        self.flask_app = flask_app
        self.url_root = url_root
        self.db_name = db_name

        # Initialize necessary directories
        os.makedirs(self.root_path, exist_ok=True)
        for dir_name in self.directories:
            os.makedirs(os.path.join(self.root_path, dir_name), exist_ok=True)

    def execute_query(self, json_obj):
        query_summary = {k: "..." for k in json_obj.keys()}
        if "url" not in json_obj:
            return str(query_summary), "Error: URL not specified"
        url = json_obj["url"]
        query_summary["url"] = url
        file_name_url = url.lstrip("/").replace('/', '_') if url != '/' else 'index'

        for filetype in ["html", "css", "python"]:
            if filetype not in json_obj.keys():
                continue
            content = json_obj[filetype]
            if filetype == "html":
                file_dir = os.path.join(self.root_path, 'templates')
                file_name = f'{file_name_url}.html'
            elif filetype == "css":
                file_dir = os.path.join(self.root_path, 'static/css')
                file_name = f'{file_name_url}.css'
            elif filetype == "python":
                file_dir = os.path.join(self.root_path, 'pages')
                file_name = f'{file_name_url}.py'  # Not used?

            if filetype == "python":
                content = f'''
from flask import render_template
from flask_httpauth import HTTPBasicAuth
from playground_web import app, auth
import sqlite3

@app.route('{self.url_root.rstrip("/")}/{url.lstrip("/")}')
@auth.login_required
{content}
'''
                content=content.replace("db_name", f"'{self.db_name}'")
            os.makedirs(file_dir, exist_ok=True)
            file_path = os.path.join(file_dir, file_name)
            with open(file_path, 'w') as f:
                f.write(content)
                print(f"File {file_name} created successfully in directory {file_dir}.")
        self.history.append((query_summary, "success"))
        return query_summary, "success"

    def context(self):
        ret = dict()
        s = ""
        for root, dirs, files in os.walk(self.root_path):
            level = root.replace(self.root_path, '').count(os.sep)
            indent = ' ' * 4 * level
            s+='{}{}/'.format(indent, os.path.basename(root))
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                s+='{}{}'.format(subindent, f)
        ret["files"] = s
        response = requests.get(f"{C.PLAYGROUND_URL}/routes_served")
        if 200 >= response.status_code < 300:
            s = response.json()
        ret['routes'] = s
        return ret

