# Pepper Robot – Phase 2: Streaming, Behaviors, Vision & Goodbye

## Phase 1 Status: COMPLETE
- `transcribe_audio_file` ✅
- `chat_with_gpt` ✅
- `reset_chat` ✅

---

## Phase 2 Goals
Layer on top of the working Phase 1 loop to add:
1. **Faster responses** via streaming (speak while GPT is still generating)
2. **Physical behavior triggers** — GPT decides when to fist bump, dance, shake hands, etc.
3. **Personality switching** — swap between Spicy and Event modes mid-conversation
4. **Vision** — Pepper describes what its camera sees and uses that context in conversation
5. **Graceful conversation endings** — detect when a user says goodbye

---

## Method 1: `chat_with_gpt_stream(message)`

**Goal:** Stream GPT-4o response and speak it sentence-by-sentence so Pepper starts talking faster.

**Key idea:** Instead of waiting for the full response, GPT sends tokens in chunks via SSE (Server-Sent Events). Accumulate tokens until you hit `.`, `!`, or `?`, then immediately speak that sentence while GPT keeps generating the rest.

**Request — add `"stream": True` to payload:**
```python
filtered_message = self.filter_text(message)
self.conversation.append({"role": "user", "content": filtered_message})

headers = {
    "Authorization": "Bearer " + self.APIKEY,
    "Content-Type": "application/json"
}
payload = {
    "model": CHATMODEL,
    "messages": self.conversation,
    "stream": True
}
response = requests.post(CHATURL, headers=headers, json=payload, stream=True)
```

**Parsing SSE chunks:**
```python
full_reply = ""
buffer = ""

for line in response.iter_lines():
    if line and line.startswith("data: "):
        chunk = line[6:]  # strip "data: " prefix
        if chunk == "[DONE]":
            break
        try:
            delta = json.loads(chunk)["choices"][0]["delta"]
            token = delta.get("content", "")
            if token:
                buffer += token
                full_reply += token

                # Speak when we hit sentence-ending punctuation
                if any(buffer.endswith(p) for p in [".", "!", "?"]):
                    cleaned = self.filter_text(buffer.strip())
                    if cleaned:
                        self.my_pepper.have_pepper_say(cleaned)
                    buffer = ""
        except Exception:
            pass

# Speak any remaining text in buffer
if buffer.strip():
    self.my_pepper.have_pepper_say(self.filter_text(buffer.strip()))

self.conversation.append({"role": "assistant", "content": full_reply})
return "done"
```

---

## Method 2: `chat_with_gpt_stream_behaviors(message)` ⭐ Most Important

**Goal:** Same as streaming, but GPT can also call **tools** to trigger Pepper's physical behaviors and switch personalities.

**How tool calling works in streaming:**
- You send a `tools` list to GPT defining available behaviors and personality switches
- GPT may respond with a `tool_calls` chunk instead of (or alongside) text
- You detect the tool call, execute the behavior or personality switch, then make a second API call to get GPT's verbal response

### Step 1 — Define tools from `.env` variables:
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "perform_behavior",
            "description": BEHAVIORS_METHOD_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "behavior": {
                        "type": "string",
                        "enum": BEHAVIORS_ENUM,
                        "description": BEHAVIORS_DESCRIPTION
                    }
                },
                "required": ["behavior"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "change_personality",
            "description": PERSONALITIES_METHOD_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "personality": {
                        "type": "string",
                        "enum": PERSONALITIES_ENUM,
                        "description": PERSONALITIES_DESCRIPTION
                    }
                },
                "required": ["personality"]
            }
        }
    }
]
```

### Step 2 — Send streaming request with tools:
```python
filtered_message = self.filter_text(message)
self.conversation.append({"role": "user", "content": filtered_message})

# Start eye rotation to show Pepper is "thinking"
self.start_rotate_eyes_thread()

headers = {
    "Authorization": "Bearer " + self.APIKEY,
    "Content-Type": "application/json"
}
payload = {
    "model": CHATMODEL,
    "messages": self.conversation,
    "stream": True,
    "tools": tools
}
response = requests.post(CHATURL, headers=headers, json=payload, stream=True)
```

### Step 3 — Parse stream for BOTH text and tool calls:
```python
full_reply = ""
buffer = ""
tool_name = None
tool_args_str = ""
tool_was_called = False

for line in response.iter_lines():
    if line and line.startswith("data: "):
        chunk = line[6:]
        if chunk == "[DONE]":
            break
        try:
            data = json.loads(chunk)
            delta = data["choices"][0]["delta"]

            # Handle tool calls
            if "tool_calls" in delta:
                tool_was_called = True
                for tc in delta["tool_calls"]:
                    if tc.get("function", {}).get("name"):
                        tool_name = tc["function"]["name"]
                    tool_args_str += tc.get("function", {}).get("arguments", "")

            # Handle text content
            token = delta.get("content", "")
            if token:
                # Stop eye rotation when Pepper starts speaking
                if self.stop_thread == False:
                    self.stop_rotate_eyes_thread()
                    self.my_pepper.fade_eyes("white")

                buffer += token
                full_reply += token

                if any(buffer.endswith(p) for p in [".", "!", "?"]):
                    if sharedVars.ISNEAR:
                        self.my_pepper.have_pepper_say(self.filter_text(buffer.strip()))
                    buffer = ""
        except Exception:
            pass

# Speak remaining buffer
if buffer.strip() and sharedVars.ISNEAR:
    self.my_pepper.have_pepper_say(self.filter_text(buffer.strip()))
