from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uuid
import json

from models import Username

conns = {}

uuid_to_usernames = {}
usernames_to_uuid = {}

app = FastAPI()

@app.get("/id")
def retrieve_id():
    c_id = str(uuid.uuid4())
    conns[c_id] = None
    return JSONResponse({"status": "success", "c_id": c_id}, status_code=200)

@app.post("/username")
def fill_username(uname: Username):
    uuid_to_usernames[uname.userid] = uname.username # for identifying sender
    usernames_to_uuid[uname.username] = uname.userid # for identifying receiver
    return JSONResponse({"status": "success"}, status_code=200)

@app.websocket("/messages/{c_id}")
async def process_message(websocket: WebSocket, c_id: str):
    """
    Server receives a message from the client, and relays it to client 2.
    """
    await websocket.accept()
    
    conns[c_id] = websocket # register the ws connection with the c_Id
    username = None

    isUpdate = True

    try:
        while True:
            if isUpdate: 
                # for the first iteration, update all existing users 
                # that a new user has joined
                for user, conn in conns.items():
                    if conn is not None:
                        join_payload = {"type": "user_join", "users": list(usernames_to_uuid.keys())}
                        await conn.send_json(join_payload)
                isUpdate = False
            
            try:
                incoming_raw = await websocket.receive_text() # await until msg is sent over ws
                incoming = json.loads(incoming_raw.strip())
            except json.JSONDecodeError:
                err_payload = {"type": "Error", "text": "input can't be parsed into JSON"}
                await websocket.send_json(err_payload)
                continue
        
            sender = c_id
            receiver_name = incoming["to"]
            

            ts = incoming["ts"]
            msg = incoming["msg"]

            try:
                username = uuid_to_usernames[c_id] # sender id -> sender name
            except KeyError:
                continue # username = None


            try:
                receiver_id = usernames_to_uuid[receiver_name] # receiver_name -> receiver_id
                ws_r = conns[receiver_id] # dial the receiver ws connection with receiver_id
            except KeyError:
                # receiver ws doesn't exist
                err_payload = {"type": "Error", "text": "Receiver doesn't exist"}
                await websocket.send_json(err_payload)
                continue

            msg_payload = {"type": "chat", "from": username, "to": receiver_name, "ts": ts, "msg": msg}

            await ws_r.send_json(msg_payload) # send on receiver's ws

    except WebSocketDisconnect:
        conns.pop(c_id, None)
        uuid_to_usernames.pop(c_id, None)
        if username is not None:
            usernames_to_uuid.pop(username, None)

        for user, conn in conns.items():
            if conn is not None:
                leave_payload = {"type": "user_left", "users": list(usernames_to_uuid.keys())}
                await conn.send_json(leave_payload)
        return
