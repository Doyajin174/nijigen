#!/usr/bin/env python3
"""
Script to populate the database with sample redeem codes
"""

from app import app, db
from models import RedeemCode
from datetime import datetime, timedelta


def seed_database():
    with app.app_context():
        # Clear existing data
        RedeemCode.query.delete()
        
        # Sample redeem codes for each game
        sample_codes = [
            # Wuthering Waves
            {
                'game': 'wuthering-waves',
                'code': 'WUTHERINGGIFT2025',
                'rewards': '100 Astrite, 10x Advanced Sealed Tube, 50,000 Shell Credits',
                'expires_at': datetime.utcnow() + timedelta(days=30),
                'status': 'new'
            },
            {
                'game': 'wuthering-waves',
                'code': 'SUMMERGIFT2025',
                'rewards': '80 Astrite, 5x Premium Sealed Tube, 30,000 Shell Credits',
                'expires_at': datetime.utcnow() + timedelta(days=5),
                'status': 'new'
            },
            {
                'game': 'wuthering-waves',
                'code': 'SPRINGCODE2025',
                'rewards': '60 Astrite, 3x Advanced Sealed Tube',
                'expires_at': datetime.utcnow() - timedelta(days=15),
                'status': 'expired'
            },
            
            # Honkai Star Rail
            {
                'game': 'honkai-star-rail',
                'code': 'STELLARGIFT2025',
                'rewards': '100 Stellar Jade, 10x Star Rail Pass, 50,000 Credits',
                'expires_at': datetime.utcnow() + timedelta(days=35),
                'status': 'new'
            },
            {
                'game': 'honkai-star-rail',
                'code': 'TRAILBLAZER2025',
                'rewards': '80 Stellar Jade, 5x Star Rail Special Pass, 30,000 Credits',
                'expires_at': datetime.utcnow() + timedelta(days=3),
                'status': 'new'
            },
            {
                'game': 'honkai-star-rail',
                'code': 'HSRANNIVERSARY2024',
                'rewards': '200 Stellar Jade, 20x Star Rail Pass',
                'expires_at': datetime.utcnow() - timedelta(days=30),
                'status': 'expired'
            },
            
            # Zenless Zone Zero
            {
                'game': 'zenless-zone-zero',
                'code': 'ZENLESSGIFT2025',
                'rewards': '100 Polychrome, 10x Encrypted Master Tape, 50,000 Dennies',
                'expires_at': datetime.utcnow() + timedelta(days=25),
                'status': 'new'
            },
            {
                'game': 'zenless-zone-zero',
                'code': 'ZEROZONE2025',
                'rewards': '80 Polychrome, 5x Signal Search, 30,000 Dennies',
                'expires_at': datetime.utcnow() + timedelta(days=8),
                'status': 'new'
            },
            {
                'game': 'zenless-zone-zero',
                'code': 'BETACODE2024',
                'rewards': '150 Polychrome, 15x Master Tape',
                'expires_at': datetime.utcnow() - timedelta(days=60),
                'status': 'expired'
            },
            
            # Genshin Impact
            {
                'game': 'genshin-impact',
                'code': 'GENSHINGIFT2025',
                'rewards': '100 Primogems, 10x Mystic Enhancement Ore, 50,000 Mora',
                'expires_at': datetime.utcnow() + timedelta(days=40),
                'status': 'new'
            },
            {
                'game': 'genshin-impact',
                'code': 'TRAVELER2025',
                'rewards': '80 Primogems, 5x Hero\'s Wit, 30,000 Mora',
                'expires_at': datetime.utcnow() + timedelta(days=7),
                'status': 'new'
            },
            {
                'game': 'genshin-impact',
                'code': 'INAZUMA2025',
                'rewards': '120 Primogems, 3x Intertwined Fate, 40,000 Mora',
                'expires_at': datetime.utcnow() + timedelta(days=20),
                'status': 'new'
            },
            {
                'game': 'genshin-impact',
                'code': 'GENSHINANNIVERSARY2024',
                'rewards': '300 Primogems, 10x Intertwined Fate',
                'expires_at': datetime.utcnow() - timedelta(days=45),
                'status': 'expired'
            }
        ]
        
        # Add all codes to database
        for code_data in sample_codes:
            code = RedeemCode(**code_data)
            db.session.add(code)
        
        db.session.commit()
        print(f"Added {len(sample_codes)} redeem codes to the database")


if __name__ == '__main__':
    seed_database()