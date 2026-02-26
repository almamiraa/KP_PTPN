"""
web/routes/demografi.py
=======================
Routes untuk modul Demografi SDM
Database: DBdemografi
"""

import os
import io
import json 
import tempfile
from pathlib import Path
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
import logging

# Import demografi modules
from modules.demografi.config import load_config
from modules.demografi.config import get_config
from modules.demografi.converter import convert_multiple
from modules.demografi.exporter import export_to_excel
from modules.demografi.utils import setup_logger, validate_excel_extension
from modules.demografi.validator import validate_conversion

# Import database
from database.connection import get_db
from database.models import (
    DemografiConversionHistory,
    DataGender,
    DataPendidikan,
    DataUsia,
    DataUnitKerja,
    DataTren,
    DemografiOutputFiles,
    get_latest_data_by_periode,
    get_all_data_by_conversion_id,
    get_data_statistics
)

# Create blueprint
demografi_bp = Blueprint('demografi', __name__)

# Setup logger
logger = setup_logger()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return validate_excel_extension(filename)


# ============================================================================
# ROUTES
# ============================================================================

@demografi_bp.route('/')
def home():
    """Home/landing page for demografi module"""
    try:
        # Optional: Load statistics if you want to show them
        # db = get_db('demografi')
        # conn = db.get_connection()
        # stats = get_statistics(conn)  # Create this function if needed
        
        return render_template('demografi/home.html')
        
    except Exception as e:
        logger.error(f"Error loading home page: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('demografi.index'))

@demografi_bp.route('/upload')
def index():
    """Demografi homepage - Upload form"""
    config = load_config()
    companies = config.get_companies_list()
    
    return render_template('demografi/upload.html',
                         company_count=len(companies),
                         companies=companies)


@demografi_bp.route('/convert', methods=['POST'])
def convert():
    """
    Process uploaded file
    ✅ WITH VALIDATION - Company coverage & data consistency
    """
    
    uploaded_file_path = None
    output_file = None
    
    try:
        # === Validate Input ===
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(url_for('demografi.index'))
        
        file = request.files['file']
        if not file or file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('demografi.index'))
        
        if not allowed_file(file.filename):
            flash('File harus berformat .xlsx atau .xlsm', 'error')
            return redirect(url_for('demografi.index'))
        
        # Get periode
        periode = request.form.get('periode', '').strip()
        if not periode:
            flash('Periode harus diisi', 'error')
            return redirect(url_for('demografi.index'))
        
        # Save to TEMP folder
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        
        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, unique_filename)
        file.save(filepath)
        uploaded_file_path = filepath
        
        logger.info(f"🔄 Processing: file={filepath}, periode={periode}")
        
        # === Load Config ===
        config = load_config()
        perusahaan_list = config.get_companies_list()
        perusahaan_codes = list(config.data['perusahaan'].keys())
        dimensi_list = ["gender", "pendidikan", "usia", "unit_kerja", "tren"]
        
        logger.info(f"📋 Expected companies: {len(perusahaan_codes)}")
        
        # === Conversion ===
        result = convert_multiple(
            file_path=filepath,
            perusahaan_list=perusahaan_list,
            periode=periode,
            dimensi_list=dimensi_list
        )
        
        # === Handle Failed Conversion ===
        if not result.success:
            error_msg = "<br>".join(result.errors) if result.errors else result.message
            
            try:
                db = get_db('demografi')
                conn = db.get_connection()
                
                DemografiConversionHistory.insert(
                    conn,
                    original_filename=file.filename,
                    output_filename="N/A",
                    periode=periode,
                    perusahaan=f"ALL ({len(perusahaan_list)} companies)",
                    total_rows=0,
                    duration=result.duration,
                    status="failed",
                    error_message=error_msg.replace("<br>", "; "),
                    total_companies=len(perusahaan_codes),
                    processed_companies=0,
                    missing_companies=json.dumps(perusahaan_codes, ensure_ascii=False),
                    validation_warnings=None,
                    company_coverage_percent=0.0
                )
            except Exception as db_error:
                logger.warning(f"Failed to save error history: {db_error}")

            flash(f"Konversi gagal: {error_msg}", 'error')
            
            if uploaded_file_path and os.path.exists(uploaded_file_path):
                try:
                    os.remove(uploaded_file_path)
                except:
                    pass
            
            return redirect(url_for('demografi.index'))
        
        # === VALIDATION ===
        logger.info("🔍 Running validation checks...")
        
        from modules.demografi.validator import validate_conversion
        
        validation_result = validate_conversion(
            dataframes=result.data,
            expected_companies=perusahaan_codes
        )
        
        validation_dict = validation_result.to_dict()

        logger.info("="*50)
        logger.info("DEBUG: Checking dataframe columns")
        if 'gender' in result.data and not result.data['gender'].empty:
            logger.info(f"Gender columns: {list(result.data['gender'].columns)}")
            logger.info(f"Sample values:")
            if 'kode_perusahaan' in result.data['gender'].columns:
                logger.info(f"  kode_perusahaan: {result.data['gender']['kode_perusahaan'].unique()[:5]}")
            if 'nama_perusahaan' in result.data['gender'].columns:
                logger.info(f"  nama_perusahaan: {result.data['gender']['nama_perusahaan'].unique()[:5]}")
        logger.info("="*50)
        
        # ✅ Remove 'status' from validation_dict to avoid duplicate
        validation_dict_clean = {k: v for k, v in validation_dict.items() if k != 'status'}
        
        logger.info(f"📊 Validation result: {validation_result.status.upper()} "
                   f"({validation_result.company_coverage_percent:.1f}% coverage)")
        
        # === Handle FAILED Validation (< 90% coverage) ===
        if validation_result.status == 'failed':
            error_parts = []
            error_parts.append(
                f"Konversi gagal: Coverage perusahaan terlalu rendah "
                f"({validation_result.company_coverage_percent:.1f}%). "
                f"Minimum required: 90%"
            )
            error_parts.append(
                f"Perusahaan terproses: {validation_result.processed_companies}/{validation_result.total_companies}"
            )
            
            if validation_result.missing_companies:
                missing_count = len(validation_result.missing_companies)
                missing_preview = ', '.join(validation_result.missing_companies[:5])
                if missing_count > 5:
                    missing_preview += f" ... (+{missing_count - 5} lainnya)"
                error_parts.append(f"Perusahaan hilang: {missing_preview}")
            
            error_msg = "<br>".join(error_parts)
            
            try:
                db = get_db('demografi')
                conn = db.get_connection()
                
                DemografiConversionHistory.insert(
                    conn,
                    original_filename=file.filename,
                    output_filename="N/A",
                    periode=periode,
                    perusahaan=f"{validation_result.processed_companies}/{validation_result.total_companies} companies",
                    total_rows=result.total_rows,
                    duration=result.duration,
                    status=validation_result.status,
                    error_message=error_msg.replace("<br>", "; "),
                    **validation_dict_clean  # ✅ Use cleaned dict
                )
            except Exception as db_error:
                logger.warning(f"Failed to save validation error: {db_error}")
            
            flash(error_msg, 'error')
            
            if uploaded_file_path and os.path.exists(uploaded_file_path):
                try:
                    os.remove(uploaded_file_path)
                except:
                    pass
            
            return redirect(url_for('demografi.index'))
        
        # === Export to TEMP Excel (for SUCCESS and WARNING) ===
        temp_output_dir = tempfile.gettempdir()
        output_file = export_to_excel(
            dataframes=result.data,
            output_dir=temp_output_dir,
            original_filename=file.filename,
            perusahaan="ALL"
        )
        output_filename = os.path.basename(output_file)
        
        logger.info(f"📄 Output file (TEMP): {output_file}")

        # === Save to Database ===
        conversion_id = None
        try:
            db = get_db('demografi')
            conn = db.get_connection()
            
            # 1. Save conversion history with validation data
            conversion_id = DemografiConversionHistory.insert(
                conn,
                original_filename=file.filename,
                output_filename=output_filename,
                periode=periode,
                perusahaan=f"{validation_result.processed_companies}/{validation_result.total_companies} companies",
                total_rows=result.total_rows,
                duration=result.duration,
                status=validation_result.status,
                error_message=None,
                **validation_dict_clean  # ✅ FIXED: Use cleaned dict
            )
            logger.info(f"✅ Conversion history saved (ID: {conversion_id}, Status: {validation_result.status})")
            
            # 2. Save data to dimension tables
            logger.info("📊 Saving conversion data to database...")
            
            DataGender.insert_bulk(conn, conversion_id, result.data.get('gender'))
            DataPendidikan.insert_bulk(conn, conversion_id, result.data.get('pendidikan'))
            DataUsia.insert_bulk(conn, conversion_id, result.data.get('usia'))
            DataUnitKerja.insert_bulk(conn, conversion_id, result.data.get('unit_kerja'))
            DataTren.insert_bulk(conn, conversion_id, result.data.get('tren'))
            
            # 3. Save Excel file to DATABASE
            logger.info("💾 Saving Excel file to database...")
            with open(output_file, 'rb') as f:
                file_content = f.read()
            
            file_size = len(file_content)
            
            DemografiOutputFiles.insert(
                conn,
                conversion_id=conversion_id,
                filename=output_filename,
                file_content=file_content,
                file_size=file_size
            )
            logger.info("✅ Excel file saved to database")
            
        except Exception as db_error:
            logger.error(f"❌ Database save error: {db_error}", exc_info=True)
            flash(f"Error: Database save failed: {str(db_error)}", 'error')
            
            if uploaded_file_path and os.path.exists(uploaded_file_path):
                try:
                    os.remove(uploaded_file_path)
                except:
                    pass
            if output_file and os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            
            return redirect(url_for('demografi.index'))
        
        # === Cleanup ALL temp files ===
        logger.info("🧹 Cleaning up temporary files...")
        
        if uploaded_file_path and os.path.exists(uploaded_file_path):
            try:
                os.remove(uploaded_file_path)
                logger.info(f"   ✅ Deleted uploaded file")
            except Exception as e:
                logger.warning(f"   ⚠️  Failed to delete uploaded file: {e}")
        
        if output_file and os.path.exists(output_file):
            try:
                os.remove(output_file)
                logger.info(f"   ✅ Deleted output file")
            except Exception as e:
                logger.warning(f"   ⚠️  Failed to delete output file: {e}")
        
        logger.info("✅ All temporary files cleaned up - NO LOCAL STORAGE")
        
        # === Success/Warning Response ===
        if validation_result.status == 'warning':
            warning_parts = []
            
            if validation_result.company_coverage_percent < 100:
                warning_parts.append(
                    f"⚠️ Hanya {validation_result.processed_companies}/{validation_result.total_companies} "
                    f"perusahaan ({validation_result.company_coverage_percent:.1f}%) yang berhasil diproses."
                )
            
            if validation_result.validation_warnings:
                warning_parts.append(
                    f"⚠️ Ditemukan {len(validation_result.validation_warnings)} "
                    "inkonsistensi data antar dimensi."
                )
            
            flash(' '.join(warning_parts), 'warning')
        else:
            flash('Konversi berhasil! Semua validasi passed.', 'success')
        
        return render_template('demografi/result.html',
                             success=True,
                             message=result.message,
                             total_rows=result.total_rows,
                             duration=result.duration,
                             output_filename=output_filename,
                             conversion_id=conversion_id,
                             sheets=list(result.data.keys()),
                             stats={dim: {
                                 'rows': len(df),
                                 'total': df['jumlah'].sum()
                             } for dim, df in result.data.items()},
                             warnings=result.warnings,
                             company_count=len(perusahaan_list),
                             validation=validation_result.to_dict())
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        
        if uploaded_file_path and os.path.exists(uploaded_file_path):
            try:
                os.remove(uploaded_file_path)
            except:
                pass
        
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('demografi.index'))
    
