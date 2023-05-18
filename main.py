"""
This file starts the webserver and the agents we want. The webserver runs in the main thread, each agent has its own
 thread. Eventually we want to be able to generate agents on the fly but matrix.org does not allow automated accounts
  creation, so I will probably need to set up our own homeserver.
"""
import json
import os.path
import sqlite3
from agent import Agent

from flask import Flask, render_template, request, redirect
from threading import Thread

from utils import db_req
import configuration as C

DOCKER_ROOT_DIR = "/app/"
if os.path.exists(DOCKER_ROOT_DIR):
    ROOT_DIR = DOCKER_ROOT_DIR
else:
    ROOT_DIR = "/home/yves/AI/Culture/server-agent/"

AGENTS_LIST_DB = f"{ROOT_DIR}/data/agents.db"
AGENTS_HOME = f"{ROOT_DIR}/data/agents/"


db_req(AGENTS_LIST_DB, '''
    CREATE TABLE IF NOT EXISTS bots (
        name TEXT NOT NULL,
        matrix_name TEXT NOT NULL,
        channels TEXT,
        description TEXT);
''')
bots = dict()
for row in db_req(AGENTS_LIST_DB, "SELECT name, matrix_name, channels, description FROM bots;"):
    try:
        channels = json.loads(row[2])
    except:
        channels = []
    bots[row[0]] = Agent(home_folder=f"{AGENTS_HOME}/{row[0]}",
                         name=row[0],
                         matrix_name=row[1],
                         channels=channels,
                         description=row[3])

app = Flask(__name__)


def init_new_agent(name, matrix_name, channels, description):
    global bots
    if not os.path.exists(f"{AGENTS_HOME}/{name}"):
        os.mkdir(f"{AGENTS_HOME}/{name}")
    res = db_req(AGENTS_LIST_DB, "SELECT * FROM bots WHERE name=?;", (name,))
    if not res or len(res)==0:
        db_req(AGENTS_LIST_DB, "INSERT INTO bots (name, matrix_name, channels, description)"
                               " VALUES (?,?,?,?);",
               (name, matrix_name, json.dumps(channels), description))
    bot = Agent(f"{AGENTS_HOME}/{name}", name, "@mind_maker_agent:matrix.org", channels, description)
    return bot


@app.route("/create_bot", methods=["POST"])
def create_bot():
    name = request.form["name"]
    desc = request.form["description"]
    room = request.form["room"]
    bot = init_new_agent(name, "@mind_maker_agent:matrix.org", [room], desc)
    bots[name] = bot
    bot.start()
    return redirect('/')

@app.route('/')
def home():
    return render_template('index.html', bots=bots)

@app.route('/bot/<name>/<path:remaining_path>', methods=['GET', 'POST'])
@app.route('/bot/<name>/')
def pass_to_bot(name, remaining_path=""):
    return bots[name].handle_request(remaining_path, request)


init_new_agent("test_agent",
               "@mind_maker_agent:matrix.org",
               ["!KWqtDRucLSHLiihsNl:matrix.org"],
               "Agent used to test prompts.")


for name, channels, description in db_req(AGENTS_LIST_DB, "SELECT name, channels, description FROM bots;"):
    bot = Agent(f"{AGENTS_HOME}/{name}", name, "@mind_maker_agent:matrix.org", json.loads(channels), description)
    bots[name] = bot
    bot.start()

app.run(host='0.0.0.0', port=8080)
