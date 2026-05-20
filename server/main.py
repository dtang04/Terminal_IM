from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uuid
import json

conns = {}

app = FastAPI()

@app.websocket("/messages")
async def process_message(websocket: WebSocket):
    """
    Server receives a message from the client, and relays it to client 2.
    """
    await websocket.accept()
    
    c_id = str(uuid.uuid4())
    conns[c_id] = websocket

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
                if incoming_raw == '\n': 
                    # websocat sends extra new line for every incoming message
                    continue
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
                ws_r = conns[receiver] # dial the receiver ws connection
            except KeyError:
                # receiver ws doesn't exist
                err_payload = {"type": "Error", "text": "Receiver doesn't exist"}
                await websocket.send_json(err_payload)
                continue

            msg_payload = {"type": "chat", "from": sender, "to": receiver, "ts": ts, "msg": msg}

            await ws_r.send_json(msg_payload) # send on receiver's ws

    except WebSocketDisconnect:
        del conns[c_id]
        for user, conn in conns.items():
            leave_payload = {"type": "user_left", "users": list(conns.keys())}
            await conn.send_json(leave_payload)
        return
