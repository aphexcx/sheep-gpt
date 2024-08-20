import argparse
import difflib
import json
import os
import time
from typing import List, Optional

import ollama
import openai
import requests

from zeroconf_listener import listener

CACHE_FILE = "message_cache.json"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Choose the model to use for response generation."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="ollama",
        choices=["ollama", "gpt-4"],
        help="The model to use for response generation.",
    )
    return parser.parse_args()


args = parse_args()

with open("system_prompt_baaahs.txt", "r") as file:
    system_prompt = file.read()
print(f"Loaded system prompt: {system_prompt[:100]}...")  # Print first 100 characters

if args.model == "ollama":
    model = "llama3.1:70b"
    print(f"Using Ollama with {model} model for response generation.")
else:
    print("Using OpenAI GPT-4 for response generation.")
    openai.api_key = "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"


# Define the maximum number of retries for failed operations
max_retries = 2

last_posted_thought = None


def load_cached_messages() -> List[str]:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return []


def save_cached_messages(messages: List[str]):
    with open(CACHE_FILE, 'w') as f:
        json.dump(messages, f)

def get_messages() -> Optional[List[str]]:
    print("Getting messages...")
    # Define the GET endpoint
    get_endpoint = f"http://{listener.server_ip}:8080/messages"
    for _ in range(max_retries):
        try:
            response = requests.get(get_endpoint)
            messages = [msg["str"] for msg in response.json() if msg["type"] == "D"]
            print(f"Got {len(messages)} messages")
            cached_messages = load_cached_messages()
            diff = difflib.ndiff(cached_messages, messages)
            new_messages = [l[2:] for l in diff if l.startswith("+ ")]
            save_cached_messages(messages)
            return new_messages
        except Exception as e:
            print(f"Error getting messages: {e}")
    return None


def stream_response(response):
    notify_generating_thought(True)
    total_response = ""
    if args.model == "ollama":
        for chunk in response:
            delta_message = chunk['message']['content']
            if delta_message:
                print(delta_message, end="", flush=True)
                total_response += delta_message
    else:
        for chunk in response:
            for choice in chunk.choices:
                delta_message = choice.delta.content
                if delta_message:
                    print(delta_message, end="", flush=True)
                    total_response += delta_message
    print()
    notify_generating_thought(False)
    return total_response


def is_question(message: str) -> bool:
    # Check if the message ends with a question mark or starts with a question word
    question_words = ['who', 'what', 'when', 'where', 'why', 'how', 'is', 'are', 'can', 'could', 'would', 'should',
                      'do', 'does', 'did']
    return message.strip().endswith('?') or any(message.lower().strip().startswith(word) for word in question_words)


def determine_in_reply_to(messages: List[str]) -> str:
    # Find the last question in the list of messages
    for message in reversed(messages):
        if is_question(message):
            return message
    # If no question is found, return the last message
    return messages[-1] if messages else ""


def post_message(output: str, in_reply_to: str) -> bool:
    global last_posted_thought
    print("Posting new thought...")
    post_endpoint = f"http://{listener.server_ip}:8080/newGPTReply"
    if output == last_posted_thought:
        print("Thought is the same as the last posted thought, skipping post.")
        return False

    for _ in range(max_retries):
        try:
            requests.post(post_endpoint, json={"answer": output, "inReplyTo": in_reply_to})
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
            if args.model == "ollama":
                stream = ollama.chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True
                )
                total_response = stream_response(stream)
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


# post_message(generate_response(["hello", "who are you?"]))


while True:
    messages = get_messages()
    if messages is not None:
        if len(messages) > 0:
            newmessages = "\n".join([msg for msg in messages])
            print(f"{len(newmessages)} new messages:\n: {newmessages}")
            response = generate_response(messages)
            if response is not None:
                in_reply_to = determine_in_reply_to(messages)
                post_message(response, in_reply_to)
        else:
            print("No new messages, skipping response generation.")
    time.sleep(5)
