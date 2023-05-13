import sqlite3

from matrix_client.client import MatrixClient
from flask import Flask, render_template
from threading import Thread
import time
import openai


user_id = "mind_maker_agent"
homeserver_url = "https://matrix-client.matrix.org"
device_id = "YOLDLKCAKY"


try:
    openai.api_key = open("/home/yves/keys/openAIAPI", "r").read().rstrip("\n")
    password = open("/home/yves/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
    room_id = "!KWqtDRucLSHLiihsNl:matrix.org"
    web_host = "http://127.0.0.1:8080"
    database_name = "agent.db"
    message_database = 'messages.db'
except FileNotFoundError:
    openai.api_key = open("/app/keys/openAIAPI", "r").read().rstrip("\n")
    password = open("/app/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
    room_id = "!qnfhwxqTeAtmZuerxX:matrix.org"
    web_host = "http://agent.iv-labs.org"
    database_name = "/app/db/agent.db"
    message_database = '/app/db/messages.db'


current_log_message=""

# Create the database and the table if they do not exist
conn = sqlite3.connect(message_database)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        timestamp TEXT NOT NULL,
        message TEXT NOT NULL
    );
''')
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
    conn = sqlite3.connect(message_database)
    cursor = conn.cursor()
    messages = cursor.execute('SELECT * FROM messages ORDER BY timestamp DESC;').fetchall()
    conn.close()
    return render_template('messages.html', messages=messages)

@app.route('/')
def home():
    return render_template('index.html')


def append_log(s):
    global current_log_message
    current_log_message += str(s) + "\n----------\n"
    print(s)


def write_log():
    global current_log_message
    conn = sqlite3.connect(message_database)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages VALUES (?, ?);', (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()), current_log_message))
    conn.commit()
    conn.close()
    current_log_message=""

def on_dis(instruction, room):
    append_log(f"Instruction: {instruction}")

    db_context = create_database_summary()
    prompt = list()
    prompt.append(
f"""You are a very competent specialized bot that retrieves in a database the information necessary to solve a task given by a user.
The task user2 gave us is:
'''
{instruction}
''' 
The current structure of the database is:\n {db_context}
You should do the task user2 gave us but rather think about the information necessary to solve this task and form SQL request to retrieve this information. 
First, list the information you need then formulate SQL requests to acquire it. 
Do not generate SQL requests that modify the database or the tables in it.
Only do read-only requests. Do not delete or insert records with these requests. Do not alter tables.
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
    s="\t"+'\n\t'.join(body.split('\n'))
    append_log(f"gpt answer\n{s}")

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
User2 gave us the following task:
'''
{instruction}
''' 
The current structure of the database is:
{db_context}

In order to help, the following SQL queries were made by an information retrieval agent:
{sql_context}

First, determine whether or not the task requires more SQL requests than the ones the retrieval agent already did.
If yes, generate only the necessary additional requests, if any. Do not repeat the requests of the retrieval agent if they were successful. 
Put ``` around your own SQL requests.
After this, if the task requires to give some information to user2, write the information he required after the string "Output: ".
User2 does not want to run SQL requests, they want to read the actual result of queries, formatted in natural language. 
Conclude the message by a single sentence starting with "Dear user," and explaining briefly if the task was successfully done.
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
    append_log(f"gpt answer\n\n{s}")

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

def on_message(room, event):
    print(event)
    if event['type'] == "m.room.message" and event['content']['msgtype'] == "m.text":
        if event['content']['body'].startswith("!echo"):
            response = event['content']['body'][5:]
            room.send_text(response)

        if event['content']['body'].startswith("!dis"):
            command = event['content']['body'][4:]
            try:
                on_dis(command, room)
            except openai.error.RateLimitError:
                append_log(f"openai\nRateLimitError")
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
