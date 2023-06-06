"""
An agent is a matrix bot that has its own context and database. It lives in a separate thread. For now it can only
be in a single matrix room at the time but the plan is that they can each have a presence in several.


"""
import json
import pickle
import re
import sqlite3
import textwrap
import time
import traceback
import types
from collections import defaultdict
from datetime import datetime

import openai
import requests
import tiktoken
from flask import render_template, abort, redirect
from matrix_client.client import MatrixClient
from jinja2 import Template, TemplateSyntaxError

import tools.sql
import tools.flask
import utils
from utils import db_req
import configuration as C

OPENAI_ERROR_RETRIES = 4        # TODO How many times do we retry after an OpenAI Rate Error?


chat_dbg_log = [
    # json.load(open("dict_20230606144810.json")),
    # json.load(open("dict_20230606144831.json")),
    json.load(open("dict_20230606153145.json"))
]

class Thought:
    def __init__(self, agent):
        self.context = defaultdict(str)
        self.agent = agent

    # Restate goal
    # Produce a python metric

        self.db_context = ""

        self.original_goal = ""
        self.restated_goal = ""
        self.metric_for_success = ""
        self.steps = list()
        self.tools_conversation = list()

    def start_thought(self, steps_limit=3):
        self.agent.create_log()
        self.agent.append_log(f"Think: {self.context['goal']}", True)
        self.do_step("intro")
        # self.do_step("code_metric")
        step_i = 0
        try:
            metric = self.eval_metric()
        except Exception:
            metric = 1
        print(f"Metric = {metric}", step_i, self.context.get("status", "ok"))

        while(self.context.get("status", "") != "failed" and
              self.context.get("status", "") != "ok" and
              step_i < steps_limit):
            print(f"Metric = {self.eval_metric()}")
            step_i += 1
            self.do_step("next_action")
        self.do_step("present_result")

    def update_context(self):
        self.context["tool_conversation"] = self.tools_conversation
        self.context["db_context"] = self.agent.tools["sql"].context()

    def do_step(self, step_name):
        self.agent.append_log(f"Think, step #{len(self.steps)} ({step_name}):", True)
        self.steps.append(step_name)
        print(f"Context:\n{self.context}\n\n")
        prompt = db_req(self.agent.bot.bot_db,
                        'SELECT prompt FROM prompts WHERE name = ?;', (step_name,))
        self.update_context()

        # env = Environment()
        # try:
        #     env.parse(template_string)
        #     print("The template is valid.")
        # except TemplateSyntaxError as e:
        #     error_line = e.lineno
        #     error_message = e.message
        #     print(f"The template is invalid. Error at line {error_line}: {error_message}")

        try:
            template = Template(prompt[0][0])
        except TemplateSyntaxError as e:
            error_line = e.lineno
            error_message = e.message
            self.agent.bot.log_room.send_text(f"The template is invalid. Error at line {error_line}: {error_message}")
            print(f"The template is invalid. Error at line {error_line}: {error_message}")

        self.update_context()
        populated_prompt = template.render(**{'c': types.SimpleNamespace(**self.context)})
        # populated_prompt = prompt.format(**{'c': types.SimpleNamespace(**self.context)})
        s,_ = self.agent.chatgpt_request(populated_prompt)
        d = utils.extract_json(s)
        if not d or type(d) is not dict:
            self.fail()
        else:
            if "type" in d.keys() and "content" in d.keys():
                print("DDD", d)
                toolname, _, answer = self.agent.tool_dispatcher(d)
                print("EEE", toolname, answer)
                if toolname.startswith("matrix"):
                    self.agent.room.send_text(str(answer))
                if type(answer) is list:
                    for a in answer:
                        self.tools_conversation.append((toolname,)+a)
                else:
                    if type(answer) is tuple:
                        self.tools_conversation.append((toolname,) + answer)
                    else:
                        self.tools_conversation.append((toolname, answer))
            for k, v in d.items():
                self.context[k] = v

    def eval_metric(self):
        locals_dict = {}
        globals_dict = {}
        if "metric_code" not in self.context:
            return -1
        program_string = self.context["metric_code"]

        # Execute the program string within the locals dictionary
        exec(program_string, globals(), locals_dict)

        # Get the metric function from the locals dictionary
        metric_func = locals_dict.get('metric')

        if metric_func:
            # Call the metric function to get the number
            result = metric_func(self.agent.playground_db_name)
            return result
        else:
            self.fail()
            return -1

    def fail(self):
        # self.context["status"] = "failed"
        pass


