from fastapi import FastAPI, WebSocket, HTTPException, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import requests
import os
import time
import random
import re 
import uuid
import websockets
import base64
import json
import wikipedia
import asyncio
from logger import logger

# --- Load environment variables ---
load_dotenv(find_dotenv())

app = FastAPI()

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Default API Keys (from .env as fallback, can be overridden from frontend)
user_keys = {
    "WEATHER_API_KEY": os.getenv("WEATHER_API_KEY"),
    "MURF_API_KEY": os.getenv("MURF_API_KEY"),
    "ASSEMBLYAI_API_KEY": os.getenv("ASSEMBLYAI_API_KEY"),
    "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
}

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
UPLOAD_FOLDER = Path("uploads"); UPLOAD_FOLDER.mkdir(exist_ok=True)
STATIC_FOLDER = Path("static"); STATIC_FOLDER.mkdir(exist_ok=True)
REPLY_FOLDER = STATIC_FOLDER / "replies"; REPLY_FOLDER.mkdir(exist_ok=True)

ASSEMBLYAI_UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
ASSEMBLYAI_TRANSCRIPT_URL = "https://api.assemblyai.com/v2/transcript"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

JOKES = [
    "Why did the programmer quit his job? Because he didn't get arrays.",
    "Why do Java developers wear glasses? Because they don't C#.",
    "Why did the computer show up at work late? It had a hard drive."
]

QUOTES = [
    "Believe you can and you're halfway there. – Theodore Roosevelt",
    "The only way to do great work is to love what you do. – Steve Jobs",
    "Success is not final, failure is not fatal: It is the courage to continue that counts. – Winston Churchill"
]

chat_history = []
active_connection: WebSocket = None


@app.get("/", response_class=HTMLResponse)
def serve_home(request: Request):
    logger.info("📄 Serving homepage (index.html)")
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/config")
async def update_config(request: Request):
    """Update runtime API keys from frontend"""
    data = await request.json()
    for key in ["WEATHER_API_KEY", "MURF_API_KEY", "ASSEMBLYAI_API_KEY", "GROQ_API_KEY"]:
        if key in data and data[key]:
            user_keys[key] = data[key]
            logger.info(f"🔑 Updated {key} from frontend")
    return {"status": "ok", "keys": list(user_keys.keys())}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global active_connection
    await websocket.accept()
    active_connection = websocket
    logger.info("✅ WebSocket connection established.")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connection = None
        logger.info("🔒 WebSocket connection closed.")


def transcribe_with_assemblyai(file_path: Path) -> str:
    logger.info(f"🎤 Starting transcription for: {file_path}")
    with open(file_path, "rb") as f:
        upload_res = requests.post(
            ASSEMBLYAI_UPLOAD_URL,
            headers={"authorization": user_keys["ASSEMBLYAI_API_KEY"]},
            data=f
        )
    upload_res.raise_for_status()
    upload_url = upload_res.json().get("upload_url")
    logger.info(f"📡 AssemblyAI upload complete, URL: {upload_url}")

    transcript_req = requests.post(
        ASSEMBLYAI_TRANSCRIPT_URL,
        headers={"authorization": user_keys["ASSEMBLYAI_API_KEY"], "content-type": "application/json"},
        json={"audio_url": upload_url}
    )
    transcript_req.raise_for_status()
    transcript_id = transcript_req.json().get("id")
    logger.info(f"🆔 Transcript request created, ID: {transcript_id}")

    while True:
        poll_res = requests.get(
            f"{ASSEMBLYAI_TRANSCRIPT_URL}/{transcript_id}",
            headers={"authorization": user_keys["ASSEMBLYAI_API_KEY"]}
        ).json()
        if poll_res["status"] == "completed":
            logger.info("✅ Transcription completed successfully")
            return poll_res["text"]
        elif poll_res["status"] == "error":
            raise Exception(f"AssemblyAI Error: {poll_res.get('error')}")
        time.sleep(2)


def get_weather(city: str) -> str:
    try:
        params = {"q": city, "appid": user_keys["WEATHER_API_KEY"], "units": "metric"}
        res = requests.get(WEATHER_URL, params=params)
        res.raise_for_status()
        data = res.json()
        desc = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        return f"🌦️ The weather in {city.title()} is {desc} with {temp}°C (feels like {feels}°C)."
    except Exception as e:
        return f"❌ Couldn't fetch weather for {city}. ({e})"


