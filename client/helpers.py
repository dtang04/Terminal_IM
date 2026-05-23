import requests

from errors import IDCreationError, GetHistoryError, RegisterUsernameError, RecipientIDError

HTTP_URI = "http://localhost:8000"

def getHistory(c_uname, r_uname):
    resp = requests.get(HTTP_URI + f"/history?username={c_uname}&recipient_name={r_uname}")

    if resp.status_code == 200:
        resp = resp.json()
        hist = resp["history"]
        for text in hist:
            print(f"[From: {text['from']} @ {text['ts']}] {text['msg']}")
        return
        
    raise GetHistoryError("History retrieval failed")

def getRecipientID(r_username):
    resp = requests.get(HTTP_URI + f"/id/{r_username}")
    
    if resp.status_code == 200:
        resp = resp.json()
        return resp["r_id"]
    
    raise RecipientIDError("Recipient not found")

def generate_id():
    resp = requests.get(HTTP_URI + "/id")
    if resp.status_code == 200:
        resp = resp.json() 
        return resp["c_id"]
    
    raise IDCreationError("ID generation failed")

def registerUsername(username, user_id):
    resp = requests.post(HTTP_URI + "/username", json={"username": username, "userid": user_id})
    if resp.status_code == 200:
        return
    
    raise RegisterUsernameError("Serverside username registration failed")

