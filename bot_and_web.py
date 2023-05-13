import sqlite3

from matrix_client.client import MatrixClient
from flask import Flask, render_template
from threading import Thread
import time
import openai

database_name = "agent.db"
user_id = "mind_maker_agent"
password = open("/home/yves/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
homeserver_url = "https://matrix-client.matrix.org"
room_id = "!qnfhwxqTeAtmZuerxX:matrix.org"
device_id = "YOLDLKCAKY"
openai.api_key = open("/home/yves/keys/openAIAPI", "r").read().rstrip("\n")

message_database = 'messages.db'

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

def execute_sql_query(queries):
    conn = sqlite3.connect(database_name)
    c = conn.cursor()
    results = ""
    for i, query in enumerate(queries.split(";\n")):
        try:
            c.execute(query)
            conn.commit()
            result = c.fetchall()
            results += f"Query:\n{query}\n\nResult:\n{str(result)}\n"
        except sqlite3.Error as e:
            results += f"Query:\n{query}\n\nResult: Error\n"
            print(e)
    conn.close()
    return results

@app.route('/')
def home():
    conn = sqlite3.connect(message_database)
    cursor = conn.cursor()
    messages = cursor.execute('SELECT * FROM messages ORDER BY timestamp DESC;').fetchall()
    conn.close()
    return render_template('messages.html', messages=messages)

def room_send(room, message):
    room.send_text(message)
    conn = sqlite3.connect(message_database)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages VALUES (?, ?);', (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()), message))
    conn.commit()
    conn.close()


def on_dis(instruction, room):
    print(f"Instruction: {instruction}")

    context = execute_sql_query("SELECT * FROM sqlite_schema;")
    prompt = list()
    prompt.append("""You are a very competent specialized bot that adds context to a task given by a user by retrieving information from a database. You should not answer the user's question but rather think about the additional context that may be contained in the database and that could be useful for the task. You need to create a SQL query able to gather additional context for another agent that will try answer that question. Your answer should absolutely contain a SQL query to try and gather more information for this task. Make sure you correctly enclose SQL with ```""")
    prompt.append(f"Current context (may or may not be relevant): here is the result of some queries on the database: {context}")
    prompt.append(f"{instruction}")

    rep = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user", "content":c} for c in prompt],
        temperature=0.1
        # max_tokens=500,
    )
    print(rep)
    body = rep["choices"][0]["message"]["content"]
    room_send(room, f"Context maker answer: {body}")
    bs = body.split("```")
    if len(bs) > 1:
        query = bs[1]
        qres = execute_sql_query(query)
        print(qres)
        room_send(room, f"Context SQL request answer: {qres}")
        context = f"Context: \nQuery: {query}\nQuery result: {qres}"
    else:
        context = ""
    print(context)

    prompt = list()
    prompt.append("""You are a very competent specialized bot that maintains a database about the community project. Your answer should contain the SQL query translating the instructions from the user. You should try really hard to produce a SQL request in your answer. Make sure you correctly enclose SQL with ```""")
    prompt.append(f"""Current context (may or may not be relevant): here is the result of some queries on the database: {context}""")
    prompt.append(instruction)
    rep = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": c} for c in prompt],
        temperature=0.1
        # max_tokens=500,
    )
    print(rep)
    body = rep["choices"][0]["message"]["content"]
    room_send(room, f"Final agent response: {body}")
    bs = body.split("```")
    if len(bs) > 1:
        query = bs[1]
        qres = execute_sql_query(query)
        print(qres)
        room_send(room, f"Final SQL answer: {qres}")
    print(context)



def on_message(room, event):
    if event['type'] == "m.room.message" and event['content']['msgtype'] == "m.text":
        if event['content']['body'].startswith("!echo"):
            response = event['content']['body'][5:]
            room_send(room, response)

        if event['content']['body'].startswith("!dis"):
            command = event['content']['body'][4:]
            on_dis(command, room)

def matrix_bot():
    client = MatrixClient(homeserver_url)
    client.login(username=user_id, password=password, sync=True)
    room = client.join_room(room_id)
    room_send(room, "Hi!")
    room.add_listener(on_message)
    client.start_listener_thread()

Thread(target=matrix_bot).start()
app.run(host='0.0.0.0', port=8080)
