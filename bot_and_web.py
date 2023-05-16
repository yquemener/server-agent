import sqlite3

from matrix_client.client import MatrixClient
from flask import Flask, render_template
from threading import Thread
import time
import openai
import textwrap
import tiktoken

user_id = "mind_maker_agent"
homeserver_url = "https://matrix-client.matrix.org"
device_id = "YOLDLKCAKY"


try:
    openai.api_key = open("/home/yves/keys/openAIAPI", "r").read().rstrip("\n")
    password = open("/home/yves/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
    room_id = "!KWqtDRucLSHLiihsNl:matrix.org"
    web_host = "http://127.0.0.1:8080"
    database_name = "agent.db"
    bot_log_database = 'bot.db'
except FileNotFoundError:
    openai.api_key = open("/app/keys/openAIAPI", "r").read().rstrip("\n")
    password = open("/app/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
    room_id = "!qnfhwxqTeAtmZuerxX:matrix.org"
    web_host = "http://agent.iv-labs.org"
    database_name = "/app/db/agent.db"
    bot_log_database = '/app/db/bot.db'


# We should really turn this into a class
current_log_message = ""
conversation_context = ""
current_conversation_summary = (-1, "") # (timestamp of last summed up message, summary)

# Create the database and the table if they do not exist
conn = sqlite3.connect(bot_log_database)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS bot_log (
        timestamp TEXT NOT NULL,
        message TEXT NOT NULL
    );''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversation (
        timestamp INTEGER NOT NULL,
        author TEXT NOT NULL,
        message TEXT NOT NULL
    );
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversation_summary (
        timestamp INTEGER NOT NULL,
        message TEXT NOT NULL
    );
''')
result = cursor.execute("SELECT * FROM conversation_summary ORDER BY timestamp DESC LIMIT 1;").fetchall()
if len(result) > 0:
    current_conversation_summary = result
conn.close()

app = Flask(__name__)


def create_database_summary():
    s = ""
    # Connect to the SQLite database
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()

    # Retrieve the table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = cursor.fetchall()

    # Loop through each table and get its structure
    for name in table_names:
        table_name = name[0]
        s+=f"Table Name: {table_name}\n"

        # Get the table's columns and data types
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        s+="Columns:\n"
        for column in columns:
            column_name = column[1]
            column_type = column[2]
            s+=f"\t{column_name}: {column_type}\n"

        s+="\n"

    # Close the database connection
    conn.close()
    return s

def execute_sql_query(queries):
    conn = sqlite3.connect(database_name)
    c = conn.cursor()
    results = ""
    for i, query in enumerate(queries.strip().split(";\n")):
        try:
            query = query.strip()
            c.execute(query)
            conn.commit()
            result = c.fetchall()
            results += f"Query:{query}\nResult:{str(result)}\n\n"
        except sqlite3.Error as e:
            results += f"Query:{query}\nResult: Error\n\n"
    conn.close()
    return results

# Route pour afficher le contenu des tables
@app.route('/db')
def show_table_data():
    conn = sqlite3.connect(database_name)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Obtenir la liste des tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    table_data = {}
    for table in tables:
        table_name = table['name']
        cursor.execute(f"SELECT * FROM {table_name};")
        rows = cursor.fetchall()
        table_data[table_name] = [dict(row) for row in rows]

    conn.close()
    return render_template('tables.html', table_data=table_data)

@app.route('/bot')
def bot():
    conn = sqlite3.connect(bot_log_database)
    cursor = conn.cursor()
    messages = cursor.execute('SELECT * FROM bot_log ORDER BY timestamp DESC;').fetchall()
    conn.close()
    return render_template('bot_log.html', messages=messages)

@app.route('/')
def home():
    return render_template('index.html')


def append_log(s, p=False):
    global current_log_message
    current_log_message += str(s) + "\n----------\n"
    if p:
        print(s)


def write_log():
    global current_log_message
    conn = sqlite3.connect(bot_log_database)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO bot_log VALUES (?, ?);', (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()), current_log_message))
    conn.commit()
    conn.close()
    current_log_message = ""

def chatgpt_request(prompt):
    if type(prompt) is str:
        sprompt = prompt
        prompt=[prompt]
        sprompt = textwrap.dedent(sprompt)
    else:
        sprompt = "\t" + "\t\n".join(prompt)
    append_log(f"gpt prompt\n{sprompt}")
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

    rep = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": c} for c in prompt],
        temperature=0.1,
        max_tokens=4000-len(enc.encode(sprompt)),
    )
    body = rep["choices"][0]["message"]["content"]
    s = "\t"+'\n\t'.join(body.split('\n'))
    s += f'\nfinish_reason {rep["choices"][0]["finish_reason"]}\n'
    s += f'tokens {rep["usage"]}\n'
    append_log(f"gpt answer\n{s}", True)

    bs = body.split("```")
    code_blocks=list()
    if len(bs) > 1:
        for i in range(1,len(bs),2):
            code_blocks.append(bs[i])
    return body, code_blocks



def on_dis(instruction, room, username, use_context=True):
    global conversation_context
    append_log(f"Instruction: {instruction}", True)

    username = extract_username(username)
    if use_context:
        convcontxt = conversation_context
    else:
        convcontxt = ""
    db_context = create_database_summary()
    prompt = list()
    prompt.append(
f"""You are a very competent specialized bot that retrieves in a database the information necessary to solve a task given by a user named {username}.
The task {username} gave us is:
'''
{instruction}
''' 
The current conversation context is:
'''
{convcontxt}
'''
The current structure of the database is:\n {db_context}
You should do the task {username} gave us but rather think about the information necessary to solve this task and form SQL request to retrieve this information. 
First, list the information you need then formulate SQL requests to acquire it. 
Only generate SELECT SQL requests. Do not generate ones that modify the database or the tables in it like DROP, ALTER, INSERT, UPDATE or REMOVE.
Put ``` around your SQL requests.
""")
    sprompt = "\t" + "\t\n".join(prompt)
    append_log(f"gpt prompt\n{sprompt}")

    rep = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user", "content":c} for c in prompt],
        temperature=0.1
        # max_tokens=500,
    )
    body = rep["choices"][0]["message"]["content"]
    s = "\t"+'\n\t'.join(body.split('\n'))
    s += f'\nfinish_reason {rep["choices"][0]["finish_reason"]}\n'
    s += f'tokens {rep["usage"]}\n'
    append_log(f"gpt answer\n{s}", True)

    bs = body.split("```")
    sql_context = ""
    if len(bs) > 1:
        if len(bs)>3:
            for i in range(1,len(bs),2):
                query = bs[i]
                qres = execute_sql_query(query)
                append_log(f"sql\n{qres}")
                sql_context += qres
        else:
            query = bs[1]
            qres = execute_sql_query(query)
            append_log(f"sql\n{qres}")
            sql_context += qres

    prompt = list()
    prompt.append(
f"""You are a very competent specialized bot that maintains a database about a community project.
User named{username} gave us the following task:
'''
{instruction}
''' 

The current conversation context is:
'''
{convcontxt}
'''

The current structure of the database is:
{db_context}

In order to help, the following SQL queries were made by an information retrieval agent:
{sql_context}

First, determine whether or not the task requires more SQL requests than the ones the retrieval agent already did.
If yes, generate only the necessary additional requests, if any. Do not repeat the requests of the retrieval agent if they were successful. 
Put ``` around your own SQL requests.
After this, if the task requires to give some information to {username}, write the information he required after the string "Output: ".
{username} does not want to run SQL requests, they want to read the actual result of queries, formatted in natural language. 
Conclude the message by a single sentence starting with "Dear {username}," and explaining briefly if the task was successfully done.
""")
    sprompt = "\t" + "\t\n".join(prompt)
    append_log(f"gpt prompt\n{sprompt}")
    rep = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": c} for c in prompt],
        temperature=0.1
        # max_tokens=500,
    )
    body = rep["choices"][0]["message"]["content"]
    s = "\t"+'\n\t'.join(body.split('\n'))
    s += f'\nfinish_reason {rep["choices"][0]["finish_reason"]}\n'
    s += f'tokens {rep["usage"]}\n'
    append_log(f"gpt answer\n\n{s}", True)

    bs = body.split("```")
    sql_answer = ""
    if len(bs) > 1:
        if len(bs)>3:
            for i in range(1,len(bs),2):
                query = bs[i]
                qres = execute_sql_query(query)
                append_log(f"sql\n{qres}")
                sql_answer += qres
        else:
            query = bs[1]
            qres = execute_sql_query(query)
            append_log(f"sql\n{qres}")
            sql_answer += qres
    write_log()
    try:
        output = body.split("Output:")[1].split("Dear user,")[0]
        room.send_text(output)
    except IndexError:
        room.send_text(body)
    if len(sql_answer.strip()) > 0:
        room.send_text(sql_answer)

# Turns a number of seconds into a human-readable approximation
def format_time_interval(seconds):
    intervals = [
        ('days', 86400),
        ('hours', 3600),
        ('minutes', 60),
        ('seconds', 1)]
    result = []
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append(f"{value} {name}")
    return result[0]


def extract_username(s):
    name = s.lstrip("@")
    server = s.split(":")[-1]
    if server == "matrix.org":
        return name.split(":")[0]
    else:
        return name


def context_summarization(page, current_summary):
    if len(current_summary) > 0:
        prompt = f"""\
        Please provide a new summary of the conversation. The summary should be succinct and include all the important information given in the conversation.  
        This is the summary of the conversation so far:
        START SUMMARY
        {current_summary}
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

    answer, codes = chatgpt_request(prompt)
    return answer

def update_conversation_context():
    global conversation_context
    global current_conversation_summary

    max_context_size = 2000

    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    token_size = len(enc.encode(current_conversation_summary[1]))
    previous_ts = current_conversation_summary[0]
    page = ""
    conn = sqlite3.connect(bot_log_database)
    cursor = conn.cursor()
    messages = cursor.execute('SELECT timestamp, author, message FROM conversation WHERE timestamp > ? ORDER BY timestamp ASC;', (previous_ts,)).fetchall()
    conn.close()
    for m in messages:
        ts, author, message = m

        if "Hi! Logs available at" in message:
            continue
        line = ""
        name = extract_username(author)
        if ts-previous_ts > 60 and previous_ts > 0:
            delta = format_time_interval(m[0]-previous_ts)
            line += f"{delta} later\n"
        line += f"{name}: {message}\n--\n"
        message_token_size = len(enc.encode(line))

        if token_size + message_token_size > max_context_size:
            current_conversation_summary = (ts, context_summarization(page, current_conversation_summary[1]))
            conn = sqlite3.connect(bot_log_database)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO conversation_summary VALUES (?, ?);', current_conversation_summary)
            conn.close()
            page = ""
            token_size = len(enc.encode(current_conversation_summary[1]))
        else:
            token_size = token_size + message_token_size
        page += line
        previous_ts = ts
    conversation_context = (current_conversation_summary[1], page)

@app.route('/conversation_context')
def on_conversation_context():
    global conversation_context
    return render_template('conversation_context.html', context=conversation_context)
#
#
# def prepare_history():
#     enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
#     max_page_size = 3800
#     max_context_size = 2000
#
#     conn = sqlite3.connect(bot_log_database)
#     cursor = conn.cursor()
#     messages = cursor.execute('SELECT timestamp, author, message FROM conversation ORDER BY timestamp ASC;').fetchall()
#
#     previous_ts=messages[0][0]
#     current_summary = ""
#     page = ""
#     toksize = 0
#     for m in messages:
#         message_token_size = len(enc.encode(m))
#         if toksize + message_token_size > max_page_size:
#             current_summary = context_summarization(page, current_summary)
#             page = ""
#         else:
#             toksize += message_token_size
#         name = extract_username(m[1])
#         message = m[2]
#         if "Hi! Logs available at" in message:
#             continue
#         if m[0]-previous_ts>60:
#             delta = format_time_interval(m[0]-previous_ts)
#             page += f"{delta} later\n"
#         page += f"{name}: {message}\n"
#         previous_ts = m[0]
#     conn.close()
#     return page, current_summary






def on_pdca(command, room, sender):
    global conversation_context
    print(command)
    append_log(f"instruction\n{command}")
    username = extract_username(sender)

    plan_prompt = f"""\
        You are a planning assistant named mind_maker_agent. Your task is to form a plan to solve the task given by the user {username}.
        Make a list of the actions necessary to achieve the task.
        The possible actions are:
        1. Query a database for additional information
        2. Ask a human
        3. Execute a SQL query to modify a database
        Return the plan as a list, for each item of the list, start with the action type number.
        Your plan should not have more than 8 steps.
        Steps should be explained in one sentence. Another agent will execute them.
        If some information is missing to make a full plan to do the task, plan for the information acquisition and conclude your plan with a "4: plan again" step.
        If 8 steps is to short to complete the tasks, put the first 7 steps of the plan and conclude your plan with a "4: plan again" step.
        
        The task {username} gave us is: {command}
        END TASK
        Here is a summary of the conversation so far:
        '''
        {conversation_context[0]}
        '''
        Here are the last messages in the conversation:
        '''
        {conversation_context[1]}
        '''
        """
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    print(len(enc.encode(plan_prompt)))

    # Plan
    answer, codes = chatgpt_request(plan_prompt)
    room.send_text(answer)

def on_void(command, room):
    append_log(f"Instruction: {command}", True)
    answer, codes = chatgpt_request(command)
    room.send_text(answer)
    write_log()



def on_message(room, event):
    print(event)

    if event['type'] == "m.room.message" and event['content']['msgtype'] == "m.text":
        conn = sqlite3.connect(bot_log_database)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO conversation VALUES (?, ?, ?);', (event['origin_server_ts'] // 1000,
                                                                      event['sender'],
                                                                      event['content']['body']))
        conn.commit()
        conn.close()
        update_conversation_context()

        if event['content']['body'].startswith("!echo"):
            response = event['content']['body'][5:]
            room.send_text(response)
        try:
            # Finds the SQL requests to do using context
            if event['content']['body'].startswith("!dis"):
                command = event['content']['body'][4:]
                on_dis(command, room, event['sender'])
            # Finds the SQL requests to do without using context
            elif event['content']['body'].startswith("!nc"):
                command = event['content']['body'][3:]
                on_dis(command, room, event['sender'], use_context=False)
            # Implements a plan do check act loop
            elif event['content']['body'].startswith("!pdca"):
                command = event['content']['body'][5:]
                on_pdca(command, room, event['sender'])
            # Directly passes the request with no other information in the prompt
            elif event['content']['body'].startswith("!void"):
                command = event['content']['body'][5:]
                on_void(command, room)
        except openai.error.RateLimitError:
            append_log(f"openai\nRateLimitError", True)
            write_log()
        except openai.error.InvalidRequestError as e:
            append_log(f"openai\nInvalidRequestError: {str(e)}", True)
            write_log()

def matrix_bot():
    client = MatrixClient(homeserver_url)
    client.login(username=user_id, password=password, sync=True)
    room = client.join_room(room_id)
    room.send_text(f"Hi! Logs available at {web_host}")
    room.add_listener(on_message)
    client.start_listener_thread()

Thread(target=matrix_bot).start()
app.run(host='0.0.0.0', port=8080)
