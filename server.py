import threading
import os

import websocket
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# the index of the current audio track from 0 to 9
current_index = -1
# the timer that periodically advances the current audio track
t = None
# websocket connection to the inference server
ws = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ws

    url = os.environ.get("INFERENCE_SERVER_WS_URL")
    if not url:
        url = "ws://localhost:8001"

    ws = websocket.create_connection(url)
    print(f"websocket connected to {url}")

    advance()

    yield

    if ws:
        ws.close()
    if t:
        t.cancel()


def generate_new_audio():
    if not ws:
        return

    global current_index

    offset = 0
    if current_index == 0:
        offset = 5
    elif current_index == 5:
        offset = 0
    else:
        return

    print("generating new audio...")

    ws.send("generate")

    wavs = []
    for i in range(5):
        raw = ws.recv()
        if isinstance(raw, str):
            continue
        wavs.append(raw)

    for i, wav in enumerate(wavs):
        with open(f"{i + offset}.mp3", "wb") as f:
            f.write(wav)

    print("audio generated.")


def advance():
    global current_index, t

    if current_index == 9:
        current_index = 0
    else:
        current_index = current_index + 1

    threading.Thread(target=generate_new_audio).start()

    t = threading.Timer(60, advance)
    t.start()


app = FastAPI(lifespan=lifespan)


@app.get("/current.mp3")
def get_current_audio():
    print("hello")
    return FileResponse(f"{current_index}.mp3")


app.mount("/", StaticFiles(directory="web", html=True), name="web")
