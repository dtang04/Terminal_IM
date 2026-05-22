from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile
from fastapi.responses import JSONResponse
from server.models import Username
from dotenv import load_dotenv
import os
import redis
import uuid
import json
import boto3
from botocore.config import Config

conns = {}

uuid_to_usernames = {}
usernames_to_uuid = {}

load_dotenv()
aws_bucket = os.getenv("S3_BUCKET")

app = FastAPI()
s3 = boto3.client("s3", config=Config(signature_version="s3v4"), region_name="us-east-2", endpoint_url="https://s3.us-east-2.amazonaws.com") # boto3 loads AWS_ACCESS_KEY_ID, AWS_REGION, AWS_SECRET_ACCESS_KEY by default

store = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

@app.get("/id")
def retrieve_id():
    """
    Generates a uuid and returns it to the client.
    """
    c_id = str(uuid.uuid4())
    conns[c_id] = None
    return JSONResponse({"status": "success", "c_id": c_id}, status_code=200)

@app.get("/id/{recipient}")
def retrieve_recipient_id(recipient: str):
    """
    Finds the recipient uuid, given a username. 
    """
    try:
        r_id = usernames_to_uuid[recipient]
        return JSONResponse({"status": "success", "r_id": r_id}, status_code=200)
    except KeyError:
        return JSONResponse({"status": "fail"}, status_code=404)

@app.get("/history")
def msg_history(username: str, recipient_name: str):
    """
    Given the username and recipient name, queries the redis kv store and returns the messages from oldest to newest.
    """
    raw_messages = store.lrange(f"{min(username, recipient_name)}_{max(username, recipient_name)}", 0, -1) # key, start, stop
                                                                                                     # if key does not exist, lrange returns []
    
    parsed_messages = []
    for r_message in raw_messages:
        r_message = json.loads(r_message)
        parsed_messages.append(r_message)

    return JSONResponse({"status": "success", "history": parsed_messages}, status_code=200)

@app.post("/username")
def fill_username(uname: Username):
    """
    Updates uuid_to_usernames and usernames_to_uuid
    """
    uuid_to_usernames[uname.userid] = uname.username # for identifying sender
    usernames_to_uuid[uname.username] = uname.userid # for identifying receiver
    return JSONResponse({"status": "success"}, status_code=200)

@app.post("/upload")
async def upload_file(filename: str):
    """
    Given a filename, allocate the upload slot in S3, and returned the presigned
    put URL and get URL.
    """
    key = f"uploads/{filename}"
    
    # Server provides client with presigned url, client uploads themselves
    put_url = s3.generate_presigned_url("put_object", Params={"Bucket": aws_bucket, "Key": key}, ExpiresIn=3600)
    get_url = s3.generate_presigned_url("get_object", Params={"Bucket": aws_bucket, "Key": key}, ExpiresIn=86400)
    return JSONResponse({"status": "success", "put_url": put_url, "get_url": get_url}, status_code=200)

@app.websocket("/messages/{c_id}")
async def process_message(websocket: WebSocket, c_id: str):
    """
    Server receives a message from the client, and relays it to client 2.
    """
    await websocket.accept()
    
    conns[c_id] = websocket # register the ws connection with the c_id
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

            # Save to redis
            redis_key = f"{min(username, receiver_name)}_{max(username, receiver_name)}" # use min-max to ensure idempotency of key
            store.rpush(redis_key, json.dumps(msg_payload))

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
