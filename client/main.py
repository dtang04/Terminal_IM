import websockets
import asyncio
import sys

import json
from datetime import datetime

URI = "ws://localhost:8000/messages"

users = []
me = None
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
            me = incoming["client_id"]

async def send(websocket):
    event_loop = asyncio.get_running_loop() # prevent the event handler from blocking on stdin
    while True:
        msg_to_send = await event_loop.run_in_executor(None, sys.stdin.readline)
        msg_to_send = msg_to_send.strip()

        payload = {"type": "chat", "to": to, "msg": msg_to_send, "ts": str(datetime.now())}
        await websocket.send(json.dumps(payload))

async def main():
    global me, to
    async with websockets.connect(URI) as ws:
        # At startup, get the users
        while True:
            incoming_raw = await ws.recv()
            incoming = json.loads(incoming_raw)

            users = incoming["users"]

            if me is None:
                me = incoming["last_joined"]

            # One time population of recipient
            other_users = [user for user in users if user != me]
            print("Current users: ", other_users)

            if len(other_users) == 0:
                continue

            validRecipient = False
            while not validRecipient:
                recipient = input("Pick a user to message ")
                if recipient not in users:
                    print("Recipient not found")
                elif recipient == me:
                    print("Recipient can't be yourself")
                else:
                    to = recipient
                    validRecipient = True
                    break
            
            if validRecipient:
                break

        await asyncio.gather(receive(ws), send(ws))


if __name__ == "__main__":
    asyncio.run(main())