@demografi_bp.route('/download')
def download():
    """
    Download file FROM DATABASE ONLY
    ✅ NO LOCAL FILE STORAGE
    """
    try:
        conversion_id = request.args.get('conversion_id', type=int)
        
        if not conversion_id:
            flash('conversion_id tidak ditemukan', 'error')
            return redirect(url_for('demografi.history'))
        
        db = get_db('demografi')  # ← DEMOGRAFI DATABASE
        conn = db.get_connection()
        
        logger.info(f"📥 Downloading from database (conversion_id={conversion_id})")
        
        file_data = DemografiOutputFiles.get_file_content(conn, conversion_id)
        
        if not file_data:
            flash('File tidak ditemukan di database', 'error')
            logger.error(f"❌ File not found in database for conversion_id={conversion_id}")
            return redirect(url_for('demografi.history'))
        
        filename, file_content, mime_type = file_data
        
        file_io = io.BytesIO(file_content)
        file_io.seek(0)
        
        logger.info(f"✅ Downloading file from database: {filename}")
        
        return send_file(
            file_io,
            mimetype=mime_type,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"❌ Error downloading file: {e}")
        flash(f"Error downloading file: {str(e)}", 'error')
        return redirect(url_for('demografi.history'))

    
@demografi_bp.route('/history')
def history():
    """View conversion history"""
    try:
        db = get_db('demografi')
        conn = db.get_connection()
        
        # ✅ SAFE: Get history with None handling
        history_records = DemografiConversionHistory.get_all(conn, limit=100)
        
        # ✅ SAFE: Clean None values from history records
        for record in history_records:
            # Ensure numeric fields have default values
            if record.get('total_rows') is None:
                record['total_rows'] = 0
            if record.get('duration') is None:
                record['duration'] = 0.0
            if record.get('company_coverage_percent') is None:
                record['company_coverage_percent'] = 0.0
            if record.get('total_companies') is None:
                record['total_companies'] = 0
            if record.get('processed_companies') is None:
                record['processed_companies'] = 0
            
            # Check file existence
            db_exists = DemografiOutputFiles.check_exists(conn, record['id'])
            record['file_exists'] = db_exists
            record['file_location'] = 'database' if db_exists else 'none'
        
        # ✅ SAFE: Get statistics with error handling
        try:
            stats = DemografiConversionHistory.get_statistics(conn)
        except Exception as stats_error:
            logger.warning(f"⚠️  Stats error (using defaults): {stats_error}")
            stats = {
                'total_conversions': len(history_records),
                'success_count': 0,
                'failed_count': 0,
                'warning_count': 0
            }
        
        # ✅ SAFE: Get data statistics with error handling
        try:
            data_stats = get_data_statistics(conn)
        except Exception as data_error:
            logger.warning(f"⚠️  Data stats error (using defaults): {data_error}")
            data_stats = {
                'total_records': 0,
                'total_companies': 0
            }
        
        return render_template('demografi/history.html',
                             histories=history_records,
                             stats=stats,
                             data_stats=data_stats)
                             
    except Exception as e:
        logger.error(f"Error loading history: {e}", exc_info=True)
        flash(f"Error loading history: {str(e)}", 'error')
        return redirect(url_for('demografi.index'))
    

