
import json
import requests
import os
import re
import datetime
import threading
import sharedVars
from myPepper import myPepper
from dotenv import load_dotenv



# Load environment variables from the .env file
load_dotenv()

# Personalities loaded
PREPROMPT_SPICY = os.getenv("PREPROMPT1") #Spicy
PREPROMPT_SPICY_COLOR = os.getenv("PREPROMPTEARCOLOR1") #Spicy

PREPROMPT_EVENT = os.getenv("PREPROMPT2") #Event Nice
PREPROMPT_EVENT_COLOR = os.getenv("PREPROMPTEARCOLOR2") #Event Nice

# Access the environment variables
API_KEY = os.getenv("CHATGPT_KEY")
TRANSCRIPTIONURL = os.getenv("TRANSCRIPTIONURL")
TRANSCRIPTIONMODEL = os.getenv("TRANSCRIPTIONMODEL")
CHATURL = os.getenv("CHATURL")
CHATMODEL = os.getenv("CHATMODEL")
GOODBYEPERSONA = os.getenv("GOODBYEPERSONA")
IMAGE_PROMPT = os.getenv("IMAGE_PROMPT")
PREPROMPT = PREPROMPT_EVENT
IMAGE_PREPROMPT = os.getenv("IMAGE_PREPROMPT")

BEHAVIORS_METHOD_DESCRIPTION = os.getenv("BEHAVIORS_METHOD_DESCRIPTION")
BEHAVIORS_ENUM = os.getenv("BEHAVIORS_ENUM")
print(BEHAVIORS_ENUM)
BEHAVIORS_ENUM = json.loads(BEHAVIORS_ENUM)
BEHAVIORS_DESCRIPTION = os.getenv("BEHAVIORS_DESCRIPTION")

PERSONALITIES_METHOD_DESCRIPTION = os.getenv("PERSONALITIES_METHOD_DESCRIPTION")
PERSONALITIES_ENUM = os.getenv("PERSONALITIES_ENUM")
PERSONALITIES_ENUM = json.loads(PERSONALITIES_ENUM)
PERSONALITIES_DESCRIPTION = os.getenv("PERSONALITIES_DESCRIPTION")

PIP = os.getenv("PIP")
PPORT = int(os.getenv("PPORT"))
LOCAL = os.getenv("LOCAL")

PERSONALITY = "PREPROMPT_EVENT"

ALLPREPROMPT = PREPROMPT + "\n\n [THIS IS WHAT YOUR ROBOT EYES SEE: " + IMAGE_PREPROMPT + " :]"

