"""
web/routes/admin.py
===================
Admin routes for configuration management
Hidden by default, accessed via keyboard shortcut (Ctrl+Shift+A)
"""

import os
import json
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
import logging

from modules.demografi.config import get_config as get_demografi_config
from modules.cost.config import get_config as get_cost_config

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Setup logger
logger = logging.getLogger(__name__)


# ============================================================================
# MAIN CONFIG MANAGER PAGE
# ============================================================================

@admin_bp.route('/config')
def config_manager():
    """Configuration manager page"""
    try:
        return render_template('admin/config.html')
    except Exception as e:
        logger.error(f"Error loading config manager: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('main.index'))


# ============================================================================
# DEMOGRAFI COMPANIES API
# ============================================================================

@admin_bp.route('/api/companies/demografi', methods=['GET'])
def get_demografi_companies():
    """Get all demografi companies"""
    try:
        config = get_demografi_config()
        companies_dict = config.get_companies_dict()
        
        # Convert to list with keys
        companies_list = []
        for key, data in companies_dict.items():
            companies_list.append({
                'key': key,
                'kode_perusahaan': data.get('kode_perusahaan', ''),
                'nama': data.get('nama', ''),
                'sheet_name': data.get('sheet_name', ''),
                'kategori': data.get('kategori', ''),
                'holding': data.get('holding', '')
            })
        
        return jsonify({
            'success': True,
            'companies': companies_list,
            'total': len(companies_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting demografi companies: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/companies/demografi', methods=['POST'])
def add_demografi_company():
    """Add new demografi company"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['key', 'kode_perusahaan', 'nama', 'sheet_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Field "{field}" is required'
                }), 400
        
        # Get current config
        config = get_demografi_config()
        
        # ✅ Build complete config structure
        # Need to preserve ALL sections (perusahaan, mapping_cell, level_definitions)
        config_data = config.data.copy()
        
        # Check if key already exists
        if data['key'] in config_data.get('perusahaan', {}):
            return jsonify({
                'success': False,
                'error': f'Company key "{data["key"]}" already exists'
            }), 400
        
        # Ensure perusahaan section exists
        if 'perusahaan' not in config_data:
            config_data['perusahaan'] = {}
        
        # Add new company
        config_data['perusahaan'][data['key']] = {
            'kode_perusahaan': data['kode_perusahaan'],
            'nama': data['nama'],
            'sheet_name': data['sheet_name'],
            'kategori': data.get('kategori', 'Sub Holding'),
            'holding': data.get('holding', '')
        }
        
        # Save to JSON file
        success = config.save_config(config_data)
        
        if success:
            logger.info(f"✅ Added demografi company: {data['key']} - {data['nama']}")
            return jsonify({
                'success': True,
                'message': f'Company "{data["nama"]}" added successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save config'
            }), 500
            
    except Exception as e:
        logger.error(f"Error adding demografi company: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/companies/demografi/<key>', methods=['PUT'])
def update_demografi_company(key):
    """Update demografi company"""
    try:
        data = request.json
        
        # Get current config
        config = get_demografi_config()
        
        # ✅ Build complete config structure
        config_data = config.data.copy()
        
        # Check if key exists
        if key not in config_data.get('perusahaan', {}):
            return jsonify({
                'success': False,
                'error': f'Company key "{key}" not found'
            }), 404
        
        # Update company data
        config_data['perusahaan'][key] = {
            'kode_perusahaan': data.get('kode_perusahaan', ''),
            'nama': data.get('nama', ''),
            'sheet_name': data.get('sheet_name', ''), 
            'kategori': data.get('kategori', 'Sub Holding'),
            'holding': data.get('holding', '')
        }
        
        # Save to JSON file
        success = config.save_config(config_data)
        
        if success:
            logger.info(f"✅ Updated demografi company: {key} - {data['nama']}")
            return jsonify({
                'success': True,
                'message': f'Company "{data["nama"]}" updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save config'
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating demografi company: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/companies/demografi/<key>', methods=['DELETE'])
def delete_demografi_company(key):
    """Delete demografi company"""
    try:
        # Get current config
        config = get_demografi_config()
        
        # ✅ Build complete config structure
        config_data = config.data.copy()
        
        # Check if key exists
        if key not in config_data.get('perusahaan', {}):
            return jsonify({
                'success': False,
                'error': f'Company key "{key}" not found'
            }), 404
        
        # Get company name for logging
        company_name = config_data['perusahaan'][key].get('nama', key)
        
        # Delete company
        del config_data['perusahaan'][key]
        
        # Save to JSON file
        success = config.save_config(config_data)
        
        if success:
            logger.info(f"✅ Deleted demografi company: {key} - {company_name}")
            return jsonify({
                'success': True,
                'message': f'Company "{company_name}" deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save config'
            }), 500
            
    except Exception as e:
        logger.error(f"Error deleting demografi company: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# COST COMPANIES API
# ============================================================================

@admin_bp.route('/api/companies/cost', methods=['GET'])
def get_cost_companies():
    """Get all cost companies"""
    try:
        config = get_cost_config()
        companies_dict = config.get_perusahaan()
        
        # Convert to list with keys
        companies_list = []
        for key, data in companies_dict.items():
            companies_list.append({
                'key': key,
                'kode_perusahaan': data.get('kode_perusahaan', ''),
                'nama': data.get('nama', ''),
                'sheet_name': data.get('sheet_name', ''),
                'holding': data.get('holding', '')
            })
        
        return jsonify({
            'success': True,
            'companies': companies_list,
            'total': len(companies_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting cost companies: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/companies/cost', methods=['POST'])
def add_cost_company():
    """Add new cost company"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['key', 'kode_perusahaan', 'nama', 'sheet_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Field "{field}" is required'
                }), 400
        
        # Get current config
        config = get_cost_config()
        
        # ✅ Build complete config structure (perusahaan + row_mapping)
        config_data = {
            'perusahaan': config.get_perusahaan().copy(),
            'row_mapping': config.get_row_mapping().copy()
        }
        
        # Check if key already exists
        if data['key'] in config_data['perusahaan']:
            return jsonify({
                'success': False,
                'error': f'Company key "{data["key"]}" already exists'
            }), 400
        
        # Add new company
        config_data['perusahaan'][data['key']] = {
            'kode_perusahaan': data['kode_perusahaan'],
            'nama': data['nama'],
            'sheet_name': data['sheet_name'],
            'holding': data.get('holding', '')
        }
        
        # Save to JSON file
        success = config.save_config(config_data)
        
        if success:
            logger.info(f"✅ Added cost company: {data['key']} - {data['nama']}")
            return jsonify({
                'success': True,
                'message': f'Company "{data["nama"]}" added successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save config'
            }), 500
            
    except Exception as e:
        logger.error(f"Error adding cost company: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/companies/cost/<key>', methods=['PUT'])
def update_cost_company(key):
    """Update cost company"""
    try:
        data = request.json
        
        # Get current config
        config = get_cost_config()
        
        # ✅ Build complete config structure (perusahaan + row_mapping)
        config_data = {
            'perusahaan': config.get_perusahaan().copy(),
            'row_mapping': config.get_row_mapping().copy()
        }
        
        # Check if key exists
        if key not in config_data['perusahaan']:
            return jsonify({
                'success': False,
                'error': f'Company key "{key}" not found'
            }), 404
        
        # Update company data
        config_data['perusahaan'][key] = {
            'kode_perusahaan': data.get('kode_perusahaan', ''),
            'nama': data.get('nama', ''),
            'sheet_name': data.get('sheet_name', ''),
            'holding': data.get('holding', '')
        }
        
        # Save to JSON file
        success = config.save_config(config_data)
        
        if success:
            logger.info(f"✅ Updated cost company: {key} - {data['nama']}")
            return jsonify({
                'success': True,
                'message': f'Company "{data["nama"]}" updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save config'
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating cost company: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/companies/cost/<key>', methods=['DELETE'])
def delete_cost_company(key):
    """Delete cost company"""
    try:
        # Get current config
        config = get_cost_config()
        
        # ✅ Build complete config structure (perusahaan + row_mapping)
        config_data = {
            'perusahaan': config.get_perusahaan().copy(),
            'row_mapping': config.get_row_mapping().copy()
        }
        
        # Check if key exists
        if key not in config_data['perusahaan']:
            return jsonify({
                'success': False,
                'error': f'Company key "{key}" not found'
            }), 404
        
        # Get company name for logging
        company_name = config_data['perusahaan'][key].get('nama', key)
        
        # Delete company
        del config_data['perusahaan'][key]
        
        # Save to JSON file
        success = config.save_config(config_data)
        
        if success:
            logger.info(f"✅ Deleted cost company: {key} - {company_name}")
            return jsonify({
                'success': True,
                'message': f'Company "{company_name}" deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save config'
            }), 500
            
    except Exception as e:
        logger.error(f"Error deleting cost company: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@admin_bp.route('/api/reload-config', methods=['POST'])
def reload_all_config():
    """Force reload all configurations"""
    try:
        # Reload demografi config
        demografi_config = get_demografi_config()
        demografi_success = demografi_config.reload()
        
        # Reload cost config
        cost_config = get_cost_config()
        cost_success = cost_config.reload()
        
        if demografi_success and cost_success:
            logger.info("🔄 All configurations reloaded successfully")
            return jsonify({
                'success': True,
                'message': 'All configurations reloaded successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to reload one or more configurations'
            }), 500
            
    except Exception as e:
        logger.error(f"Error reloading config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/export-config/<module>', methods=['GET'])
def export_config(module):
    """Export config as JSON file (backup)"""
    try:
        if module == 'demografi':
            config = get_demografi_config()
            config_data = config.data  # ✅ Direct access to data attribute
            filename = 'demografi.json'
        elif module == 'cost':
            config = get_cost_config()
            # ✅ Build complete structure for export
            config_data = {
                'perusahaan': config.get_perusahaan(),
                'row_mapping': config.get_row_mapping()
            }
            filename = 'cost.json'
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid module'
            }), 400
        
        from flask import send_file
        import io
        
        # Create JSON string
        json_str = json.dumps(config_data, indent=2, ensure_ascii=False)
        
        # Create file-like object
        json_bytes = io.BytesIO(json_str.encode('utf-8'))
        json_bytes.seek(0)
        
        return send_file(
            json_bytes,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'backup_{filename}'
        )
        
    except Exception as e:
        logger.error(f"Error exporting config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500