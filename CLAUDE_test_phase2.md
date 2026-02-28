# Pepper – Phase 2 Testing Guide

## What Was Implemented in Phase 2
- `get_description_of_image_as_base64` ✅
- `get_description_of_image_as_base64_threaded` ✅
- `isGoodbye` ✅
- `chat_with_gpt_stream` ✅
- `chat_with_gpt_stream_behaviors` ✅

## Important: Run with Python 2.7.18
```
python2 chatGPT.py
```

---

## How to Test Without Pepper Hardware

Most Phase 2 methods call `self.my_pepper.have_pepper_say()` which requires the robot.
To test safely on your laptop, mock out the Pepper hardware at the top of `__main__`:

```python
if __name__ == "__main__":

    # --- MOCK PEPPER FOR TESTING (remove when running on real robot) ---
    class FakePepper:
        def have_pepper_say(self, text):
            print("[PEPPER SAYS]: " + text.encode("utf-8"))
        def fade_eyes(self, color):
            print("[EYES]: " + str(color))
        def change_eye_color_with_turn(self, r, g, b, s, t):
            print("[EYE ROTATE]")
        def start_behavior(self, name):
            print("[BEHAVIOR]: " + name)
        def launchAndStopBehavior(self, name):
            print("[BEHAVIOR LAUNCH+STOP]: " + name)

    chatGPT_Interact = chatGPTInteract(APIKEY=API_KEY)
    chatGPT_Interact.my_pepper = FakePepper()  # override the real Pepper
    # --- END MOCK ---
```

This lets you see exactly what Pepper *would* say and do, printed to terminal.

---

## Test 1: `isGoodbye`

**What to verify:** Returns "yes" for farewells, "no" for normal conversation.

```python
# Test isGoodbye
print("--- TEST: isGoodbye ---")
cases = [
    ("See you later!", "yes"),
    ("Goodbye, thanks!", "yes"),
    ("What is the weather today?", "no"),
    ("Tell me about Deloitte.", "no"),
]
for msg, expected in cases:
    result = chatGPT_Interact.isGoodbye(msg).strip().lower()
    status = "PASS" if result == expected else "FAIL (got: " + result + ")"
    print(status + " | '" + msg + "'")
```

**Common failure causes:**
- `GOODBYEPERSONA` is `None` — check `.env` has this key
- API error — print `response.status_code` inside the method

---

## Test 2: `get_description_of_image_as_base64`

**What to verify:** Sends a real image and gets back a text description.

You need a base64 image string. Use this helper to get one from any `.jpg` on your machine:

```python
import base64

def load_image_as_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
```

Then test:
```python
# Test vision
print("--- TEST: get_description_of_image_as_base64 ---")

# Use one of the existing env images already in the project
image_str = load_image_as_base64("envImages/6Yh6n36r21.jpg")  # already in the repo

description = chatGPT_Interact.get_description_of_image_as_base64(image_str)

if not description:
    print("FAIL: empty description")
elif description.startswith("Error"):
    print("FAIL: API error - " + description)
else:
    print("PASS: " + description.encode("utf-8"))
```

**Note:** There are already sample images in the `envImages/` folder from previous Pepper camera captures. Use those.

---

## Test 3: `get_description_of_image_as_base64_threaded`

**What to verify:** Updates `IMAGE_PREPROMPT` and `ALLPREPROMPT` in the background.

```python
import time

print("--- TEST: get_description_of_image_as_base64_threaded ---")
import chatGPT as chatgpt_module

print("IMAGE_PREPROMPT before: " + str(chatgpt_module.IMAGE_PREPROMPT))

image_str = load_image_as_base64("envImages/6Yh6n36r21.jpg")
chatGPT_Interact.get_description_of_image_as_base64_threaded(image_str)

# Wait for thread to finish
time.sleep(5)

print("IMAGE_PREPROMPT after: " + str(chatgpt_module.IMAGE_PREPROMPT))

if chatgpt_module.IMAGE_PREPROMPT == "Waiting for a description to come back from the camera eyes.":
    print("FAIL: IMAGE_PREPROMPT was not updated")
else:
    print("PASS: vision context updated in globals")
```

---

## Test 4: `chat_with_gpt_stream`

**What to verify:** Output arrives sentence-by-sentence (printed progressively), not all at once.

