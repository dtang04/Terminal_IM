from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uuid
import json

from models import Username

conns = {}
usernames = {}

app = FastAPI()

@app.post("/username")
def fill_username(uname: Username):
    usernames[uname.userid] = uname.username
    return JSONResponse({"status": "success"}, status_code=200)

@app.websocket("/messages")
async def process_message(websocket: WebSocket):
    """
    Server receives a message from the client, and relays it to client 2.
    """
    await websocket.accept()
    
    c_id = str(uuid.uuid4())
    conns[c_id] = websocket
    username = None

    isUpdate = True

    try:
        while True:
    
            if isUpdate: 
                # for the first iteration, update all existing users 
                # that a new user has joined
                for user, conn in conns.items():
                    join_payload = {"type": "user_join", "users": list(conns.keys()), "last_joined": c_id}
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
            receiver = incoming["to"]
            ts = incoming["ts"]
            msg = incoming["msg"]

            try:
                username = usernames[c_id]
            except KeyError:
                continue # username = None

            try:
                ws_r = conns[receiver] # dial the receiver ws connection
            except KeyError:
                # receiver ws doesn't exist
                err_payload = {"type": "Error", "text": "Receiver doesn't exist"}
                await websocket.send_json(err_payload)
                continue

            msg_payload = {"type": "chat", "from": sender, "to": receiver, "ts": ts, "msg": msg, "sender_username": username}

            await ws_r.send_json(msg_payload) # send on receiver's ws

    except WebSocketDisconnect:
        del conns[c_id]
        for user, conn in conns.items():
            leave_payload = {"type": "user_left", "users": list(conns.keys())}
            await conn.send_json(leave_payload)
        return
