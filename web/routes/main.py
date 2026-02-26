"""
web/routes/main.py
==================
Main routes: Homepage, About, Error handling
"""

from flask import Blueprint, render_template, request
import logging

logger = logging.getLogger(__name__)

# Create blueprint
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """
    Homepage - Module Selector
    Shows cards for Demografi and Cost modules
    """
    return render_template('index.html')


@main_bp.route('/about')
def about():
    """About page - System information"""
    try:
        # Get module info
        modules = [
            {
                'name': 'Demografi SDM',
                'icon': 'fa-users',
                'description': 'Konversi data demografi karyawan (Gender, Pendidikan, Usia, Unit Kerja, Tren)',
                'database': 'DBdemografi',
                'tables': 7,
                'features': [
                    'Multi-dimensional analysis',
                    'Trend calculation',
                    'Monthly dashboard',
                    'Visual analytics'
                ]
            },
            {
                'name': 'Cost Management',
                'icon': 'fa-calculator',
                'description': 'Konversi data biaya operasional (REAL, RKAP, Periode)',
                'database': 'DBcost',
                'tables': 3,
                'features': [
                    'Payment type analysis',
                    'Cost breakdown by holding',
                    'Achievement tracking',
                    'Period comparison'
                ]
            }
        ]
        
        return render_template('about.html', modules=modules)
        
    except Exception as e:
        logger.error(f"Error loading about page: {e}")
        return render_template('error.html', error=str(e)), 500


@main_bp.errorhandler(404)
def not_found(e):
    """404 error handler"""
    return render_template('error.html', 
                         error_code=404,
                         error_title="Halaman Tidak Ditemukan",
                         error="URL yang Anda cari tidak ada di sistem."), 404


@main_bp.errorhandler(500)
def server_error(e):
    """500 error handler"""
    logger.error(f"Server error: {e}", exc_info=True)
    return render_template('error.html',
                         error_code=500,
                         error_title="Kesalahan Server",
                         error=str(e)), 500


@main_bp.errorhandler(413)
def file_too_large(e):
    """413 error handler - File too large"""
    return render_template('error.html',
                         error_code=413,
                         error_title="File Terlalu Besar",
                         error="Ukuran file melebihi batas maksimal 50MB"), 413