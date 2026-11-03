
import os
import csv
import io
import smtplib

from datetime import datetime, timedelta
from email.message import EmailMessage

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, make_response
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import inspect, text

from models.user import db, User
from models.incident import Incident, Activity
from ai_priority import predict_priority


# ==================================================
# 1. ENVIRONMENT CONFIGURATION
# ==================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"))


# ==================================================
# 2. FLASK CONFIGURATION
# ==================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "CLOUDSENTINEL_SECRET_KEY",
    "change-this-development-key"
)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cloudsentinel.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# ==================================================
# 3. CONSTANTS
# ==================================================

VALID_ROLES = {
    "student",
    "technician",
    "admin"
}

VALID_STATUSES = {
    "Reported",
    "In Progress",
    "Resolved"
}

VALID_CATEGORIES = {
    "Electrical",
    "Internet",
    "Infrastructure",
    "Classroom",
    "Water",
    "Cleanliness",
    "Other",
    "Security"
}

SLA_HOURS = {
    "Critical": 4,
    "High": 12,
    "Medium": 24,
    "Low": 72
}


# ==================================================
# 4. EMAIL NOTIFICATION
# ==================================================

def send_notice(to_email, subject, body):

    host = os.environ.get("SMTP_HOST", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").replace(" ", "").strip()
    sender = os.environ.get("MAIL_FROM", user).strip()

    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError:
        app.logger.error("Invalid SMTP_PORT in .env file.")
        return False

    if not all([host, user, password, to_email, sender]):
        app.logger.error("Email configuration is incomplete.")
        return False

    if (
        "paste_" in password.lower()
        or "your" in user.lower()
        or "yourgmail" in sender.lower()
    ):
        app.logger.error("SMTP credentials still contain placeholders.")
        return False

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email
        msg.set_content(body)

        if port == 465:

            with smtplib.SMTP_SSL(
                host,
                port,
                timeout=20
            ) as server:

                server.login(user, password)
                server.send_message(msg)

        else:

            with smtplib.SMTP(
                host,
                port,
                timeout=20
            ) as server:

                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(user, password)
                server.send_message(msg)

        app.logger.info(
            "Email successfully sent to %s",
            to_email
        )

        return True

    except Exception:
        app.logger.exception(
            "CloudSentinel email delivery failed"
        )
        return False


# ==================================================
# 5. ACTIVITY LOGGING
# ==================================================

def log_activity(incident, message):

    db.session.add(
        Activity(
            incident_id=incident.id,
            user_id=session["user_id"],
            message=message
        )
    )


# ==================================================
# 6. PASSWORD HASH CHECK
# ==================================================

def is_password_hash(value):

    return (
        isinstance(value, str)
        and (
            value.startswith("scrypt:")
            or value.startswith("pbkdf2:")
        )
    )


# ==================================================
# 7. HOME PAGE
# ==================================================

@app.route("/")
def home():

    return render_template("index.html")


# ==================================================
# 8. REGISTER
# ==================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student").strip().lower()

        if not name or not email or not password:

            return render_template(
                "register.html",
                error="Please fill in all fields."
            )

        if len(password) < 6:

            return render_template(
                "register.html",
                error="Password must be at least 6 characters long."
            )

        if role not in VALID_ROLES:

            return render_template(
                "register.html",
                error="Please select a valid account role."
            )

        if User.query.filter_by(email=email).first():

            return render_template(
                "register.html",
                error="Email already registered."
            )

        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# ==================================================
# 9. LOGIN
# ==================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        valid_password = False

        if user:

            if is_password_hash(user.password):

                try:
                    valid_password = check_password_hash(
                        user.password,
                        password
                    )

                except (ValueError, TypeError):
                    valid_password = False

            else:

                # Compatibility with older accounts
                valid_password = user.password == password

                if valid_password:
                    user.password = generate_password_hash(password)
                    db.session.commit()

        if user and valid_password:

            session.clear()

            session["user_id"] = user.id
            session["user_name"] = user.name
            session["user_role"] = user.role

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))

            if user.role == "technician":
                return redirect(url_for("technician_dashboard"))

            return redirect(url_for("student_dashboard"))

        return render_template(
            "login.html",
            error="Invalid email or password."
        )

    return render_template("login.html")