@demografi_bp.route('/visualize')
def visualize():
    """Visualisasi data dalam bentuk chart"""
    try:
        db = get_db('demografi')  # ← DEMOGRAFI DATABASE
        conn = db.get_connection()
        
        histories = DemografiConversionHistory.get_all(conn, limit=100)
        conversion_id = request.args.get('conversion_id', type=int)
        
        return render_template('demografi/visualization.html',
                             histories=histories,
                             conversion_id=conversion_id)
    except Exception as e:
        logger.error(f"Error loading visualization: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('demografi.history'))


@demografi_bp.route('/dashboard')
def monthly_dashboard():
    """Dashboard monitoring bulanan"""
    try:
        selected_month = request.args.get('month', type=int)
        selected_year = request.args.get('year', type=int)
        current_year = datetime.now().year
        
        has_data = selected_month and selected_year
        
        return render_template('demografi/dashboard.html',
                             selected_month=selected_month,
                             selected_year=selected_year,
                             current_year=current_year,
                             has_data=has_data)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('demografi.history'))

@demografi_bp.route('/api/monthly-data/<int:year>/<int:month>')
def api_monthly_data(year, month):
    """API endpoint untuk monthly dashboard data"""
    try:
        db = get_db('demografi')
        conn = db.get_connection()

        # ✅ FORMAT PERIODE YANG BENAR
        periode = f"{year}-{month:02d}"
        logger.info(f"🔍 Querying monthly data for periode: {periode}")

        # Load config
        config = get_config()

        # Mapping kategori perusahaan
        company_category_map = {}
        for _, company_data in config.data['perusahaan'].items():
            kode = company_data['kode_perusahaan']
            kategori = company_data.get('kategori', 'Sub Holding')
            company_category_map[kode] = kategori

        # ✅ AMBIL DATA BULAN TERAKHIR (SATU PINTU)
        data = get_latest_data_by_periode(conn, periode)

        has_any_data = any(not df.empty for df in data.values())

        response = {
            'has_data': has_any_data,
            'sub_holding': {
                'summary': {
                    'total_karyawan': 0,
                    'total_tetap': 0,
                    'total_tidak_tetap': 0,
                    'rasio_tetap': 0
                },
                'usia_bod46': {'labels': [], 'values': []},
                'usia_bod13': {'labels': [], 'values': []},
                'usia_total': {'labels': [], 'values': []},
                'pendidikan_bod46': {'labels': [], 'values': []},
                'pendidikan_bod13': {'labels': [], 'values': []},
                'pendidikan_total': {'labels': [], 'values': []},
                'gender_tetap': {'labels': [], 'values': []},
                'gender_tidak_tetap': {'labels': [], 'values': []},
                'gender_total': {'labels': [], 'values': []},
                'unit_kerja_tetap': {'labels': [], 'values': []},
                'unit_kerja_tidak_tetap': {'labels': [], 'values': []},
                'tren': {'labels': [], 'values': []}
            },
            'non_ptpn': {
                'summary': {
                    'total_karyawan': 0,
                    'total_tetap': 0,
                    'total_tidak_tetap': 0,
                    'rasio_tetap': 0
                },
                'usia_bod46': {'labels': [], 'values': []},
                'usia_bod13': {'labels': [], 'values': []},
                'usia_total': {'labels': [], 'values': []},
                'pendidikan_bod46': {'labels': [], 'values': []},
                'pendidikan_bod13': {'labels': [], 'values': []},
                'pendidikan_total': {'labels': [], 'values': []},
                'gender_tetap': {'labels': [], 'values': []},
                'gender_tidak_tetap': {'labels': [], 'values': []},
                'gender_total': {'labels': [], 'values': []},
                'unit_kerja_tetap': {'labels': [], 'values': []},
                'unit_kerja_tidak_tetap': {'labels': [], 'values': []},
                'tren': {'labels': [], 'values': []}
            }
        }

        if not has_any_data:
            logger.warning(f"⚠️  No data found for {year}-{month:02d}")
            response['message'] = f'Tidak ada data untuk bulan {month} tahun {year}'
            return json.dumps(response), 200, {'Content-Type': 'application/json'}

        def split_by_category(df):
            """Split dataframe menjadi Sub Holding dan Non PTPN"""
            if df.empty:
                return df.iloc[0:0].copy(), df.iloc[0:0].copy()

            if 'nama_perusahaan' in df.columns and 'kode_perusahaan' not in df.columns:
                def get_category_from_name(nama):
                    for company_name, company_data in config.data['perusahaan'].items():
                        if company_data['nama'] == nama:
                            return company_data.get('kategori', 'Sub Holding')
                    return 'Sub Holding'

                df['kategori_perusahaan'] = df['nama_perusahaan'].apply(get_category_from_name)

            elif 'kode_perusahaan' in df.columns:
                df['kategori_perusahaan'] = df['kode_perusahaan'].map(company_category_map)
                df['kategori_perusahaan'] = df['kategori_perusahaan'].fillna('Sub Holding')
            else:
                df['kategori_perusahaan'] = 'Sub Holding'

            sub_holding = df[df['kategori_perusahaan'] == 'Sub Holding'].copy()
            non_ptpn = df[df['kategori_perusahaan'] == 'Non PTPN'].copy()

            logger.info(f"   Split: Sub Holding={len(sub_holding)}, Non PTPN={len(non_ptpn)}")

            return sub_holding, non_ptpn

        def filter_by_bod(df, bod_levels):
            """Filter dataframe by BOD levels"""
            if df.empty:
                return df
            if 'kategori_jabatan' not in df.columns:
                return df
            return df[df['kategori_jabatan'].str.contains('|'.join(bod_levels), na=False, regex=True)]

        def process_category_data(category_data_dict, category_key):
            """Process data untuk satu kategori (Sub Holding atau Non PTPN)"""

            if 'tren' in category_data_dict and not category_data_dict['tren'].empty:
                tren_grouped = category_data_dict['tren'].groupby('kategori')['jumlah'].sum()
                response[category_key]['summary']['total_tetap'] = int(tren_grouped.get('TETAP', 0))
                response[category_key]['summary']['total_tidak_tetap'] = int(tren_grouped.get('NON TETAP', 0))
                response[category_key]['summary']['total_karyawan'] = (
                    response[category_key]['summary']['total_tetap'] +
                    response[category_key]['summary']['total_tidak_tetap']
                )

                if response[category_key]['summary']['total_karyawan'] > 0:
                    response[category_key]['summary']['rasio_tetap'] = round(
                        (response[category_key]['summary']['total_tetap'] /
                         response[category_key]['summary']['total_karyawan']) * 100, 1
                    )

            if 'usia' in category_data_dict and not category_data_dict['usia'].empty:
                usia_df = category_data_dict['usia']

                usia_bod46 = filter_by_bod(usia_df, ['BOD-4', 'BOD-5', 'BOD-6'])
                if not usia_bod46.empty:
                    grouped = usia_bod46.groupby('kategori')['jumlah'].sum()
                    response[category_key]['usia_bod46']['labels'] = grouped.index.tolist()
                    response[category_key]['usia_bod46']['values'] = grouped.values.tolist()

                usia_bod13 = filter_by_bod(usia_df, ['BOD-1', 'BOD-2', 'BOD-3'])
                if not usia_bod13.empty:
                    grouped = usia_bod13.groupby('kategori')['jumlah'].sum()
                    response[category_key]['usia_bod13']['labels'] = grouped.index.tolist()
                    response[category_key]['usia_bod13']['values'] = grouped.values.tolist()

                grouped_total = usia_df.groupby('kategori')['jumlah'].sum()
                response[category_key]['usia_total']['labels'] = grouped_total.index.tolist()
                response[category_key]['usia_total']['values'] = grouped_total.values.tolist()

            if 'pendidikan' in category_data_dict and not category_data_dict['pendidikan'].empty:
                pend_df = category_data_dict['pendidikan']

                pend_bod46 = filter_by_bod(pend_df, ['BOD-4', 'BOD-5', 'BOD-6'])
                if not pend_bod46.empty:
                    grouped = pend_bod46.groupby('kategori')['jumlah'].sum().sort_values(ascending=False)
                    response[category_key]['pendidikan_bod46']['labels'] = grouped.index.tolist()
                    response[category_key]['pendidikan_bod46']['values'] = grouped.values.tolist()

                pend_bod13 = filter_by_bod(pend_df, ['BOD-1', 'BOD-2', 'BOD-3'])
                if not pend_bod13.empty:
                    grouped = pend_bod13.groupby('kategori')['jumlah'].sum().sort_values(ascending=False)
                    response[category_key]['pendidikan_bod13']['labels'] = grouped.index.tolist()
                    response[category_key]['pendidikan_bod13']['values'] = grouped.values.tolist()

                grouped_total = pend_df.groupby('kategori')['jumlah'].sum().sort_values(ascending=False)
                response[category_key]['pendidikan_total']['labels'] = grouped_total.index.tolist()
                response[category_key]['pendidikan_total']['values'] = grouped_total.values.tolist()

            if 'gender' in category_data_dict and not category_data_dict['gender'].empty:
                gender_df = category_data_dict['gender']

                if 'kelompok' in gender_df.columns:
                    gender_tetap = gender_df[gender_df['kelompok'] == 'TETAP']
                    if not gender_tetap.empty:
                        grouped = gender_tetap.groupby('kategori')['jumlah'].sum()
                        response[category_key]['gender_tetap']['labels'] = grouped.index.tolist()
                        response[category_key]['gender_tetap']['values'] = grouped.values.tolist()

                    gender_tidak_tetap = gender_df[gender_df['kelompok'] == 'TIDAK TETAP']
                    if not gender_tidak_tetap.empty:
                        grouped = gender_tidak_tetap.groupby('kategori')['jumlah'].sum()
                        response[category_key]['gender_tidak_tetap']['labels'] = grouped.index.tolist()
                        response[category_key]['gender_tidak_tetap']['values'] = grouped.values.tolist()

                grouped_total = gender_df.groupby('kategori')['jumlah'].sum()
                response[category_key]['gender_total']['labels'] = grouped_total.index.tolist()
                response[category_key]['gender_total']['values'] = grouped_total.values.tolist()

            if 'unit_kerja' in category_data_dict and not category_data_dict['unit_kerja'].empty:
                unit_df = category_data_dict['unit_kerja']

                if 'kelompok' in unit_df.columns:
                    unit_tetap = unit_df[unit_df['kelompok'] == 'TETAP']
                    if not unit_tetap.empty:
                        grouped = unit_tetap.groupby('kategori')['jumlah'].sum().sort_values(ascending=False)
                        response[category_key]['unit_kerja_tetap']['labels'] = grouped.index.tolist()
                        response[category_key]['unit_kerja_tetap']['values'] = grouped.values.tolist()

                    unit_tidak_tetap = unit_df[unit_df['kelompok'] == 'TIDAK TETAP']
                    if not unit_tidak_tetap.empty:
                        grouped = unit_tidak_tetap.groupby('kategori')['jumlah'].sum().sort_values(ascending=False)
                        response[category_key]['unit_kerja_tidak_tetap']['labels'] = grouped.index.tolist()
                        response[category_key]['unit_kerja_tidak_tetap']['values'] = grouped.values.tolist()

            if 'tren' in category_data_dict and not category_data_dict['tren'].empty:
                grouped = category_data_dict['tren'].groupby('kategori')['jumlah'].sum()
                response[category_key]['tren']['labels'] = grouped.index.tolist()
                response[category_key]['tren']['values'] = grouped.values.tolist()

        sub_holding_data = {}
        non_ptpn_data = {}

        for dimensi, df in data.items():
            if not df.empty:
                sub_df, non_df = split_by_category(df)
                sub_holding_data[dimensi] = sub_df
                non_ptpn_data[dimensi] = non_df

        process_category_data(sub_holding_data, 'sub_holding')
        process_category_data(non_ptpn_data, 'non_ptpn')

        logger.info(
            f"✅ Response: Sub Holding={response['sub_holding']['summary']['total_karyawan']}, "
            f"Non PTPN={response['non_ptpn']['summary']['total_karyawan']}"
        )

        return json.dumps(response), 200, {'Content-Type': 'application/json'}

    except Exception as e:
        logger.error(f"❌ Error getting monthly data: {e}", exc_info=True)
        return json.dumps({
            'error': True,
            'message': str(e)
        }), 500, {'Content-Type': 'application/json'}
    
