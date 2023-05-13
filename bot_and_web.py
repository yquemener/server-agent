import sqlite3

from matrix_client.client import MatrixClient
from flask import Flask, render_template
from threading import Thread
import time
import openai

database_name = "agent.db"
user_id = "mind_maker_agent"
homeserver_url = "https://matrix-client.matrix.org"
device_id = "YOLDLKCAKY"

try:
    openai.api_key = open("/home/yves/keys/openAIAPI", "r").read().rstrip("\n")
    password = open("/home/yves/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
    room_id = "!KWqtDRucLSHLiihsNl:matrix.org"
except FileNotFoundError:
    openai.api_key = open("/app/keys/openAIAPI", "r").read().rstrip("\n")
    password = open("/app/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
    room_id = "!qnfhwxqTeAtmZuerxX:matrix.org"

message_database = 'messages.db'
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
    for i, query in enumerate(queries.split(";\n")):
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

@app.route('/')
def home():
    conn = sqlite3.connect(message_database)
    cursor = conn.cursor()
    messages = cursor.execute('SELECT * FROM messages ORDER BY timestamp DESC;').fetchall()
    conn.close()
    return render_template('messages.html', messages=messages)


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

    context = create_database_summary()
    prompt = list()
    prompt.append("""You are a very competent specialized bot that adds context to a task given by a user by retrieving information from a database. You should not answer the user's question but rather think about the additional context that may be contained in the database and that could be useful for the task. You need to create a SQL query able to gather additional context for another agent that will try answer that question. Your answer should absolutely contain a SQL query to try and gather more information for this task. Make sure you correctly enclose SQL with ```""")
    prompt.append(f"Current structure of the database:\n {context}")
    prompt.append(f"{instruction}")

    sprompt = "\t" + "\t\n".join(prompt)
    append_log(f"<b>gpt prompt</b><br>{sprompt}")

    rep = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user", "content":c} for c in prompt],
        temperature=0.1
        # max_tokens=500,
    )
    body = rep["choices"][0]["message"]["content"]
    s="\t"+'\n\t'.join(body.split('\n'))
    append_log(f"<b>gpt answer</b><br>{s}")

    bs = body.split("```")
    sql_context = ""
    if len(bs) > 1:
        if len(bs)>3:
            for i in range(1,len(bs),2):
                query = bs[i]
                qres = execute_sql_query(query)
                append_log(f"<b>sql</b><br>{qres}")
                sql_context += qres
        else:
            query = bs[1]
            qres = execute_sql_query(query)
            append_log(f"<b>sql</b><br>{qres}")
            sql_context += qres

    prompt = list()
    prompt.append("""You are a very competent specialized bot that maintains a database about the community project. Your answer should contain the SQL query translating the instructions from the user. You should try really hard to produce a SQL request in your answer. Make sure you correctly enclose SQL with ```""")
    prompt.append(f"""Current context (may or may not be relevant): here is the result of some queries on the database: {sql_context}""")
    prompt.append(instruction)
    sprompt = "\t" + "\t\n".join(prompt)
    append_log(f"<b>gpt prompt</b><br>{sprompt}")
    rep = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": c} for c in prompt],
        temperature=0.1
        # max_tokens=500,
    )
    body = rep["choices"][0]["message"]["content"]
    s = "\t"+'\n\t'.join(body.split('\n'))
    append_log(f"<b>gpt answer</b><br>\n{s}")

    bs = body.split("```")
    sql_answer = ""
    if len(bs) > 1:
        if len(bs)>3:
            for i in range(1,len(bs),2):
                query = bs[i]
                qres = execute_sql_query(query)
                append_log(f"<b>sql</b><br>{qres}")
                sql_answer += qres
        else:
            query = bs[1]
            qres = execute_sql_query(query)
            append_log(f"<b>sql</b><br>{qres}")
            sql_answer += qres
    write_log()
    room.send_text(sql_answer)

def on_message(room, event):
    print(event)
    if event['type'] == "m.room.message" and event['content']['msgtype'] == "m.text":
        if event['content']['body'].startswith("!echo"):
            response = event['content']['body'][5:]
            room.send_text(response)

        if event['content']['body'].startswith("!dis"):
            command = event['content']['body'][4:]
            on_dis(command, room)

def matrix_bot():
    client = MatrixClient(homeserver_url)
    client.login(username=user_id, password=password, sync=True)
    room = client.join_room(room_id)
    room.send_text("Hi!")
    room.add_listener(on_message)
    client.start_listener_thread()

Thread(target=matrix_bot).start()
app.run(host='0.0.0.0', port=8080)
