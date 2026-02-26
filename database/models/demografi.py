"""
database/models/demografi.py
=============================
Database models untuk modul Demografi
Complete version with all functions from original project
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# SQL TABLE CREATION QUERIES
# ============================================================================

CREATE_DEMOGRAFI_TABLES = {
    'conversion_history': """
        CREATE TABLE conversion_history (
            id INT IDENTITY(1,1) PRIMARY KEY,
            created_at DATETIME NOT NULL DEFAULT GETDATE(),
            original_filename NVARCHAR(255) NOT NULL,
            output_filename NVARCHAR(255),
            periode NVARCHAR(20) NOT NULL,
            perusahaan NVARCHAR(100),
            total_rows INT DEFAULT 0,
            duration FLOAT DEFAULT 0,
            status NVARCHAR(20) DEFAULT 'processing',
            error_message NVARCHAR(MAX),
            total_companies INT NULL,
            processed_companies INT NULL,
            missing_companies NVARCHAR(MAX) NULL,
            validation_warnings NVARCHAR(MAX) NULL,
            company_coverage_percent DECIMAL(5,2) NULL
        );
        
        CREATE INDEX idx_periode ON conversion_history(periode);
        CREATE INDEX idx_status ON conversion_history(status);
        CREATE INDEX idx_created_at ON conversion_history(created_at DESC);
        CREATE INDEX idx_status_coverage ON conversion_history(status, company_coverage_percent);
    """,
    
    'data_gender': """
        CREATE TABLE data_gender (
            id INT IDENTITY(1,1) PRIMARY KEY,
            conversion_id INT NULL,
            holding NVARCHAR(100) NULL,
            kode_perusahaan NVARCHAR(50) NOT NULL,
            periode DATE NOT NULL,
            kelompok NVARCHAR(50) NOT NULL,
            kelompok_jabatan NVARCHAR(100) NOT NULL,
            kategori_jabatan NVARCHAR(100) NOT NULL,
            kategori NVARCHAR(50) NOT NULL,
            jumlah INT NOT NULL,
            created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
            
            FOREIGN KEY (conversion_id) REFERENCES conversion_history(id)
        );
        
        CREATE INDEX idx_gender_periode ON data_gender(periode DESC);
        CREATE INDEX idx_gender_perusahaan ON data_gender(kode_perusahaan);
        CREATE INDEX idx_gender_conversion ON data_gender(conversion_id);
    """,
    
    'data_pendidikan': """
        CREATE TABLE data_pendidikan (
            id INT IDENTITY(1,1) PRIMARY KEY,
            conversion_id INT NULL,
            holding NVARCHAR(100) NULL,
            kode_perusahaan NVARCHAR(50) NOT NULL,
            periode DATE NOT NULL,
            kelompok NVARCHAR(50) NOT NULL,
            kelompok_jabatan NVARCHAR(100) NOT NULL,
            kategori_jabatan NVARCHAR(100) NOT NULL,
            kategori NVARCHAR(50) NOT NULL,
            jumlah INT NOT NULL,
            created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
            
            FOREIGN KEY (conversion_id) REFERENCES conversion_history(id)
        );
        
        CREATE INDEX idx_pendidikan_periode ON data_pendidikan(periode DESC);
        CREATE INDEX idx_pendidikan_perusahaan ON data_pendidikan(kode_perusahaan);
        CREATE INDEX idx_pendidikan_conversion ON data_pendidikan(conversion_id);
    """,
    
    'data_usia': """
        CREATE TABLE data_usia (
            id INT IDENTITY(1,1) PRIMARY KEY,
            conversion_id INT NULL,
            holding NVARCHAR(100) NULL,
            kode_perusahaan NVARCHAR(50) NOT NULL,
            periode DATE NOT NULL,
            kelompok NVARCHAR(50) NOT NULL,
            kelompok_jabatan NVARCHAR(100) NOT NULL,
            kategori_jabatan NVARCHAR(100) NOT NULL,
            kategori NVARCHAR(50) NOT NULL,
            jumlah INT NOT NULL,
            created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
            
            FOREIGN KEY (conversion_id) REFERENCES conversion_history(id)
        );
        
        CREATE INDEX idx_usia_periode ON data_usia(periode DESC);
        CREATE INDEX idx_usia_perusahaan ON data_usia(kode_perusahaan);
        CREATE INDEX idx_usia_conversion ON data_usia(conversion_id);
    """,
    
    'data_unit_kerja': """
        CREATE TABLE data_unit_kerja (
            id INT IDENTITY(1,1) PRIMARY KEY,
            conversion_id INT NULL,
            holding NVARCHAR(100) NULL,
            kode_perusahaan NVARCHAR(50) NOT NULL,
            periode DATE NOT NULL,
            kelompok NVARCHAR(50) NOT NULL,
            kelompok_jabatan NVARCHAR(100) NOT NULL,
            kategori_jabatan NVARCHAR(100) NOT NULL,
            kategori NVARCHAR(50) NOT NULL,
            jumlah INT NOT NULL,
            created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
            
            FOREIGN KEY (conversion_id) REFERENCES conversion_history(id)
        );
        
        CREATE INDEX idx_unit_kerja_periode ON data_unit_kerja(periode DESC);
        CREATE INDEX idx_unit_kerja_perusahaan ON data_unit_kerja(kode_perusahaan);
        CREATE INDEX idx_unit_kerja_conversion ON data_unit_kerja(conversion_id);
    """,
    
    'data_tren': """
        CREATE TABLE data_tren (
            id INT IDENTITY(1,1) PRIMARY KEY,
            conversion_id INT NULL,
            periode DATE NOT NULL,
            nama_perusahaan NVARCHAR(200) NOT NULL,
            kategori NVARCHAR(50) NOT NULL,
            jumlah INT NOT NULL,
            created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
            
            FOREIGN KEY (conversion_id) REFERENCES conversion_history(id)
        );
        
        CREATE INDEX idx_tren_periode ON data_tren(periode DESC);
        CREATE INDEX idx_tren_perusahaan ON data_tren(nama_perusahaan);
        CREATE INDEX idx_tren_conversion ON data_tren(conversion_id);
    """,
    
    'conversion_files': """
        CREATE TABLE conversion_files (
            id INT IDENTITY(1,1) PRIMARY KEY,
            conversion_id INT NOT NULL,
            filename NVARCHAR(500) NOT NULL,
            file_content VARBINARY(MAX) NOT NULL,
            file_size BIGINT NOT NULL,
            mime_type NVARCHAR(100) NOT NULL,
            created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
            
            FOREIGN KEY (conversion_id) REFERENCES conversion_history(id)
        );
        
        CREATE INDEX idx_conversion_files_conversion_id ON conversion_files(conversion_id);
    """
}

DROP_DEMOGRAFI_TABLES = """
IF OBJECT_ID('conversion_files', 'U') IS NOT NULL DROP TABLE conversion_files;
IF OBJECT_ID('data_tren', 'U') IS NOT NULL DROP TABLE data_tren;
IF OBJECT_ID('data_unit_kerja', 'U') IS NOT NULL DROP TABLE data_unit_kerja;
IF OBJECT_ID('data_usia', 'U') IS NOT NULL DROP TABLE data_usia;
IF OBJECT_ID('data_pendidikan', 'U') IS NOT NULL DROP TABLE data_pendidikan;
IF OBJECT_ID('data_gender', 'U') IS NOT NULL DROP TABLE data_gender;
IF OBJECT_ID('conversion_history', 'U') IS NOT NULL DROP TABLE conversion_history;
"""


# ============================================================================
# MODEL: CONVERSION HISTORY
# ============================================================================

class DemografiConversionHistory:
    """Model untuk table conversion_history"""
    
    @staticmethod
    def insert(conn, original_filename: str, output_filename: str, periode: str, 
           perusahaan: str, total_rows: int, duration: float, status: str, 
           error_message: str = None,
           total_companies: int = None,
           processed_companies: int = None,
           missing_companies: str = None,
           validation_warnings: str = None,
           company_coverage_percent: float = None) -> int:
        """
        Insert new conversion record
        ✅ Updated with validation fields
        
        Args:
            ... (existing args)
            total_companies: Total companies expected
            processed_companies: Companies successfully processed
            missing_companies: JSON string of missing company codes
            validation_warnings: JSON string of validation warnings
            company_coverage_percent: Percentage of companies processed
        
        Returns:
            int: conversion_id
        """
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversion_history 
            (original_filename, output_filename, periode, perusahaan, 
            total_rows, duration, status, error_message,
            total_companies, processed_companies, missing_companies,
            validation_warnings, company_coverage_percent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            original_filename,
            output_filename,
            periode,
            perusahaan,
            total_rows,
            duration,
            status,
            error_message,
            total_companies,
            processed_companies,
            missing_companies,
            validation_warnings,
            company_coverage_percent
        ))
        
        conn.commit()
        
        cursor.execute("SELECT @@IDENTITY")
        conversion_id = cursor.fetchone()[0]
        cursor.close()
        
        logger.info(f"✅ Conversion history saved (ID: {conversion_id}, Status: {status}, Coverage: {company_coverage_percent}%)")
        
        return conversion_id
    
    @staticmethod
    def get_all(conn, limit: int = 100) -> list:
        """Get all conversion history with validation info"""
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT TOP (?)
                id,
                created_at,
                original_filename,
                output_filename,
                periode,
                perusahaan,
                total_rows,
                duration,
                status,
                error_message,
                total_companies,
                processed_companies,
                missing_companies,
                validation_warnings,
                company_coverage_percent
            FROM conversion_history
            ORDER BY created_at DESC
        """, (limit,))
        
        results = cursor.fetchall()
        cursor.close()
        
        return [
            {
                'id': row.id,
                'created_at': row.created_at.strftime('%Y-%m-%d %H:%M:%S') if row.created_at else '',
                'original_filename': row.original_filename,
                'output_filename': row.output_filename,
                'periode': row.periode,
                'perusahaan': row.perusahaan,
                'total_rows': row.total_rows or 0,
                'duration': row.duration or 0,
                'status': row.status,
                'error_message': row.error_message,
                'total_companies': row.total_companies,
                'processed_companies': row.processed_companies,
                'missing_companies': row.missing_companies,
                'validation_warnings': row.validation_warnings,
                'company_coverage_percent': float(row.company_coverage_percent) if row.company_coverage_percent else None
            }
            for row in results
        ]
    
    @staticmethod
    def get_by_id(conn, conversion_id: int) -> dict:
        """Get single conversion history by ID with validation info"""
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id,
                created_at,
                original_filename,
                output_filename,
                periode,
                perusahaan,
                total_rows,
                duration,
                status,
                error_message,
                total_companies,
                processed_companies,
                missing_companies,
                validation_warnings,
                company_coverage_percent
            FROM conversion_history
            WHERE id = ?
        """, (conversion_id,))
        
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            return None
        
        return {
            'id': row.id,
            'created_at': row.created_at.strftime('%Y-%m-%d %H:%M:%S') if row.created_at else '',
            'original_filename': row.original_filename,
            'output_filename': row.output_filename,
            'periode': row.periode,
            'perusahaan': row.perusahaan,
            'total_rows': row.total_rows or 0,
            'duration': row.duration or 0,
            'status': row.status,
            'error_message': row.error_message,
            'total_companies': row.total_companies,
            'processed_companies': row.processed_companies,
            'missing_companies': row.missing_companies,
            'validation_warnings': row.validation_warnings,
            'company_coverage_percent': float(row.company_coverage_percent) if row.company_coverage_percent else None
        }
   
    @staticmethod
    def get_recent(conn, days: int = 7) -> List[Dict]:
        """Get history dari N hari terakhir"""
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id,
                FORMAT(created_at, 'yyyy-MM-dd HH:mm:ss') as created_at,
                original_filename,
                output_filename,
                periode,
                perusahaan,
                total_rows,
                duration,
                status,
                error_message
            FROM conversion_history
            WHERE created_at >= DATEADD(day, -?, GETDATE())
            ORDER BY created_at DESC
        """, (days,))
        
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        cursor.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    @staticmethod
    def delete(conn, history_id: int) -> bool:
        """Delete conversion history"""
        cursor = conn.cursor()
        
        # Delete related data first (manual cascade)
        tables = ['conversion_files', 'data_tren', 'data_unit_kerja', 
                 'data_usia', 'data_pendidikan', 'data_gender']
        
        for table in tables:
            try:
                cursor.execute(f"DELETE FROM {table} WHERE conversion_id = ?", (history_id,))
                logger.info(f"   Deleted {cursor.rowcount} rows from {table}")
            except Exception as e:
                logger.warning(f"   Error deleting from {table}: {e}")
        
        # Delete history record
        cursor.execute("DELETE FROM conversion_history WHERE id = ?", (history_id,))
        conn.commit()
        
        deleted = cursor.rowcount > 0
        cursor.close()
        
        if deleted:
            logger.info(f"✅ History deleted (ID: {history_id})")
        
        return deleted
    
    @staticmethod
    def delete_old(conn, days: int = 30) -> int:
        """Delete history older than N days"""
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM conversion_history
            WHERE created_at < DATEADD(day, -?, GETDATE())
        """, (days,))
        
        conn.commit()
        deleted = cursor.rowcount
        cursor.close()
        
        if deleted > 0:
            logger.info(f"✅ Deleted {deleted} old history records")
        
        return deleted
    
    @staticmethod
    def get_statistics(conn) -> Dict:
        """Get overall statistics"""
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_conversions,
                ISNULL(SUM(total_rows), 0) as total_rows_processed,
                ISNULL(AVG(duration), 0) as avg_duration,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count
            FROM conversion_history
        """)
        
        row = cursor.fetchone()
        cursor.close()
        
        total = row.total_conversions or 0
        success = row.success_count or 0
        
        return {
            'total_conversions': total,
            'total_rows_processed': row.total_rows_processed or 0,
            'avg_duration': round(row.avg_duration or 0, 2),
            'success_rate': round((success / total * 100) if total > 0 else 0, 1)
        }


