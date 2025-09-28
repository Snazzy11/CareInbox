
import os
from dotenv import load_dotenv
from agentmail import AgentMail

import requests

load_dotenv()

def connect():
    """
    Connect to AgentMail
    :return: AgentMail client
    """
    api_key = os.getenv("AGENTMAIL_API_KEY")

    client = AgentMail(
        api_key=api_key
    )
    return client

api_key = os.getenv("AGENTMAIL_API_KEY")
main_client = AgentMail(
    api_key=api_key
)

def create_inbox(client):
    print("Creating inbox...")
    inbox = client.inboxes.create() # domain is optional

    print("Inbox created successfully!")
    print(inbox)

def get_email_messages(client, inbox_id: str, limit=None):
    """
    List all messages in an inbox.
    :param limit: Optional limit of messages to return. Default to all messages.
    :param client: AgentMail client
    :param inbox_id: id of the inbox
    :return:
    """

    if limit is not None:
        limit = int(limit)

        return client.inboxes.messages.list(
            inbox_id=inbox_id,
            limit=limit
        )

    else:
        return client.inboxes.messages.list(
        inbox_id=inbox_id
    )

def get_most_recent_message(client, inbox_id: str):
    """
    List the most recent message in an inbox.
    :param client: AgentMail client
    :param inbox_id: id of the inbox
    :return:
    """

    return client.inboxes.messages.list(
        inbox_id=inbox_id,
        limit=1
    )

def get_single_message(client, inbox_id: str, message_id: str):
    """
    Get a single message from the inbox.
    :param client: AgentMail client
    :param inbox_id: id of the inbox
    :param message_id: id of the message
    :return: Full message object; https://docs.agentmail.to/api-reference/inboxes/messages/get
    """

    return client.inboxes.messages.get(
        inbox_id=inbox_id,
        message_id=message_id
    )

if __name__ == '__main__':
    # client = connect()
    inbox_id = os.getenv("AGENTMAIL_INBOX_ID")

    newest_message_id = get_most_recent_message(main_client, inbox_id).messages[0].message_id

    newest_message = get_single_message(main_client, inbox_id, newest_message_id)

    print(newest_message)

    print(f"\n\nMessage Subject: {newest_message.subject}\n\nMessage Body: {newest_message.text}")