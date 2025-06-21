from app import db
from datetime import datetime
from sqlalchemy import DateTime, String, Text, Integer


class RedeemCode(db.Model):
    __tablename__ = 'redeem_codes'
    
    id = db.Column(Integer, primary_key=True)
    game = db.Column(String(100), nullable=False, index=True)  # wuthering-waves, honkai-star-rail, etc.
    code = db.Column(String(50), nullable=False, unique=True)
    rewards = db.Column(Text, nullable=False)  # Description of rewards
    expires_at = db.Column(DateTime, nullable=True)  # Expiration date
    status = db.Column(String(20), nullable=False, default='new')  # new, expired, active
    created_at = db.Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<RedeemCode {self.code} for {self.game}>'
    
    @property
    def is_expired(self):
        """Check if the code is expired based on expires_at date"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    @property
    def is_expiring_soon(self):
        """Check if the code expires within 7 days"""
        if self.expires_at:
            days_until_expiry = (self.expires_at - datetime.utcnow()).days
            return 0 <= days_until_expiry <= 7
        return False