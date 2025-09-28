
---

## 📄 SETUP.md
```markdown
# Setup for Smart Email Responder

This guide explains how to configure API keys, environment variables, and dependencies for the project.

---

## Setting up API Keys

Three API Keys are needed to run this project:

- **Google Calendar API**: https://developers.google.com/workspace/calendar/api/quickstart/python  
- **Google Gmail API**: https://developers.google.com/gmail/api/quickstart/python  
- **OpenAI API**: https://platform.openai.com/api-keys  

Optional:
- **Ngrok**: https://ngrok.com (for testing and receiving webhooks remotely)

Create accounts and follow the steps at each link to generate the required credentials.

---

## Environment Variables

Create a `.env` file in the project root with the following keys:

```sh
OPENAI_API_KEY=your-openai-api-key
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
NGROK_AUTHTOKEN=your-ngrok-authtoken  # optional