```

### Step 4 — Execute tool call if one was triggered:
```python
if tool_was_called and tool_name:
    try:
        args = json.loads(tool_args_str)
    except Exception:
        args = {}

    if tool_name == "perform_behavior":
        behavior = args.get("behavior", "")
        # Run behavior in a background thread so it doesn't block speech
        behavior_thread = threading.Thread(
            target=self.my_pepper.start_behavior, args=(behavior,)
        )
        behavior_thread.start()

    elif tool_name == "change_personality":
        global PREPROMPT, PERSONALITY, ALLPREPROMPT
        new_personality = args.get("personality", "")

        if new_personality == "PREPROMPT_SPICY":
            PREPROMPT = PREPROMPT_SPICY
            PERSONALITY = "PREPROMPT_SPICY"
        elif new_personality == "PREPROMPT_EVENT":
            PREPROMPT = PREPROMPT_EVENT
            PERSONALITY = "PREPROMPT_EVENT"

        ALLPREPROMPT = PREPROMPT + "\n\n [THIS IS WHAT YOUR ROBOT EYES SEE: " + IMAGE_PREPROMPT + " :]"
        self.reset_chat()
        # Re-add the user message so context isn't lost after personality switch
        self.conversation.append({"role": "user", "content": filtered_message})

        # Make a follow-up call with tool_choice=none to get verbal response
        payload2 = {
            "model": CHATMODEL,
            "messages": self.conversation,
            "stream": True,
            "tools": tools,
            "tool_choice": "none"
        }
        response2 = requests.post(CHATURL, headers=headers, json=payload2, stream=True)
        full_reply = ""
        buffer = ""
        for line in response2.iter_lines():
            if line and line.startswith("data: "):
                chunk = line[6:]
                if chunk == "[DONE]":
                    break
                try:
                    token = json.loads(chunk)["choices"][0]["delta"].get("content", "")
                    if token:
                        buffer += token
                        full_reply += token
                        if any(buffer.endswith(p) for p in [".", "!", "?"]):
                            if sharedVars.ISNEAR:
                                self.my_pepper.have_pepper_say(self.filter_text(buffer.strip()))
                            buffer = ""
                except Exception:
                    pass
        if buffer.strip() and sharedVars.ISNEAR:
            self.my_pepper.have_pepper_say(self.filter_text(buffer.strip()))

self.conversation.append({"role": "assistant", "content": full_reply})

# Make sure eye thread is stopped
if not self.stop_thread:
    self.stop_rotate_eyes_thread()

return "done"
```

---

## Method 3: `get_description_of_image_as_base64(image_str)`

**Goal:** Send a base64 image from Pepper's camera to GPT-4o Vision and get back a text description of what Pepper "sees".

```python
def get_description_of_image_as_base64(self, image_str):
    headers = {
        "Authorization": "Bearer " + self.APIKEY,
        "Content-Type": "application/json"
    }
    payload = {
        "model": CHATMODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": IMAGE_PROMPT
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/jpeg;base64," + image_str
                        }
                    }
                ]
            }
        ],
        "max_tokens": 300
    }
    try:
        response = requests.post(CHATURL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return "Unable to process image: " + str(response.status_code)
    except Exception as e:
        print("Vision error: " + str(e))
        return "Vision unavailable."
```

## Method 4: `get_description_of_image_as_base64_threaded(image_str)`

**Goal:** Run vision in a background thread so it doesn't block the conversation, then update the system prompt with what Pepper sees.

```python
def get_description_of_image_as_base64_threaded(self, image_str):
    global IMAGE_PREPROMPT, ALLPREPROMPT
    description = self.get_description_of_image_as_base64(image_str)
    IMAGE_PREPROMPT = description
    ALLPREPROMPT = PREPROMPT + "\n\n [THIS IS WHAT YOUR ROBOT EYES SEE: " + IMAGE_PREPROMPT + " :]"
    self.update_conversation_preprompt()
    print("Vision update: " + description)
```

---

## Method 5: `isGoodbye(message)`

**Goal:** Ask GPT if the user's message signals the end of the conversation. Returns "yes" or "no".

```python
def isGoodbye(self, message):
    headers = {
        "Authorization": "Bearer " + self.APIKEY,
        "Content-Type": "application/json"
    }
    goodbye_messages = [
        {"role": "system", "content": GOODBYEPERSONA},
        {"role": "user", "content": message}
    ]
    payload = {
        "model": CHATMODEL,
        "messages": goodbye_messages
    }
    try:
        response = requests.post(CHATURL, headers=headers, json=payload)
        return response.json()["choices"][0]["message"]["content"].strip().lower()
    except Exception as e:
        print("isGoodbye error: " + str(e))
        return "no"
```

---

## Implementation Order for Phase 2

1. `get_description_of_image_as_base64` + `get_description_of_image_as_base64_threaded` — easiest win, adds visible intelligence
2. `isGoodbye` — simple, standalone
3. `chat_with_gpt_stream` — get streaming working first without tool complexity
4. `chat_with_gpt_stream_behaviors` — the crown jewel, implement last

---

## Testing Tips

- Test `chat_with_gpt_stream` by watching Pepper start speaking before the full response is generated
- Test behaviors by saying something like "can you do a fist bump" — Pepper should extend its arm AND say something
- Test personality switch by saying "switch to Spicy Pepper" — tone should change noticeably
- Test vision by walking up to Pepper and asking "what do you see?" — the IMAGE_PREPROMPT in the system prompt will provide the context

Good luck — this is what makes the judges go wow!
