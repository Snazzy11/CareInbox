# BACKEND #
# Sales Agent Example

Build an agent that sells products to prospects via email.

## Requirements

- Python 3.11 or higher
- [AgentMail API key](httaps://agentmail.io)
- [OpenAI API key](https://platform.openai.com)
- [Ngrok account](https://ngrok.com) (for receiving webhooks)

## Setup

### Ngrok

1. Sign up for a free Ngrok account at [ngrok.com](https://ngrok.com)
2. Get your Ngrok auth token
3. Claim your free static domain

This will create a persistent domain (your-subdomain.ngrok-free.app) that you can use to receive AgentMail webhooks.

### Config

Create a `.env` file with the following content:

```sh
AGENTMAIL_API_KEY=your-agentmail-api-key
OPENAI_API_KEY=your-openai-api-key
NGROK_AUTHTOKEN=your-ngrok-authtoken

INBOX_USERNAME=your-inbox-username
WEBHOOK_DOMAIN=your-webhook-domain
```

Export enivornment variables in the `.env` file

```sh
export $(grep -v '^#' .env | xargs)
```

### AgentMail

Create an inbox

```sh
curl -X POST https://api.agentmail.to/v0/inboxes \
     -H "Authorization: Bearer $AGENTMAIL_API_KEY" \
     -H "Content-Type: application/json" \
     -d "{
  \"username\": \"$INBOX_USERNAME\",
  \"display_name\": \"Email Agent\"
}"
```

Create a webhook

// Edited version due to previous error

```sh
curl -X POST https://api.agentmail.to/v0/webhooks \
     -H "Authorization: Bearer $AGENTMAIL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://'"$WEBHOOK_DOMAIN"'/webhooks",
    "inbox": "'"$INBOX_USERNAME"'@agentmail.to",
    "event_types": ["message.received"] 
  }'
```

### Install

```sh
uv venv
source .venv/bin/activate
uv pip install .
```

## Run

Start the server

```sh
python main.py
```

Now send an email to `your-inbox-username@agentmail.to` with a product to sell and a prospect to sell to. You should provide the name and email address of the prospect.

The Sales Agent will autonomously email the prospect with a sales pitch, answer any of the prospect's questions, and report any intent signals back to you.

Note: You should restart the python script after every sales sequence as the agent stores context in local memory.

# FRONTEND #
## Mantine Vite template

## Features

This template comes with the following features:

- [PostCSS](https://postcss.org/) with [mantine-postcss-preset](https://mantine.dev/styles/postcss-preset)
- [TypeScript](https://www.typescriptlang.org/)
- [Storybook](https://storybook.js.org/)
- [Vitest](https://vitest.dev/) setup with [React Testing Library](https://testing-library.com/docs/react-testing-library/intro)
- ESLint setup with [eslint-config-mantine](https://github.com/mantinedev/eslint-config-mantine)

## npm scripts

## Build and dev scripts

- `dev` – start development server
- `build` – build production version of the app
- `preview` – locally preview production build

### Testing scripts

- `typecheck` – checks TypeScript types
- `lint` – runs ESLint
- `prettier:check` – checks files with Prettier
- `vitest` – runs vitest tests
- `vitest:watch` – starts vitest watch
- `test` – runs `vitest`, `prettier:check`, `lint` and `typecheck` scripts

### Other scripts

- `storybook` – starts storybook dev server
- `storybook:build` – build production storybook bundle to `storybook-static`
- `prettier:write` – formats all files with Prettier