@demografi_bp.route('/api/validation-detail/<int:conversion_id>')
def api_validation_detail(conversion_id):
    """API endpoint to get validation detail for a conversion"""
    try:
        db = get_db('demografi')
        conn = db.get_connection()
        
        history = DemografiConversionHistory.get_by_id(conn, conversion_id)
        
        if not history:
            return json.dumps({
                'error': 'Conversion not found'
            }), 404, {'Content-Type': 'application/json'}
        
        from modules.demografi.validator import parse_validation_data
        from modules.demografi.config import get_config
        
        validation_data = parse_validation_data(history)
        
        # ✅ NEW: Get company names mapping
        config = get_config()
        company_names = {}
        for key, data in config.data['perusahaan'].items():
            company_names[key] = data.get('nama', key)
        
        response = {
            'conversion_id': conversion_id,
            'status': history.get('status', 'unknown'),
            'total_companies': validation_data['total_companies'],
            'processed_companies': validation_data['processed_companies'],
            'coverage_percent': validation_data['company_coverage_percent'],
            'missing_companies': validation_data['missing_companies'],
            'validation_warnings': validation_data['validation_warnings'],
            'has_validation': validation_data['has_validation'],
            'company_names': company_names  # ✅ NEW
        }
        
        return json.dumps(response, ensure_ascii=False), 200, {'Content-Type': 'application/json; charset=utf-8'}
        
    except Exception as e:
        logger.error(f"❌ Error getting validation detail: {e}", exc_info=True)
        return json.dumps({
            'error': str(e)
        }), 500, {'Content-Type': 'application/json'}

      
