# SheepGPT Chatbot

This project is a chatbot built using the Llama 2 model via the `mlc_chat` library. It fetches messages from a server, generates responses, and posts the responses back to the server.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python 3.6 or higher
- `requests` library
- `psutil` library
- `difflib` library
- `mlc_chat` library

### Installing

1. Clone the repository
2. Install the required libraries using pip:

```bash
pip install -r requirements.txt
```

## Running the Chatbot

To run the chatbot, execute the `sheepGPT.py` script:

```bash
python sheepGPT.py
```

The chatbot will start fetching messages from the server, generate responses, and post the responses back to the server.

## Built With

- [Python](https://www.python.org/)
- [Llama 2](https://github.com/llamachat/llama) via the `mlc_chat` library

## Authors

- Your Name

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

- The `mlc_chat` library for providing the chat module
- The Llama 2 model
