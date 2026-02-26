"""
web/routes/cost.py
==================
Routes untuk modul Cost Management
Database: DBcost
"""

import os
import io
import json
import tempfile
from pathlib import Path
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
import logging

# Import cost modules
from modules.cost.config import ConfigLoader
from modules.cost.excel_reader import ExcelReader
from modules.cost.column_detector import ColumnDetector
from modules.cost.data_processor import DataProcessor
from modules.cost.output_writer import OutputWriter
from modules.cost.validator import validate_upload

# Import database
from database.connection import get_db
from database.models.cost import (
    CostUploadHistory,
    CostData,
    CostOutputFiles
)

# Create blueprint
cost_bp = Blueprint('cost', __name__, url_prefix='/cost')

# Setup logger
logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xlsm'}


# ============================================================================
# ROUTES
# ============================================================================

@cost_bp.route('/')
@cost_bp.route('/home')
def home():
    """Cost homepage"""
    return render_template('cost/home.html')


@cost_bp.route('/upload')
def upload():
    """Upload page"""
    try:
        # ✅ Load config to get companies info
        config = ConfigLoader("config/cost.json")
        
        companies = config.get_companies_list()
        company_count = config.get_companies_count()
        
        return render_template('cost/upload.html',
                             companies=companies,
                             company_count=company_count)
    except Exception as e:
        logger.error(f"Error loading upload page: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('cost.history'))


@cost_bp.route('/convert', methods=['POST'])
def convert():
    """
    Process uploaded cost file with validation
    ✅ Company coverage validation (90% minimum)
    ✅ NO LOCAL FILE STORAGE - All files in database only
    """
    
    uploaded_file_path = None
    output_file_path = None
    
    try:
        # === Validate Input ===
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(url_for('cost.upload'))
        
        file = request.files['file']
        if not file or file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('cost.upload'))
        
        if not allowed_file(file.filename):
            flash('File harus berformat .xlsx atau .xlsm', 'error')
            return redirect(url_for('cost.upload'))
        
        # === Get Periode from Form Input ===
        periode_input = request.form.get('periode')  # Format: YYYY-MM-DD from date input
        if not periode_input:
            flash('Periode harus diisi', 'error')
            return redirect(url_for('cost.upload'))
        
        # Parse periode to required formats
        try:
            periode_date = datetime.strptime(periode_input, '%Y-%m-%d')
            
            # Format 1: YYYY-MM (for column detection & database)
            period_search = periode_date.strftime('%Y-%m')
            
            # Format 2: dd/MM/yyyy (for output display)
            period_full = periode_date.strftime('%d/%m/%Y')
            
            # Format 3: MMM-YY (for display: Jan-25, Feb-25)
            month_names = {
                1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
            }
            month_abbr = month_names[periode_date.month]
            year_short = periode_date.strftime('%y')
            periode_display = f"{month_abbr}-{year_short}"
            
            logger.info(f"📅 Periode: search={period_search}, full={period_full}, display={periode_display}")
            
        except ValueError:
            flash('Format periode tidak valid', 'error')
            return redirect(url_for('cost.upload'))
        
        # Save to TEMP folder
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        
        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, unique_filename)
        file.save(filepath)
        uploaded_file_path = filepath
        
        logger.info(f"🔄 Processing cost file: {filepath}")
        
        # === Load Config ===
        config = ConfigLoader("config/cost.json")
        
        # === Start Processing ===
        start_time = datetime.now()
        
        # 1. Read Excel
        reader = ExcelReader(filepath)
        
        # 2. Process ALL sheets
        processor = DataProcessor(config, reader)
        result = processor.process_all_sheets(
            period_search=period_search,  # YYYY-MM for detection
            period_full=period_full        # dd/MM/yyyy for output
        )
        
        if not result or len(result) == 0:
            raise Exception("Tidak ada data yang berhasil diproses")
        
        logger.info(f"✅ Processed {len(result)} rows total")
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # === ✅ VALIDATION ===
        logger.info("🔍 Running validation checks...")
        
        from modules.cost.validator import validate_upload
        import pandas as pd
        
        # Convert result list to DataFrame for validation
        df = pd.DataFrame(result)
        
        # Get expected companies from config
        perusahaan_dict = config.get_perusahaan()
        expected_company_keys = list(perusahaan_dict.keys())
        
        validation_result = validate_upload(
            dataframe=df,
            expected_companies=expected_company_keys
        )
        
        validation_dict = validation_result.to_dict()
        
        # Remove 'status' from validation_dict to avoid duplicate
        validation_dict_clean = {k: v for k, v in validation_dict.items() if k != 'status'}
        
        logger.info(f"📊 Validation result: {validation_result.status.upper()} "
                   f"({validation_result.company_coverage_percent:.1f}% coverage)")
        
        # === Handle FAILED Validation (< 90% coverage) ===
        if validation_result.status == 'failed':
            error_parts = []
            error_parts.append(
                f"Upload gagal: Coverage perusahaan terlalu rendah "
                f"({validation_result.company_coverage_percent:.1f}%). "
                f"Minimum required: 90%"
            )
            error_parts.append(
                f"Perusahaan terproses: {validation_result.processed_companies}/{validation_result.total_companies}"
            )
            
            if validation_result.missing_companies:
                missing_count = len(validation_result.missing_companies)
                missing_names = [validation_result.config_key_to_name.get(k, k) for k in validation_result.missing_companies[:5]]
                missing_preview = ', '.join(missing_names)
                if missing_count > 5:
                    missing_preview += f" ... (+{missing_count - 5} lainnya)"
                error_parts.append(f"Perusahaan hilang: {missing_preview}")
            
            error_msg = "<br>".join(error_parts)
            
            # Save to database with failed status (no Excel file)
            try:
                db = get_db('cost')
                conn = db.get_connection()
                
                CostUploadHistory.insert(
                    conn,
                    original_filename=file.filename,
                    output_filename="N/A",
                    periode=period_search,
                    perusahaan=f"{validation_result.processed_companies}/{validation_result.total_companies} companies",
                    total_rows=len(result),
                    duration=duration,
                    status=validation_result.status,
                    error_message=error_msg.replace("<br>", "; "),
                    **validation_dict_clean
                )
            except Exception as db_error:
                logger.warning(f"Failed to save validation error: {db_error}")
            
            flash(error_msg, 'error')
            
            # Cleanup
            if uploaded_file_path and os.path.exists(uploaded_file_path):
                try:
                    os.remove(uploaded_file_path)
                except:
                    pass
            
            # Close reader
            reader.close()
            
            return redirect(url_for('cost.upload'))
        
        # === Export to Excel (for SUCCESS and WARNING) ===
        logger.info("📄 Creating Excel output...")
        writer = OutputWriter()
        file_bytes = writer.write_excel_to_bytes(result, period_full)
        
        # Filename with periode
        base_name = filename.rsplit('.', 1)[0]
        output_filename = f"{base_name}_{periode_display}.xlsx"
        
        # Save bytes to temp file
        output_file_path = os.path.join(temp_dir, output_filename)
        with open(output_file_path, 'wb') as f:
            f.write(file_bytes)
        
        logger.info(f"⏱️  Duration: {duration:.2f}s")
        
        # === Save to Database ===
        upload_id = None
        try:
            db = get_db('cost')
            conn = db.get_connection()
            
            # 1. Save upload history with validation data
            upload_id = CostUploadHistory.insert(
                conn,
                original_filename=file.filename,
                output_filename=output_filename,
                periode=period_search,
                perusahaan=f"{validation_result.processed_companies}/{validation_result.total_companies} companies",
                total_rows=len(result),
                duration=duration,
                status=validation_result.status,  # Use validation status
                error_message=None,
                **validation_dict_clean  # Include validation data
            )
            logger.info(f"✅ Upload history saved (ID: {upload_id}, Status: {validation_result.status})")
            
            # 2. Save cost data to database
            logger.info("💾 Saving cost data to database...")
            rows_inserted = CostData.insert_batch(conn, upload_id, result)
            logger.info(f"✅ Inserted {rows_inserted} cost data rows")
            
            # 3. Save Excel file to database
            logger.info("💾 Saving Excel file to database...")
            file_size_kb = len(file_bytes) / 1024
            
            CostOutputFiles.insert(
                conn,
                upload_id=upload_id,
                filename=output_filename,
                file_content=file_bytes,
                file_size_kb=file_size_kb
            )
            logger.info("✅ Excel file saved to database")
            
        except Exception as db_error:
            logger.error(f"❌ Database save error: {db_error}", exc_info=True)
            flash(f"Error: Database save failed: {str(db_error)}", 'error')
            
            # Cleanup
            if uploaded_file_path and os.path.exists(uploaded_file_path):
                try:
                    os.remove(uploaded_file_path)
                except:
                    pass
            if output_file_path and os.path.exists(output_file_path):
                try:
                    os.remove(output_file_path)
                except:
                    pass
            
            reader.close()
            return redirect(url_for('cost.upload'))
        
        # === Cleanup temp files ===
        logger.info("🧹 Cleaning up temporary files...")
        
        if uploaded_file_path and os.path.exists(uploaded_file_path):
            try:
                os.remove(uploaded_file_path)
                logger.info("   ✅ Deleted uploaded file")
            except Exception as e:
                logger.warning(f"   ⚠️  Failed to delete: {e}")
        
        if output_file_path and os.path.exists(output_file_path):
            try:
                os.remove(output_file_path)
                logger.info("   ✅ Deleted output file")
            except Exception as e:
                logger.warning(f"   ⚠️  Failed to delete: {e}")
        
        logger.info("✅ All temporary files cleaned - NO LOCAL STORAGE")
        
        # === Calculate holding summary for result page ===
        holding_summary = {}
        for row in result:
            holding = row['holding']
            if holding not in holding_summary:
                holding_summary[holding] = {
                    'row_count': 0,
                    'payment_types': set(),
                    'total_real': 0,
                    'total_rkap': 0
                }
            
            holding_summary[holding]['row_count'] += 1
            holding_summary[holding]['payment_types'].add(row['payment_type'])
            holding_summary[holding]['total_real'] += row.get('REAL', 0) or 0
            holding_summary[holding]['total_rkap'] += row.get('RKAP', 0) or 0
        
        # Convert sets to counts
        for holding in holding_summary:
            holding_summary[holding]['payment_types'] = len(holding_summary[holding]['payment_types'])
        
        # Close reader
        reader.close()
        
        # === Success/Warning Response ===
        if validation_result.status == 'warning':
            flash(
                f"⚠️ Hanya {validation_result.processed_companies}/{validation_result.total_companies} "
                f"perusahaan ({validation_result.company_coverage_percent:.1f}%) yang berhasil diproses.",
                'warning'
            )
        else:
            flash('✅ Upload berhasil! Semua validasi passed.', 'success')
        
        return render_template('cost/result.html',
                             success=True,
                             message=f"Cost data berhasil diproses untuk periode {periode_display}",
                             upload_id=upload_id,
                             periode_display=periode_display,
                             total_rows=len(result),
                             sheet_count=len(reader.sheet_names),
                             duration=duration,
                             holding_summary=holding_summary,
                             validation=validation_result.to_dict(),  # ✅ Pass validation to template
                             warnings=[])
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        
        # Cleanup on error
        if uploaded_file_path and os.path.exists(uploaded_file_path):
            try:
                os.remove(uploaded_file_path)
            except:
                pass
        
        if output_file_path and os.path.exists(output_file_path):
            try:
                os.remove(output_file_path)
            except:
                pass
        
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('cost.upload'))
    
