# TerminalIM

A simple IM platform based in Terminal.

To test:

## Server

Startup: 

```
uvicorn server.main:app --reload
```

To test:

Server:
```
uvicorn server.main:app --reload
```

Client 1: 
```
python client/main.py
```

Client 2:
```
python client/main.py
```

More clients can be created, but each client must confirm with a recipient first before sending IMs.
