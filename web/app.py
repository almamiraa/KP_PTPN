"""
web/app.py
==========
Flask application factory for PTPN Unified Converter
"""

from flask import Flask
from pathlib import Path
import os
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def create_app():
    """
    Create and configure Flask application
    
    Returns:
        Flask app instance
    """
    
    app = Flask(__name__)
    
    # ===================================================================
    # CONFIGURATION
    # ===================================================================
    
    app.config['SECRET_KEY'] = os.getenv(
        'SECRET_KEY','secret key')
    
    # File upload settings
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_FILE_SIZE_MB', 50)) * 1024 * 1024
    
    # ✅ NO UPLOAD/OUTPUT FOLDERS - Files stored in database only
    # These paths might be used for temp files only (auto-deleted)
    app.config['UPLOAD_FOLDER'] = None  # Not used
    app.config['OUTPUT_FOLDER'] = None  # Not used
    
    logger.info("✅ Flask config: NO local file storage - Database only")
    
    # ===================================================================
    # REGISTER BLUEPRINTS
    # ===================================================================
    
    logger.info("Registering blueprints...")
    
    from web.routes import main_bp, demografi_bp, cost_bp
    from web.routes.admin import admin_bp  # ✅ Admin blueprint
    
    # Main routes (homepage, about, error handling)
    app.register_blueprint(main_bp)
    logger.info("✓ Registered: main_bp → /")
    
    # Demografi module
    app.register_blueprint(demografi_bp, url_prefix='/demografi')
    logger.info("✓ Registered: demografi_bp → /demografi")
    
    # Cost module
    app.register_blueprint(cost_bp, url_prefix='/cost')
    logger.info("✓ Registered: cost_bp → /cost")
    
    # ✅ Admin module (hidden by default - Ctrl+Shift+A to show)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    logger.info("✓ Registered: admin_bp → /admin (hidden by default)")
    
    # ===================================================================
    # GLOBAL ERROR HANDLERS
    # ===================================================================
    
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('error.html',
                             error_code=404,
                             error_title="Halaman Tidak Ditemukan",
                             error="URL yang Anda cari tidak ada."), 404
    
    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        logger.error(f"Server error: {e}", exc_info=True)
        return render_template('error.html',
                             error_code=500,
                             error_title="Kesalahan Server",
                             error=str(e)), 500
    
    @app.errorhandler(413)
    def file_too_large(e):
        from flask import render_template
        max_size = app.config['MAX_CONTENT_LENGTH'] / 1024 / 1024
        return render_template('error.html',
                             error_code=413,
                             error_title="File Terlalu Besar",
                             error=f"Ukuran file maksimal: {max_size:.0f}MB"), 413
    
    # ===================================================================
    # STARTUP INFO
    # ===================================================================
    
    logger.info("=" * 70)
    logger.info("🌿 PTPN UNIFIED CONVERTER - Application Created")
    logger.info("=" * 70)
    logger.info(f"Environment: {os.getenv('FLASK_ENV', 'production')}")
    logger.info(f"Debug mode: {os.getenv('FLASK_DEBUG', 'False')}")
    logger.info(f"Max upload size: {app.config['MAX_CONTENT_LENGTH']/1024/1024:.0f}MB")
    logger.info(f"File storage: DATABASE ONLY (no local storage)")
    logger.info("=" * 70)
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)