import websockets
import asyncio
import sys
import requests
import json
from datetime import datetime

WS_URI = "ws://localhost:8000/messages"
HTTP_URI = "http://localhost:8000"

users = []
me = None # this client's id
myUsername = None # this client's username
to = None # recipient's username
to_id = None # recipient's id

async def receive(websocket):
    """
    Async function that reads from a websocket connection.
    """
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
    """
    Async function that reads from a websocket. 

    Blocking calls such as stdin.readline and POST /upload are run in separate
    executor threads to prevent blocking the event loop.

    /upload <filepath> opens the file at the filepath, and sends it via POST /upload.
    """
    event_loop = asyncio.get_running_loop() # prevent the event handler from blocking on stdin
    while True:
        msg_to_send = await event_loop.run_in_executor(None, sys.stdin.readline)
        msg_to_send = msg_to_send.strip()

        if msg_to_send.startswith("/upload "):
            filepath = msg_to_send[8:]

            try:
                file = open(filepath, "rb")
            except FileNotFoundError:
                print("File not found")
                continue
            
            resp = await event_loop.run_in_executor(None, lambda: requests.post(HTTP_URI + f"/upload?filename={file.name.split('/')[-1]}")) # use lambda with run_in_executor when blocking func has args
                                                                                                                                            # filename.split("/")[-1] gets the filename from the full dir
            resp = resp.json()
                                                                                                   
            presigned_url_PUT = resp["put_url"]
            presigned_url_GET = resp["get_url"]

            await event_loop.run_in_executor(None, lambda: requests.put(presigned_url_PUT, data=file, headers={"Content-Type": "application/octet-stream"})) # upload to S3's presigned url client-side
                                                                                                                                                         # application/octet-stream is generic data
            file.close()

            payload_upload = {"type": "chat", "to": to, "msg": presigned_url_GET, "ts": str(datetime.now())}
            await websocket.send(json.dumps(payload_upload))
            continue

        payload = {"type": "chat", "to": to, "msg": msg_to_send, "ts": str(datetime.now())}
        await websocket.send(json.dumps(payload))

async def main():
    """
    Performs synchronous setup (username, recipient population, history display), dials the
    websocket, then begins the async functions (receive, send)
    """
    global me, myUsername, to, to_id, WS_URI

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
                    to = recipient
                    resp = requests.get(HTTP_URI + f"/id/{to}")
                    if resp.status_code == 200:
                        resp = resp.json()
                        to_id = resp["r_id"] # populate recipient's id
                    validRecipient = True
                    break
            
            if validRecipient:
                # if valid recipient, get the history
                resp = requests.get(HTTP_URI + f"/history?username={myUsername}&recipient_name={to}")

                if resp.status_code == 200:
                    resp = resp.json()
                    hist = resp["history"]
                    for text in hist:
                        print(f"[From: {text['from']} @ {text['ts']}] {text['msg']}")

                break

        await asyncio.gather(receive(ws), send(ws))


if __name__ == "__main__":
    asyncio.run(main())