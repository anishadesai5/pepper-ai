# Pepper – Phase 1 Testing Guide

## Critical: Python 2.7.18 Required
Pepper's NAOqi SDK ONLY works with Python 2.7.18. All code must run against this interpreter.
- Download: https://www.python.org/downloads/release/python-2718/
- In VS Code: set your interpreter to the Python 2.7.18 path
- In terminal, always run: `python2 chatGPT.py` (not `python3`)
- Verify with: `python2 --version` → should print `Python 2.7.18`

---

## What to Test

The `__main__` block at the bottom of `chatGPT.py` is your test harness.
It already does the following in order:
1. Calls `chat_with_gpt("Hello")` to warm up the conversation
2. Does an ambient sound check
3. Records audio
4. Calls `transcribe_audio_file(file_path)`
5. Calls `chat_with_gpt(transcription_text)` with the transcribed speech
6. Deletes the audio file

Run it directly (without connecting to Pepper hardware):
```
python2 chatGPT.py
```

---

## Test 1: `transcribe_audio_file`

**What to verify:**
- The function returns an object (not None)
- That object has a `.text` attribute
- `.text` contains the words you spoke

**Manual test — add this temporarily to `__main__`:**
```python
# Test transcription only
test_path = "test_audio.wav"  # record a short wav manually first
result = chatGPT_Interact.transcribe_audio_file(test_path)
if result is None:
    print("FAIL: returned None - check API key and file path")
elif not hasattr(result, "text"):
    print("FAIL: result has no .text attribute")
elif result.text == "":
    print("FAIL: transcription is empty")
else:
    print("PASS: " + result.text.encode("utf-8"))
```

**Common failure causes:**
- Wrong API key in `.env` — check `CHATGPT_KEY`
- File path doesn't exist — print `file_path` before calling
- Audio file is silent — the ambient check may have failed
- Python 2 `open()` issue — make sure file is opened in binary mode `"rb"`

---

## Test 2: `chat_with_gpt`

**What to verify:**
- Returns a non-empty string
- The conversation list grows by 2 entries (user + assistant) per call
- `self.conversation` starts with the system prompt intact

**Manual test — add this temporarily to `__main__`:**
```python
# Test basic chat
print("Conversation length before: " + str(len(chatGPT_Interact.conversation)))
reply = chatGPT_Interact.chat_with_gpt("Hello, introduce yourself briefly.")
print("Conversation length after: " + str(len(chatGPT_Interact.conversation)))

if not reply:
    print("FAIL: empty reply")
elif len(chatGPT_Interact.conversation) < 3:  # system + user + assistant = 3
    print("FAIL: conversation not growing correctly")
else:
    print("PASS: " + reply.encode("utf-8"))
```

**Common failure causes:**
- `CHATURL` or `CHATMODEL` not loaded from `.env` — print both before the call
- API key issue — check response status: `print(response.status_code)`
- `response.json()` fails — print `response.text` to see raw error from OpenAI

---

## Test 3: `reset_chat`

**What to verify:**
- After calling `reset_chat()`, `self.conversation` has exactly 1 entry
- That entry is `{"role": "system", "content": ALLPREPROMPT}`
- Prior conversation turns are gone

**Manual test — add this temporarily to `__main__`:**
```python
# Build up some conversation history first
chatGPT_Interact.chat_with_gpt("Tell me a joke.")
chatGPT_Interact.chat_with_gpt("Tell me another.")
print("Before reset: " + str(len(chatGPT_Interact.conversation)) + " messages")

chatGPT_Interact.reset_chat()
print("After reset: " + str(len(chatGPT_Interact.conversation)) + " messages")

if len(chatGPT_Interact.conversation) != 1:
    print("FAIL: should have exactly 1 message after reset")
elif chatGPT_Interact.conversation[0]["role"] != "system":
    print("FAIL: first message should be system role")
else:
    print("PASS: conversation reset correctly")
```

---

## Python 2.7 Gotchas to Watch For

| Issue | Python 3 | Python 2.7 Fix |
|---|---|---|
| Print | `print("x")` | `print("x")` works, but `print x` also valid |
| Unicode output | works natively | use `.encode("utf-8")` before printing |
| String types | all `str` | `str` vs `unicode` — use `str()` to be safe |
| `json.loads` input | accepts `str` | accepts `str` — same |
| `open()` | `open(f, "rb")` | `open(f, "rb")` — same |
| Integer division | `5/2 = 2.5` | `5/2 = 2` — add `from __future__ import division` if needed |
| `requests` library | pip3 install | `pip2 install requests` |

---

## Checking Your `.env` Loads Correctly

If anything seems broken, add this debug block at the top of `__main__`:
```python
print("API KEY loaded: " + str(bool(API_KEY)))
print("CHAT URL: " + str(CHATURL))
print("TRANSCRIPTION URL: " + str(TRANSCRIPTIONURL))
print("PREPROMPT loaded: " + str(bool(PREPROMPT)))
print("IMAGE PREPROMPT: " + str(IMAGE_PREPROMPT))
```
If any print `None`, your `.env` isn't loading. Make sure `python-dotenv` is installed for Python 2:
```
pip2 install python-dotenv
```

---

## Installing Dependencies for Python 2.7

```bash
pip2 install requests
pip2 install python-dotenv
pip2 install pyaudio
pip2 install numpy
pip2 install pydub
pip2 install opencv-python
```

Or using the requirements file if it exists:
```bash
pip2 install -r requirements.txt
```

---

## Definition of Done for Phase 1

- [ ] `transcribe_audio_file` returns object with non-empty `.text`
- [ ] `chat_with_gpt("Hello")` returns a non-empty string
- [ ] `self.conversation` grows correctly (system + pairs of user/assistant)
- [ ] `reset_chat()` leaves exactly 1 message (the system prompt) in `self.conversation`
- [ ] No Python 2.7 syntax errors anywhere in `chatGPT.py`

Once all four are checked off, move to `CLAUDE_phase2.md`.