@demografi_bp.route('/api/chart-data/<int:conversion_id>')
def api_get_chart_data(conversion_id):
    """API endpoint untuk get chart data."""
    try:
                
        db = get_db('demografi')
        conn = db.get_connection()
        
        data = get_all_data_by_conversion_id(conn, conversion_id)
        
        response = {
            'stats': {},
            'gender': {'labels': [], 'values': []},
            'pendidikan': {'labels': [], 'values': []},
            'usia': {'labels': [], 'values': []},
            'unit_kerja': {'labels': [], 'values': []},
            'tren': {'labels': [], 'values': []},
            'company': {'labels': [], 'values': []}
        }
        
        # Process Gender
        if 'gender' in data and not data['gender'].empty:
            gender_df = data['gender'].groupby('kategori')['jumlah'].sum()
            response['gender']['labels'] = gender_df.index.tolist()
            response['gender']['values'] = gender_df.values.tolist()
        
        # Process Pendidikan
        if 'pendidikan' in data and not data['pendidikan'].empty:
            pend_df = data['pendidikan'].groupby('kategori')['jumlah'].sum().sort_values(ascending=False)
            response['pendidikan']['labels'] = pend_df.index.tolist()
            response['pendidikan']['values'] = pend_df.values.tolist()
        
        # Process Usia
        if 'usia' in data and not data['usia'].empty:
            usia_df = data['usia'].groupby('kategori')['jumlah'].sum()
            age_order = ['<26', '26-30', '31-35', '36-40', '41-45', '46-50', '51-55', '>55']
            usia_df = usia_df.reindex([x for x in age_order if x in usia_df.index])
            response['usia']['labels'] = usia_df.index.tolist()
            response['usia']['values'] = usia_df.values.tolist()
        
        # Process Unit Kerja (Top 5)
        if 'unit_kerja' in data and not data['unit_kerja'].empty:
            unit_df = data['unit_kerja'].groupby('kategori')['jumlah'].sum().sort_values(ascending=False).head(5)
            response['unit_kerja']['labels'] = unit_df.index.tolist()
            response['unit_kerja']['values'] = unit_df.values.tolist()
        
        # Process Tren
        if 'tren' in data and not data['tren'].empty:
            tren_df = data['tren'].groupby('kategori')['jumlah'].sum()
            response['tren']['labels'] = tren_df.index.tolist()
            response['tren']['values'] = tren_df.values.tolist()
        
        # Process Company (Top 10)
        if 'gender' in data and not data['gender'].empty:
            company_df = data['gender'].groupby('kode_perusahaan')['jumlah'].sum().sort_values(ascending=False).head(10)
            response['company']['labels'] = company_df.index.tolist()
            response['company']['values'] = company_df.values.tolist()
        
        # Calculate statistics
        total_karyawan = 0
        total_laki_laki = 0
        total_perempuan = 0
        total_tetap = 0
        
        if 'gender' in data and not data['gender'].empty:
            total_karyawan = data['gender']['jumlah'].sum()
            gender_grouped = data['gender'].groupby('kategori')['jumlah'].sum()
            total_laki_laki = gender_grouped.get('LAKI-LAKI', 0)
            total_perempuan = gender_grouped.get('PEREMPUAN', 0)
        
        if 'tren' in data and not data['tren'].empty:
            tren_grouped = data['tren'].groupby('kategori')['jumlah'].sum()
            total_tetap = tren_grouped.get('TETAP', 0)
        
        response['stats'] = {
            'total_karyawan': int(total_karyawan),
            'total_laki_laki': int(total_laki_laki),
            'total_perempuan': int(total_perempuan),
            'total_tetap': int(total_tetap)
        }
        
        return json.dumps(response), 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        logger.error(f"Error getting chart data: {e}", exc_info=True)
        return json.dumps({'error': str(e)}), 500, {'Content-Type': 'application/json'}