@cost_bp.route('/api/validation-detail/<int:upload_id>')
def api_validation_detail(upload_id):
    """API endpoint to get validation detail for an upload"""
    try:
        db = get_db('cost')
        conn = db.get_connection()
        
        history = CostUploadHistory.get_by_id(conn, upload_id)
        
        if not history:
            return json.dumps({
                'error': 'Upload not found'
            }), 404, {'Content-Type': 'application/json'}
        
        from modules.cost.validator import parse_validation_data
        from modules.cost.config import ConfigLoader
        
        validation_data = parse_validation_data(history)
        
        # Get company names mapping
        config = ConfigLoader("config/cost.json")
        company_names = {}
        for key, data in config.get_perusahaan().items():
            company_names[key] = data.get('nama', key)
        
        # ✅ Convert Decimal to float
        coverage_percent = validation_data['company_coverage_percent']
        if coverage_percent is not None:
            coverage_percent = float(coverage_percent)
        else:
            coverage_percent = 0.0
        
        response = {
            'upload_id': upload_id,
            'status': history.get('status', 'unknown'),
            'total_companies': validation_data['total_companies'],
            'processed_companies': validation_data['processed_companies'],
            'coverage_percent': coverage_percent,  # ✅ Now it's float
            'missing_companies': validation_data['missing_companies'],
            'validation_warnings': [],  # Always empty for cost
            'has_validation': validation_data['has_validation'],
            'company_names': company_names
        }
        
        return json.dumps(response, ensure_ascii=False), 200, {'Content-Type': 'application/json; charset=utf-8'}
        
    except Exception as e:
        logger.error(f"❌ Error getting validation detail: {e}", exc_info=True)
        return json.dumps({
            'error': str(e)
        }), 500, {'Content-Type': 'application/json'}
    
