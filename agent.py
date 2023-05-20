"""
An agent is a matrix bot that has its own context and database. It lives in a separate thread. For now it can only
be in a single matrix room at the time but the plan is that they can each have a presence in several.

- TODO Have several joined discussion per agent
- TODO find a way to make it work on encrypted channels

"""
import json
import re
import sqlite3
import textwrap
import time

import openai
import tiktoken
from flask import render_template, abort, redirect
from matrix_client.client import MatrixClient

import utils
from utils import db_req
import configuration as C


class Agent():
    def __init__(self, home_folder, name, matrix_name, channels=[], description=""):
        self.home_folder = home_folder
        self.name = name
        self.matrix_name = matrix_name
        self.channels = channels
        self.description = description

        self.conversation_summary = (-1, "")  # (timestamp of last summed up message, summary)
        self.conversation_context = ["", ""]
        self.current_log = []
        self.update_history = True

        self.system_db_name = f"{home_folder}/system.db"
        self.playground_db_name = f"{home_folder}/playground.db"

        self.client = MatrixClient(C.HOMESERVER_URL)
        self.rooms = list()

        db_req(self.system_db_name, '''
            CREATE TABLE IF NOT EXISTS bot_log (
                timestamp TEXT NOT NULL,
                message TEXT NOT NULL
            );''')
        db_req(self.system_db_name, '''
            CREATE TABLE IF NOT EXISTS conversation (
                timestamp INTEGER NOT NULL,
                author TEXT NOT NULL,
                message TEXT NOT NULL
            );
        ''')
        db_req(self.system_db_name, '''
            CREATE TABLE IF NOT EXISTS conversation_summary (
                timestamp INTEGER NOT NULL,
                message TEXT NOT NULL
            );
        ''')
        db_req(self.system_db_name, "CREATE TABLE IF NOT EXISTS prompts (name TEXT, prompt TEXT)")

        result = db_req(self.system_db_name,
                        "SELECT * FROM conversation_summary ORDER BY timestamp DESC LIMIT 1;")
        if len(result) > 0:
            self.conversation_summary = result[0]

    def append_log(self, s, p=False):
        self.current_log.append(str(s))
        if p:
            print(s)

    def write_log(self):
        db_req(self.system_db_name, 'INSERT INTO bot_log VALUES (?, ?);',
               (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()), json.dumps(self.current_log)))
        self.current_log = []

    def context_summarization(self, page, previous_summary):
        if len(previous_summary) > 0:
            prompt = f"""\
            Please provide a new summary of the conversation. The summary should be succinct and include all the important information given in the conversation.  
            This is the summary of the conversation so far:
            START SUMMARY
            {previous_summary}
            END SUMMARY
            The following messages were since added to the conversation:
            START MESSAGES
            {page}
            END MESSAGES
            """
        else:
            prompt = f"""\
            Please provide a summary of the following conversation. The summary should be succinct and include all the important information given in the conversation.
            START MESSAGES
            {page}
            END MESSAGES"""
        answer, codes = self.chatgpt_request(prompt)
        return answer

    def update_conversation_context(self):
        MAX_CONTEXT_SIZE = 2000

        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
        token_size = len(enc.encode(self.conversation_summary[1]))
        previous_ts = self.conversation_summary[0]
        page = ""
        messages = db_req(self.system_db_name,
                          'SELECT timestamp, author, message FROM conversation WHERE timestamp > ? ORDER BY timestamp ASC;',
                          (previous_ts,)
                          )
        for m in messages:
            ts, author, message = m
            if "Hi! Logs available at" in message:
                continue
            line = ""
            name = utils.extract_username(author)
            if ts - previous_ts > 60 and previous_ts > 0:
                delta = utils.format_time_interval(m[0] - previous_ts)
                line += f"{delta} later\n"
            line += f"{name}: {message}\n\n"
            message_token_size = len(enc.encode(line))

            if token_size + message_token_size > MAX_CONTEXT_SIZE:
                self.conversation_summary = (ts, self.context_summarization(page, self.conversation_summary[1]))
                db_req(self.system_db_name, 'INSERT INTO conversation_summary VALUES (?, ?);',
                       self.conversation_summary)
                page = ""
                token_size = len(enc.encode(self.conversation_summary[1]))
            else:
                token_size = token_size + message_token_size
            page += line
            previous_ts = ts
        self.conversation_context = (self.conversation_summary[1], page)

    def chatgpt_request(self, prompt):
        if type(prompt) is str:
            sprompt = prompt
            prompt = [prompt]
            sprompt = textwrap.dedent(sprompt)
        else:
            sprompt = "\t" + "\t\n".join(prompt)
        self.append_log(f"gpt prompt\n{sprompt}")
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

        rep = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": c} for c in prompt],
            temperature=0.1,
            max_tokens=4000 - len(enc.encode(sprompt)),
        )
        body = rep["choices"][0]["message"]["content"]
        s = "\t" + '\n\t'.join(body.split('\n'))
        s += f'\nfinish_reason {rep["choices"][0]["finish_reason"]}\n'
        s += f'tokens {rep["usage"]}\n'
        self.append_log(f"gpt answer\n{s}", True)

        bs = body.split("```")
        code_blocks = list()
        if len(bs) > 1:
            for i in range(1, len(bs), 2):
                code_blocks.append(bs[i])
        return body, code_blocks

    def use_prompt(self, prompt_name, command, room, sender):
        # Runs a prompt that's from the prompts database
        self.append_log(f"Instruction: {prompt_name} {command}", True)
        prompt = db_req(self.system_db_name,
                        'SELECT prompt FROM prompts WHERE name = ?;', (prompt_name,))
        if len(prompt) == 0:
            return
        prompt = prompt[0][0]

        prompt_context = {
            "instruction": " ".join(command.split(" ")[1:]),
            "username": utils.extract_username(sender),
            "conversation_context": self.conversation_context
        }
        populated_prompt = prompt.format(**prompt_context)
        answer, codes = self.chatgpt_request(populated_prompt)
        room.send_text(answer)

    def on_message(self, room, event):
        print(event)
        try:
            if event['type'] == "m.room.message" and event['content']['msgtype'] == "m.text":
                line = event['content']['body']
                instruction = line
                if instruction[0] == "!":
                    if instruction[1] == "!":
                        self.update_history = False
                    else:
                        self.update_history = True
                    args = line.split(" ")
                    command = args[0].lstrip("!")
                    instruction = " ".join(args[1:])
                    if command == "echo":
                        room.send_text(instruction)
                    try:
                        prompt_name = command.lstrip("!")
                        self.use_prompt(prompt_name, instruction, room, event['sender'])

                    # TODO: afficher un message hors de l'historique quand ces erreurs arrivent
                    except openai.error.RateLimitError:
                        self.append_log(f"openai\nRateLimitError", True)
                    except openai.error.InvalidRequestError as e:
                        self.append_log(f"openai\nInvalidRequestError: {str(e)}", True)
                    except Exception as e:
                        self.append_log(f"Python exception\nError: {type(e).__name__}: {e}", True)
                    finally:
                        self.write_log()
                if self.update_history:
                    db_req(self.system_db_name, 'INSERT INTO conversation VALUES (?, ?, ?);',
                           (event['origin_server_ts'] // 1000, event['sender'], instruction))
                    self.update_conversation_context()
                else:
                    print(event)
                    if event['type'] == "m.room.message" and event['sender'].split(":") == "@mind_maker_agent":
                        self.update_history = True
        except Exception as e:
            self.append_log(f"Python exception\nError: {type(e).__name__}: {e}", True)

    def on_invitation(self, room_id, event):
        print(f"Invited in {room_id}!")
        utils.pprint(event)
        try:
            room = self.client.join_room(room_id)  # Automatically join the invited room
            print(f"Joined room: {room_id}")
            room.add_listener(self.on_message)
            self.rooms.append(room)
            self.channels.append(room_id)
        except Exception as e:
            print(f"Failed to join room: {room_id}")
            print(e)


    def prompt_edit(self, form):
        name = form['name']
        prompt = form['prompt']
        if 'delete_prompt' in form:
            db_req(self.system_db_name, "DELETE FROM prompts WHERE name=?",
                   (form["name"],))
        else:
            existing = db_req(self.system_db_name, "SELECT name FROM prompts WHERE name=?",
                              (form["name"],))

            if existing:
                db_req(self.system_db_name, "UPDATE prompts SET prompt=? WHERE name=?",
                       (prompt, name))
            else:
                db_req(self.system_db_name,
                       "INSERT INTO prompts (name, prompt) VALUES (?, ?)",
                       (name, prompt))

    def handle_request(self, path, request):
        print(path)
        if path == "/" or path == "":
            return render_template('agent_home.html', agent=self)
        elif path == "playground":
            return render_template('playground.html', agent=self, table_data=[])
        elif path.startswith("chatlogs"):
            log = db_req(self.system_db_name, "SELECT timestamp, message FROM bot_log ORDER BY timestamp DESC;")
            messages = list()
            for m in log:
                if len(json.loads(m[1])) == 0:
                    continue
                messages.append((m[0], json.loads(m[1])))
            return render_template('bot_log.html', agent=self, messages=messages)
        elif path.startswith("prompts_edit"):
            if request.method == 'POST':
                self.prompt_edit(request.form)
            rows = db_req(self.system_db_name, "SELECT name, prompt FROM prompts")
            prompts = list()
            for r in rows:
                prompt = re.sub(r'\r?\n', '<br>', r[1])
                prompt = re.sub(r'\'', '\\\'', prompt)
                prompts.append((r[0], prompt))
            return render_template('prompts_edit.html', agent=self, prompts=prompts)

        elif path.startswith("conversation_context"):
            if path.startswith("conversation_context/reset"):
                print("reset")
                db_req(self.system_db_name, "DELETE FROM conversation;")
                self.conversation_context = ("", "")
                self.conversation_summary = (-1, "")
                self.update_conversation_context()
            return render_template('conversation_context.html', agent=self)

        abort(404)

    def start(self):
        self.client.login(username=self.matrix_name.lstrip("@").split(":")[0],
                          password=C.MATRIX_PASSWORD,
                          sync=True)
        self.client.add_invite_listener(self.on_invitation)
        for channel in self.channels:
            if channel.endswith("matrix.org"):
                continue
            room = self.client.join_room(channel)
            self.rooms.append(room)
            room.send_text(f"Hi! Logs available at {C.HOSTNAME}")
            room.add_listener(self.on_message)
        self.client.start_listener_thread()



