import pandas as pd
from datetime import datetime
from typing import List, Dict

from modules.demografi.config import get_config
from modules.demografi.excel_reader import ExcelReader
from modules.demografi.utils import (
    get_logger, ConversionResult, ProgressTracker, 
    parse_date, ValidationError
)

logger = get_logger()

def convert(file_path: str, perusahaan: str, periode: str, 
           dimensi_list: List[str]) -> ConversionResult:

    start_time = datetime.now()
    result = ConversionResult()
    
    try:
        logger.info("=" * 80)
        logger.info("MULAI KONVERSI")
        logger.info(f"   File: {file_path}")
        logger.info(f"   Perusahaan: {perusahaan}")
        logger.info(f"   Periode: {periode}")
        logger.info(f"   Dimensi: {', '.join(dimensi_list)}")
        logger.info("=" * 80)

        logger.info("\n📝 Loading config...")
        config = get_config()
        
        company = config.get_company(perusahaan)
        periode_std = parse_date(periode)
        
        # Storage untuk setiap dimensi
        rows_by_dimensi = {
            'gender': [],
            'pendidikan': [],
            'usia': [],
            'unit_kerja': [],
            'tren': []
        }
        
        with ExcelReader(file_path) as reader:
            
            logger.info("\n" + "="*60)
            logger.info("📊 PROCESSING: KARYAWAN TETAP")
            logger.info("="*60)
            
            reader.select_sheet(company['sheet_name'])
            
            tetap_levels = config.get_level_definitions('TETAP')
            
            for level_def in tetap_levels:
                kelompok_jabatan = level_def['kelompok_jabatan']
                level_bod = level_def['level_bod']
                
                logger.info(f"\n   📌 {kelompok_jabatan} - {level_bod}")
                
                # Filter dimensi yang bukan 'tren'
                dims_to_process = [d for d in dimensi_list if d != 'tren']
                
                for dimensi in dims_to_process:
                    mapping = config.get_mapping_tetap(
                        kelompok_jabatan, level_bod, dimensi
                    )
                    
                    if not mapping:
                        logger.info(f"      ℹ️  {dimensi}: no mapping")
                        continue
                    
                    kategori_count = 0
                    for kategori, cell in mapping.items():
                        jumlah = reader.read_cell(cell)
                        
                        # Transform kategori display
                        if dimensi == 'gender':
                            kategori_display = (
                                'LAKI-LAKI' if kategori == 'L' else 'PEREMPUAN'
                            )
                        else:
                            kategori_display = kategori
                        
                        row = {
                            'holding': company.get('holding', ''),
                            'kode_perusahaan': company['kode_perusahaan'],
                            'periode': periode_std,
                            'kelompok': 'TETAP',
                            'kelompok_jabatan': kelompok_jabatan,
                            'kategori_jabatan': level_bod,
                            'kategori': kategori_display,
                            'jumlah': jumlah
                        }
                        
                        rows_by_dimensi[dimensi].append(row)
                        kategori_count += 1
                    
                    logger.info(f"      ✅ {dimensi}: {kategori_count} kategori")
            
            # ================================================================
            # PROCESS TIDAK TETAP (gender, unit_kerja only)
            # ================================================================
            logger.info("\n" + "="*60)
            logger.info("📊 PROCESSING: KARYAWAN TIDAK TETAP")
            logger.info("="*60)
            
            tidak_tetap_levels = config.get_level_definitions('TIDAK TETAP')
            
            for level_def in tidak_tetap_levels:
                kelompok_jabatan = level_def['kelompok_jabatan']
                kategori_jabatan_raw = level_def['kategori_jabatan']
                
                logger.info(f"\n   📌 {kelompok_jabatan} - {kategori_jabatan_raw}")
                
                # Get available dimensions (hanya gender dan unit_kerja)
                available_dims = config.get_available_dimensions(
                    'TIDAK TETAP', kelompok_jabatan, 
                    kategori_jabatan=kategori_jabatan_raw
                )
                
                # Filter dimensi yang tersedia dan bukan 'tren'
                dims_to_process = [
                    d for d in dimensi_list 
                    if d in available_dims and d != 'tren'
                ]
                
                for dimensi in dims_to_process:
                    mapping = config.get_mapping_tidak_tetap(
                        kelompok_jabatan, kategori_jabatan_raw, dimensi
                    )
                    
                    if not mapping:
                        logger.info(f"      ℹ️  {dimensi}: no mapping")
                        continue
                    
                    kategori_count = 0
                    for kategori, cell in mapping.items():
                        jumlah = reader.read_cell(cell)
                        
                        # Transform kategori display
                        if dimensi == 'gender':
                            kategori_display = (
                                'LAKI-LAKI' if kategori == 'L' else 'PEREMPUAN'
                            )
                        else:
                            kategori_display = kategori
                        
                        row = {
                            'holding': company.get('holding', ''),
                            'kode_perusahaan': company['kode_perusahaan'],
                            'periode': periode_std,
                            'kelompok': 'TIDAK TETAP',
                            'kelompok_jabatan': kelompok_jabatan,
                            'kategori_jabatan': kategori_jabatan_raw,
                            'kategori': kategori_display,
                            'jumlah': jumlah
                        }
                        
                        rows_by_dimensi[dimensi].append(row)
                        kategori_count += 1
                    
                    logger.info(f"      ✅ {dimensi}: {kategori_count} kategori")
        
        # ====================================================================
        # CREATE DATAFRAMES
        # ====================================================================
        logger.info("\n📋 Membuat DataFrames...")
        
        dataframes = {}
        
        for dimensi, rows in rows_by_dimensi.items():
            if dimensi == 'tren':
                continue  # Skip tren, akan dibuat terpisah
                
            if rows:  # Only create DataFrame if ada data
                df = pd.DataFrame(rows)
                dataframes[dimensi] = df
                logger.info(f"   ✅ DataFrame {dimensi.upper()}: {len(df)} rows")
        
        # ====================================================================
        # GENERATE TREN FROM GENDER DATA
        # ====================================================================
        if 'tren' in dimensi_list and 'gender' in dataframes:
            logger.info("\n" + "="*60)
            logger.info("📊 GENERATING: DIMENSI TREN (from gender)")
            logger.info("="*60)
            
            gender_df = dataframes['gender']
            
            # Group by kelompok (TETAP/TIDAK TETAP) per company
            tren_grouped = gender_df.groupby(['periode', 'kode_perusahaan', 'kelompok'])['jumlah'].sum().reset_index()
            
            # Transform ke format tren
            tren_data = []
            for _, row in tren_grouped.iterrows():
                # Get company name from code
                company_name = None
                for comp_name, comp_config in config.data.get('perusahaan', {}).items():
                    if comp_config['kode_perusahaan'] == row['kode_perusahaan']:
                        company_name = comp_config['nama']
                        break
                
                if not company_name:
                    company_name = row['kode_perusahaan']
                
                # Map kategori
                kategori = 'TETAP' if row['kelompok'] == 'TETAP' else 'NON TETAP'
                
                tren_data.append({
                    'periode': row['periode'],
                    'nama_perusahaan': company_name,
                    'kategori': kategori,
                    'jumlah': row['jumlah']
                })
            
            if tren_data:
                dataframes['tren'] = pd.DataFrame(tren_data)
                logger.info(f"   ✅ Tren generated: {len(tren_data)} rows")
                
                # Log summary
                tren_summary = dataframes['tren'].groupby('kategori')['jumlah'].sum()
                for kategori, total in tren_summary.items():
                    logger.info(f"      • {kategori}: {total:,}")
            else:
                logger.warning("   ⚠️  No tren data generated")
        
        if not dataframes:
            raise ValidationError("Tidak ada data yang berhasil dibaca")
        
        # ====================================================================
        # STATISTICS
        # ====================================================================
        logger.info("\n📈 Statistik:")
        
        total_rows = sum(len(df) for df in dataframes.values())
        
        for dimensi, df in dataframes.items():
            total = df['jumlah'].sum()
            logger.info(f"   • {dimensi.upper()}: {total:,} total ({len(df)} rows)")
        
        # ====================================================================
        # RESULT
        # ====================================================================
        result.success = True
        result.message = "Konversi berhasil"
        result.total_rows = total_rows
        result.data = dataframes
        result.duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ KONVERSI SELESAI")
        logger.info(f"   Total baris: {result.total_rows:,}")
        logger.info(f"   DataFrames: {', '.join(dataframes.keys())}")
        logger.info(f"   Durasi: {result.duration:.2f} detik")
        logger.info("=" * 80)
        
        return result
        
    except Exception as e:
        logger.error(f"\n❌ Error: {str(e)}", exc_info=True)
        
        result.success = False
        result.message = f"Error: {str(e)}"
        result.errors.append(str(e))
        result.duration = (datetime.now() - start_time).total_seconds()
        
        return result


