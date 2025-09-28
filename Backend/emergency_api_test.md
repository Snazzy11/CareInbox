# Emergency API Testing - cURL Examples

## Overview

The emergency state system allows external clients to monitor when the AI agent flags a message as requiring human review and to reset the emergency state after handling.

## API Endpoints

### 1. Check Emergency Status (GET)

Query the current emergency state to see if there are any flagged messages requiring attention.

```bash
# Check emergency status
curl -X GET http://localhost:8080/emergency/status

# Expected response when no emergency:
# {
#   "emergency_active": false,
#   "timestamp": null,
#   "last_thread_id": null,
#   "message": null
# }

# Expected response when emergency is active:
# {
#   "emergency_active": true,
#   "timestamp": "2025-09-28T10:15:30",
#   "last_thread_id": "thread_abc123",
#   "message": "Emergency flagged by agent"
# }
```

### 2. Reset Emergency Status (POST)

Reset the emergency state after a human has reviewed and handled the flagged message.

```bash
# Reset emergency state
curl -X POST http://localhost:8080/emergency/reset

# Expected response:
# {
#   "status": "emergency_state_reset",
#   "timestamp": "2025-09-28T10:20:45"
# }
```

## Testing Workflow

### Step 1: Monitor for Emergencies

Set up a monitoring script that periodically checks the emergency status:

```bash
# Check every 30 seconds for emergencies
while true; do
  echo "Checking emergency status at $(date)..."
  curl -s http://localhost:8080/emergency/status | jq '.'
  if [ $(curl -s http://localhost:8080/emergency/status | jq -r '.emergency_active') = "true" ]; then
    echo "🚨 EMERGENCY DETECTED! Human review required."
    # Add your notification logic here (email, Slack, etc.)
  fi
  sleep 30
done
```

### Step 2: Simulate Emergency Trigger

To test the emergency system, send an email to your AgentMail inbox with emergency keywords that would trigger the agent to return JSON:

```
Subject: Urgent Help Needed
Body: I'm having severe chest pain and difficulty breathing. What should I do?
```

The agent should detect this as an emergency and set the emergency state to active.

### Step 3: Check Emergency Status

After sending the emergency email, check the status:

```bash
curl -X GET http://localhost:8080/emergency/status
```

### Step 4: Reset After Handling

Once a human has reviewed and handled the emergency, reset the state:

```bash
curl -X POST http://localhost:8080/emergency/reset
```

### Step 5: Verify Reset

Confirm the emergency state has been cleared:

```bash
curl -X GET http://localhost:8080/emergency/status
```

## Production Considerations

1. **Authentication**: In production, add authentication to these endpoints to prevent unauthorized access.

2. **Logging**: Consider adding audit logs for emergency state changes.

3. **Notifications**: Integrate with your notification system (email, Slack, PagerDuty) to alert staff when emergencies are detected.

4. **Monitoring**: Set up automated monitoring that checks the emergency endpoint regularly.

## Example Integration Script

```bash
#!/bin/bash
# emergency_monitor.sh - Simple emergency monitoring script

ENDPOINT="http://localhost:8080/emergency/status"
RESET_ENDPOINT="http://localhost:8080/emergency/reset"

check_emergency() {
    local status=$(curl -s "$ENDPOINT" | jq -r '.emergency_active')
    local timestamp=$(curl -s "$ENDPOINT" | jq -r '.timestamp')
    local message=$(curl -s "$ENDPOINT" | jq -r '.message')

    if [ "$status" = "true" ]; then
        echo "🚨 EMERGENCY ACTIVE since $timestamp"
        echo "Message: $message"
        echo "Manual reset required after review: curl -X POST $RESET_ENDPOINT"
        return 0
    else
        echo "✅ No emergency detected"
        return 1
    fi
}

# Run the check
check_emergency
```

Make the script executable and run it:

```bash
chmod +x emergency_monitor.sh
./emergency_monitor.sh
```
