import openai,os

# HOMESERVER_URL = "https://matrix-client.matrix.org"
HOMESERVER_URL = "https://matrix.iv-labs.org:8448"
DOCKER_ROOT_DIR = "/app/db/"

if os.path.exists(DOCKER_ROOT_DIR):
    ROOT_DIR = DOCKER_ROOT_DIR
else:
    ROOT_DIR = "/home/yves/AI/Culture/server-agent/data/"

BOT_DB = f"{ROOT_DIR}/bot.db"
AGENTS_HOME = f"{ROOT_DIR}/agents/"

LOG_ROOM = "!ezhJHIWSMUNzYznSQo:matrix.org"

try:
    openai.api_key = open("/home/yves/keys/openAIAPI", "r").read().rstrip("\n")
    BOT_USERNAME = "@mind_maker_bot_local:matrix.iv-labs.org"
    MATRIX_PASSWORD = open("/home/yves/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
    HTTP_PASSWORD = open("/home/yves/keys/MindMakerHttpPassword", "r").read().rstrip("\n")
    HOSTNAME = "http://127.0.0.1:8080"
    PLAYGROUND_URL = "http://127.0.0.1:5481"
    JSON_LOG = True
except FileNotFoundError:
    openai.api_key = open("/app/keys/openAIAPI", "r").read().rstrip("\n")
    BOT_USERNAME = "@mind_maker_bot:matrix.iv-labs.org"
    MATRIX_PASSWORD = open("/app/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
    HTTP_PASSWORD = open("/app/keys/MindMakerHttpPassword", "r").read().rstrip("\n")
    HOSTNAME = "http://agent.iv-labs.org"
    PLAYGROUND_URL = "http://agent.iv-labs.org:5481"
    JSON_LOG = False