def convert_multiple(file_path: str, perusahaan_list: List[str], 
                    periode: str, dimensi_list: List[str]) -> ConversionResult:
    """Convert multiple companies dan gabungkan per dimensi."""

    start_time = datetime.now()

    logger.info(f"🔄 Converting {len(perusahaan_list)} companies...")
    
    # Storage untuk semua dimensi
    all_data = {
        'gender': [],
        'pendidikan': [],
        'usia': [],
        'unit_kerja': [],
        'tren': []
    }
    errors = []
    
    for perusahaan in perusahaan_list:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {perusahaan}")
        logger.info('='*60)
        
        result = convert(file_path, perusahaan, periode, dimensi_list)
        
        if result.success:
            # Append data dari setiap dimensi
            for dimensi, df in result.data.items():
                all_data[dimensi].append(df)
        else:
            errors.extend(result.errors)
    
    final_result = ConversionResult()
    
    # Combine all DataFrames
    combined = {}
    for dimensi, df_list in all_data.items():
        if df_list:  # Jika ada data untuk dimensi ini
            combined[dimensi] = pd.concat(df_list, ignore_index=True)
    
    if combined:
        total_rows = sum(len(df) for df in combined.values())
        
        final_result.success = True
        final_result.message = f"{len(perusahaan_list)} perusahaan berhasil diproses"
        final_result.total_rows = total_rows
        final_result.data = combined
    else:
        final_result.success = False
        final_result.message = "Semua konversi gagal"
    
    final_result.errors = errors

    # 🔥 SET DURATION - TAMBAHKAN INI!
    final_result.duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"\n✅ Total duration: {final_result.duration:.2f} seconds")
    
    return final_result