# ==================================================
# 10. STUDENT DASHBOARD
# ==================================================

@app.route("/student-dashboard")
def student_dashboard():

    if (
        "user_id" not in session
        or session.get("user_role") != "student"
    ):
        return redirect(url_for("login"))

    incidents = Incident.query.filter_by(
        reported_by=session["user_id"]
    ).order_by(
        Incident.created_at.desc()
    ).all()

    return render_template(
        "student_dashboard.html",
        name=session.get("user_name", "Student"),
        incidents=incidents,
        now=datetime.utcnow()
    )


# ==================================================
# 11. REPORT INCIDENT
# ==================================================

@app.route("/report-incident", methods=["GET", "POST"])
def report_incident():

    if (
        "user_id" not in session
        or session.get("user_role") != "student"
    ):
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "Other").strip()
        location = request.form.get("location", "").strip()

        if not title or not description or not location:

            return render_template(
                "report_incident.html",
                error="Please fill in all required fields."
            )

        if category not in VALID_CATEGORIES:
            category = "Other"

        priority = predict_priority(
            f"{title} {description} {category}"
        )

        incident = Incident(
            title=title,
            description=description,
            category=category,
            location=location,
            priority=priority,
            status="Reported",
            reported_by=session["user_id"],
            sla_due_at=datetime.utcnow() + timedelta(
                hours=SLA_HOURS.get(priority, 24)
            )
        )

        db.session.add(incident)
        db.session.flush()

        log_activity(
            incident,
            "Incident reported. Machine-learning priority: "
            + priority + "."
        )

        db.session.commit()

        user = db.session.get(User, session["user_id"])

        if user:

            send_notice(
                user.email,
                "CloudSentinel incident received",
                (
                    f"Your incident #{incident.id} was received.\n"
                    f"Title: {incident.title}\n"
                    f"Priority: {priority}\n"
                    f"Status: Reported"
                )
            )

        return redirect(url_for("student_dashboard"))

    return render_template("report_incident.html")


# ==================================================
# 12. INCIDENT DETAILS
# ==================================================

