import argparse
import difflib
import time
from typing import List, Optional

import openai
import requests
from mlc_llm import MLCEngine

from zeroconf_listener import listener


def parse_args():
    parser = argparse.ArgumentParser(
        description="Choose the model to use for response generation."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="llama3",
        choices=["llama3", "gpt-4"],
        help="The model to use for response generation.",
    )
    return parser.parse_args()


args = parse_args()

with open("system_prompt_sjobs.txt", "r") as file:
    system_prompt = file.read()

if args.model == "llama3":
    # Create engine
    model = "Llama-3.1-70B-Instruct-q4f16_1-MLC"
    print(f"Loading {model}...")
    engine = MLCEngine(model)
else:
    print("Using OpenAI GPT-4 for response generation.")
    openai.api_key = "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"


# Define the maximum number of retries for failed operations
max_retries = 2

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
            messages = [msg["str"] for msg in response.json() if msg["type"] == "D"]
            print(f"Got {len(messages)} messages")
            diff = difflib.ndiff(local_messages, messages)
            new_messages = [l[2:] for l in diff if l.startswith("+ ")]
            local_messages = messages
            return new_messages
        except Exception as e:
            print(f"Error getting messages: {e}")
    return None


def stream_response(response):
    notify_generating_thought(True)
    total_response = ""
    for chunk in response:
        for choice in chunk.choices:
            delta_message = choice.delta.content
            if delta_message:
                print(delta_message, end="", flush=True)
                total_response += delta_message
                post_partial(delta_message)
    print()
    notify_generating_thought(False)
    return total_response


def post_partial(chunk: str) -> bool:
    # print("Posting partial message chunk...")
    # Define the POST endpoint
    post_endpoint = f"http://{listener.server_ip}:8080/streamPartialSheepThought"
    # for _ in range(max_retries):
    try:
        requests.post(post_endpoint, json={"message": chunk})
        # print(f"Partial message chunk posted: {chunk}")
        return True
    except Exception as e:
        print(f"Error posting partial message: {e}")
    return False


def post_message(output: str) -> bool:
    global last_posted_thought
    print("Posting new thought...")
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


def notify_generating_thought(generating: bool) -> bool:
    print(f"Notifying sheep is thinking={generating}...")
    post_endpoint = f"http://{listener.server_ip}:8080/isGeneratingThought"
    for _ in range(max_retries):
        try:
            requests.post(post_endpoint, json={"isGenerating": generating})
            print("Sheep is thinking notification posted")
            return True
        except Exception as e:
            print(f"Error posting sheep is thinking notification: {e}")
    return False


def generate_response(messages: List[str]) -> Optional[str]:
    print("Generating response...")
    prompt = "\n".join(messages)
    for _ in range(max_retries):
        try:
            if args.model == "llama3":
                response = engine.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    model=model,
                    stream=True,
                )
                total_response = stream_response(response)
                print("Response generated")
                return total_response
            else:
                response = openai.ChatCompletion.create(
                    model="gpt-4-1106-preview",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0,
                    stream=True,
                )
                total_response = stream_response(response)
                print("Response generated")
                return total_response
        except Exception as e:
            print(f"Error generating response: {e}")
            notify_generating_thought(False)
    return None


generate_response(["hello", "how are you?"])

while True:
    messages = get_messages()
    if messages is not None:
        if len(messages) > 0:
            newmessages = "\n".join([msg for msg in messages])
            print(f"New messages\n: {newmessages}")
            output = generate_response(messages)
            if output is not None:
                post_message(output)
        else:
            print("No new messages, skipping response generation.")
    time.sleep(5)
