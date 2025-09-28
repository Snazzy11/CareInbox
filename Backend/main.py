import os
import asyncio
import json
from threading import Thread
from datetime import datetime, timedelta, timezone
from itertools import count
from typing import Any, Dict, List, Optional, Set

import ngrok
from flask import Flask, request, Response

# Comment: wire up Google Calendar integration so the agent books real events
from zoneinfo import ZoneInfo

# Comment: reuse our calendar helper for real calendar operations
from CreateCalendar import CalendarAPI

from agentmail import AgentMail
from agentmail_toolkit.openai import AgentMailToolkit
from agents import Agent, Runner  # openai-agents
from agents.tool import function_tool  # openai-agents


# --------------------------
# Server & AgentMail wiring
# --------------------------
PORT = int(os.getenv("PORT", "8080"))
DOMAIN = os.getenv("WEBHOOK_DOMAIN")  # optional; can be None
INBOX = f"{os.getenv('INBOX_USERNAME')}@agentmail.to"

# Expose a public URL for webhooks (optional if you're deploying behind your own domain)
listener = ngrok.forward(PORT, domain=DOMAIN, authtoken_from_env=True)
app = Flask(__name__)

client = AgentMail()  # API key read from env: AGENTMAIL_API_KEY


# --------------------------
# Deduping + Thread Memory
# --------------------------
# Some providers retry webhooks; also your app may restart and race.
# We maintain small in-memory sets to avoid double-processing.
PROCESSED_EVENT_IDS: Set[str] = set()
PROCESSED_MESSAGE_IDS: Set[str] = set()

# Keep per-thread chat histories (list of dict[{role, content}])
THREAD_MESSAGES: Dict[str, List[Dict[str, str]]] = {}

# Capture emergency-flagged agent outputs for later human handling
FLAGGED_RESPONSES: Dict[str, Dict[str, Any]] = {}

# Comment: track emergency state that external clients can query and reset
EMERGENCY_STATE = {
    "active": False,
    "timestamp": None,
    "last_thread_id": None,
    "message": None
}

# Comment: maintain in-memory availability so the agent can do true scheduling
AVAILABLE_SLOTS: Set[str] = set()
# Comment: track booked appointments for auditing and potential future use
BOOKED_APPOINTMENTS: Dict[str, Dict[str, Any]] = {}
# Comment: provide monotonically increasing confirmation IDs
_SLOT_ID_COUNTER = count(1)
# Comment: hardcode everything to UTC-4 timezone and fixed date
CLINIC_TIMEZONE_NAME = "UTC-4"
CLINIC_TIMEZONE = timezone(timedelta(hours=-4))
# Comment: hardcoded current date for consistent testing - set to 10 AM
FIXED_DATE = datetime(2025, 9, 28, 10, 0, 0, tzinfo=CLINIC_TIMEZONE)
# Comment: lazily initialize calendar API so OAuth prompts only occur when needed
_calendar_api: Optional[CalendarAPI] = None


def get_current_time() -> datetime:
    """Comment: return hardcoded current time in UTC-4 timezone"""
    return FIXED_DATE


def get_calendar_api() -> CalendarAPI:
    """Comment: instantiate or reuse the Google Calendar client."""
    global _calendar_api
    if _calendar_api is None:
        _calendar_api = CalendarAPI()
    return _calendar_api


