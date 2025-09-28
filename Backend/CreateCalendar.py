import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Full calendar access
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """Authenticate and return a Google Calendar service object"""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)

class CalendarAPI:
    def __init__(self):
        self.service = get_calendar_service()

    def add_event(self, title: str, description: str, start_dt: datetime.datetime, end_dt: datetime.datetime, tz="America/New_York"):
        """Add a new calendar event with title and description"""
        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": tz},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": tz},
        }
        try:
            created = self.service.events().insert(calendarId="primary", body=event).execute()
            print(f"✅ Event created: {created.get('htmlLink')}")
            return created["id"]
        except HttpError as error:
            print(f"❌ Error creating event: {error}")
            return None

    def delete_event(self, event_id: str):
        """Delete an event by its ID"""
        try:
            self.service.events().delete(calendarId="primary", eventId=event_id).execute()
            print("❌ Event deleted successfully")
            return True
        except HttpError as error:
            print(f"❌ Error deleting event: {error}")
            return False

    def list_events(self, n=10):
        """List the next n events"""
        now = datetime.datetime.utcnow().isoformat() + "Z"
        try:
            events_result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=n,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            if not events:
                print("No upcoming events found.")
                return []
            for ev in events:
                start = ev["start"].get("dateTime", ev["start"].get("date"))
                summary = ev.get("summary", "(no title)")
                desc = ev.get("description", "")
                print(f"- {start}: {summary} — {desc}")
            return events
        except HttpError as error:
            print(f"❌ Error fetching events: {error}")
            return []

# Example usage
if __name__ == "__main__":
    api = CalendarAPI()

    # Add a test event
    start = datetime.datetime(2025, 10, 1, 10, 0)
    end = datetime.datetime(2025, 10, 1, 11, 0)

    # MAKE SURE THAT VALUES ARE DATETIME OBJECTS

    # WRITE EVENT
    # event_id = api.add_event("EVENT TABLE", "PROJECT DESCRIPTION", START, END)
    event_id = api.add_event("Team Meeting 2", "Discuss project milestones", start, end)

    # READ EVENTS
    api.list_events(5)

    # DELETE EVENT
    # if event_id:
    #     api.delete_event(event_id)