class Agent:
    def __init__(self, room, bot):
        self.first_ts = -1
        self.bot = bot
        self.room = room

        self.conversation_summary = (-1, "")  # (timestamp of last summed up message, summary)
        self.conversation_context = ["", ""]
        self.current_log = []
        self.log_in_db = False
        self.last_insert_id = None
        self.update_history = True
        self.temperature = 0.1
        self.request_finished = False

        self.system_db_name = f"{C.ROOT_DIR}/agent_{room.room_id}.db"
        self.playground_db_name = f"{C.ROOT_DIR}/agent_playground_{room.room_id}.db"

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

        result = db_req(self.system_db_name,
                        "SELECT * FROM conversation_summary ORDER BY timestamp DESC LIMIT 1;")
        if len(result) > 0:
            self.conversation_summary = result[0]

        self.tools = {
            "sql": tools.sql.SqlModule(self.playground_db_name),
            "flask": tools.flask.FlaskModule(f"{C.ROOT_DIR}/playground_server/")
        }
        self.update_conversation_context()
        self.bot.client.api._send("PUT", f"/rooms/{self.room.room_id}/typing/{self.bot.client.user_id}",
                                  {"typing": False, "timeout": 3000})

    def append_log(self, s, p=False):
        self.current_log.append(str(s))

        if self.log_in_db:
            # If the log is already in db, update the last inserted row
            self.update_log()
        else:
            # If the log is not in db, insert a new row and set log_in_db to True
            self.create_log()
            self.log_in_db = True

        if p:
            print(s)

    def create_log(self):
        with sqlite3.connect(self.system_db_name) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO bot_log VALUES (?, ?);',
                      (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()), json.dumps(self.current_log)))
            self.last_insert_id = c.lastrowid  # Get the ID of the inserted row
            conn.commit()

    def update_log(self):
        with sqlite3.connect(self.system_db_name) as conn:
            c = conn.cursor()
            c.execute('UPDATE bot_log SET message = ? WHERE rowid = ?;', (json.dumps(self.current_log), self.last_insert_id))
            conn.commit()

    def write_log(self):
        self.current_log = []
        self.log_in_db = False

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

    def tool_dispatcher(self, d):
        self.append_log(f"Tool {d['type']} request:\n{d['content']}")
        if d["type"].startswith("matrix_") or d["type"] == "matrix":
            self.room.send_text(str(d.get("content", "...")))
            return d["type"], d["content"], ""
        if d["type"].startswith("!"):
            return d["type"], d["content"], ""
        content = d["content"]
        if type(content) is list:
            content = "\n".join(content)
        answer = self.tools[d["type"]].execute_query(content)
        if type(answer) is list:
            for q, a in answer:
                self.append_log(f"Tool {d['type']} request:\n{q}", True)
                self.append_log(f"Tool {d['type']} answer:\n{a}", True)
        else:
            self.append_log(f"Tool {d['type']} answer:\n{answer}", True)
        return d["type"], d["content"], answer

    def chatgpt_request(self, prompt):
        if type(prompt) is str:
            sprompt = prompt
            prompt = [prompt]
            sprompt = textwrap.dedent(sprompt)
        else:
            sprompt = "\t" + "\t\n".join(prompt)
        self.append_log(f"gpt prompt\n{sprompt}")
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

        global chat_dbg_log
        if len(chat_dbg_log) > 0:
            s = chat_dbg_log.pop(0)["choices"][0]["message"]["content"]
            self.append_log(f"gpt answer\n{s}", True)
            return s, []
        rep = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": c} for c in prompt],
            temperature=self.temperature,
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

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"dict_{timestamp}.json"

        with open(filename, "w") as file:
            json.dump(rep, file,indent=4, sort_keys=True)
        return body, code_blocks

    def use_prompt(self, prompt_name, command, room, sender, ts, recursion=0):
        print(self.temperature)
        if self.request_finished:
            if recursion==0:
                self.bot.client.api._send("PUT", f"/rooms/{self.room.room_id}/typing/{self.bot.client.user_id}",
                                          {"typing": False, "timeout": 30000})
            return

        self.bot.client.api._send("PUT", f"/rooms/{self.room.room_id}/typing/{self.bot.client.user_id}",
                                  {"typing": True, "timeout": 30000})
        if recursion > 3:
            room.send_text("Recursion limit reached")
            self.bot.client.api._send("PUT", f"/rooms/{self.room.room_id}/typing/{self.bot.client.user_id}",
                                      {"typing": False, "timeout": 3000})
            return
        # Runs a prompt that's from the prompts database
        self.append_log(f"Instruction: {prompt_name} {command}", True)
        prompt = db_req(self.bot.bot_db,
                        'SELECT prompt FROM prompts WHERE name = ?;', (prompt_name,))
        if len(prompt) == 0:
            return
        prompt = prompt[0][0]

        conversation_context_str = ""

        if self.conversation_context[0] != "":
            conversation_context_str += "Here is a summary of the conversation so far:\n"
            conversation_context_str += "'''\n"
            conversation_context_str += self.conversation_context[0]+"\n"
            conversation_context_str += "'''\n"

        if self.conversation_context[1] != "":
            conversation_context_str += "Here are the last messages in the conversation:\n"
            conversation_context_str += "'''\n"
            conversation_context_str += self.conversation_context[1]+"\n"
            conversation_context_str += "'''\n"


        prompt_context = {
            "instruction": command,
            "username": utils.extract_username(sender),
            "conversation_context": self.conversation_context,
            "conversation_context_str": conversation_context_str,
            "sql_summary": self.tools["sql"].context(),
            "sql_conversation": self.tools["sql"].conversation()
        }
        populated_prompt = prompt.format(**prompt_context)
        answer, codes = self.chatgpt_request(populated_prompt)
        if len(codes) == 0:
            room.send_text(answer)
        else:
            for code in codes:
                ret = self.tool_dispatcher(code)
                if ret:
                    tool_name, tool_query, tool_answer = ret
                    print("__", ret)
                    if tool_name.startswith("matrix_") or tool_name == "matrix":
                        room.send_text(tool_query)
                        self.request_finished = True
                        return
                    elif tool_name == "Error":
                        room.send_text(tool_query)
                        self.request_finished = True
                        return
                    elif tool_name.startswith("!"):
                        self.use_prompt(tool_name.lstrip("!"), tool_query, room, self.bot.name, ts, recursion + 1)
                        self.bot.log_room.send_text(f"{self.bot.name}: Sending prompt {tool_name} with instruction {tool_query}")
                    else:
                        if tool_answer:
                            for query, query_result in tool_answer:
                                print(query, query_result)
                                self.bot.log_room.send_text(f"{self.bot.name}: {query}")
                                self.bot.log_room.send_text(f"{tool_name}: {str(query_result)}")
                    break   # We only want to execute the first valid code
            self.use_prompt(prompt_name, command, room, sender, ts, recursion+1)

    def on_message(self, event):
        if event["origin_server_ts"] < self.first_ts:
            print("Ignored")
            return
        try:
            if event['type'] == "m.room.message" and event['content']['msgtype'] == "m.text":
                line = event['content']['body']
                instruction = line
                if instruction == "":
                    return
                if instruction[0] == "!":
                    self.bot.client.api._send("PUT", f"/rooms/{self.room.room_id}/typing/{self.bot.client.user_id}",
                                               {"typing": True, "timeout": 30000})
                    self.request_finished = False
                    if instruction[1] == "!":
                        self.update_history = False
                    else:
                        self.update_history = True
                    args = line.split(" ")
                    command = args[0].lstrip("!")
                    try:
                        self.temperature = float(args[1])
                    except:
                        self.temperature = 0.1
                    instruction = " ".join(args[1:])
                    if command == "echo":
                        self.room.send_text(instruction)
                    elif command == "think":
                        thought = Thought(self)
                        thought.context["username"] = utils.extract_username(event['sender'])
                        thought.context["goal"] = instruction
                        thought.context["conversation_context"] = self.conversation_context
                        thought.context["sql_summary"] = self.tools["sql"].context(),
                        thought.context["sql_conversation"] = self.tools["sql"].conversation()
                        thought.start_thought()
                    try:
                        prompt_name = command.lstrip("!")
                        for t in self.tools.values():
                            t.reset()
                        self.use_prompt(prompt_name, instruction, self.room, event['sender'], event['origin_server_ts'])

                    except openai.error.RateLimitError:
                        self.append_log(f"openai\nRateLimitError", True)
                        self.update_history = False
                        self.room.send_text("OpenAI RateLimitError (Open source: quand??)")
                    except openai.error.InvalidRequestError as e:
                        self.append_log(f"openai\nInvalidRequestError: {str(e)}", True)
                        self.update_history = False
                        self.room.send_text("OpenAI InvalidRequestError (Probablement une erreur de programmation/prompt)")
                    except Exception as e:
                        self.append_log(f"Python exception\nError: {type(e).__name__}: {e}", True)
                        self.room.send_text(f"Python exception:\n{traceback.format_exc()}")
                        self.update_history = False
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
            self.append_log(f"Python exception\nError: {traceback.format_exc()}", True)
        finally:
            try:
                self.bot.client.api._send("PUT", f"/rooms/{self.room.room_id}/typing/{self.bot.client.user_id}",
                                          {"typing": False, "timeout": 3000})
                pass
            except:
                pass