# ============================================================================
# MODEL: DATA GENDER
# ============================================================================

class DataGender:
    """Model untuk table data_gender"""
    
    @staticmethod
    def insert_bulk(conn, conversion_id: int, df: pd.DataFrame) -> int:
        """Bulk insert gender data"""
        if df is None or len(df) == 0:
            logger.warning("No gender data to insert")
            return 0
        
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO data_gender
            (conversion_id, holding, kode_perusahaan, periode, 
             kelompok, kelompok_jabatan, kategori_jabatan, kategori, jumlah)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        data = [
            (
                conversion_id,
                row.get('holding', ''),
                row['kode_perusahaan'],
                row['periode'],
                row['kelompok'],
                row['kelompok_jabatan'],
                row['kategori_jabatan'],
                row['kategori'],
                row['jumlah']
            )
            for _, row in df.iterrows()
        ]
        
        cursor.executemany(sql, data)
        conn.commit()
        rows_inserted = cursor.rowcount
        cursor.close()
        
        logger.info(f"✅ Inserted {rows_inserted} rows into data_gender")
        
        return rows_inserted
    
    @staticmethod
    def get_by_conversion_id(conn, conversion_id: int) -> pd.DataFrame:
        """Get gender data by conversion_id"""
        query = """
            SELECT
                holding, kode_perusahaan, periode, kelompok,
                kelompok_jabatan, kategori_jabatan, kategori, jumlah
            FROM data_gender
            WHERE conversion_id = ?
            ORDER BY kode_perusahaan, kelompok_jabatan
        """
        
        df = pd.read_sql(query, conn, params=(conversion_id,))
        logger.info(f"Loaded {len(df)} rows from data_gender")
        
        return df


