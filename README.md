# Conversational IVR PoC

A proof-of-concept Interactive Voice Response (IVR) system built with FastAPI that orchestrates speech recognition (ASR), text-to-speech (TTS), and large language model (LLM) components to power dynamic phone / WebRTC call flows.

## Features (planned)
- Webhook endpoint to receive call/media events
- Extensible flow engine (JSON DSL)
- Pluggable ASR/TTS/LLM providers (local or cloud)
- Session + transcript persistence
- Simple demo harness and sample flow
- Optional dashboard UI

## Quick Start
(After installing dependencies listed in `requirements.txt`)

```bash
bash run_dev.sh
```

Then visit: http://localhost:8000/docs

## Project Structure
See `RepoStructure.txt` for the intended layout.

## License
MIT (adjust as needed)
