import datetime
import os.path
import tkinter as tk
from tkinter import ttk, messagebox

from tkcalendar import Calendar
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Full calendar access
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
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

class CalendarGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Google Calendar GUI")
        self.geometry("750x500")
        self.service = get_calendar_service()

        # Treeview for events
        self.tree = ttk.Treeview(self, columns=("start", "summary"), show="headings")
        self.tree.heading("start", text="Start")
        self.tree.heading("summary", text="Event")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)

        # Buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Fetch Events", command=self.fetch_events).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Add Event", command=self.add_event_dialog).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete Selected", command=self.delete_selected).pack(side=tk.LEFT, padx=5)

        self.events = []

    def fetch_events(self):
        try:
            now = datetime.datetime.utcnow().isoformat() + "Z"
            events_result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=20,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            self.events = events_result.get("items", [])

            for i in self.tree.get_children():
                self.tree.delete(i)

            for ev in self.events:
                start = ev["start"].get("dateTime", ev["start"].get("date"))
                summary = ev.get("summary", "(no title)")
                self.tree.insert("", tk.END, values=(start, summary))
        except HttpError as error:
            messagebox.showerror("Error", f"An error occurred: {error}")

    def add_event_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add Event")

        tk.Label(dialog, text="Title:").pack(pady=5)
        title_entry = tk.Entry(dialog, width=40)
        title_entry.pack(pady=5)

        tk.Label(dialog, text="Start Date:").pack()
        start_cal = Calendar(dialog, selectmode="day")
        start_cal.pack(pady=5)
        tk.Label(dialog, text="Start Time (HH:MM 24h):").pack()
        start_time = tk.Entry(dialog)
        start_time.insert(0, "10:00")
        start_time.pack(pady=5)

        tk.Label(dialog, text="End Date:").pack()
        end_cal = Calendar(dialog, selectmode="day")
        end_cal.pack(pady=5)
        tk.Label(dialog, text="End Time (HH:MM 24h):").pack()
        end_time = tk.Entry(dialog)
        end_time.insert(0, "11:00")
        end_time.pack(pady=5)

        def save_event():
            title = title_entry.get()
            if not title:
                messagebox.showerror("Error", "Title required")
                return

            try:
                start_dt = datetime.datetime.combine(
                    start_cal.selection_get(),
                    datetime.datetime.strptime(start_time.get(), "%H:%M").time()
                )
                end_dt = datetime.datetime.combine(
                    end_cal.selection_get(),
                    datetime.datetime.strptime(end_time.get(), "%H:%M").time()
                )
            except Exception:
                messagebox.showerror("Error", "Invalid time format. Use HH:MM (24h).")
                return

            # Template for all events
            event = {
                "summary": title,
                "start": {"dateTime": start_dt.isoformat().replace("+00:00", "Z")},
                "end":   {"dateTime": end_dt.isoformat().replace("+00:00", "Z")},
                # no "timeZone" fields

            }

            try:
                # Add event
                created = self.service.events().insert(calendarId="primary", body=event).execute()
                messagebox.showinfo("Success", f"Event created: {created.get('htmlLink')}")
                dialog.destroy()
                self.fetch_events()
            except HttpError as error:
                messagebox.showerror("Error", f"An error occurred: {error}")

        tk.Button(dialog, text="Save Event", command=save_event).pack(pady=10)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Delete", "No event selected")
            return
        idx = self.tree.index(selected[0])
        event_id = self.events[idx]["id"]
        try:
            # Delete event
            self.service.events().delete(calendarId="primary", eventId=event_id).execute()
            messagebox.showinfo("Deleted", "Event deleted successfully")
            self.fetch_events()
        except HttpError as error:
            messagebox.showerror("Error", f"An error occurred: {error}")

if __name__ == "__main__":
    app = CalendarGUI()
    app.mainloop()