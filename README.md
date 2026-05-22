# Terminal Instant Messenger

A simple IM platform based in Terminal, and a side project to practice WebSocket connections and `async` event loop management.

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

Redis KV store with homebrew:
```
brew services start redis
```

More clients can be created, but each client must confirm with a recipient first and set their username before sending IMs.

`boto3` is used to establish a client that connects to AWS. It reads credentials at `~/.aws/credentials`, and reads `S3_BUCKET` from .env.