```python
print("--- TEST: chat_with_gpt_stream ---")
print("Watch for [PEPPER SAYS] lines arriving one sentence at a time...")
result = chatGPT_Interact.chat_with_gpt_stream("Tell me three interesting facts about robots.")

if result != "done":
    print("FAIL: did not return 'done'")
else:
    print("PASS: streaming complete")

# Confirm conversation history was updated
last = chatGPT_Interact.conversation[-1]
if last["role"] != "assistant":
    print("FAIL: assistant reply not appended to conversation")
else:
    print("PASS: conversation history updated correctly")
```

**What good output looks like:**
```
[PEPPER SAYS]: Robots have been around since the 1950s.
[PEPPER SAYS]: They are used in manufacturing, healthcare, and space exploration.
[PEPPER SAYS]: The word robot comes from a Czech word meaning forced labor.
PASS: streaming complete
```

**What bad output looks like (not streaming):**
All three sentences arrive in one `[PEPPER SAYS]` block — means sentence boundary detection isn't working.

---

## Test 5: `chat_with_gpt_stream_behaviors` ⭐ Most Important

**What to verify:**
- Pepper speaks a response
- A behavior is triggered when contextually appropriate
- Personality switches when requested

```python
print("--- TEST: behaviors - physical action ---")
chatGPT_Interact.chat_with_gpt_stream_behaviors(
    "Can you do a fist bump to greet me?"
)
# Expected: [BEHAVIOR LAUNCH+STOP] printed, plus a verbal response

print("--- TEST: behaviors - personality switch ---")
chatGPT_Interact.chat_with_gpt_stream_behaviors(
    "Switch to Spicy Pepper mode please."
)
# Expected: personality globals update, conversation resets, Pepper speaks in new persona

print("--- TEST: behaviors - emotion ---")
chatGPT_Interact.chat_with_gpt_stream_behaviors(
    "That is absolutely amazing, I am so surprised!"
)
# Expected: a surprise or mystical behavior triggered
```

**Common failure causes:**
- Eye rotation thread crashes — check `start_rotate_eyes_thread` / `stop_rotate_eyes_thread`
- Tool call arguments not parsed — print `tool_calls` dict after stream ends
- `BEHAVIORS_ENUM` is `None` — confirm `json.loads` ran at import time
- Second request after tool call not firing — add a print inside `if second_request_needed:`

---

## Full Phase 2 Test Run — Copy/Paste into `__main__`

```python
if __name__ == "__main__":
    import base64, time
    import chatGPT as chatgpt_module

    class FakePepper:
        def have_pepper_say(self, text):
            print("[PEPPER SAYS]: " + text.encode("utf-8"))
        def fade_eyes(self, color):
            print("[EYES]: " + str(color))
        def change_eye_color_with_turn(self, r, g, b, s, t):
            print("[EYE ROTATE]")
        def start_behavior(self, name):
            print("[BEHAVIOR]: " + name)
        def launchAndStopBehavior(self, name):
            print("[BEHAVIOR LAUNCH+STOP]: " + name)

    chatGPT_Interact = chatGPTInteract(APIKEY=API_KEY)
    chatGPT_Interact.my_pepper = FakePepper()

    def load_image_as_base64(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    # Test 1
    print("\n=== isGoodbye ===")
    print(chatGPT_Interact.isGoodbye("Bye, see you later!").encode("utf-8"))
    print(chatGPT_Interact.isGoodbye("What time is it?").encode("utf-8"))

    # Test 2
    print("\n=== Vision ===")
    img = load_image_as_base64("envImages/6Yh6n36r21.jpg")
    print(chatGPT_Interact.get_description_of_image_as_base64(img).encode("utf-8"))

    # Test 3
    print("\n=== Streaming ===")
    chatGPT_Interact.chat_with_gpt_stream("Say hello in three short sentences.")

    # Test 4
    print("\n=== Behaviors ===")
    chatGPT_Interact.chat_with_gpt_stream_behaviors("Give me a fist bump!")

    # Test 5
    print("\n=== Personality Switch ===")
    chatGPT_Interact.chat_with_gpt_stream_behaviors("Switch to Spicy Pepper.")
```

---

## Definition of Done for Phase 2

- [ ] `isGoodbye("bye")` returns `"yes"`, `isGoodbye("what time is it")` returns `"no"`
- [ ] `get_description_of_image_as_base64` returns a non-empty descriptive string
- [ ] `IMAGE_PREPROMPT` global updates after threaded vision call
- [ ] `chat_with_gpt_stream` prints sentences one at a time (not all at once)
- [ ] `chat_with_gpt_stream_behaviors` triggers `[BEHAVIOR]` output for social requests
- [ ] Personality switch updates `PERSONALITY` global and resets conversation
- [ ] No crashes on any of the above

Once all pass → connect to Pepper and run `main.py`!
