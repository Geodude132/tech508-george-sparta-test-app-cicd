from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import UserMixin
from datetime import datetime

# Initialize extensions (to be initialized in app.py)
db = SQLAlchemy()
bcrypt = Bcrypt()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    firstname = db.Column(db.String(64), nullable=False)
    lastname = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    requests = db.relationship('Request', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Request(db.Model):
    __tablename__ = 'requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    request_created = db.Column(db.DateTime, default=datetime.utcnow)
    correlation_id = db.Column(db.String(64))
    customer_filename = db.Column(db.String(255))
    original_resolution = db.Column(db.String(32))
    original_filesize = db.Column(db.Integer)
    resized_filename = db.Column(db.String(255))
    resized_resolution = db.Column(db.String(32))
    new_filesize = db.Column(db.Integer)
    reduce_to_percent = db.Column(db.Integer)
    status = db.Column(db.String(32))
    failure_reason = db.Column(db.String(255))
    expiry = db.Column(db.DateTime)
    type = db.Column(db.String(16), default='image')  # 'image' or 'zip'