@demografi_bp.route('/data/<int:conversion_id>')
def view_data(conversion_id):
    """View conversion data details"""
    try:
        db = get_db('demografi')  # ← DEMOGRAFI DATABASE
        conn = db.get_connection()
        
        history = DemografiConversionHistory.get_by_id(conn, conversion_id)
        if not history:
            flash('Conversion not found', 'error')
            return redirect(url_for('demografi.history'))
        
        data = get_all_data_by_conversion_id(conn, conversion_id)
        
        preview_data = {}
        for dimensi, df in data.items():
            if not df.empty:
                preview_data[dimensi] = {
                    'total_rows': len(df),
                    'preview': df.head(100).to_dict('records'),
                    'columns': list(df.columns)
                }
        
        return render_template('demografi/detail.html',
                             history=history,
                             data=preview_data,
                             conversion_id=conversion_id)
    except Exception as e:
        logger.error(f"Error viewing data: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('demografi.history'))


@demografi_bp.route('/delete/<int:conversion_id>', methods=['POST'])
def delete_conversion(conversion_id):
    """Delete conversion history and all related data"""
    try:
        from database.models.demografi import DemografiConversionHistory

        db = get_db('demografi')  # ← DEMOGRAFI DATABASE
        conn = db.get_connection()
        
        history = DemografiConversionHistory.get_by_id(conn, conversion_id)
        
        if not history:
            flash('Conversion tidak ditemukan', 'error')
            return redirect(url_for('demografi.history'))
        
        # Delete from database (cascade to all related data)
        success = DemografiConversionHistory.delete(conn, conversion_id)
        
        if success:
            flash(f'Conversion #{conversion_id} berhasil dihapus', 'success')
            logger.info(f"✅ Deleted conversion #{conversion_id}: {history['original_filename']}")
        else:
            flash('Gagal menghapus conversion', 'error')
        
        return redirect(url_for('demografi.history'))
        
    except Exception as e:
        logger.error(f"Error deleting conversion: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('demografi.history'))
       
@demografi_bp.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    flash('File terlalu besar! Maksimal 50MB', 'error')
    return redirect(url_for('demografi.index'))


@demografi_bp.errorhandler(500)
def internal_error(e):
    """Handle internal server error."""
    logger.error(f"Internal server error: {e}")
    flash('Internal server error. Please try again.', 'error')
    return redirect(url_for('demografi.index'))