@app.route("/incident/<int:incident_id>")
def incident_details(incident_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    incident = Incident.query.get_or_404(incident_id)

    role = session.get("user_role")

    if (
        role == "student"
        and incident.reported_by != session["user_id"]
    ):
        return redirect(url_for("student_dashboard"))

    if (
        role == "technician"
        and incident.assigned_to is not None
        and incident.assigned_to != session["user_id"]
    ):
        return redirect(url_for("technician_dashboard"))

    if role not in VALID_ROLES:
        return redirect(url_for("login"))

    assigned_technician = None

    if incident.assigned_to:

        assigned_technician = User.query.filter_by(
            id=incident.assigned_to,
            role="technician"
        ).first()

    activities = Activity.query.filter_by(
        incident_id=incident.id
    ).order_by(
        Activity.created_at.desc()
    ).all()

    # IMPORTANT: Pass now to the incident details template.
    return render_template(
        "incident_details.html",
        incident=incident,
        assigned_technician=assigned_technician,
        activities=activities,
        now=datetime.utcnow()
    )


# ==================================================
# 13. TECHNICIAN DASHBOARD
# ==================================================

@app.route("/technician-dashboard")
def technician_dashboard():

    if (
        "user_id" not in session
        or session.get("user_role") != "technician"
    ):
        return redirect(url_for("login"))

    incidents = Incident.query.filter(
        (Incident.assigned_to == session["user_id"])
        | (Incident.assigned_to.is_(None))
    ).order_by(
        Incident.created_at.desc()
    ).all()

    return render_template(
        "technician_dashboard.html",
        name=session.get("user_name", "Technician"),
        incidents=incidents,
        now=datetime.utcnow()
    )


# ==================================================
# 14. UPDATE INCIDENT STATUS
# ==================================================

@app.route("/update-incident/<int:incident_id>", methods=["POST"])
def update_incident(incident_id):

    if (
        "user_id" not in session
        or session.get("user_role") != "technician"
    ):
        return redirect(url_for("login"))

    incident = Incident.query.get_or_404(incident_id)

    if (
        incident.assigned_to is not None
        and incident.assigned_to != session["user_id"]
    ):
        return redirect(url_for("technician_dashboard"))

    status = request.form.get("status", "")

    if status in VALID_STATUSES:

        old_status = incident.status

        incident.status = status

        if incident.assigned_to is None:
            incident.assigned_to = session["user_id"]

        log_activity(
            incident,
            f"Status changed from {old_status} to {status}."
        )

        db.session.commit()

        reporter = db.session.get(
            User,
            incident.reported_by
        )

        if reporter:

            send_notice(
                reporter.email,
                "CloudSentinel incident updated",
                (
                    f"Incident #{incident.id} has been updated.\n"
                    f"New status: {status}"
                )
            )

    return redirect(url_for("technician_dashboard"))


# ==================================================
# 15. ADMIN DASHBOARD
# ==================================================

@app.route("/admin-dashboard")
def admin_dashboard():

    if (
        "user_id" not in session
        or session.get("user_role") != "admin"
    ):
        return redirect(url_for("login"))

    incidents = Incident.query.order_by(
        Incident.created_at.desc()
    ).all()

    technicians = User.query.filter_by(
        role="technician"
    ).order_by(
        User.name.asc()
    ).all()

    stats = {
        key: Incident.query.filter_by(status=value).count()
        for key, value in [
            ("reported", "Reported"),
            ("in_progress", "In Progress"),
            ("resolved", "Resolved")
        ]
    }

    stats["total"] = Incident.query.count()

    now = datetime.utcnow()

    stats["overdue"] = Incident.query.filter(
        Incident.status != "Resolved",
        Incident.sla_due_at < now
    ).count()

    stats["sla_on_track"] = Incident.query.filter(
        Incident.status != "Resolved",
        Incident.sla_due_at >= now
    ).count()

    for priority in ["low", "medium", "high", "critical"]:

        stats[priority] = Incident.query.filter_by(
            priority=priority.title()
        ).count()

    categories = {
        category: Incident.query.filter_by(
            category=category
        ).count()
        for category in sorted(VALID_CATEGORIES)
    }

    return render_template(
        "admin_dashboard.html",
        name=session.get("user_name", "Admin"),
        incidents=incidents,
        technicians=technicians,
        categories=categories,
        now=now,
        **stats
    )


# ==================================================
# 16. ASSIGN TECHNICIAN
# ==================================================

@app.route("/assign-technician/<int:incident_id>", methods=["POST"])
def assign_technician(incident_id):

    if (
        "user_id" not in session
        or session.get("user_role") != "admin"
    ):
        return redirect(url_for("login"))

    incident = Incident.query.get_or_404(incident_id)

    technician_id = request.form.get(
        "technician_id",
        type=int
    )

    technician = None

    if technician_id:

        technician = User.query.filter_by(
            id=technician_id,
            role="technician"
        ).first()

    if technician:

        incident.assigned_to = technician.id

        if incident.status == "Reported":
            incident.status = "In Progress"

        log_activity(
            incident,
            "Assigned to technician: " + technician.name + "."
        )

        db.session.commit()

        send_notice(
            technician.email,
            "CloudSentinel assignment",
            (
                f"Incident #{incident.id} has been assigned to you.\n"
                f"Title: {incident.title}\n"
                f"Location: {incident.location}\n"
                f"Priority: {incident.priority}"
            )
        )

    return redirect(url_for("admin_dashboard"))


# ==================================================
# 17. ADD INCIDENT ACTIVITY UPDATE
# ==================================================

@app.route("/incident/<int:incident_id>/update", methods=["POST"])
def add_incident_update(incident_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    incident = Incident.query.get_or_404(incident_id)

    role = session.get("user_role")

    if (
        role == "student"
        and incident.reported_by != session["user_id"]
    ):
        return redirect(url_for("student_dashboard"))

    if (
        role == "technician"
        and incident.assigned_to not in (
            None,
            session["user_id"]
        )
    ):
        return redirect(url_for("technician_dashboard"))

    if role not in VALID_ROLES:
        return redirect(url_for("login"))

    message = request.form.get(
        "message",
        ""
    ).strip()

    if message:

        db.session.add(
            Activity(
                incident_id=incident.id,
                user_id=session["user_id"],
                message=message[:500]
            )
        )

        db.session.commit()

    return redirect(
        url_for(
            "incident_details",
            incident_id=incident.id
        )
    )


# ==================================================
# 18. EXPORT INCIDENTS TO CSV
# ==================================================

@app.route("/export/incidents.csv")
def export_incidents():

    if (
        "user_id" not in session
        or session.get("user_role") != "admin"
    ):
        return redirect(url_for("login"))

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Title",
        "Category",
        "Location",
        "Priority",
        "Status",
        "Created UTC",
        "SLA Due UTC",
        "Overdue"
    ])

    incidents = Incident.query.order_by(
        Incident.created_at.desc()
    ).all()

    for incident in incidents:

        due = incident.sla_due_at or (
            incident.created_at + timedelta(hours=24)
        )

        overdue = (
            incident.status != "Resolved"
            and datetime.utcnow() > due
        )

        writer.writerow([
            incident.id,
            incident.title,
            incident.category,
            incident.location,
            incident.priority,
            incident.status,
            incident.created_at,
            due,
            "Yes" if overdue else "No"
        ])

    response = make_response(output.getvalue())

    response.headers["Content-Disposition"] = (
        "attachment; filename=cloudsentinel_incidents.csv"
    )

    response.headers["Content-Type"] = (
        "text/csv; charset=utf-8"
    )

    return response


