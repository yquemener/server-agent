"""
An agent is a matrix bot that has its own context and database. It lives in a separate thread. For now it can only
be in a single matrix room at the time but the plan is that they can each have a presence in several.


"""
import json
import re
import sqlite3
import textwrap
import time
import traceback

import openai
import requests
import tiktoken
from flask import render_template, abort, redirect
from matrix_client.client import MatrixClient

import tools.sql
import utils
from utils import db_req
import configuration as C


class Agent:
    def __init__(self, room, bot):
        self.first_ts = -1
        self.bot = bot
        self.room = room

        self.conversation_summary = (-1, "")  # (timestamp of last summed up message, summary)
        self.conversation_context = ["", ""]
        self.current_log = []
        self.update_history = True

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
            "sql": tools.sql.SqlModule(self.playground_db_name)
        }
        self.update_conversation_context()

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

    def tool_dispatcher(self, s):
        # Remove the first line: it is either empty or contains a datatype because of the syntax ```json
        try:
            s = "\n".join(s.split("\n")[1:])
            d = json.loads(s)
            if d["type"]=="matrix":
                return d["type"], d["content"], ""
            content = d["content"]
            if type(content) is list:
                content = "\n".join(content)
            answer = self.tools[d["type"]].execute_query(content)
            return d["type"], d["content"], answer
        except:
            return

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

    def use_prompt(self, prompt_name, command, room, sender, ts, recursion=0):
        self.bot.client.api._send("PUT", f"/rooms/{self.room.room_id}/typing/{self.bot.client.user_id}",
                                  {"typing": True, "timeout": 30000})
        if recursion > 6:
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

        prompt_context = {
            "instruction": command,
            "username": utils.extract_username(sender),
            "conversation_context": self.conversation_context,
            "sql_summary": self.tools["sql"].context()
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
                    if tool_name == "matrix":
                        room.send_text(tool_query)
                        return
                    else:
                        print(tool_answer)
                        for query, query_result in tool_answer:
                            print(query, query_result)
                            self.bot.log_room.send_text(f"{self.bot.name}: {query}")
                            db_req(self.system_db_name, 'INSERT INTO conversation VALUES (?, ?, ?);',
                                   (ts // 1000, "mind_maker_agent", query))
                            self.bot.log_room.send_text(f"{tool_name}: {str(query_result)}")
                            db_req(self.system_db_name, 'INSERT INTO conversation VALUES (?, ?, ?);',
                                   (ts // 1000, tool_name, str(query_result)))
                        self.update_conversation_context()
                    break   # We only want to execute the first valid code
            self.use_prompt(prompt_name, command, room, sender, ts, recursion+1)

        # for code in codes:
        #     self.tool_dispatcher(code)

    def on_message(self, event):
        if event["origin_server_ts"] < self.first_ts:
            print("Ignored")
            return
        try:
            if event['type'] == "m.room.message" and event['content']['msgtype'] == "m.text":
                line = event['content']['body']
                instruction = line
                if instruction[0] == "!":
                    self.bot. client.api._send("PUT", f"/rooms/{self.room.room_id}/typing/{self.bot.client.user_id}",
                                               {"typing": True, "timeout": 30000})
                    if instruction[1] == "!":
                        self.update_history = False
                    else:
                        self.update_history = True
                    args = line.split(" ")
                    command = args[0].lstrip("!")
                    instruction = " ".join(args[1:])
                    if command == "echo":
                        self.room.send_text(instruction)
                    try:
                        prompt_name = command.lstrip("!")
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
