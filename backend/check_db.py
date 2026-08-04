import sqlite3
conn = sqlite3.connect('meetingpilot.db')
print('meetings:', conn.execute("SELECT sql FROM sqlite_master WHERE name='meetings';").fetchone())
print('users:', conn.execute("SELECT sql FROM sqlite_master WHERE name='users';").fetchone())
print('transcripts:', conn.execute("SELECT sql FROM sqlite_master WHERE name='transcripts';").fetchone())
print('google_calendar_tokens:', conn.execute("SELECT sql FROM sqlite_master WHERE name='google_calendar_tokens';").fetchone())

