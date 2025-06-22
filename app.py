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
    
    # 자동 라이브 모니터링 시작
    try:
        from live_stream_monitor import start_auto_monitoring
        start_auto_monitoring()
        print("자동 라이브 스트림 모니터링이 시작되었습니다.")
    except Exception as e:
        print(f"자동 모니터링 시작 실패: {e}")

@app.route('/')
def index():
    """Serve the main game redeem codes page"""
    return render_template('index_dynamic.html')

@app.route('/live-monitor')
def live_monitor():
    """실시간 라이브 OCR 모니터 페이지"""
    return render_template('browser_live_monitor.html')

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

@app.route('/api/manual-code', methods=['POST'])
def add_manual_code():
    """수동으로 코드 추가"""
    from flask import request
    from datetime import datetime
    from models import RedeemCode
    
    data = request.get_json()
    
    if not data or 'code' not in data:
        return jsonify({'error': 'Code is required'}), 400
    
    code = data['code'].upper().strip()
    expiry_str = data.get('expiry')
    rewards = data.get('rewards', '')
    
    # 유효기간 파싱
    expiry_date = None
    if expiry_str:
        try:
            expiry_date = datetime.strptime(expiry_str, '%Y/%m/%d %H:%M')
        except ValueError:
            try:
                expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d %H:%M')
            except ValueError:
                pass
    
    # 중복 확인
    existing = RedeemCode.query.filter_by(code=code).first()
    if existing:
        return jsonify({'error': 'Code already exists'}), 409
    
    # 새 코드 저장
    new_code = RedeemCode(
        game='wuthering-waves',
        code=code,
        rewards=rewards,
        expires_at=expiry_date,
        status='new'
    )
    db.session.add(new_code)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'code': code,
        'message': 'Code added successfully'
    })

@app.route('/api/scrape-manual', methods=['POST'])
def trigger_manual_scrape():
    """수동 스크래핑 트리거"""
    try:
        from scrapers.myungjo_youtube_scraper import scrape_youtube_official
        result = scrape_youtube_official()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/live-ocr/start', methods=['POST'])
def start_live_ocr():
    """실시간 OCR 모니터링 시작"""
    try:
        from live_ocr_monitor import start_live_monitoring
        start_live_monitoring()
        return jsonify({'success': True, 'message': 'Live OCR monitoring started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/live-ocr/stop', methods=['POST'])
def stop_live_ocr():
    """실시간 OCR 모니터링 중지"""
    try:
        from live_ocr_monitor import stop_live_monitoring
        stop_live_monitoring()
        return jsonify({'success': True, 'message': 'Live OCR monitoring stopped'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-ocr', methods=['POST'])
def process_ocr():
    """브라우저에서 전송된 이미지 OCR 처리"""
    try:
        from flask import request
        import base64
        import io
        from PIL import Image
        import pytesseract
        import re
        from datetime import datetime
        
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'Image data required'}), 400
        
        # base64 이미지 디코딩
        image_data = data['image'].split(',')[1]  # data:image/png;base64, 부분 제거
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # OCR 실행
        text = pytesseract.image_to_string(image, config='--psm 6')
        
        # 코드 패턴 검색
        code_patterns = [
            r'\b[A-Z]{2,4}[0-9A-Z]{8,15}\b',
            r'\b[A-Z0-9]{10,16}\b'
        ]
        
        found_codes = set()
        for pattern in code_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) >= 8:
                    found_codes.add(match.upper())
        
        # 유효기간 검색
        date_pattern = r'(\d{4})/(\d{1,2})/(\d{1,2})\s*(\d{1,2}):(\d{2})'
        date_match = re.search(date_pattern, text)
        expiry = None
        if date_match:
            year, month, day, hour, minute = date_match.groups()
            expiry = f"{year}/{month.zfill(2)}/{day.zfill(2)} {hour.zfill(2)}:{minute}"
        
        # 새로운 코드를 데이터베이스에 저장
        new_codes = []
        for code in found_codes:
            existing = RedeemCode.query.filter_by(code=code).first()
            if not existing:
                expiry_date = None
                if expiry:
                    try:
                        expiry_date = datetime.strptime(expiry, '%Y/%m/%d %H:%M')
                    except ValueError:
                        pass
                
                new_code = RedeemCode(
                    game='wuthering-waves',
                    code=code,
                    rewards='',
                    expires_at=expiry_date,
                    status='new'
                )
                db.session.add(new_code)
                new_codes.append(code)
        
        if new_codes:
            db.session.commit()
        
        return jsonify({
            'codes': list(found_codes),
            'new_codes': new_codes,
            'expiry': expiry,
            'text': text
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
