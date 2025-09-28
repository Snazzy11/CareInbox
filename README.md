# Smart Email Responder

Build an agent that **fetches emails, generates smart responses, and schedules meetings** — powered by **Google Gemini/OpenAI APIs** with a simple Tkinter GUI.

---

## Requirements

- Python 3.11 or higher  
- [Google Cloud credentials](https://console.cloud.google.com) for Gmail/Calendar APIs  
- [OpenAI API key](https://platform.openai.com)  
- [Ngrok account](https://ngrok.com) (optional, for receiving webhooks or remote testing)  

---

## Features

- Fetches incoming emails via Gmail API or IMAP/SMTP  
- Generates smart responses using OpenAI/Gemini  
- Schedules meetings directly on Google Calendar  
- Tkinter GUI with:  
  - Dropdowns for formality & thinking depth  
  - Real-time log output  
  - Flashing alert indicator for important messages  

---

## Install

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
