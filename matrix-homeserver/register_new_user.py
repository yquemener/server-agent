import requests


def login(server_url, username, password):
    data = {
        "type": "m.login.password",
        "user": username,
        "password": password,
    }

    response = requests.post(
        f"{server_url}/_matrix/client/r0/login",
        json=data,
    )

    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to login: {response.content}")


# Usage
# admin_token = login(
#     server_url="http://matrix.iv-labs.org:8008",
#     username="admin",
#     password=open("/home/yves/keys/MatrixHomeserver", "r").read().strip(),
# )

def create_user(server_url, admin_token, username, password):
    data = {
        "password": password,
        "admin": False,  # Set to True to create an admin account
    }

    headers = {
        "Authorization": f"Bearer {admin_token}",
    }

    # Use the /_synapse/admin/v2/users/<user_id> API
    response = requests.put(
        f"{server_url}/_synapse/admin/v2/users/@{username}:matrix.iv-labs.org",
        json=data,
        headers=headers,
    )

    if 200 <= response.status_code < 300:
        return response.json()
    else:
        print(response.status_code)
        raise Exception(f"Failed to create user: {response.content}")


# Usage
u=create_user(
    server_url="http://matrix.iv-labs.org:8008",
    admin_token=open("/home/yves/keys/MatrixHomeserverAdminToken", "r").read().strip(),
    username="dbguser3",
    password="dbguser3",
)

print(u)