# ============================================================================
# MODEL: DATA PENDIDIKAN
# ============================================================================

class DataPendidikan:
    """Model untuk table data_pendidikan"""
    
    @staticmethod
    def insert_bulk(conn, conversion_id: int, df: pd.DataFrame) -> int:
        """Bulk insert pendidikan data"""
        if df is None or len(df) == 0:
            logger.warning("No pendidikan data to insert")
            return 0
        
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO data_pendidikan
            (conversion_id, holding, kode_perusahaan, periode, 
             kelompok, kelompok_jabatan, kategori_jabatan, kategori, jumlah)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        data = [
            (
                conversion_id,
                row.get('holding', ''),
                row['kode_perusahaan'],
                row['periode'],
                row['kelompok'],
                row['kelompok_jabatan'],
                row['kategori_jabatan'],
                row['kategori'],
                row['jumlah']
            )
            for _, row in df.iterrows()
        ]
        
        cursor.executemany(sql, data)
        conn.commit()
        rows_inserted = cursor.rowcount
        cursor.close()
        
        logger.info(f"✅ Inserted {rows_inserted} rows into data_pendidikan")
        
        return rows_inserted
    
    @staticmethod
    def get_by_conversion_id(conn, conversion_id: int) -> pd.DataFrame:
        """Get pendidikan data by conversion_id"""
        query = """
            SELECT
                holding, kode_perusahaan, periode, kelompok,
                kelompok_jabatan, kategori_jabatan, kategori, jumlah
            FROM data_pendidikan
            WHERE conversion_id = ?
            ORDER BY kode_perusahaan, kelompok_jabatan
        """
        
        df = pd.read_sql(query, conn, params=(conversion_id,))
        logger.info(f"Loaded {len(df)} rows from data_pendidikan")
        
        return df


