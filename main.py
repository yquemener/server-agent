"""
This file starts the webserver and the agents we want. The webserver runs in the main thread, each agent has its own
 thread. Eventually we want to be able to generate agents on the fly but matrix.org does not allow automated accounts
  creation, so I will probably need to set up our own homeserver.
"""
import json
import os.path
import sqlite3
from agent import Agent

from flask import Flask, render_template, request, redirect, abort
from threading import Thread

from utils import db_req
import configuration as C


# TODO: Empêcher le bot de refaire toutes les instructions passés après un join (sync=False?)
# TODO: Mettre un meilleur username
# TODO: Reactivate the avatar change but as an option in the web interface
# TODO: Mettre à jour la table des rooms rejointes lors d'une invitation
# TODO: afficher le nom des rooms au lieu de juste leur adresse dans la page principale

# AGENT_USERNAME = "@mind_maker_agent:matrix.org"

db_req(C.AGENTS_LIST_DB, '''
    CREATE TABLE IF NOT EXISTS bots (
        name TEXT NOT NULL,
        matrix_name TEXT NOT NULL,
        channels TEXT,
        description TEXT);
''')
agents = dict()
for row in db_req(C.AGENTS_LIST_DB, "SELECT name, matrix_name, channels, description FROM bots;"):
    try:
        channels = json.loads(row[2])
    except:
        channels = []
    agents[row[0]] = Agent(home_folder=f"{C.AGENTS_HOME}/{row[0]}",
                           name=row[0],
                           matrix_name=row[1],
                           channels=channels,
                           description=row[3])

app = Flask(__name__)


def init_new_agent(name, matrix_name, channels, description):
    global agents
    if not os.path.exists(f"{C.AGENTS_HOME}/{name}"):
        os.mkdir(f"{C.AGENTS_HOME}/{name}")
    res = db_req(C.AGENTS_LIST_DB, "SELECT * FROM bots WHERE name=?;", (name,))
    if not res or len(res)==0:
        db_req(C.AGENTS_LIST_DB, "INSERT INTO bots (name, matrix_name, channels, description)"
                               " VALUES (?,?,?,?);",
               (name, matrix_name, json.dumps(channels), description))
    bot = Agent(f"{C.AGENTS_HOME}/{name}", name, C.AGENT_USERNAME, channels, description)
    return bot


@app.route("/create_bot", methods=["POST"])
def create_bot():
    name = request.form["name"]
    desc = request.form["description"]
    room = request.form["room"]
    bot = init_new_agent(name, C.AGENT_USERNAME, [room], desc, avatar=f"{C.ROOT_DIR}/pictures/portrait1.jpg")
    agents[name] = bot
    bot.start()
    return redirect('/')

@app.route('/')
def home():
    return render_template('index.html', bots=agents)

@app.route('/bot/<name>/<path:remaining_path>', methods=['GET', 'POST'])
@app.route('/bot/<name>/')
def pass_to_bot(name, remaining_path=""):
    try:
        return agents[name].handle_request(remaining_path, request)
    except:
        return abort(501)


# init_new_agent("dbg_agent",
#                AGENT_USERNAME,
#                ["!wUvlFWLZgparqjdjBy:matrix.iv-labs.org"],
#                "Agent used to test prompts.")

# init_new_agent("test_agent",
#                "@mind_maker_agent:matrix.org",
#                ["!KWqtDRucLSHLiihsNl:matrix.org"],
#                "Agent used to test prompts.")
#

res = db_req(C.AGENTS_LIST_DB, "SELECT name, channels, description FROM bots;")
for name, channels, description in res:
    agent = Agent(f"{C.AGENTS_HOME}/{name}", name, C.AGENT_USERNAME, json.loads(channels), description, avatar=f"{C.ROOT_DIR}/pictures/portrait1.jpg")
    agents[name] = agent
    agent.start()
app.run(host='0.0.0.0', port=8080)
