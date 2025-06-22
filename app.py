import os
from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401
    db.create_all()
    
    # 스케줄러 시작 (백그라운드에서 매시간 스크래핑)
    try:
        from scheduler import start_scheduler
        start_scheduler()
        print("명조 유튜브 스크래퍼 스케줄러가 시작되었습니다.")
    except Exception as e:
        print(f"스케줄러 시작 실패: {e}")

@app.route('/')
def index():
    """Serve the main game redeem codes page"""
    return render_template('index_dynamic.html')

@app.route('/api/codes/<game>')
def get_codes(game):
    """API endpoint to get redeem codes for a specific game"""
    from models import RedeemCode
    codes = RedeemCode.query.filter_by(game=game).all()
    return jsonify([{
        'id': code.id,
        'code': code.code,
        'rewards': code.rewards,
        'expires_at': code.expires_at.isoformat() if code.expires_at else None,
        'status': code.status,
        'created_at': code.created_at.isoformat()
    } for code in codes])

@app.route('/api/scrape/youtube')
def manual_scrape():
    """수동으로 명조 유튜브 스크래핑 실행"""
    try:
        from scrapers.myungjo_youtube_scraper import scrape_youtube_official
        result = scrape_youtube_official()
        return jsonify({
            'success': True,
            'message': f'스크래핑 완료: {result["total"]}개 코드 발견, {result["newCodes"]}개 새로 저장',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'스크래핑 실패: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