# ============================================================================
# MODEL: DATA USIA
# ============================================================================

class DataUsia:
    """Model untuk table data_usia"""
    
    @staticmethod
    def insert_bulk(conn, conversion_id: int, df: pd.DataFrame) -> int:
        """Bulk insert usia data"""
        if df is None or len(df) == 0:
            logger.warning("No usia data to insert")
            return 0
        
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO data_usia
            (conversion_id, holding, kode_perusahaan, periode, 
             kelompok, kelompok_jabatan, kategori_jabatan, kategori, jumlah)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        data = [
            (
                conversion_id,
                row.get('holding', ''),
                row['kode_perusahaan'],
                row['periode'],
                row['kelompok'],
                row['kelompok_jabatan'],
                row['kategori_jabatan'],
                row['kategori'],
                row['jumlah']
            )
            for _, row in df.iterrows()
        ]
        
        cursor.executemany(sql, data)
        conn.commit()
        rows_inserted = cursor.rowcount
        cursor.close()
        
        logger.info(f"✅ Inserted {rows_inserted} rows into data_usia")
        
        return rows_inserted
    
    @staticmethod
    def get_by_conversion_id(conn, conversion_id: int) -> pd.DataFrame:
        """Get usia data by conversion_id"""
        query = """
            SELECT
                holding, kode_perusahaan, periode, kelompok,
                kelompok_jabatan, kategori_jabatan, kategori, jumlah
            FROM data_usia
            WHERE conversion_id = ?
            ORDER BY kode_perusahaan, kelompok_jabatan
        """
        
        df = pd.read_sql(query, conn, params=(conversion_id,))
        logger.info(f"Loaded {len(df)} rows from data_usia")
        
        return df


