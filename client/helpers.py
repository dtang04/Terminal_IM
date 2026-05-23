import requests

HTTP_URI = "http://localhost:8000"

def getHistory(c_uname, r_uname):
    resp = requests.get(HTTP_URI + f"/history?username={c_uname}&recipient_name={r_uname}")

    if resp.status_code == 200:
        resp = resp.json()
        hist = resp["history"]
        for text in hist:
            print(f"[From: {text['from']} @ {text['ts']}] {text['msg']}")
