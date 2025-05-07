from app import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    searches = db.relationship('SearchHistory', backref='user', lazy=True)
    
    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    query = db.Column(db.String(255), nullable=False)
    parameters = db.Column(db.Text, nullable=True)  # JSON string of search parameters
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"SearchHistory('{self.query}', '{self.created_at}')"

class CachedSearch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cache_key = db.Column(db.String(512), unique=True, nullable=False)
    results = db.Column(db.Text, nullable=False)  # JSON string of search results
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    def __repr__(self):
        return f"CachedSearch('{self.cache_key}', '{self.created_at}')"
