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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
