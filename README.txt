CloudSentinel — Improved Project Package
========================================

This ZIP contains your integrated CloudSentinel Flask project with a refreshed interface.

Features included
- Responsive student dashboard with incident summary cards, instant search, and status/priority filters.
- Incident detail page with status progress, creation/update timestamps, and assigned technician name.
- Admin dashboard with incident statistics, category/priority overview, instant search and filters, and technician assignment.
- Technician work queue with search and status updates.
- Refreshed login, registration, and incident-reporting pages.
- Passwords are now stored as one-way hashes for newly registered accounts.
- Existing accounts with old plain-text passwords remain compatible: when an old account successfully logs in, its password is upgraded to a hash automatically.
- Existing SQLite database structure is retained; no database deletion is needed.

How to run on Windows
1. Extract this ZIP.
2. Open the extracted `CloudSentinel` folder.
3. Click the address bar in File Explorer, type `powershell`, and press Enter.
4. (Recommended) Create a virtual environment:
       python -m venv venv
       .\venv\Scripts\Activate.ps1
5. Install dependencies:
       pip install -r requirements.txt
6. Start the app:
       python app.py
7. Open this address in your browser:
       http://127.0.0.1:5000

If PowerShell blocks virtual environment activation, run:
       Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
Then activate the environment again.

Important notes
- Keep your existing `instance/cloudsentinel.db` (if present) when moving this project so your existing incidents and users are retained. If the database file is located elsewhere in your original project, copy it into the same location before running.
- For an existing project, back up the original folder before replacing it with this package.
- The registration page retains the Student/Technician/Admin role selector for local MCA-project demonstration. In a real deployment, administrator account creation must be restricted.
- The development secret key is a fallback for local testing only. Before deployment, set the `CLOUDSENTINEL_SECRET_KEY` environment variable to a long random secret.
- Run only on your own machine for your demo; this configuration is not hardened for public internet deployment.


ADDED FEATURES
- ML-based incident priority prediction using scikit-learn (trained from a small built-in example dataset).
- SLA deadlines: Critical 4h, High 12h, Medium 24h, Low 72h.
- Activity timeline with incident notes and status/assignment events.
- Admin CSV export: /export/incidents.csv
- Interactive map: /incident-map (admin only; requires internet for Leaflet/OpenStreetMap and best-effort geocoding).
- Email notifications are configured through the `.env` file in the project folder. The included `.env` has placeholders only; you must enter your own Gmail address and Google App Password. For Gmail, enable 2-Step Verification and create an App Password at https://myaccount.google.com/apppasswords. Then run `python -m pip install -r requirements.txt` and restart with `python app.py`. Never share your real `.env` or App Password.

Note: Email is disabled until SMTP settings are configured. Browser map geocoding depends on third-party service availability and location text quality. Back up your database before replacing existing files.


LATEST IMPROVEMENTS
- Campus map now always plots incident pins at an approximate RVCE campus position; it does not rely on Nominatim finding room names. Exact room/building coordinates need to be surveyed and configured.
- SLA details now compare the deadline with current UTC time; admin dashboard shows overdue and within-SLA counts.
- Admin can open Test Email to verify Gmail SMTP settings. Email sending still requires the owner to add a valid Gmail App Password to .env.
- .env is excluded from Git using .gitignore. Never upload real credentials.

EMAIL SETUP
1. Enable Google 2-Step Verification and create a Google App Password.
2. Open .env in this folder and set SMTP_USER, SMTP_PASSWORD and MAIL_FROM.
3. Restart Flask, sign in as admin, and use Test Email.

RUN
python -m pip install -r requirements.txt
python app.py
