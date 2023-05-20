from matrix_client.client import MatrixClient

import utils

private_room = "!HROixbOzztGJQanWkr:matrix.iv-labs.org"
public_room = "!tGRhfymrxRWSrFicoE:matrix.iv-labs.org"

HOMESERVER_URL = "https://matrix.iv-labs.org:8448"
MATRIX_PASSWORD = "dbguser2"


def on_invitation(room_id, event):
    print("Invited!")
    print(room_id)
    utils.pprint(event)
    try:
        room = client.join_room(room_id)  # Automatically join the invited room
        print(f"Joined room: {room_id}")
        room.add_listener(on_message)
    except Exception as e:
        print(f"Failed to join room: {room_id}")
        print(e)


def on_message(room_id, event):
    print("Message received!")
    print(room_id)
    utils.pprint(event)


client = MatrixClient(HOMESERVER_URL)
client.login(username="dbguser2",
             password=MATRIX_PASSWORD,
             sync=True)
client.add_invite_listener(on_invitation)
try:
    room1 = client.join_room(public_room)
    room1.send_text(f"Hi 1!")
    room1.add_listener(on_message)
except:
    print(f"Could not enter {public_room}")
try:
    room2 = client.join_room(private_room)
    room2.send_text(f"Hi 2!")
    room2.add_listener(on_message)
except:
    print(f"Could not enter {private_room}")

client.start_listener_thread()
client.sync_thread.join()
