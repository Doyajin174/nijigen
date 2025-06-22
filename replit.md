# Game Redeem Codes App

## Overview

This is a Flask-based web application that aggregates and displays redeem codes for popular mobile games, specifically focusing on Wuthering Waves, Honkai: Star Rail, and Zenless Zone Zero. The application provides a clean, modern interface for users to browse, copy, and track game redeem codes with their expiration dates and status.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database ORM**: SQLAlchemy with Flask-SQLAlchemy extension
- **Database**: PostgreSQL (configured via environment variables)
- **Deployment**: Gunicorn WSGI server with autoscale deployment target
- **Session Management**: Flask's built-in session handling with configurable secret key

### Frontend Architecture
- **Template Engine**: Jinja2 (Flask's default)
- **Styling**: Custom CSS with modern dark theme, responsive design
- **JavaScript**: Vanilla JavaScript for interactivity
- **Fonts**: Google Fonts (Inter family)
- **Layout**: CSS Grid and Flexbox for responsive design

### Database Schema
The application uses a single main entity:
- **RedeemCode Model**: Stores game codes with game type, code value, rewards description, expiration date, status, and timestamps

## Key Components

### Core Application Files
- **app.py**: Main Flask application with database configuration and route definitions
- **main.py**: Application entry point for development server
- **models.py**: SQLAlchemy database models and business logic
- **seed_data.py**: Database seeding script for populating sample data

### Templates
- **index_dynamic.html**: Main application template with modern dark theme
- **index.html**: Alternative static template (appears to be incomplete)

### External Integrations
- **YouTube Scraper**: Located in `scrapers/myungjo_youtube_scraper.py` for automated code collection from official YouTube channels
- **Google Fonts**: For typography (Inter font family)

## Data Flow

1. **Code Collection**: Scrapers collect redeem codes from official sources (YouTube channels)
2. **Database Storage**: Codes are stored with metadata (game type, rewards, expiration, status)
3. **API Endpoint**: `/api/codes/<game>` provides JSON data for specific games
4. **Frontend Display**: Dynamic template renders codes with filtering and status indicators
5. **User Interaction**: Copy-to-clipboard functionality and responsive navigation

## External Dependencies

### Python Packages
- Flask 3.1.1+ (web framework)
- SQLAlchemy 2.0.41+ (database ORM)
- Flask-SQLAlchemy 3.1.1+ (Flask-SQLAlchemy integration)
- psycopg2-binary 2.9.10+ (PostgreSQL adapter)
- Gunicorn 23.0.0+ (WSGI server)
- email-validator 2.2.0+ (email validation utilities)
- Werkzeug 3.1.3+ (WSGI utilities)

### External Services
- **PostgreSQL Database**: Primary data storage
- **YouTube API**: For automated scraping (requires YOUTUBE_API_KEY environment variable)
- **Google Fonts**: For web typography

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `SESSION_SECRET`: Flask session encryption key
- `YOUTUBE_API_KEY`: YouTube Data API key for scraping

## Deployment Strategy

### Platform Configuration
- **Target**: Replit with autoscale deployment
- **Server**: Gunicorn with production-ready configuration
- **Port Mapping**: Internal port 5000 mapped to external port 80
- **Proxy Handling**: ProxyFix middleware for proper header handling

### Development Workflow
- **Development Server**: Flask development server with debug mode
- **Production Server**: Gunicorn with bind configuration and reload capability
- **Database Migrations**: Automatic table creation on application startup

### Production Considerations
- Pool connection management with 300-second recycle and pre-ping
- Session security with environment-based secret key
- Proxy headers properly handled for deployment environment

## Changelog

```
Changelog:
- June 22, 2025. Initial setup
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```