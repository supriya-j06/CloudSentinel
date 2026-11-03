from datetime import datetime, timedelta
from models.user import db
class Incident(db.Model):
    __tablename__="incidents"
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(200),nullable=False)
    description=db.Column(db.Text,nullable=False)
    category=db.Column(db.String(100),nullable=False)
    location=db.Column(db.String(200),nullable=False)
    priority=db.Column(db.String(50),nullable=False,default="Medium")
    status=db.Column(db.String(50),nullable=False,default="Reported")
    reported_by=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False)
    assigned_to=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
    sla_due_at=db.Column(db.DateTime,default=lambda: datetime.utcnow()+timedelta(hours=24))
class Activity(db.Model):
    __tablename__="activities"
    id=db.Column(db.Integer,primary_key=True)
    incident_id=db.Column(db.Integer,db.ForeignKey("incidents.id"),nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False)
    message=db.Column(db.String(500),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