# ============================================================================
# MODEL: DATA UNIT KERJA
# ============================================================================

class DataUnitKerja:
    """Model untuk table data_unit_kerja"""
    
    @staticmethod
    def insert_bulk(conn, conversion_id: int, df: pd.DataFrame) -> int:
        """Bulk insert unit kerja data"""
        if df is None or len(df) == 0:
            logger.warning("No unit kerja data to insert")
            return 0
        
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO data_unit_kerja
            (conversion_id, holding, kode_perusahaan, periode, 
             kelompok, kelompok_jabatan, kategori_jabatan, kategori, jumlah)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        data = [
            (
                conversion_id,
                row.get('holding', ''),
                row['kode_perusahaan'],
                row['periode'],
                row['kelompok'],
                row['kelompok_jabatan'],
                row['kategori_jabatan'],
                row['kategori'],
                row['jumlah']
            )
            for _, row in df.iterrows()
        ]
        
        cursor.executemany(sql, data)
        conn.commit()
        rows_inserted = cursor.rowcount
        cursor.close()
        
        logger.info(f"✅ Inserted {rows_inserted} rows into data_unit_kerja")
        
        return rows_inserted
    
    @staticmethod
    def get_by_conversion_id(conn, conversion_id: int) -> pd.DataFrame:
        """Get unit kerja data by conversion_id"""
        query = """
            SELECT
                holding, kode_perusahaan, periode, kelompok,
                kelompok_jabatan, kategori_jabatan, kategori, jumlah
            FROM data_unit_kerja
            WHERE conversion_id = ?
            ORDER BY kode_perusahaan, kelompok_jabatan
        """
        
        df = pd.read_sql(query, conn, params=(conversion_id,))
        logger.info(f"Loaded {len(df)} rows from data_unit_kerja")
        
        return df