class chatGPTInteract():

    def __init__(self,  APIKEY):
        self.APIKEY = APIKEY
        if __name__ != "__main__":
            self.my_pepper = myPepper(PIP=PIP, PPORT=PPORT, LOCAL=LOCAL)

        # Initialize conversation with a persona prompt
        self.conversation = [
            {"role": "system", "content": ALLPREPROMPT}
        ]

        self.stop_thread = False  # Initialize the stop flag

    def rotate_eyes(self):
        """
        Loop that animates Pepper's eyes while waiting for a response.
        Runs in a background thread until self.stop_thread is True.
        Calls self.my_pepper.change_eye_color_with_turn() to show rotating white/gray eye effect.
        Used as a 'waiting' indicator during AI processing.
        """
        while not self.stop_thread:
            print("--- MAIN - rotate_eyes")
            self.my_pepper.change_eye_color_with_turn(200, 200, 200, 1, 1)
            #time.sleep(0.1)  # Wait for 1 second before repeating
            
    def start_rotate_eyes_thread(self):
        """
        Start the eye-rotation thread.
        Resets self.stop_thread to False, creates and starts a thread running rotate_eyes().
        """
        self.stop_thread = False  # Make sure the flag is reset when starting
        self.rotate_eyes_thread = threading.Thread(target=self.rotate_eyes)
        self.rotate_eyes_thread.start()
    
    def stop_rotate_eyes_thread(self):
        """
        Stop the eye-rotation thread.
        Sets self.stop_thread to True and joins the thread so it exits cleanly.
        """
        self.stop_thread = True  # Set the flag to signal the thread to stop
        self.rotate_eyes_thread.join()  # Wait for the thread to finish its current task and exit

    def update_conversation_preprompt(self):
        print("--- update_conversation_preprompt ---")
        for node in self.conversation:
            if node["role"] == "system":
                node["content"] = ALLPREPROMPT
                break  # Exit the loop after updating the first 'system' node

    def get_description_of_image_as_base64(self, image_str):
        """
        Use vision AI to describe an image.
        Sends base64 image to the vision API (e.g., GPT-4o) with IMAGE_PROMPT.
        Parses JSON response and returns the text description.
        Handles non-200 responses and returns error message string.
        """
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
                        {"type": "text", "text": IMAGE_PROMPT},
                        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_str}}
                    ]
                }
            ]
        }
        response = requests.post(CHATURL, headers=headers, json=payload)
        if response.status_code != 200:
            return "Error getting image description: " + str(response.status_code)
        return response.json()["choices"][0]["message"]["content"]

    def get_description_of_image_as_base64_threaded(self, image_str):
        """
        Run image description in a background thread and update context.
        Calls get_description_of_image_as_base64(), then updates IMAGE_PREPROMPT
        and ALLPREPROMPT with the result, and calls update_conversation_preprompt().
        """
        def run():
            global IMAGE_PREPROMPT, ALLPREPROMPT
            description = self.get_description_of_image_as_base64(image_str)
            IMAGE_PREPROMPT = description
            ALLPREPROMPT = PREPROMPT + "\n\n [THIS IS WHAT YOUR ROBOT EYES SEE: " + IMAGE_PREPROMPT + " :]"
            self.update_conversation_preprompt()

        thread = threading.Thread(target=run)
        thread.start()

    def add_period_to_newlines(self, input_string):
        """
        Add periods before newlines for TTS formatting.
        Replaces \\r\\n, \\n, and \\r with .\\r\\n, .\\n, and .\\r respectively.
        Returns the modified string.
        """
        # Replace carriage returns and newlines with period + carriage return/newline
        modified_string = input_string.replace("\r\n", ".\r\n")  # for Windows-style line endings
        modified_string = modified_string.replace("\n", ".\n")   # for UNIX-style line endings
        modified_string = modified_string.replace("\r", ".\r")   # for old Mac-style line endings
        
        return modified_string
    
    def filter_text(self, text):
        """
        Sanitize text for TTS and API use.
        Removes non-ASCII or unwanted characters, replaces newlines with spaces.
        Keeps letters, digits, whitespace, and common punctuation ('\",.!?:;-).
        Returns the filtered string.
        """
        filtered_text = text

        #pattern = r'[^\x00-\x7F]'  # Matches any character outside the ASCII range (0-127)
        #filtered_text = re.sub(pattern, '', text)
        
        pattern = r'[^\w\s\'",.!?:;-]' #Matches and filters out strange characters.
        filtered_text = re.sub(pattern, ' ', filtered_text.replace('\n', ' '))

        #print("--- CHATGPT -> FILTER_TEXT -> TEXT = " + str(filtered_text))

        #filtered_text = self.add_period_to_newlines(filtered_text)

        return filtered_text
    
    def isGoodbye(self, message):
        """
        Determine if the user's message indicates they are saying goodbye.
        Sends message to API with GOODBYEPERSONA as system prompt.
        Returns the model's response (e.g., 'yes' or 'no').
        Note: Current implementation has a bug - uses self.conversation instead of goodbye-specific messages.
        """
        headers = {
            "Authorization": "Bearer " + self.APIKEY,
            "Content-Type": "application/json"
        }
        payload = {
            "model": CHATMODEL,
            "messages": [
                {"role": "system", "content": GOODBYEPERSONA},
                {"role": "user", "content": message}
            ]
        }
        response = requests.post(CHATURL, headers=headers, json=payload)
        return response.json()["choices"][0]["message"]["content"]

    def reset_chat(self):
        """
        Reset the conversation to the current personality.
        Replaces self.conversation with a single system message containing ALLPREPROMPT.
        Clears prior turns while preserving the current personality.
        """
        self.conversation = [{"role": "system", "content": ALLPREPROMPT}]

    def chat_with_gpt_stream(self, message):
        """
        Stream ChatGPT response and speak it sentence-by-sentence via Pepper.
        Filters message, appends to conversation, sends streaming request to chat API.
        Parses SSE chunks, accumulates text until sentence-ending punctuation (. ! ?).
        For each complete sentence: filters and calls self.my_pepper.have_pepper_say().
        Appends full assistant reply to conversation. Returns 'done'.
        """
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

        full_reply = ""
        current_sentence = ""

        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0]["delta"]
                        if "content" in delta and delta["content"]:
                            chunk = delta["content"]
                            full_reply += chunk
                            current_sentence += chunk

                            if current_sentence.rstrip().endswith((".", "!", "?")):
                                sentence_to_say = self.filter_text(current_sentence)
                                if sentence_to_say.strip():
                                    self.my_pepper.have_pepper_say(sentence_to_say)
                                current_sentence = ""
                    except (ValueError, KeyError):
                        pass

        if current_sentence.strip():
            sentence_to_say = self.filter_text(current_sentence)
            if sentence_to_say.strip():
                self.my_pepper.have_pepper_say(sentence_to_say)

        self.conversation.append({"role": "assistant", "content": full_reply})
        return "done"

    def chat_with_gpt_stream_behaviors(self, message):
        """
        Stream ChatGPT response with tool calls for behaviors and personality switching.
        Filters message, appends to conversation, starts eye-rotation thread.
        Sends streaming request with tools: perform_behavior, change_personality.
        Parses streaming chunks for text and tool_calls. On sentence boundaries: stops eye
        rotation, sets eye color by personality, calls have_pepper_say() if ISNEAR.
        If tool called: perform_behavior runs behavior in thread; change_personality updates
        PREPROMPT/PERSONALITY/ALLPREPROMPT, resets chat, re-adds user message.
        Makes second request with tool_choice='none' if tool was called.
        Appends assistant response to conversation. Returns 'done'.
        """
        global PREPROMPT, PERSONALITY, ALLPREPROMPT

        filtered_message = self.filter_text(message)
        self.conversation.append({"role": "user", "content": filtered_message})
        self.start_rotate_eyes_thread()

        headers = {
            "Authorization": "Bearer " + self.APIKEY,
            "Content-Type": "application/json"
        }

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "perform_behavior",
                    "description": BEHAVIORS_METHOD_DESCRIPTION,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "behavior_name": {
                                "type": "string",
                                "description": BEHAVIORS_DESCRIPTION,
                                "enum": BEHAVIORS_ENUM
                            }
                        },
                        "required": ["behavior_name"]
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
                                "description": PERSONALITIES_DESCRIPTION,
                                "enum": PERSONALITIES_ENUM
                            }
                        },
                        "required": ["personality"]
                    }
                }
            }
        ]

        payload = {
            "model": CHATMODEL,
            "messages": self.conversation,
            "stream": True,
            "tools": tools
        }

        response = requests.post(CHATURL, headers=headers, json=payload, stream=True)

        full_reply = ""
        current_sentence = ""
        tool_calls = {}  # index -> {"name": str, "arguments": str}
        eyes_running = True

        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0]["delta"]

                        if "content" in delta and delta["content"]:
                            chunk = delta["content"]
                            full_reply += chunk
                            current_sentence += chunk

                            if current_sentence.rstrip().endswith((".", "!", "?")):
                                if eyes_running:
                                    self.stop_rotate_eyes_thread()
                                    eyes_running = False
                                if PERSONALITY == "PREPROMPT_SPICY":
                                    self.my_pepper.fade_eyes(PREPROMPT_SPICY_COLOR)
                                else:
                                    self.my_pepper.fade_eyes(PREPROMPT_EVENT_COLOR)
                                if sharedVars.ISNEAR:
                                    sentence_to_say = self.filter_text(current_sentence)
                                    if sentence_to_say.strip():
                                        self.my_pepper.have_pepper_say(sentence_to_say)
                                current_sentence = ""

                        if "tool_calls" in delta:
                            for tc in delta["tool_calls"]:
                                idx = tc["index"]
                                if idx not in tool_calls:
                                    tool_calls[idx] = {"name": "", "arguments": ""}
                                if "function" in tc:
                                    if "name" in tc["function"]:
                                        tool_calls[idx]["name"] += tc["function"]["name"]
                                    if "arguments" in tc["function"]:
                                        tool_calls[idx]["arguments"] += tc["function"]["arguments"]
                    except (ValueError, KeyError):
                        pass

        # Speak any trailing text
        if current_sentence.strip():
            if eyes_running:
                self.stop_rotate_eyes_thread()
                eyes_running = False
            if sharedVars.ISNEAR:
                sentence_to_say = self.filter_text(current_sentence)
                if sentence_to_say.strip():
                    self.my_pepper.have_pepper_say(sentence_to_say)

        if eyes_running:
            self.stop_rotate_eyes_thread()
            eyes_running = False

        # Process accumulated tool calls
        second_request_needed = False
        for idx in sorted(tool_calls.keys()):
            tc = tool_calls[idx]
            try:
                args = json.loads(tc["arguments"])
            except ValueError:
                continue

            if tc["name"] == "perform_behavior":
                behavior_name = args.get("behavior_name", "")
                behavior_thread = threading.Thread(
                    target=self.my_pepper.launchAndStopBehavior,
                    args=(behavior_name,)
                )
                behavior_thread.start()
                second_request_needed = True

            elif tc["name"] == "change_personality":
                personality = args.get("personality", "")
                if personality == "PREPROMPT_SPICY":
                    PREPROMPT = PREPROMPT_SPICY
                    PERSONALITY = "PREPROMPT_SPICY"
                else:
                    PREPROMPT = PREPROMPT_EVENT
                    PERSONALITY = "PREPROMPT_EVENT"
                ALLPREPROMPT = PREPROMPT + "\n\n [THIS IS WHAT YOUR ROBOT EYES SEE: " + IMAGE_PREPROMPT + " :]"
                self.reset_chat()
                self.conversation.append({"role": "user", "content": filtered_message})
                second_request_needed = True

        # Second request with tool_choice='none' if a tool was called
        if second_request_needed:
            payload2 = {
                "model": CHATMODEL,
                "messages": self.conversation,
                "stream": True,
                "tools": tools,
                "tool_choice": "none"
            }
            response2 = requests.post(CHATURL, headers=headers, json=payload2, stream=True)

            full_reply = ""
            current_sentence = ""

            for line in response2.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0]["delta"]
                            if "content" in delta and delta["content"]:
                                chunk = delta["content"]
                                full_reply += chunk
                                current_sentence += chunk

                                if current_sentence.rstrip().endswith((".", "!", "?")):
                                    if PERSONALITY == "PREPROMPT_SPICY":
                                        self.my_pepper.fade_eyes(PREPROMPT_SPICY_COLOR)
                                    else:
                                        self.my_pepper.fade_eyes(PREPROMPT_EVENT_COLOR)
                                    if sharedVars.ISNEAR:
                                        sentence_to_say = self.filter_text(current_sentence)
                                        if sentence_to_say.strip():
                                            self.my_pepper.have_pepper_say(sentence_to_say)
                                    current_sentence = ""
                        except (ValueError, KeyError):
                            pass

            if current_sentence.strip() and sharedVars.ISNEAR:
                sentence_to_say = self.filter_text(current_sentence)
                if sentence_to_say.strip():
                    self.my_pepper.have_pepper_say(sentence_to_say)

        if full_reply:
            self.conversation.append({"role": "assistant", "content": full_reply})
        return "done"

    def chat_with_gpt(self, message):
        """
        Non-streaming chat with ChatGPT.
        Filters message, appends to conversation, sends single request to chat API.
        Appends assistant reply to conversation. Returns the reply text.
        """
        filtered_message = self.filter_text(message)
        self.conversation.append({"role": "user", "content": filtered_message})

        headers = {
            "Authorization": "Bearer " + self.APIKEY,
            "Content-Type": "application/json"
        }
        payload = {
            "model": CHATMODEL,
            "messages": self.conversation
        }
        response = requests.post(CHATURL, headers=headers, json=payload)
        reply = response.json()["choices"][0]["message"]["content"]
        self.conversation.append({"role": "assistant", "content": reply})
        return reply


    def transcribe_audio_file(self, file_path):
        """
        Transcribe an audio file to text using the transcription API (e.g., Whisper).
        Sends file to TRANSCRIPTIONURL. Returns the response object (or error placeholder).
        Handles request exceptions.
        """
        try:
            headers = {"Authorization": "Bearer " + self.APIKEY}
            files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "audio/wav")}
            data = {"model": TRANSCRIPTIONMODEL}
            response = requests.post(TRANSCRIPTIONURL, headers=headers, files=files, data=data)

            class TranscriptionResult(object):
                pass
            result = TranscriptionResult()
            result.text = response.json()["text"]
            return result
        except requests.exceptions.RequestException as e:
            print("Transcription request error: " + str(e))
            return None

# Example usage:

if __name__ == "__main__":

    from recordAudio4 import manageAudio
    
    chatGPT_Interact = chatGPTInteract(APIKEY=API_KEY)
    manage_audio = manageAudio()
    

    # Initial greeting to get the conversation started
    chatGPT_Interact.chat_with_gpt("Hello")
    
    # Record an audio file
    manage_audio.ambient_sound_check()
    file_path = manage_audio.record_audio()

    # Perform transcription
    transcription_response = chatGPT_Interact.transcribe_audio_file(file_path)

    #output the response
    if transcription_response:

        transcription_text = transcription_response.text
        #print("API Response:" + transcription_text)
        chatbot_response = chatGPT_Interact.chat_with_gpt(transcription_text)
        print(chatbot_response.encode('utf-8'))
    else:
        print("API request failed.")

    #delete file and print the response
    is_audio_file_deleted = str(manage_audio.delete_file(file_path))
    print("audio deleted? - " + is_audio_file_deleted)
    #print("preprompt? - " + ALLPREPROMPT )

