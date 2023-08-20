import requests
import time
import psutil
from mlc_chat import ChatModule
from mlc_chat.callback import StreamToStdout

CHATMODEL = "Llama-2-70b-chat-hf-q4f16_1"

print(f"Loading {CHATMODEL}...")
# Create a ChatModule instance
cm = ChatModule(model=CHATMODEL)
print(f"{CHATMODEL} loaded")
print(f"Current RAM usage: {psutil.Process().memory_info().rss / 1024 ** 2} MB")

# Define the GET and POST endpoints
get_endpoint = "http://10.53.1.86:8080/messages"
post_endpoint = "http://10.53.1.86:8080/newUserMessage"

# Define the maximum number of retries for failed operations
max_retries = 3

def get_messages():
    print("Getting messages...")
    for _ in range(max_retries):
        try:
            response = requests.get(get_endpoint)
            messages = response.json()
            print(f"Got {len(messages)} messages")
            return messages
        except Exception as e:
            print(f"Error getting messages: {e}")
    return None

def generate_response(messages):
    print("Generating response...")
    with open('prompt.txt', 'r') as file:
        prompt = file.read()
    prompt += "\n".join([msg["str"] for msg in messages])
    for _ in range(max_retries):
        try:
            response = cm.generate(
                prompt=prompt,
                progress_callback=StreamToStdout(callback_interval=2),
            )
            print("Response generated")
            return response
        except Exception as e:
            print(f"Error generating response: {e}")
    return None

def post_message(output):
    print("Posting new thought...")
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
        output = generate_response(messages)
        if output is not None:
            post_message(output)
    time.sleep(60)
