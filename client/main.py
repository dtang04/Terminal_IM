import websockets
import asyncio
import sys
import requests
import json
from datetime import datetime

WS_URI = "ws://localhost:8000/messages"
HTTP_URI = "http://localhost:8000"

users = []
me = None
myUsername = None
to = None

async def receive(websocket):
    global users, me
    while True:
        incoming_raw = await websocket.recv()
        incoming = json.loads(incoming_raw)

        if incoming["type"] == "chat":
            msg = incoming["msg"]
            ts = incoming["ts"]
            sender = incoming["from"]

            print(f"[From: {sender} @ {ts}] {msg}")
        
        if incoming["type"] == "user_join":
            users = incoming["users"] # update the user map global

async def send(websocket):
    event_loop = asyncio.get_running_loop() # prevent the event handler from blocking on stdin
    while True:
        msg_to_send = await event_loop.run_in_executor(None, sys.stdin.readline)
        msg_to_send = msg_to_send.strip()

        payload = {"type": "chat", "to": to, "msg": msg_to_send, "ts": str(datetime.now())}
        await websocket.send(json.dumps(payload))

async def main():
    global me, myUsername, to, WS_URI

    # Register user name serverside
    myUsername = input("Username: ")

    # Gets the client id from server
    resp_id = requests.get(HTTP_URI + "/id")
    resp_id = resp_id.json() 
    me = resp_id["c_id"]

    resp_username = requests.post(HTTP_URI + "/username", json={"username": myUsername, "userid": me})

    # resolve the websocket URI
    WS_URI = WS_URI + "/" + me

    async with websockets.connect(WS_URI) as ws:
        # At startup, get the users
        while True:
            # Wait for user map from server
            incoming_raw = await ws.recv()
            incoming = json.loads(incoming_raw)

            users = incoming["users"]

            # One time population of recipient
            other_users = [user for user in users if user != myUsername]
            print("Current users: ", other_users)

            if len(other_users) == 0:
                continue

            validRecipient = False
            while not validRecipient:
                recipient = input("Pick a user to message ")
                if recipient not in users:
                    print("Recipient not found")
                elif recipient == myUsername:
                    print("Recipient can't be yourself")
                else:
                    to = recipient # recipient username
                    validRecipient = True
                    break
            
            if validRecipient:
                break

        await asyncio.gather(receive(ws), send(ws))


if __name__ == "__main__":
    asyncio.run(main())