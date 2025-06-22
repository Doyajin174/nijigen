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

## Recent Changes

- **2025-06-22**: 프로젝트를 Replit 환경으로 성공적으로 마이그레이션
- **2025-06-22**: PostgreSQL 데이터베이스 설정 및 연결 완료  
- **2025-06-22**: 명조 유튜브 스크래퍼 테스트 성공 (3개 리딤코드 추출)
- **2025-06-22**: 매시간 자동 스크래핑 스케줄러 구현 및 활성화
- **2025-06-22**: 수동 스크래핑을 위한 API 엔드포인트 추가
- **2025-06-22**: 실시간 라이브 화면 OCR 모니터링 시스템 구현
- **2025-06-22**: 브라우저 확장용 OCR 스크립트 및 API 엔드포인트 추가
- **2025-06-22**: 스크린샷에서 DTJ7CVACLBGF 코드 수동 추출 및 저장
- **2025-06-22**: 붕괴 스타레일 유튜브 영상에서 2개 코드 추출 (HONKAISTARRAIL, ACCOUNTCENTER)
- **2025-06-22**: 유튜브 영상 스크래핑 API 엔드포인트 추가
- **2025-06-22**: 브라우저 기반 실시간 라이브 OCR 모니터링 페이지 구현
- **2025-06-22**: 로컬 컴퓨터용 독립 실행 OCR 모니터링 프로그램 개발

## User Preferences

- **언어**: 한국어 사용
- **소통 스타일**: 간단명료한 일상 언어  
- **기능 우선순위**: 명조 유튜브 스크래핑 기능을 중시
- **OCR 선호도**: 실시간 라이브 스트림에서 코드 자동 감지 기능 선호