# ============================================================================
# MODEL: DATA TREN
# ============================================================================

class DataTren:
    """Model untuk table data_tren"""
    
    @staticmethod
    def insert_bulk(conn, conversion_id: int, df: pd.DataFrame) -> int:
        """Bulk insert tren data"""
        if df is None or len(df) == 0:
            logger.warning("No tren data to insert")
            return 0
        
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO data_tren
            (conversion_id, periode, nama_perusahaan, kategori, jumlah)
            VALUES (?, ?, ?, ?, ?)
        """
        
        data = [
            (
                conversion_id,
                row['periode'],
                row['nama_perusahaan'],
                row['kategori'],
                row['jumlah']
            )
            for _, row in df.iterrows()
        ]
        
        cursor.executemany(sql, data)
        conn.commit()
        rows_inserted = cursor.rowcount
        cursor.close()
        
        logger.info(f"✅ Inserted {rows_inserted} rows into data_tren")
        
        return rows_inserted
    
    @staticmethod
    def get_by_conversion_id(conn, conversion_id: int) -> pd.DataFrame:
        """Get tren data by conversion_id"""
        query = """
            SELECT
                periode, nama_perusahaan, kategori, jumlah
            FROM data_tren
            WHERE conversion_id = ?
            ORDER BY nama_perusahaan
        """
        
        df = pd.read_sql(query, conn, params=(conversion_id,))
        logger.info(f"Loaded {len(df)} rows from data_tren")
        
        return df


# ============================================================================
# MODEL: CONVERSION FILES
# ============================================================================

class DemografiOutputFiles:
    """Model untuk table conversion_files"""
    
    @staticmethod
    def insert(
        conn,
        conversion_id: int,
        filename: str,
        file_content: bytes,
        file_size: int,
        mime_type: str = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ) -> int:
        """Save file to database"""
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversion_files
            (conversion_id, filename, file_content, file_size, mime_type)
            VALUES (?, ?, ?, ?, ?)
        """, (
            conversion_id,
            filename,
            file_content,
            file_size,
            mime_type
        ))
        
        conn.commit()
        
        cursor.execute("SELECT @@IDENTITY")
        file_id = cursor.fetchone()[0]
        cursor.close()
        
        logger.info(f"✅ File saved to database (ID: {file_id}, Size: {file_size:,} bytes)")
        
        return file_id
    
    @staticmethod
    def get_file_content(conn, conversion_id: int) -> Optional[tuple]:
        """Get file from database"""
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT filename, file_content, mime_type
            FROM conversion_files
            WHERE conversion_id = ?
        """, (conversion_id,))
        
        row = cursor.fetchone()
        cursor.close()
        
        if row:
            return (row.filename, row.file_content, row.mime_type)
        return None
    
    @staticmethod
    def check_exists(conn, conversion_id: int) -> bool:
        """Check if file exists in database"""
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM conversion_files
            WHERE conversion_id = ?
        """, (conversion_id,))
        
        count = cursor.fetchone()[0]
        cursor.close()
        
        return count > 0


