import openai,os

# HOMESERVER_URL = "https://matrix-client.matrix.org"
HOMESERVER_URL = "https://matrix.iv-labs.org:8448"
# TODO nginx redirect from 80 (and https) to 8448
DOCKER_ROOT_DIR = "/app/db/"

if os.path.exists(DOCKER_ROOT_DIR):
    ROOT_DIR = DOCKER_ROOT_DIR
else:
    ROOT_DIR = "/home/yves/AI/Culture/server-agent/data/"

AGENTS_LIST_DB = f"{ROOT_DIR}/agents.db"
AGENTS_HOME = f"{ROOT_DIR}/agents/"
AGENT_USERNAME = "@dbguser1:matrix.iv-labs.org"

try:
    openai.api_key = open("/home/yves/keys/openAIAPI", "r").read().rstrip("\n")
    # MATRIX_PASSWORD = open("/home/yves/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
    MATRIX_PASSWORD = "dbguser1"
    HOSTNAME = "http://127.0.0.1:8080"
except FileNotFoundError:
    openai.api_key = open("/app/keys/openAIAPI", "r").read().rstrip("\n")
    # MATRIX_PASSWORD = open("/app/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
    MATRIX_PASSWORD = "dbguser1"
    HOSTNAME = "http://agent.iv-labs.org"
