"""
This file starts the webserver and the Matrix bot.

Time for a bit of definition and design:
    - There is one webserver
    - There is one single matrix bot: an entity that logs into, joins rooms where it is invited and listens to them
    - There are as many agents as rooms joined. Each room where the bot joined has a separate agent

Agents each have a separate context
Agents each have their "playground" database where they can send requests
Prompts are stored at the bot level and shared across agents
We probably want agents to have separate threads for GPT requests processing

Databases:
/bot.db
    - stores prompts
/agent_<room_id>.db
    - stores conversations
    - stores logs
    - stores context_summaries
/agent_playground_<room_id>.db
    - database the agent can use to send SQL requests
"""
import json
import re

import tiktoken
from matrix_client.client import MatrixClient
from time import sleep

import utils
from agent import Agent

from flask import Flask, render_template, request, redirect, abort
from threading import Thread

from utils import db_req
import configuration as C


# TODO: Design prompts chaining
# TODO: The summarization prompt should be acquired from the prompts table and should be agent specific
# TODO: Make listener mode where the agent listens to a conversation and sums it up on demand
# TODO: Restore context even for the first request
# TODO: Bouton HTML pour effacer la DB playground
# TODO: Reactivate the avatar change but as an option in the web interface
# TODO nginx redirect from 80 (and https) to 8448 (so that the server url is https://matrix.iv-labs.org instead
#  of http://matrix.iv-labs.org:8448)
# TODO find a way to make the bot work on encrypted channels. Can be long: the lib used apparently does not support it
#  well


class Bot:
    def __init__(self, bot_db_path):
        self.bot_db = bot_db_path
        self.client = None
        self.agents = dict()
        self.first_ts = -1

        db_req(self.bot_db, '''
            CREATE TABLE IF NOT EXISTS prompts (
                name TEXT NOT NULL,
                prompt TEXT NOT NULL);
        ''')

    def on_message(self, room, event):
        print(room.name, event)
        self.agents[room.room_id].on_message(event)

    def on_invitation(self, room_id, event):
        print(f"Invited in {room_id}!")
        sleep(1)
        try:
            room = self.client.join_room(room_id)
            print(f"Joined room: {room_id}")
            self.agents[room_id] = Agent(room, self)
            if type(event) is not str:
                for e in event["events"]:
                    ts = e.get("origin_server_ts", -1)
                    if ts > self.agents[room_id].first_ts:
                        self.agents[room_id].first_ts = ts
            else:
                self.agents[room_id].first_ts = event.get("origin_server_ts",
                                                          self.agents[room_id].first_ts)
            # self.agents[room_id].first_ts = event["origin_server_ts"]
            room.send_text(f"Hi! Logs available at {C.HOSTNAME}")
            room.add_listener(self.on_message)

        except Exception as e:
            print(f"Failed to join room: {room_id}")
            print(e)

    def start(self, server, user, password):
        # Log in
        self.client = MatrixClient(C.HOMESERVER_URL)
        self.client.login(username=C.BOT_USERNAME.lstrip("@").split(":")[0],
                     password=C.MATRIX_PASSWORD,
                     sync=False)

        # Listens to new invitation
        self.client.add_invite_listener(self.on_invitation)

        # Starts the Matrix bot mainloop in a different thread
        self.client.start_listener_thread()

        # Initialize listeners on already joined rooms
        self.client.api.sync()
        sleep(1)
        joined_rooms = self.client.rooms
        print("Joined rooms:")
        for room_id, room in joined_rooms.items():
            print(f"- {room.name}")
            room.add_listener(self.on_message)
            self.agents[room_id] = Agent(room, self)




# Now initializing the web server
app = Flask(__name__)

encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
@app.route('/')
def home():
    return render_template('index.html', joined_rooms=bot.client.rooms,
                           name=bot.client.user_id)