# ============================================================================
# HELPER FUNCTIONS - CRITICAL FOR VISUALIZATION & DASHBOARD!
# ============================================================================

def get_all_data_by_conversion_id(conn, conversion_id: int) -> Dict[str, pd.DataFrame]:
    """
    Get ALL dimension data for specific conversion_id
    PENTING: Dipakai untuk view data & visualize by conversion_id
    
    Returns:
        dict: {'gender': df, 'pendidikan': df, 'usia': df, 'unit_kerja': df, 'tren': df}
    """
    return {
        'gender': DataGender.get_by_conversion_id(conn, conversion_id),
        'pendidikan': DataPendidikan.get_by_conversion_id(conn, conversion_id),
        'usia': DataUsia.get_by_conversion_id(conn, conversion_id),
        'unit_kerja': DataUnitKerja.get_by_conversion_id(conn, conversion_id),
        'tren': DataTren.get_by_conversion_id(conn, conversion_id)
    }


def get_latest_data_by_periode(conn, periode: str, dimensi: str = None) -> Dict[str, pd.DataFrame]:
    """
    🔥 CRITICAL FUNCTION FOR DASHBOARD! 🔥
    Get LATEST data for specific periode (YYYY-MM or YYYY-MM-DD)
    
    If multiple uploads exist for the same month, return the most recent one
    This is THE CORE function for monthly dashboard monitoring!
    
    Args:
        conn: Database connection
        periode: Periode string (YYYY-MM-DD format)
        dimensi: Optional specific dimensi
    
    Returns:
        dict: {'gender': df, 'pendidikan': df, 'usia': df, 'unit_kerja': df, 'tren': df}
    
    Example:
        For January 2026, if there are 5 uploads:
        - Upload 1: 2026-01-12 10:00 (created_at)
        - Upload 2: 2026-01-12 14:00 (created_at)
        - Upload 3: 2026-01-20 10:00 (created_at) ← This will be selected (latest)
        
        System will return data from Upload 3
    """
    
    tables = {
        'gender': 'data_gender',
        'pendidikan': 'data_pendidikan',
        'usia': 'data_usia',
        'unit_kerja': 'data_unit_kerja',
        'tren': 'data_tren'
    }
    
    # Filter jika dimensi specific
    if dimensi:
        if dimensi not in tables:
            raise ValueError(f"Invalid dimensi: {dimensi}")
        tables = {dimensi: tables[dimensi]}
    
    results = {}
    
    # Extract YYYY-MM dari periode
    year_month = periode[:7]  # Get YYYY-MM
    logger.info(f"📅 Querying LATEST data for year-month: {year_month}")
    
    cursor = conn.cursor()
    
    # Step 1: Get conversion_id yang paling baru untuk bulan ini
    cursor.execute("""
        SELECT TOP 1 t.conversion_id, ch.created_at
        FROM data_tren t
        INNER JOIN conversion_history ch ON t.conversion_id = ch.id
        WHERE FORMAT(t.periode, 'yyyy-MM') = ?
        ORDER BY ch.created_at DESC
    """, (year_month,))
    
    result = cursor.fetchone()
    
    if not result:
        logger.warning(f"⚠️  No data found for {year_month}")
        # Return empty DataFrames
        for dim in tables.keys():
            results[dim] = pd.DataFrame()
        cursor.close()
        return results
    
    latest_conversion_id = result[0]
    latest_created_at = result[1]
    
    logger.info(f"✅ Found latest conversion_id: {latest_conversion_id} (uploaded at: {latest_created_at})")
    
    # Step 2: Get data untuk conversion_id tersebut
    for dim, table in tables.items():
        try:
            if table == "data_tren":
                query = f"""
                    SELECT
                        periode,
                        nama_perusahaan,
                        kategori,
                        jumlah
                    FROM {table}
                    WHERE conversion_id = ?
                    ORDER BY nama_perusahaan
                """
            else:
                query = f"""
                    SELECT
                        holding,
                        kode_perusahaan,
                        periode,
                        kelompok,
                        kelompok_jabatan,
                        kategori_jabatan,
                        kategori,
                        jumlah
                    FROM {table}
                    WHERE conversion_id = ?
                    ORDER BY kode_perusahaan, kelompok_jabatan
                """

            df = pd.read_sql(query, conn, params=(latest_conversion_id,))
            results[dim] = df
            
            if not df.empty:
                logger.info(f"✅ {table}: {len(df)} rows (conversion_id: {latest_conversion_id})")
            else:
                logger.warning(f"⚠️  {table}: No data (conversion_id: {latest_conversion_id})")
                
        except Exception as e:
            logger.error(f"❌ Error loading {table}: {e}")
            results[dim] = pd.DataFrame()
    
    cursor.close()
    
    return results


