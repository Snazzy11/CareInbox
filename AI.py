import os
from dotenv import load_dotenv

from google import genai
from google.genai import types


def connect():
    load_dotenv()
    gemini_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=gemini_key)
    return client

# TODO: Using flash-lite for testing
# response = client.models.generate_content(
#     model="gemini-2.5-flash-lite", contents="Explain how AI works in a few words",
#     config=types.GenerateContentConfig(
#             thinking_config=types.ThinkingConfig(thinking_budget=0) #Thinking off
#             # Turn off thinking:
#             # thinking_config=types.ThinkingConfig(thinking_budget=0)
#             # Turn on dynamic thinking:
#             # thinking_config=types.ThinkingConfig(thinking_budget=-1)
#         ),
# )
# print('\n' + response.text)

def create_conversation(client, pre_train=True):
    """
    Create a persistent conversation with Gemini API which can remember what it was told.
    :param client: Gemini client
    :return: chat object of the conversation ref
    """
    load_dotenv()
    chat = client.chats.create(model=os.getenv('GEMINI_MODEL'))

    if pre_train:
        with open('main_prompt.txt') as prompt_file:
            prompt = prompt_file.read()
            chat.send_message(prompt)
            prompt_file.close()


def send_basic_message(client, chat, message: str) -> str:
    """
    Send a basic message to a chat.
    :param client: Gemini client
    :param chat: Gemini persistent chat
    :param message: Message to send
    :return: Gemini's response
    """
    return chat.send_message(message)