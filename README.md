# Simple IM

A simple IM platform.

To test:

## Server

Startup: 

```
uvicorn server.main:app --reload
```

Test ws connections with websocat:

Create clients:

```
websocat ws://localhost:8000/messages
```

Send messages from one client to another:

```
{"to": "<other_client_id>", "ts": ts , "msg": msg}
```