# ==================================================
# 19. ADMIN EMAIL TEST
# ==================================================

@app.route("/admin/email-test", methods=["GET", "POST"])
def admin_email_test():

    if (
        "user_id" not in session
        or session.get("user_role") != "admin"
    ):
        return redirect(url_for("login"))

    result = None

    if request.method == "POST":

        recipient = request.form.get(
            "email",
            ""
        ).strip()

        if not recipient or "@" not in recipient:

            result = "Enter a valid recipient email address."

        elif send_notice(
            recipient,
            "CloudSentinel email test",
            "Your CloudSentinel email notifications are configured correctly."
        ):

            result = (
                "Test email sent. Check your inbox and spam folder."
            )

        else:

            result = (
                "Email was not sent. Check the Flask terminal "
                "for the detailed SMTP error."
            )

    configured = all([
        os.environ.get("SMTP_HOST"),
        os.environ.get("SMTP_USER"),
        os.environ.get("SMTP_PASSWORD")
    ])

    return render_template(
        "email_test.html",
        result=result,
        configured=configured
    )


# ==================================================
# 20. INCIDENT MAP
# ==================================================

@app.route("/incident-map")
def incident_map():

    if (
        "user_id" not in session
        or session.get("user_role") != "admin"
    ):
        return redirect(url_for("login"))

    incidents = Incident.query.all()

    return render_template(
        "incident_map.html",
        incidents=incidents,
        now=datetime.utcnow()
    )


# ==================================================
# 21. LOGOUT
# ==================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# ==================================================
# 22. DATABASE INITIALIZATION
# ==================================================

with app.app_context():

    db.create_all()

    inspector = inspect(db.engine)

    columns = {
        column["name"]
        for column in inspector.get_columns("incidents")
    }

    if "sla_due_at" not in columns:

        db.session.execute(
            text(
                "ALTER TABLE incidents "
                "ADD COLUMN sla_due_at DATETIME"
            )
        )

        db.session.execute(
            text(
                "UPDATE incidents "
                "SET sla_due_at = datetime(created_at, '+24 hours') "
                "WHERE sla_due_at IS NULL"
            )
        )

        db.session.commit()


# ==================================================
# 23. RUN APPLICATION
# ==================================================

if __name__ == "__main__":

    app.run(debug=True)