@app.route('/prompts_edit', methods=["GET", "POST"])
def prompts_edit():
    if request.method == 'POST':
        name = request.form['name']
        prompt = request.form['prompt']
        if 'delete_prompt' in request.form:
            db_req(bot.bot_db, "DELETE FROM prompts WHERE name=?", (request.form["name"],))
        else:
            existing = db_req(bot.bot_db, "SELECT name FROM prompts WHERE name=?", (request.form["name"],))

            if existing:
                db_req(bot.bot_db, "UPDATE prompts SET prompt=? WHERE name=?", (prompt, name))
            else:
                db_req(bot.bot_db, "INSERT INTO prompts (name, prompt) VALUES (?, ?)", (name, prompt))
    rows = db_req(bot.bot_db, "SELECT name, prompt FROM prompts")
    prompts = list()
    for r in rows:
        prompt = re.sub(r'\r?\n', '<br>', r[1])
        prompt = re.sub(r'\'', '\\\'', prompt)
        prompts.append((r[0], prompt))
    return render_template('prompts_edit.html', bot=bot, prompts=prompts)

@app.route('/agent/<room_id>')
def agent_home(room_id):
    return render_template('agent_home.html', name=room_id)


@app.route('/agent/<room_id>/logs')
def conversation_logs(room_id):
    log = db_req(bot.agents[room_id].system_db_name, "SELECT timestamp, message FROM bot_log ORDER BY timestamp DESC;")
    messages = list()
    for m in log:
        if len(json.loads(m[1])) == 0:
            continue
        messages.append((m[0], json.loads(m[1])))
    return render_template('bot_log.html', name=room_id, messages=messages)

@app.route('/agent/<room_id>/playground')
def show_playground(room_id):
    tables = db_req(bot.agents[room_id].playground_db_name,
           "SELECT name FROM sqlite_master WHERE type='table';", row_factory=True)
    table_data = {}
    for table in tables:
        print(table)
        table_name = table['name']
        rows=db_req(bot.agents[room_id].playground_db_name,f"SELECT * FROM {table_name};", row_factory=True)
        table_data[table_name] = [dict(row) for row in rows]
    return render_template('playground.html', table_data=table_data,
                           name=room_id)

@app.route('/agent/<room_id>/conversation_context')
def conversation_context(room_id):
    print(bot.agents)
    size0 = len(encoder.encode(bot.agents[room_id].conversation_context[0]))
    size1 = len(encoder.encode(bot.agents[room_id].conversation_context[1]))
    return render_template('conversation_context.html', name=room_id, agent=bot.agents[room_id], sizes=(size0, size1))

@app.route('/agent/<room_id>/conversation_context/reset', methods=["POST"])
def conversation_context_reset(room_id):
    db_req(bot.agents[room_id].system_db_name, "DELETE FROM conversation;")
    bot.agents[room_id].conversation_context = ("", "")
    bot.agents[room_id].conversation_summary = (-1, "")
    bot.agents[room_id].update_conversation_context()
    return redirect(f'/agent/{room_id}/conversation_context')


#
# @app.route('/bot/<name>/<path:remaining_path>', methods=['GET', 'POST'])
# @app.route('/bot/<name>/')
# def pass_to_bot(name, remaining_path=""):
#     try:
#         return agents[name].handle_request(remaining_path, request)
#     except:
#         return abort(501)
#
#
# # init_new_agent("dbg_agent",
# #                AGENT_USERNAME,
# #                ["!wUvlFWLZgparqjdjBy:matrix.iv-labs.org"],
# #                "Agent used to test prompts.")
#
# # init_new_agent("test_agent",
# #                "@mind_maker_agent:matrix.org",
# #                ["!KWqtDRucLSHLiihsNl:matrix.org"],
# #                "Agent used to test prompts.")
# #
#
# res = db_req(C.AGENTS_LIST_DB, "SELECT name, channels, description FROM bots;")
# for name, channels, description in res:
#     agent = Agent(f"{C.AGENTS_HOME}/{name}", name, C.BOT_USERNAME, json.loads(channels), description, avatar=f"{C.ROOT_DIR}/pictures/portrait1.jpg")
#     agents[name] = agent
#     agent.start()


bot = Bot(C.BOT_DB)
bot.start(C.HOMESERVER_URL,
          C.BOT_USERNAME.lstrip("@").split(":")[0],
          C.MATRIX_PASSWORD)


app.run(host='0.0.0.0', port=8080)
