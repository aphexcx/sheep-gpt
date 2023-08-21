from typing import Dict, List, Optional, Any

import requests
import time
import psutil
import socket
from zeroconf import ServiceBrowser, Zeroconf, ServiceListener
from mlc_chat import ChatModule, ChatConfig, ConvConfig
from mlc_chat.callback import StreamToStdout

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

class MyListener(ServiceListener):
    server_ip: Optional[str]
    last_fetched_message: Optional[Dict[str, Any]]

    def __init__(self) -> None:
        self.server_ip = None
        self.last_fetched_message = None

    def remove_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
        print(f"Service {name} removed")

    def add_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
        info = zeroconf.get_service_info(type, name)
        print(f"Service {name} added, service info: {info}")
        if info.addresses:
            self.server_ip = socket.inet_ntoa(info.addresses[0])
            print(f"Server IP updated: {self.server_ip}")
        else:
            print("No addresses found for the service")

    def update_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
        info = zeroconf.get_service_info(type, name)
        print(f"Service {name} updated, service info: {info}")
        if info.addresses:
            self.server_ip = socket.inet_ntoa(info.addresses[0])
            print(f"Server IP updated: {self.server_ip}")
        else:
            print("No addresses found for the updated service")

zeroconf = Zeroconf()
listener = MyListener()
browser = ServiceBrowser(zeroconf, "_beatlinkdata._tcp.local.", listener)

# Define the maximum number of retries for failed operations
max_retries = 3

def get_messages() -> Optional[List[Dict[str, Any]]]:
    print("Getting messages...")
    # Define the GET endpoint
    get_endpoint = f"http://{listener.server_ip}:8080/messages"
    for _ in range(max_retries):
        try:
            response = requests.get(get_endpoint)
            messages = response.json()
            print(f"Got {len(messages)} messages")
            if listener.last_fetched_message is None:
                new_messages = messages[-1:]
            else:
                new_messages = []
                for message in reversed(messages):
                    if message == listener.last_fetched_message:
                        break
                    new_messages.append(message)
                new_messages.reverse()
            if messages:
                listener.last_fetched_message = messages[-1]
            return new_messages
        except Exception as e:
            print(f"Error getting messages: {e}")
    return None

def generate_response(messages: List[Dict[str, Any]]) -> Optional[str]:
    print("Generating response...")
    prompt = "" #"Here are the most recent messages people have written: \n"
    prompt += "\n".join([msg["str"] for msg in messages])
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
    print("Posting new thought...")
    # Define the POST endpoint
    post_endpoint = f"http://{listener.server_ip}:8080/newSheepThought"
    for _ in range(max_retries):
        try:
            requests.post(post_endpoint, json={"message": output})
            print("Thought posted")
            return True
        except Exception as e:
            print(f"Error posting message: {e}")
    return False


while True:
    messages = get_messages()
    if messages is not None:
        if len(messages) > 0:
            output = generate_response(messages)
            if output is not None:
                post_message(output)
        else:
            print("No new messages, skipping response generation.")
    time.sleep(30)
