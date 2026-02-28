# Pepper Robot – AI Concierge Assistant
## Hackathon Context

This project powers **Pepper**, a SoftBank humanoid robot acting as a Deloitte AI concierge. Pepper listens to employees, understands their queries using OpenAI, and responds with speech and physical behaviors (dances, handshakes, fist bumps, etc.).

The codebase is written in **Python 2.7** (required by Pepper's NAOqi SDK). All OpenAI calls use the `requests` library directly — do NOT use the `openai` Python package.

---

## What the Judge Wants to See

1. **Pepper talks back** — A working voice conversation loop (listen → transcribe → respond → speak)
2. **Personality switching** — Pepper can swap between "Spicy" (sarcastic) and "Event" (friendly Gen Z) modes mid-conversation
3. **Physical behaviors triggered by AI** — GPT decides when to fist bump, dance, shake hands, etc. using tool/function calling
4. **Vision awareness** — Pepper describes what it sees via its camera and uses that in conversation
5. **Response under 5 seconds** — Achieved via streaming (speak sentence-by-sentence as GPT responds)

---

## Phase 1 – Core Conversation Loop (Start Here)

Implement these three methods in `chatGPT.py` in this order:

---

### 1. `transcribe_audio_file(file_path)`

**Goal:** Send a recorded `.wav` file to OpenAI Whisper and return the transcription object.

**Key variables already available:**
- `TRANSCRIPTIONURL` = `"https://api.openai.com/v1/audio/transcriptions"`
- `TRANSCRIPTIONMODEL` = `"whisper-1"`
- `self.APIKEY` = your OpenAI key

**Expected behavior:**
- Open the file at `file_path` in binary mode
- POST it to the Whisper API with `model=whisper-1`
- Return the response object (caller accesses `.text` on it)
- Handle request exceptions gracefully (print error, return None)

**Hint — request structure:**
```python
headers = {"Authorization": "Bearer " + self.APIKEY}
files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "audio/wav")}
data = {"model": TRANSCRIPTIONMODEL}
response = requests.post(TRANSCRIPTIONURL, headers=headers, files=files, data=data)
```
The returned object needs a `.text` attribute — parse `response.json()["text"]` and attach it, or wrap in a simple object.

---

### 2. `chat_with_gpt(message)`

**Goal:** Send a message to GPT-4o and return the assistant's reply as a string.

**Key variables already available:**
- `CHATURL` = `"https://api.openai.com/v1/chat/completions"`
- `CHATMODEL` = `"gpt-4o"`
- `self.conversation` = list of message dicts (already initialized with system prompt)
- `self.APIKEY`

**Expected behavior:**
- Filter the message using `self.filter_text(message)`
- Append `{"role": "user", "content": filtered_message}` to `self.conversation`
- POST `self.conversation` to the chat API
- Parse the assistant reply from `response.json()["choices"][0]["message"]["content"]`
- Append `{"role": "assistant", "content": reply}` to `self.conversation`
- Return the reply string

**Hint — request structure:**
```python
headers = {
    "Authorization": "Bearer " + self.APIKEY,
    "Content-Type": "application/json"
}
payload = {
    "model": CHATMODEL,
    "messages": self.conversation
}
response = requests.post(CHATURL, headers=headers, json=payload)
```

---

### 3. `reset_chat()`

**Goal:** Clear conversation history and restart with just the system prompt (called when a new person approaches).

**Expected behavior:**
- Replace `self.conversation` with a fresh list containing only the system message:
```python
self.conversation = [{"role": "system", "content": ALLPREPROMPT}]
```

---

## File Map

| File | Purpose |
|---|---|
| `main.py` | Main loop — wires audio, transcription, GPT, and Pepper hardware together |
| `chatGPT.py` | **YOUR FOCUS** — All OpenAI API interactions. Methods are stubbed with `pass` |
| `myPepper.py` | Hardware control — speech, LEDs, behaviors, camera, tablet display |
| `recordAudio4.py` | Audio recording — ambient calibration, VAD, silence detection |
| `sharedVars.py` | Global state — `ISNEAR` (person detected) and `ISRECORDING` (mic override) |
| `OverrideBtn.py` | Tkinter GUI button to manually override microphone |
| `.env` | All config — API keys, Pepper IP, personality prompts, behavior lists |

---

## Environment Variables (from `.env`)

| Variable | Description |
|---|---|
| `CHATGPT_KEY` | OpenAI API key |
| `PIP` | Pepper's IP address on the local network |
| `PPORT` | Pepper's port (default 9559) |
| `CHATURL` | OpenAI chat completions endpoint |
| `CHATMODEL` | GPT model to use (gpt-4o) |
| `TRANSCRIPTIONURL` | Whisper transcription endpoint |
| `TRANSCRIPTIONMODEL` | Whisper model (whisper-1) |
| `PREPROMPT1` | "Spicy" sarcastic personality system prompt |
| `PREPROMPT2` | "Event" friendly personality system prompt |
| `BEHAVIORS_ENUM` | JSON list of available Pepper animation names |
| `BEHAVIORS_DESCRIPTION` | Descriptions of when to trigger each behavior |
| `IMAGE_PREPROMPT` | Live description of what Pepper's camera sees |

---

## Important Notes

- **Python 2.7** — use `print "text"` not `print("text")` where needed, and `str()` for string conversions
- **No `openai` package** — use `requests` for all API calls
- `self.conversation` maintains full chat history for context — do not reset it mid-conversation
- `ALLPREPROMPT` = personality prompt + image description stitched together
- `filter_text()` is already implemented — always run user input through it before sending to API
- Pepper's `have_pepper_say()` handles both speaking AND displaying text on the tablet

---

## Phase 2 (After Phase 1 Works)

- `chat_with_gpt_stream` — Stream responses sentence by sentence for faster speech
- `chat_with_gpt_stream_behaviors` — Add tool/function calling so GPT triggers physical behaviors
- `get_description_of_image_as_base64` — Vision: describe what Pepper's camera sees
- `isGoodbye` — Detect conversation endings

Good luck!
