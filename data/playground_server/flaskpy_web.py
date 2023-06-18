import json

from flask import Flask, request, render_template, redirect
import os
import sqlite3
import importlib
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

import configuration as C

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

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('/home/yves/AI/Culture/server-agent/data//agent_playground_!BBYKuRbtZEwhOkchnh:matrix.org.db')
    c = conn.cursor()
    c.execute("SELECT * FROM makers")
    data = c.fetchall()
    conn.close()
    return '''
    <html>
        <head>
            <title>Dashboard</title>
        </head>
        <body>
            <table>
                <tr>
                    <th>name</th>
                    <th>mécanique</th>
                    <th>fabrication</th>
                    <th>électronique</th>
                    <th>programmation</th>
                </tr>
                {% for row in data %}
                <tr>
                    <td>{{ row[0] }}</td>
                    <td>{{ row[1] }}</td>
                    <td>{{ row[2] }}</td>
                    <td>{{ row[3] }}</td>
                    <td>{{ row[4] }}</td>
                </tr>
                {% endfor %}
            </table>
        </body>
    </html>
    '''

@app.route('/form', methods=['GET', 'POST'])
def form():
    if request.method == 'POST':
        name = request.form['name']
        mecanique = request.form['mecanique']
        fabrication = request.form['fabrication']
        electronique = request.form['electronique']
        programmation = request.form['programmation']
        conn = sqlite3.connect('/home/yves/AI/Culture/server-agent/data//agent_playground_!BBYKuRbtZEwhOkchnh:matrix.org.db')
        c = conn.cursor()
        c.execute("INSERT INTO makers (name, mécanique, fabrication, électronique, programmation) VALUES (?, ?, ?, ?, ?)", (name, mecanique, fabrication, electronique, programmation))
        conn.commit()
        conn.close()
        return redirect('/dashboard')
    else:
        return '''
        <html>
            <head>
                <title>Form</title>
            </head>
            <body>
                <form method='POST'>
                    <label for='name'>Name:</label>
                    <input type='text' id='name' name='name'><br>
                    <label for='mecanique'>Mécanique:</label>
                    <input type='number' id='mecanique' name='mecanique'><br>
                    <label for='fabrication'>Fabrication:</label>
                    <input type='number' id='fabrication' name='fabrication'><br>
                    <label for='electronique'>Électronique:</label>
                    <input type='number' id='electronique' name='electronique'><br>
                    <label for='programmation'>Programmation:</label>
                    <input type='number' id='programmation' name='programmation'><br>
                    <input type='submit' value='Submit'>
                </form>
            </body>
        </html>
        '''