def get_data_statistics(conn) -> Dict:
    """Get statistics dari semua data tables"""
    cursor = conn.cursor()
    
    stats = {}
    
    tables = ['data_gender', 'data_pendidikan', 'data_usia', 
             'data_unit_kerja', 'data_tren']
    
    for table in tables:
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total_rows,
                ISNULL(SUM(jumlah), 0) as total_karyawan
            FROM {table}
        """)
        
        row = cursor.fetchone()
        dimensi = table.replace('data_', '')
        
        stats[dimensi] = {
            'total_rows': row.total_rows or 0,
            'total_karyawan': row.total_karyawan or 0
        }
    
    cursor.close()
    
    return stats

def to_chart_data(df: pd.DataFrame) -> Dict[str, list]:
    """
    Convert aggregated dataframe to chart.js friendly format
    Expect columns: kategori, jumlah
    """
    if df is None or df.empty:
        return {"labels": [], "values": []}

    grouped = (
        df.groupby('kategori', as_index=False)['jumlah']
          .sum()
          .sort_values('kategori')
    )

    return {
        "labels": grouped['kategori'].tolist(),
        "values": grouped['jumlah'].tolist()
    }


def insert_all_conversion_data(
    conn,
    conversion_id: int,
    dataframes: Dict[str, pd.DataFrame]
) -> Dict[str, int]:
    """
    Insert ALL conversion data (all dimensions) in one call
    
    Args:
        conn: Database connection
        conversion_id: ID from conversion_history
        dataframes: Dict {'gender': df, 'pendidikan': df, ...}
    
    Returns:
        dict: {'gender': rows_inserted, 'pendidikan': rows_inserted, ...}
    """
    results = {}
    
    dimension_models = {
        'gender': DataGender,
        'pendidikan': DataPendidikan,
        'usia': DataUsia,
        'unit_kerja': DataUnitKerja,
        'tren': DataTren
    }
    
    for dimensi, df in dataframes.items():
        if dimensi in dimension_models and df is not None and len(df) > 0:
            try:
                model = dimension_models[dimensi]
                rows = model.insert_bulk(conn, conversion_id, df)
                results[dimensi] = rows
            except Exception as e:
                logger.error(f"Error inserting {dimensi} data: {e}")
                results[dimensi] = 0
        else:
            results[dimensi] = 0
    
    return results