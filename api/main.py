import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
# Ensure unified database path is available to blueprints before import
def _resolve_db_path() -> str:
    # 1) Respect explicit env var if provided
    env_path = os.environ.get('BEE_DB_PATH')
    if env_path:
        os.makedirs(os.path.dirname(env_path), exist_ok=True)
        return env_path
    
    # 2) Preferred production/data path (aligns with systemd ReadWritePaths)
    prod_dir = "/opt/bee-monitoring/data"
    try:
        if os.path.isdir("/opt/bee-monitoring") and os.access("/opt/bee-monitoring", os.W_OK):
            os.makedirs(prod_dir, exist_ok=True)
            return os.path.join(prod_dir, 'bee_monitoring.db')
    except Exception:
        pass
    
    # 3) Fallback to local repo path for development
    local_dir = os.path.join(os.path.dirname(__file__), 'database')
    os.makedirs(local_dir, exist_ok=True)
    return os.path.join(local_dir, 'bee_monitoring.db')

os.environ['BEE_DB_PATH'] = _resolve_db_path()

from api.models.user import db
from api.routes.user import user_bp
from api.routes.bee_monitoring import bee_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'digital4ai_bee_monitoring_secret_key_2025'

# Enable CORS for cross-origin requests from the React dashboard
CORS(app)

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(bee_bp, url_prefix='/api/bee')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.environ['BEE_DB_PATH']}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve static files and handle SPA routing"""
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

@app.route('/api/status')
def api_status():
    """API status endpoint"""
    return {
        'status': 'online',
        'service': 'Digital4.ai Bee Monitoring API',
        'version': '1.0.0',
        'endpoints': {
            'bee_monitoring': '/api/bee/',
            'user_management': '/api/',
            'health_check': '/api/bee/health'
        }
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
