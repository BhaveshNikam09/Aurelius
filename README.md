# Aurelius

**AI Voice Agent** — a real-time conversational agent that listens, thinks, and speaks back.

![Status](https://img.shields.io/badge/status-active-success)
![Python](https://img.shields.io/badge/python-3.7%2B-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Overview

Aurelius is an AI-powered voice agent that interacts naturally with users, performs tasks, and provides intelligent responses in real time. It pipes live voice input through speech-to-text, an LLM for reasoning, and text-to-speech for a natural spoken reply — all wrapped in a modern, chat-style interface.

## Tech Stack

- **Backend:** FastAPI, Async Python, WebSockets
- **Speech-to-Text:** AssemblyAI
- **LLM Reasoning:** Groq
- **Text-to-Speech:** Murf AI
- **Weather Integration:** Weather API (for location/weather-aware queries)
- **Frontend:** HTML, CSS, JavaScript

## Architecture

```
User Voice
    │
    ▼
Speech-to-Text (AssemblyAI)
    │
    ▼
LLM Reasoning (Groq)  ◄──► Weather API (optional, for weather/location queries)
    │
    ▼
Text-to-Speech (Murf AI)
    │
    ▼
Audio Response ──► User
```

The FastAPI backend coordinates each stage over WebSockets, streaming audio in and responses back out with minimal latency, so the conversation feels continuous rather than turn-based. API keys for each service (Weather, Murf, AssemblyAI, Groq) are managed from the in-app configuration sidebar.

## Features

- **Smarter UI** — sleek, modern chat-style interface for smoother, more intuitive interactions
- **Dynamic Sidebar** — manage API keys and configuration without touching code
- **Conversation Logging** — full interaction history for insights and troubleshooting
- **Real-Time Task Handling** — the agent performs tasks and answers queries live
- **Multi-Platform Support** — deployable across various platforms

## Prerequisites

- Python 3.7+
- API keys for:
  - AssemblyAI (Speech-to-Text)
  - Murf AI (Text-to-Speech)
  - Groq (LLM)
  - A Weather API provider (for weather-aware responses)

## Installation

**1. Clone the repository**
```bash
git clone https://github.com/BhaveshNikam09/Aurelius
cd Aurelius
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Configure API keys**

Set your API keys either via a `.env` file or directly in the app's **API Configuration** sidebar once it's running:

- Weather API Key
- Murf API Key
- AssemblyAI API Key
- Groq API Key

**4. Run the application**
```bash
python app.py
```

## Usage

Once running, interact with Aurelius through the chat-style UI:

- Speak naturally — Aurelius transcribes, reasons, and responds with synthesized speech
- Use the sidebar to manage API keys and configuration
- Review past interactions in the conversation log

## Customization

- Update API keys and configuration via the sidebar
- Modify the conversation flow in `conversation_flow.py`
- Swap LLM providers by changing the relevant environment variable / config entry

## Screenshots

**Chat interface**
![Aurelius chat UI](./screenshots/chat-ui.png)

**API configuration sidebar**
![Aurelius config sidebar](./screenshots/config-sidebar.png)


## Contributing

Feel free to fork this repository, submit issues, or open pull requests for improvements.

## License

MIT
