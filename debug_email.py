#!/usr/bin/env python
"""Debug email sending issues."""
import logging
from lms_agent.config import settings
from lms_agent.db import Database
from lms_agent.notifier import Notifier
from lms_agent.logging_config import setup_logging

logger = setup_logging()

print("=" * 70)
print("Email Notification Debug")
print("=" * 70)

# Check 1: Configuration
print("\n1. SMTP Configuration:")
print(f"   Host: {settings.smtp_host}")
print(f"   Port: {settings.smtp_port}")
print(f"   From: {settings.smtp_from}")
print(f"   To: {', '.join(settings.get_smtp_to_list())}")
print(f"   Username: {settings.smtp_username}")
print(f"   Password: {'*' * len(settings.smtp_password)}")

# Check 2: Database state
print("\n2. Database Records:")
db = Database(settings.db_path)

import sqlite3
conn = sqlite3.connect(settings.db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM files")
file_count = c.fetchone()[0]
print(f"   Files: {file_count}")

c.execute("SELECT COUNT(*) FROM assignments")
assign_count = c.fetchone()[0]
print(f"   Assignments: {assign_count}")

c.execute("SELECT * FROM assignments")
assignments = c.fetchall()
if assignments:
    print("\n   Assignment Details:")
    for a in assignments:
        print(f"     - {a['name']} (course_id: {a['course_id']})")
        print(f"       Due: {a['due_at']} | Submitted: {a['submitted']}")

c.execute("SELECT COUNT(*) FROM notifications")
notif_count = c.fetchone()[0]
print(f"   Notifications sent: {notif_count}")

conn.close()

# Check 3: Test email sending
print("\n3. Testing Email Send:")
try:
    db = Database(settings.db_path)
    notifier = Notifier(settings, db)
    notifier._send(
        subject="[LMS] Test Email",
        body_text="This is a test email to verify SMTP configuration works."
    )
    print("   ✅ Test email sent successfully!")
except Exception as e:
    print(f"   ❌ Email failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("Debug Complete")
print("=" * 70)