def seed_available_slots(days: int = 7) -> None:
    """Comment: populate AVAILABLE_SLOTS using live calendar availability."""
    AVAILABLE_SLOTS.clear()

    # Comment: get hardcoded current time in UTC-4
    now_local = get_current_time()
    start_local = (now_local + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

    # Comment: fetch existing events so we avoid double-booking
    calendar = get_calendar_api()
    existing = calendar.list_events(200) or []

    # Comment: capture busy intervals in UTC for overlap checks
    busy_intervals: List[tuple[datetime, datetime]] = []
    for event in existing:
        start_info = event.get("start") or {}
        end_info = event.get("end") or {}
        start_str = start_info.get("dateTime")
        end_str = end_info.get("dateTime")
        if not start_str or not end_str:
            # Comment: skip all-day or malformed events for now
            continue
        try:
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00")).astimezone(timezone.utc)
            end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            continue
        busy_intervals.append((start_dt, end_dt))

    for day_offset in range(days):
        day_start_local = (start_local + timedelta(days=day_offset)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        for slot_index in range(16):
            slot_local = day_start_local + timedelta(minutes=30 * slot_index)
            if slot_local < start_local:
                continue
            slot_start_utc = slot_local.astimezone(timezone.utc)
            slot_end_utc = slot_start_utc + timedelta(minutes=30)
            # Comment: skip if this 30-minute block overlaps an existing event
            overlaps = any(
                slot_start_utc < busy_end and slot_end_utc > busy_start
                for busy_start, busy_end in busy_intervals
            )
            if overlaps:
                continue
            # Comment: store slots in UTC-4 format for consistency
            slot_start_local_iso = slot_local.isoformat(timespec="minutes")
            AVAILABLE_SLOTS.add(slot_start_local_iso)
            print(f"[DEBUG] Added available slot: {slot_start_local_iso}")


seed_available_slots()


def _normalize_slot(slot: str) -> Optional[str]:
    """Coerce arbitrary slot strings into the canonical ISO format we store."""
    if not slot:
        return None

    candidate = slot.strip()
    if not candidate:
        return None

    try:
        # Comment: handle various timezone formats
        if candidate.endswith("Z"):
            parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        elif "+" in candidate or candidate.count("-") > 2:
            parsed = datetime.fromisoformat(candidate)
        else:
            # Comment: assume naive inputs are in UTC-4
            parsed = datetime.fromisoformat(candidate).replace(tzinfo=CLINIC_TIMEZONE)
    except ValueError:
        # Comment: if parsing fails, surface the raw string for visibility but fail matching
        return slot.strip()

    normalized = parsed.replace(second=0, microsecond=0)
    if normalized.tzinfo is None:
        # Comment: assume naive inputs are given in the clinic's local timezone
        normalized = normalized.replace(tzinfo=CLINIC_TIMEZONE)
    
    # Comment: if time is midnight (00:00), default to 9 AM clinic opening time
    if normalized.hour == 0 and normalized.minute == 0:
        normalized = normalized.replace(hour=9)
    
    # Comment: convert to UTC-4 and return in ISO format
    return normalized.astimezone(CLINIC_TIMEZONE).isoformat(timespec="minutes")


def _suggest_alternatives(limit: int = 5) -> List[str]:
    """Return the next few available slots in chronological order."""
    return sorted(AVAILABLE_SLOTS)[:limit]


def _reserve_slot(slot: str, patient_name: str, reason: str) -> Dict[str, Any]:
    """Reserve the given slot and record the appointment."""
    AVAILABLE_SLOTS.discard(slot)
    confirmation_id = f"CONF-{next(_SLOT_ID_COUNTER):04d}"

    # Comment: parse slot time (already in UTC-4 format)
    slot_start_local = datetime.fromisoformat(slot)
    slot_end_local = slot_start_local + timedelta(minutes=30)

    # Comment: convert to UTC for Google Calendar to avoid timezone confusion
    slot_start_utc = slot_start_local.astimezone(timezone.utc)
    slot_end_utc = slot_end_local.astimezone(timezone.utc)
    
    # Comment: create naive UTC datetime objects for Google Calendar
    slot_start_naive = slot_start_utc.replace(tzinfo=None)
    slot_end_naive = slot_end_utc.replace(tzinfo=None)

    # Comment: create the calendar event so the appointment exists in Google Calendar
    calendar = get_calendar_api()
    event_id = calendar.add_event(
        title=f"Appointment with {patient_name}",
        description=f"Reason: {reason}",
        start_dt=slot_start_naive,
        end_dt=slot_end_naive,
        tz="UTC",  # Comment: Use UTC to avoid timezone conversion issues
    )

    if not event_id:
        # Comment: if calendar creation failed, reinsert slot and surface the issue
        AVAILABLE_SLOTS.add(slot)
        raise RuntimeError("Failed to create calendar event")

    appointment = {
        "confirmation_id": confirmation_id,
        "slot": slot,
        "patient": patient_name,
        "reason": reason,
        "location": "MHacks Clinic",
        "provider": "Dr. Yimmy Yapper",
        "duration_minutes": 30,
        "created_at": get_current_time().isoformat(timespec="seconds"),
        "calendar_event_id": event_id,
    }
    BOOKED_APPOINTMENTS[confirmation_id] = appointment

    # Comment: refresh availability so the agent reflects the latest calendar state
    seed_available_slots()
    return appointment


def is_already_processed(event_id: str, message_id: str) -> bool:
    if event_id in PROCESSED_EVENT_IDS or message_id in PROCESSED_MESSAGE_IDS:
        return True
    PROCESSED_EVENT_IDS.add(event_id)
    PROCESSED_MESSAGE_IDS.add(message_id)
    # Keep the sets bounded (very naive LRU-ish trim)
    if len(PROCESSED_EVENT_IDS) > 5000:
        PROCESSED_EVENT_IDS.clear()
    if len(PROCESSED_MESSAGE_IDS) > 5000:
        PROCESSED_MESSAGE_IDS.clear()
    return False


# --------------------------
# Tool: ScheduleAppointment (stub)
# --------------------------
@function_tool
async def schedule_appointment(
    patient_name: str,
    reason: str,
    preferred_slots: Optional[List[str]] = None,
    confirmed: bool = False,
) -> Dict[str, Any]:
    """
    Comment: Core scheduling logic — checks availability, reserves slots, or proposes options.
    Comment: The agent interprets the returned status to decide whether to confirm or keep chatting.
    """
    ts = get_current_time().isoformat(timespec="seconds")
    print("\n[TOOL CALL] schedule_appointment")
    print(f"  time: {ts}")
    print(f"  patient_name: {patient_name!r}")
    print(f"  reason: {reason!r}")
    print(f"  preferred_slots: {preferred_slots or []}")
    print(f"  confirmed: {confirmed}\n")

    # Comment: refresh availability from Google Calendar at the start of each request
    seed_available_slots()

    normalized_slots: List[str] = []
    unavailable_slots: List[str] = []
    invalid_inputs: List[str] = []

    # Comment: normalize and classify the requested slots, if any were supplied
    for raw_slot in preferred_slots or []:
        print(f"[DEBUG] Processing raw slot: {raw_slot}")
        normalized = _normalize_slot(raw_slot)
        print(f"[DEBUG] Normalized to: {normalized}")
        if not normalized:
            invalid_inputs.append(raw_slot)
            continue
        if normalized in AVAILABLE_SLOTS:
            print(f"[DEBUG] Slot {normalized} is AVAILABLE")
            normalized_slots.append(normalized)
        else:
            print(f"[DEBUG] Slot {normalized} is NOT AVAILABLE")
            print(f"[DEBUG] Available slots: {sorted(list(AVAILABLE_SLOTS))[:5]}")
            unavailable_slots.append(normalized)

    if confirmed and not normalized_slots:
        # Comment: patient tried to confirm an unavailable slot; prompt for new options
        alternatives = _suggest_alternatives()
        return {
            "status": "unavailable",
            "requested_slots": unavailable_slots,
            "invalid_slots": invalid_inputs,
            "alternatives": alternatives,
            "note": "Requested slot unavailable; offered alternatives.",
        }

    if normalized_slots and confirmed:
        # Comment: reserve the earliest viable slot and hand details back to the agent
        chosen_slot = sorted(normalized_slots)[0]
        try:
            appointment = _reserve_slot(chosen_slot, patient_name, reason)
        except Exception as exc:
            print(f"[ERROR] Failed to reserve slot {chosen_slot}: {exc}")
            alternatives = _suggest_alternatives()
            return {
                "status": "error",
                "appointment": None,
                "alternatives": alternatives,
                "note": "Calendar error while booking; please choose another time.",
            }
        return {
            "status": "booked",
            "appointment": appointment,
            "alternatives": [],
            "note": "Confirmed requested time.",
        }

    # Comment: if patient suggested times but none were free, offer close alternatives
    if unavailable_slots and not confirmed:
        alternatives = _suggest_alternatives()
        return {
            "status": "unavailable",
            "requested_slots": unavailable_slots,
            "invalid_slots": invalid_inputs,
            "alternatives": alternatives,
            "note": "Requested slots are already booked.",
        }

    # Comment: no confirmed selection yet — share top choices to continue the dialogue
    alternatives = _suggest_alternatives()
    return {
        "status": "awaiting_patient",
        "requested_slots": normalized_slots,
        "invalid_slots": invalid_inputs,
        "alternatives": alternatives,
        "note": "Present options to patient and wait for their pick.",
    }


# --------------------------
# Agent System Prompt
# --------------------------
instructions = f"""
You are an email triage and scheduling agent for a clinic. Your name is CareInbox.
Your email address is {INBOX}.

CURRENT DATE & TIME CONTEXT
- Today's date is {get_current_time().strftime('%A, %B %d, %Y')} at {get_current_time().strftime('%I:%M %p')} (UTC-4)
- When patients mention dates, always check if they're requesting past dates and clarify if needed
- If a patient requests a past date, politely explain it's not possible and offer current available dates

GOALS
1) Read incoming emails and classify intent: scheduling, routine question, admin request, or potential emergency.
2) If emergency or severe red-flag symptoms (e.g., chest pain, stroke signs, suicidal ideation, severe breathing issues), DO NOT provide medical advice. Reply with a json object with the key emergency: true and message: a brief urgent-safety message for the human review.
3) If scheduling is requested, gather any missing details (legal name, visit reason, availability) and call the schedule_appointment tool. Supply the patient's name, reason, and any concrete preferred times the patient provides. If the patient did not give any time, pass an empty list so the tool can propose available slots.
4) For routine/admin questions (refill status, hours, directions, paperwork), answer succinctly and politely.
5) Keep all outputs as plain-text email bodies (no Subject). Never use markdown or placeholders.

STYLE
- Be concise, friendly, and professional.
- Assume the writer is the patient unless they state otherwise.
- When you schedule successfully, include the time (or note it's pending), provider, location, and confirmation ID in the reply.
- If info is missing (e.g., legal name or DOB), politely ask in the reply while still taking helpful action (e.g., offer times or say staff will follow up).
- When discussing scheduling, confirm which of the presented slots the patient prefers, then call the tool again once you have a concrete choice.
- A successful booking requires the tool to return status "booked"; otherwise keep the conversation going.
- Always include the full date (including year) when mentioning appointment times to avoid confusion.

FLAGGING
- When you believe this message needs human review (clinical urgency or uncertainty), return a json object with the key emergency: true and message: a brief urgent-safety message about the situation. DO NOT REPLY TO THE EMAIL. ONLY RETURN THE JSON OBJECT.

TOOLS
- Use the schedule_appointment function to check availability, reserve slots, and get fallback suggestions.
- Use AgentMail tools to reply to patients.

IMPORTANT GUARDRAILS
- The operational hours are 9:00 AM to 5:00 PM, all days of the week.
- Only reply to inbound 'received' messages that your agent has not already replied to.
- Do not reply to your own sent messages.
"""

agent = Agent(
    name="Clinic Agent",
    instructions=instructions,
    tools=AgentMailToolkit(client).get_tools() + [schedule_appointment],
)


# --------------------------
# Helpers
# --------------------------
def format_prompt_from_email(email: Dict[str, Any]) -> str:
    """Turn an email object into a user message for the LLM."""
    from_addr = email.get("from") or email.get("from_", "")
    subject = email.get("subject", "(no subject)")
    body = (email.get("text") or "").strip()
    return f"From: {from_addr}\nSubject: {subject}\nBody:\n{body}\n"


def should_reply_to(email: Dict[str, Any]) -> bool:
    """
    Basic gating to avoid double replies:
    - Only handle inbound messages (label 'received').
    - If message already marked 'replied', skip.
    """
    labels = set(email.get("labels") or [])
    if "received" not in labels:
        return False
    if "replied" in labels:
        return False
    return True


def get_thread_messages(thread_id: str) -> List[Dict[str, str]]:
    """Fetch or create the per-thread memory list."""
    if thread_id not in THREAD_MESSAGES:
        THREAD_MESSAGES[thread_id] = []
    return THREAD_MESSAGES[thread_id]


def persist_thread_messages(thread_id: str, response) -> None:
    """Update per-thread memory after a run."""
    THREAD_MESSAGES[thread_id] = response.to_input_list()


# --------------------------
# Emergency State API Endpoints
# --------------------------
@app.route("/emergency/status", methods=["GET"])
def get_emergency_status():
    """Comment: allow external clients to query the current emergency state"""
    return {
        "emergency_active": EMERGENCY_STATE["active"],
        "timestamp": EMERGENCY_STATE["timestamp"],
        "last_thread_id": EMERGENCY_STATE["last_thread_id"],
        "message": EMERGENCY_STATE["message"]
    }


@app.route("/emergency/reset", methods=["POST"])
def reset_emergency_status():
    """Comment: allow external clients to reset the emergency state"""
    global EMERGENCY_STATE
    EMERGENCY_STATE = {
        "active": False,
        "timestamp": None,
        "last_thread_id": None,
        "message": None
    }
    return {"status": "emergency_state_reset", "timestamp": get_current_time().isoformat(timespec="seconds")}


# --------------------------
# Webhook: receive emails
# --------------------------
@app.route("/webhooks", methods=["POST"])
def receive_webhook():
    payload = request.json or {}
    # Respond immediately to avoid retries; process async to keep webhook snappy
    Thread(target=process_webhook, args=(payload,)).start()
    return Response(status=200)


def process_webhook(payload: Dict[str, Any]) -> None:
    try:
        event_id = payload.get("event_id", "")
        email = payload.get("message", {}) or {}
        message_id = email.get("message_id", "")
        thread_id = email.get("thread_id", "")

        # Deduping: skip if we've seen this event or message
        if is_already_processed(event_id, message_id):
            print(f"[DEDUPED] event_id={event_id} message_id={message_id}")
            return

        # Gate: only reply to fresh inbound messages
        if not should_reply_to(email):
            print(f"[SKIP] Not an inbound/unreplied message (message_id={message_id})")
            return

        # Build prompt and run the agent with per-thread memory
        prompt = format_prompt_from_email(email)
        print("\n=== Incoming Email =====================")
        print(f"thread_id: {thread_id}")
        print(f"message_id: {message_id}")
        print(prompt)
        print("=======================================\n")

        prior = get_thread_messages(thread_id)
        response = asyncio.run(Runner.run(agent, prior + [{"role": "user", "content": prompt}]))

        final_text = (response.final_output or "").strip()

        # When the agent returns JSON, treat it as a flagged response
        is_json = False
        if final_text.startswith("{") and final_text.endswith("}"):
            try:
                parsed = json.loads(final_text)
                is_json = True
            except json.JSONDecodeError:
                parsed = None
        else:
            parsed = None

        if is_json and isinstance(parsed, dict) and parsed.get("emergency") is True:
            # Comment: store flagged responses with metadata for later review
            # Store flagged response for later human handling
            FLAGGED_RESPONSES[thread_id] = {
                "timestamp": get_current_time().isoformat(timespec="seconds"),
                "message_id": message_id,
                "event_id": event_id,
                "payload": parsed,
            }

            # Comment: update global emergency state for external client monitoring
            global EMERGENCY_STATE
            EMERGENCY_STATE = {
                "active": True,
                "timestamp": get_current_time().isoformat(timespec="seconds"),
                "last_thread_id": thread_id,
                "message": parsed.get("message", "Emergency flagged by agent")
            }

            # Comment: remind developers where to trigger notification hooks
            print("\n=== Agent Flagged ======================")
            print(json.dumps(FLAGGED_RESPONSES[thread_id], indent=2))
            print(f"Emergency state activated: {EMERGENCY_STATE}")
            print("=======================================\n")

            # Comment: bail out early so no automated reply is sent
            # Optionally notify other systems here (e.g., emit WebSocket event)
            return

        print("\n=== Agent Reply ========================")
        print(final_text)
        print("=======================================\n")

        # Send the reply (reply to THIS specific message_id)
        client.inboxes.messages.reply(
            inbox_id=INBOX,
            message_id=message_id,
            text=final_text,
        )

        # Update labels to prevent re-replying to the same message
        try:
            client.inboxes.messages.update(
                inbox_id=INBOX,
                message_id=message_id,
                add_labels=["replied"],
                remove_labels=["unreplied"],
            )
        except Exception as e:
            # Non-fatal; continue
            print(f"[WARN] Failed to update labels for {message_id}: {e}")

        # Persist per-thread memory
        persist_thread_messages(thread_id, response)

    except Exception as e:
        print(f"[ERROR] process_webhook failed: {e}")


# --------------------------
# Entrypoint
# --------------------------
if __name__ == "__main__":
    public_url = listener.url() if hasattr(listener, "url") else "(ngrok disabled)"
    print(f"Public webhook URL: {public_url}")
    print(f"Inbox: {INBOX}\n")
    app.run(port=PORT)
