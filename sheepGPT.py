from typing import Dict, List, Optional, Any
import difflib

import requests
import time
import psutil
from mlc_chat import ChatModule, ChatConfig, ConvConfig
from mlc_chat.callback import StreamToStdout

from zeroconf_listener import listener


CHATMODEL = "Llama-2-70b-chat-hf-q4f16_1"

with open('system_prompt.txt', 'r') as file:
    system_prompt = file.read()

print(f"Loading {CHATMODEL}...")
# Create a ChatModule instance
conv_config = ConvConfig(system=system_prompt)
config = ChatConfig(temperature=0.75, conv_config=conv_config)
cm = ChatModule(model=CHATMODEL, chat_config=config)
print(f"{CHATMODEL} loaded")
print(f"Current RAM usage: {psutil.Process().memory_info().rss / 1024 ** 2} MB")


# Define the maximum number of retries for failed operations
max_retries = 3

local_messages = []
last_posted_thought = None


def get_messages() -> Optional[List[str]]:
    global local_messages
    print("Getting messages...")
    # Define the GET endpoint
    get_endpoint = f"http://{listener.server_ip}:8080/messages"
    for _ in range(max_retries):
        try:
            response = requests.get(get_endpoint)
            messages = [msg["str"] for msg in response.json()]
            print(f"Got {len(messages)} messages")
            diff = difflib.ndiff(local_messages, messages)
            new_messages = [l[2:] for l in diff if l.startswith('+ ')]
            local_messages = messages
            return new_messages
        except Exception as e:
            print(f"Error getting messages: {e}")
    return None


def generate_response(messages: List[str]) -> Optional[str]:
    print("Generating response...")
    prompt = "" #"Here are the most recent messages people have written: \n"
    prompt += "\n".join([msg for msg in messages])
    for _ in range(max_retries):
        try:
            response = cm.generate(
                prompt=prompt,
                progress_callback=StreamToStdout(callback_interval=2),
            )
            print("Response generated")
            print(cm.stats())
            print(f"Current RAM usage: {psutil.Process().memory_info().rss / 1024 ** 2} MB")
            return response
        except Exception as e:
            print(f"Error generating response: {e}")
    return None


def post_message(output: str) -> bool:
    global last_posted_thought
    print("Posting new thought...")
    # Define the POST endpoint
    post_endpoint = f"http://{listener.server_ip}:8080/newSheepThought"
    if output == last_posted_thought:
        print("Thought is the same as the last posted thought, skipping post.")
        return False
    for _ in range(max_retries):
        try:
            requests.post(post_endpoint, json={"message": output})
            print("Thought posted")
            last_posted_thought = output
            return True
        except Exception as e:
            print(f"Error posting message: {e}")
    return False


while True:
    messages = get_messages()
    if messages is not None:
        if len(messages) > 0:
            newmessages ="\n".join([msg for msg in messages])
            print(f"New messages\n: {newmessages}")
            output = generate_response(messages)
            if output is not None:
                post_message(output)
        else:
            print("No new messages, skipping response generation.")
    time.sleep(20)