@cost_bp.route('/download')
def download():
    """Download file FROM DATABASE ONLY"""
    try:
        upload_id = request.args.get('upload_id', type=int)
        
        if not upload_id:
            flash('Upload ID tidak ditemukan', 'error')
            return redirect(url_for('cost.history'))
        
        db = get_db('cost')
        conn = db.get_connection()
        
        logger.info(f"📥 Downloading from database (upload_id={upload_id})")
        
        file_data = CostOutputFiles.get_file_content(conn, upload_id)
        
        if not file_data:
            flash('File tidak ditemukan di database', 'error')
            return redirect(url_for('cost.history'))
        
        filename, file_content, mime_type = file_data
        
        file_io = io.BytesIO(file_content)
        file_io.seek(0)
        
        logger.info(f"✅ Downloading: {filename}")
        
        return send_file(
            file_io,
            mimetype=mime_type,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"❌ Download error: {e}")
        flash(f"Error downloading: {str(e)}", 'error')
        return redirect(url_for('cost.history'))


@cost_bp.route('/history')
def history():
    """View upload history"""
    try:
        db = get_db('cost')
        conn = db.get_connection()
        
        histories = CostUploadHistory.get_all(conn, limit=100)
        
        return render_template('cost/history.html', histories=histories)
    except Exception as e:
        logger.error(f"Error loading history: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('cost.upload'))


@cost_bp.route('/data/<int:upload_id>')
def view_data(upload_id):
    """View cost data details grouped by holding"""
    try:
        db = get_db('cost')
        conn = db.get_connection()
        
        # Get upload info
        upload = CostUploadHistory.get_by_id(conn, upload_id)
        if not upload:
            flash('Upload not found', 'error')
            return redirect(url_for('cost.history'))
        
        # Get data grouped by holding
        data = CostData.get_by_upload_id_grouped(conn, upload_id)
        
        return render_template('cost/detail.html',
                             upload=upload,
                             data=data)
    except Exception as e:
        logger.error(f"Error viewing data: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('cost.history'))

@cost_bp.route('/dashboard')
def dashboard():
    """Dashboard page - yearly cost analysis"""
    try:
        db = get_db('cost')
        conn = db.get_connection()
        
        # Get available years from data
        available_years = CostData.get_available_years(conn)
        
        # Get selected year from query param or use latest
        selected_year = request.args.get('year', type=int)
        
        # Check if we have data for selected year
        has_data = False
        if selected_year:
            # Quick check if data exists
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) 
                FROM cost_data 
                WHERE RIGHT(periode, 4) = ?
            """, (str(selected_year),))  # ← FIX: Use RIGHT() and str()
            count = cursor.fetchone()[0]
            cursor.close()
            has_data = count > 0
            
            # ✅ ADD DEBUG LOG
            logger.info(f"Dashboard: year={selected_year}, count={count}, has_data={has_data}")
            print(f"[DEBUG] Dashboard render: year={selected_year}, has_data={has_data}, available_years={available_years}")
        
        current_year = datetime.now().year
        
        return render_template(
            'cost/dashboard.html',
            available_years=available_years,
            selected_year=selected_year,
            current_year=current_year,
            has_data=has_data  # ← Make sure this is passed!
        )
        
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}", exc_info=True)
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('cost.history'))


@cost_bp.route('/api/yearly-data/<int:year>')
def api_yearly_data(year):
    """
    API endpoint for yearly dashboard data
    ✅ Returns data with 4 values per period
    ✅ If duplicate months exist, takes the LATEST upload (highest id)
    """
    try:
        db = get_db('cost')
        conn = db.get_connection()
        
        # Get all data aggregated properly
        yearly_data = CostData.get_yearly_dashboard_data(conn, year)
        
        if not yearly_data['monthly']['labels']:
            return jsonify({
                'success': False,
                'has_data': False,
                'message': f'Tidak ada data bulanan untuk tahun {year}'
            })
                
        return jsonify({
            'success': True,
            'has_data': True,
            'year': year,
            **yearly_data
        })
        
    except Exception as e:
        logger.error(f"Error loading yearly data: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@cost_bp.route('/visualize')
def visualize():
    """Visualize cost data for single upload"""
    try:
        db = get_db('cost')
        conn = db.get_connection()
        
        # Get all histories for dropdown
        histories = CostUploadHistory.get_all(conn, limit=100)
        
        # Get selected upload_id
        upload_id = request.args.get('upload_id', type=int)
        
        return render_template('cost/visualization.html',
                             histories=histories,
                             upload_id=upload_id)
    except Exception as e:
        logger.error(f"Error loading visualize: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('cost.history'))


@cost_bp.route('/api/visualization-data/<int:upload_id>')
def api_visualization_data(upload_id):
    """API endpoint for single upload visualization"""
    try:
        db = get_db('cost')
        conn = db.get_connection()
        
        # Get visualization data
        data = CostData.get_visualization_data(conn, upload_id)
        
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"❌ API error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@cost_bp.route('/delete/<int:upload_id>', methods=['POST'])
def delete_upload(upload_id):
    """Delete upload and all related data"""
    try:
        db = get_db('cost')
        conn = db.get_connection()
        
        upload = CostUploadHistory.get_by_id(conn, upload_id)
        
        if not upload:
            flash('Upload tidak ditemukan', 'error')
            return redirect(url_for('cost.history'))
        
        # Delete (cascade to cost_data and output_files)
        success = CostUploadHistory.delete(conn, upload_id)
        
        if success:
            flash(f'✅ Upload #{upload_id} berhasil dihapus', 'success')
            logger.info(f"✅ Deleted upload #{upload_id}: {upload['original_filename']}")
        else:
            flash('Gagal menghapus upload', 'error')
        
        return redirect(url_for('cost.history'))
        
    except Exception as e:
        logger.error(f"Error deleting upload: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('cost.history'))


@cost_bp.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    flash('File terlalu besar! Maksimal 50MB', 'error')
    return redirect(url_for('cost.upload'))


@cost_bp.errorhandler(500)
def internal_error(e):
    """Handle internal server error"""
    logger.error(f"Internal error: {e}")
    flash('Internal server error. Please try again.', 'error')
    return redirect(url_for('cost.upload'))