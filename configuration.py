import openai

# HOMESERVER_URL = "https://matrix-client.matrix.org"
HOMESERVER_URL = "https://matrix.iv-labs.org:8448"
# TODO nginx redirect from 80 (and https) to 8448

try:
    openai.api_key = open("/home/yves/keys/openAIAPI", "r").read().rstrip("\n")
    # MATRIX_PASSWORD = open("/home/yves/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
    MATRIX_PASSWORD = "dbguser1"
    HOSTNAME = "http://127.0.0.1:8080"
except FileNotFoundError:
    openai.api_key = open("/app/keys/openAIAPI", "r").read().rstrip("\n")
    MATRIX_PASSWORD = open("/app/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
    HOSTNAME = "http://agent.iv-labs.org"
