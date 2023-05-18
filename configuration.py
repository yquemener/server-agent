import openai

HOMESERVER_URL = "https://matrix-client.matrix.org"

try:
    openai.api_key = open("/home/yves/keys/openAIAPI", "r").read().rstrip("\n")
    MATRIX_PASSWORD = open("/home/yves/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
    HOSTNAME = "http://127.0.0.1:8080"
except FileNotFoundError:
    openai.api_key = open("/app/keys/openAIAPI", "r").read().rstrip("\n")
    MATRIX_PASSWORD = open("/app/keys/MindMakerAgentPassword", "r").read().rstrip("\n")
    HOSTNAME = "http://agent.iv-labs.org"