def get_llm_reply(text: str) -> str:
    try:
        lower_text = text.lower().strip()

        if lower_text.startswith(("calculate", "what is", "solve")):
            try:
                expression = re.sub(r'[^0-9\+\-\*\/\.\(\) ]', '', text)
                result = eval(expression)
                return f"🧮 The result is: {result}"
            except:
                return "❌ I couldn't calculate that."

        if "joke" in lower_text or "funny" in lower_text:
            return random.choice(JOKES)

        if "quote" in lower_text or "motivate" in lower_text:
            return random.choice(QUOTES)

        if lower_text.startswith(("who is", "what is", "tell me about")):
            try:
                summary = wikipedia.summary(text, sentences=2)
                logger.info("📖 Reply source: Wikipedia")
                return summary
            except Exception as e:
                logger.warning(f"Wikipedia lookup failed: {e}")

        llm_res = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {user_keys['GROQ_API_KEY']}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": text}], "max_tokens": 300}
        )
        llm_res.raise_for_status()
        reply = llm_res.json()["choices"][0]["message"]["content"].strip()
        logger.info("🤖 Reply source: Groq LLM")
        return reply

    except Exception as e:
        logger.error(f"❌ LLM API failed: {e}")
        try:
            summary = wikipedia.summary(text, sentences=2)
            logger.info("📖 Fallback reply source: Wikipedia")
            return summary
        except:
            return "I'm having trouble connecting right now."


async def stream_murf_tts(text: str, voice_id: str, websocket: WebSocket):
    WS_URL = "wss://api.murf.ai/v1/speech/stream-input"
    logger.info("🎧 Starting Murf streaming TTS...")
    try:
        async with websockets.connect(
            f"{WS_URL}?api-key={user_keys['MURF_API_KEY']}&sample_rate=44100&channel_type=MONO&format=MP3"
        ) as murf_ws:
            await murf_ws.send(json.dumps({
                "voice_config": {
                    "voiceId": voice_id,
                    "format": "mp3",
                    "style": "Conversational"
                }
            }))
            await murf_ws.send(json.dumps({"text": text, "end": True}))

            start_time = time.time()
            while True:
                if time.time() - start_time > 20:
                    logger.warning("⚠️ Murf stream timeout reached, forcing stop")
                    break

                try:
                    murf_msg = await asyncio.wait_for(murf_ws.recv(), timeout=5)
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Murf no data for 5s, breaking stream")
                    break

                data = json.loads(murf_msg)
                if "audio" in data:
                    audio_bytes = base64.b64decode(data["audio"])
                    await websocket.send_json({
                        "type": "audio",
                        "data": base64.b64encode(audio_bytes).decode("utf-8")
                    })
                    logger.info(f"🎵 Sent audio chunk ({len(audio_bytes)} bytes)")
                if data.get("final"):
                    logger.info("✅ Murf stream marked as final")
                    break

            await websocket.send_json({"type": "audio_end"})

    except Exception as e:
        logger.error(f"❌ Murf streaming failed: {e}")
        await websocket.send_json({"type": "error", "message": f"Murf stream failed: {e}"})


def murf_tts_to_file(text: str, voice_id: str) -> str:
    logger.info("💾 Generating full Murf TTS file...")
    url = "https://api.murf.ai/v1/speech/generate"
    headers = {"Authorization": f"Bearer {user_keys['MURF_API_KEY']}", "Content-Type": "application/json"}
    payload = {"voiceId": 'bn-IN-arnab', "style": "Conversational", "format": "MP3", "text": text}
    
    res = requests.post(url, headers=headers, json=payload)
    res.raise_for_status()

    audio_url = res.json().get("audioFile")
    logger.info(f"📡 Murf file generated, downloading from: {audio_url}")
    audio_data = requests.get(audio_url).content

    filename = f"{uuid.uuid4()}.mp3"
    filepath = REPLY_FOLDER / filename
    with open(filepath, "wb") as f:
        f.write(audio_data)
    logger.info(f"💾 Saved audio file locally at {filepath}")
    return f"/static/replies/{filename}"


@app.post("/llm/query")
async def llm_query(file: UploadFile = File(...), voiceId: str = Form("en-US-amara")):
    global chat_history, active_connection

    if not active_connection:
        raise HTTPException(status_code=400, detail="No active WebSocket connection.")

    try:
        file_path = UPLOAD_FOLDER / f"{uuid.uuid4()}_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())
        logger.info(f"🎤 Audio uploaded: {file_path}")

        transcript_text = await run_in_threadpool(transcribe_with_assemblyai, file_path)
        logger.info(f"📝 Transcript: {transcript_text}")
        await active_connection.send_json({"type": "transcript", "data": transcript_text})

        llm_reply = await run_in_threadpool(get_llm_reply, transcript_text)
        logger.info(f"🤖 Reply: {llm_reply}")
        await active_connection.send_json({"type": "llm_reply", "data": llm_reply})

        chat_history.append({"user": transcript_text, "bot": llm_reply})
        await active_connection.send_json({"type": "history", "data": chat_history})

        await stream_murf_tts(llm_reply, voiceId, active_connection)

        file_url = await run_in_threadpool(murf_tts_to_file, llm_reply, voiceId)
        await active_connection.send_json({"type": "audio_file", "url": file_url})
        logger.info(f"📡 Sent saved audio file URL to frontend: {file_url}")

        logger.info("🎯 Audio sent successfully (stream + file) and saved locally")

        return JSONResponse(content={"message": "Done"})
    except Exception as e:
        logger.error(f"❌ Query failed: {e}")
        return JSONResponse(content={"message": f"Error: {e}"}, status_code=500)
