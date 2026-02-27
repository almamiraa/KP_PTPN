"""
database/models/cost.py
=======================
Database models untuk modul Cost
Tables: upload_history, cost_data, output_files
"""

import logging

logger = logging.getLogger(__name__)


# ============================================================================
# SQL TABLE CREATION QUERIES
# ============================================================================

CREATE_COST_TABLES = {
    'upload_history': """
        CREATE TABLE upload_history (
            id INT IDENTITY(1,1) PRIMARY KEY,
            created_at DATETIME NOT NULL DEFAULT GETDATE(),
            original_filename NVARCHAR(255) NOT NULL,
            output_filename NVARCHAR(255),
            periode DATE NOT NULL,
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
        
        CREATE INDEX idx_periode ON upload_history(periode);
        CREATE INDEX idx_status ON upload_history(status);
        CREATE INDEX idx_created_at ON upload_history(created_at DESC);
        CREATE INDEX idx_status_coverage ON upload_history(status, company_coverage_percent);
    """,
    
    'cost_data': """
        CREATE TABLE cost_data (
            id BIGINT IDENTITY(1,1) PRIMARY KEY,
            upload_id INT NOT NULL,
            holding NVARCHAR(50) NOT NULL,
            kode_perusahaan NVARCHAR(10) NOT NULL,
            periode DATE NOT NULL,
            payment_type NVARCHAR(20) NOT NULL,
            cost_description NVARCHAR(255) NOT NULL,
            real_bulan_ini DECIMAL(18,2),
            rkap_bulan_ini DECIMAL(18,2),
            real_sd DECIMAL(18,2),
            rkap_sd DECIMAL(18,2),
            created_at DATETIME DEFAULT GETDATE(),
            FOREIGN KEY (upload_id) REFERENCES upload_history(id) ON DELETE CASCADE
        );
        
        CREATE INDEX idx_cost_data_upload ON cost_data(upload_id);
        CREATE INDEX idx_cost_data_periode ON cost_data(periode);
        CREATE INDEX idx_cost_data_holding ON cost_data(holding);
        CREATE INDEX idx_cost_data_payment_type ON cost_data(payment_type);
    """,
    
    'output_files': """
        CREATE TABLE output_files (
            id INT IDENTITY(1,1) PRIMARY KEY,
            upload_id INT NOT NULL,
            filename NVARCHAR(255) NOT NULL,
            file_content VARBINARY(MAX) NOT NULL,
            file_size_kb DECIMAL(10,2),
            mime_type NVARCHAR(100)
                DEFAULT 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            created_at DATETIME DEFAULT GETDATE(),
            FOREIGN KEY (upload_id) REFERENCES upload_history(id) ON DELETE CASCADE
        );
        
        CREATE INDEX idx_output_files_upload ON output_files(upload_id);
    """
}

DROP_COST_TABLES = """
IF OBJECT_ID('cost_data', 'U') IS NOT NULL DROP TABLE cost_data;
IF OBJECT_ID('output_files', 'U') IS NOT NULL DROP TABLE output_files;
IF OBJECT_ID('upload_history', 'U') IS NOT NULL DROP TABLE upload_history;
"""


# ============================================================================
# MODEL: UPLOAD HISTORY
# ============================================================================

class CostUploadHistory:
    """Model untuk upload history table"""
    
    @staticmethod
    def insert(conn, original_filename: str, output_filename: str, periode: str,
               perusahaan: str, total_rows: int, duration: float, status: str = 'success',
               error_message: str = None, 
               total_companies: int = None,
               processed_companies: int = None,
               missing_companies: str = None,
               validation_warnings: str = None,
               company_coverage_percent: float = None) -> int:
        """
        Insert upload history record with validation data
        
        Args:
            conn: Database connection
            original_filename: Original uploaded filename
            output_filename: Processed output filename
            periode: Period (YYYY-MM format)
            perusahaan: Company info
            total_rows: Total rows processed
            duration: Processing duration in seconds
            status: Upload status (success/warning/failed)
            error_message: Error message if failed
            total_companies: Expected total companies
            processed_companies: Actually processed companies
            missing_companies: JSON list of missing company codes
            validation_warnings: JSON list of validation warnings
            company_coverage_percent: Coverage percentage
        
        Returns:
            upload_id
        """
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO upload_history (
                original_filename, output_filename, periode, perusahaan,
                total_rows, duration, status, error_message,
                total_companies, processed_companies, missing_companies,
                validation_warnings, company_coverage_percent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            original_filename, output_filename, periode, perusahaan,
            total_rows, duration, status, error_message,
            total_companies, processed_companies, missing_companies,
            validation_warnings, company_coverage_percent
        ))
        
        conn.commit()
        
        # Get last inserted ID
        cursor.execute("SELECT @@IDENTITY")
        upload_id = cursor.fetchone()[0]
        cursor.close()
        
        return upload_id
    
    @staticmethod
    def get_all(conn, limit: int = None) -> list:
        """
        Get all upload history records with validation data
        
        Args:
            conn: Database connection
            limit: Optional limit for number of records (default: all)
        
        Returns:
            List of upload history records
        """
        cursor = conn.cursor()
        
        # Build query with optional limit
        if limit:
            query = f"""
                SELECT TOP {limit}
                    uh.id,
                    uh.created_at,
                    uh.original_filename,
                    uh.output_filename,
                    uh.periode,
                    uh.perusahaan,
                    uh.total_rows,
                    uh.duration,
                    uh.status,
                    uh.error_message,
                    uh.total_companies,
                    uh.processed_companies,
                    uh.missing_companies,
                    uh.validation_warnings,
                    uh.company_coverage_percent,
                    CASE WHEN [of].id IS NOT NULL THEN 1 ELSE 0 END as file_exists
                FROM upload_history uh
                LEFT JOIN output_files [of] ON uh.id = [of].upload_id
                ORDER BY uh.created_at DESC
            """
        else:
            query = """
                SELECT 
                    uh.id,
                    uh.created_at,
                    uh.original_filename,
                    uh.output_filename,
                    uh.periode,
                    uh.perusahaan,
                    uh.total_rows,
                    uh.duration,
                    uh.status,
                    uh.error_message,
                    uh.total_companies,
                    uh.processed_companies,
                    uh.missing_companies,
                    uh.validation_warnings,
                    uh.company_coverage_percent,
                    CASE WHEN [of].id IS NOT NULL THEN 1 ELSE 0 END as file_exists
                FROM upload_history uh
                LEFT JOIN output_files [of] ON uh.id = [of].upload_id
                ORDER BY uh.created_at DESC
            """
        
        cursor.execute(query)
        
        columns = [column[0] for column in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            results.append(row_dict)
        
        cursor.close()
        return results
    
    @staticmethod
    def get_by_id(conn, upload_id: int) -> dict:
       
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                uh.id,
                uh.created_at,
                uh.original_filename,
                uh.output_filename,
                uh.periode,
                uh.perusahaan,
                uh.total_rows,
                uh.duration,
                uh.status,
                uh.error_message,
                uh.total_companies,
                uh.processed_companies,
                uh.missing_companies,
                uh.validation_warnings,
                uh.company_coverage_percent,
                CASE WHEN [of].id IS NOT NULL THEN 1 ELSE 0 END as file_exists
            FROM upload_history uh
            LEFT JOIN output_files [of] ON uh.id = [of].upload_id
            WHERE uh.id = ?
        """, (upload_id,))
        
        row = cursor.fetchone()
        
        if row:
            columns = [column[0] for column in cursor.description]
            result = dict(zip(columns, row))
            cursor.close()
            return result
        
        cursor.close()
        return None

    @staticmethod
    def delete(conn, upload_id: int) -> bool:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM upload_history WHERE id = ?",
                (upload_id,)
            )
            conn.commit()
            cursor.close()
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Delete failed: {e}")
            return False

# ============================================================================
# MODEL: COST DATA
# ============================================================================

class CostData:
    """Model untuk table cost_data"""
    
    @staticmethod
    def insert_batch(conn, upload_id: int, data_list: list) -> int:
       
        if not data_list:
            logger.warning("No cost data to insert")
            return 0
        
        cursor = conn.cursor()
        
        insert_sql = """
            INSERT INTO cost_data 
            (upload_id, holding, kode_perusahaan, periode, payment_type, 
             cost_description, real_bulan_ini, rkap_bulan_ini, real_sd, rkap_sd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        for data in data_list:
            cursor.execute(insert_sql, (
                upload_id,
                data['holding'],
                data['kode_perusahaan'],
                data['periode'],
                data['payment_type'],
                data['cost_description'],
                data['REAL'],
                data['RKAP'],
                data['REAL_SD'],
                data['RKAP_SD']
            ))
        
        conn.commit()
        rows_inserted = cursor.rowcount
        cursor.close()
        
        logger.info(f"✅ Inserted {rows_inserted} rows into cost_data")
        
        return rows_inserted
    
    @staticmethod
    def get_by_upload_id(conn, upload_id: int, limit: int = 100) -> list:
        """Get cost data for specific upload (with limit for preview)"""
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT TOP ({limit})
                holding, kode_perusahaan, periode, payment_type,
                cost_description, real_bulan_ini, rkap_bulan_ini,
                real_sd, rkap_sd
            FROM cost_data
            WHERE upload_id = ?
            ORDER BY holding, kode_perusahaan, payment_type
        """, (upload_id,))
        
        results = cursor.fetchall()
        cursor.close()
        
        return [
            {
                'holding': row.holding,
                'kode_perusahaan': row.kode_perusahaan,
                'periode': row.periode,
                'payment_type': row.payment_type,
                'cost_description': row.cost_description,
                'REAL': float(row.real_bulan_ini) if row.real_bulan_ini else 0,
                'RKAP': float(row.rkap_bulan_ini) if row.rkap_bulan_ini else 0,
                'REAL_SD': float(row.real_sd) if row.real_sd else 0,
                'RKAP_SD': float(row.rkap_sd) if row.rkap_sd else 0
            }
            for row in results
        ]
    
    @staticmethod
    def get_by_upload_id_grouped(conn, upload_id: int) -> dict:
        """
        Get cost data grouped by holding and payment_type for detail view
        
        Returns:
            Dict with structure: {holding: {total_rows, columns, preview}}
        """
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                holding,
                payment_type,
                cost_description,
                periode,
                kode_perusahaan,
                SUM(real_bulan_ini) as real_bulan,
                SUM(rkap_bulan_ini) as rkap_bulan,
                SUM(real_sd) as real_sd,
                SUM(rkap_sd) as rkap_sd,
                COUNT(*) as row_count
            FROM cost_data
            WHERE upload_id = ?
            GROUP BY holding, payment_type, cost_description, periode, kode_perusahaan
            ORDER BY holding, payment_type, cost_description
        """, (upload_id,))
        
        results = cursor.fetchall()
        cursor.close()
        
        # Group by holding
        grouped_data = {}
        for row in results:
            holding = row.holding
            if holding not in grouped_data:
                grouped_data[holding] = {
                    'total_rows': 0,
                    'columns': ['holding', 'kode_perusahaan', 'periode', 'payment_type', 
                               'cost_description', 'real_bulan', 'rkap_bulan', 'real_sd', 'rkap_sd'],
                    'preview': []
                }
            
            grouped_data[holding]['total_rows'] += row.row_count
            grouped_data[holding]['preview'].append({
                'holding': row.holding,
                'kode_perusahaan': row.kode_perusahaan,
                'periode': row.periode,
                'payment_type': row.payment_type,
                'cost_description': row.cost_description,
                'real_bulan': float(row.real_bulan) if row.real_bulan else 0,
                'rkap_bulan': float(row.rkap_bulan) if row.rkap_bulan else 0,
                'real_sd': float(row.real_sd) if row.real_sd else 0,
                'rkap_sd': float(row.rkap_sd) if row.rkap_sd else 0
            })
        
        logger.info(f"Loaded cost data grouped by {len(grouped_data)} holdings")
        
        return grouped_data
    
    @staticmethod
    def get_dashboard_summary(conn, periode: str = None) -> dict:
       
        cursor = conn.cursor()
        
        # Build query with optional periode filter
        where_clause = "WHERE periode = ?" if periode else ""
        params = (periode,) if periode else ()
        
        # Total by holding
        cursor.execute(f"""
            SELECT 
                holding,
                SUM(real_bulan_ini) as total_real,
                SUM(rkap_bulan_ini) as total_rkap,
                SUM(real_sd) as total_real_sd,
                SUM(rkap_sd) as total_rkap_sd
            FROM cost_data
            {where_clause}
            GROUP BY holding
            ORDER BY holding
        """, params)
        
        by_holding = []
        for row in cursor.fetchall():
            by_holding.append({
                'holding': row.holding,
                'total_real': float(row.total_real) if row.total_real else 0,
                'total_rkap': float(row.total_rkap) if row.total_rkap else 0,
                'total_real_sd': float(row.total_real_sd) if row.total_real_sd else 0,
                'total_rkap_sd': float(row.total_rkap_sd) if row.total_rkap_sd else 0,
                'achievement': (float(row.total_real) / float(row.total_rkap) * 100) 
                    if row.total_rkap and row.total_rkap != 0 else 0
            })
        
        # Total by payment type
        cursor.execute(f"""
            SELECT 
                payment_type,
                SUM(real_bulan_ini) as total_real,
                SUM(rkap_bulan_ini) as total_rkap
            FROM cost_data
            {where_clause}
            GROUP BY payment_type
        """, params)
        
        by_payment_type = []
        for row in cursor.fetchall():
            by_payment_type.append({
                'payment_type': row.payment_type,
                'total_real': float(row.total_real) if row.total_real else 0,
                'total_rkap': float(row.total_rkap) if row.total_rkap else 0
            })
        
        # Top cost descriptions
        cursor.execute(f"""
            SELECT TOP 10
                cost_description,
                SUM(real_bulan_ini) as total_real,
                SUM(rkap_bulan_ini) as total_rkap
            FROM cost_data
            {where_clause}
            GROUP BY cost_description
            ORDER BY SUM(real_bulan_ini) DESC
        """, params)
        
        top_costs = []
        for row in cursor.fetchall():
            top_costs.append({
                'cost_description': row.cost_description,
                'total_real': float(row.total_real) if row.total_real else 0,
                'total_rkap': float(row.total_rkap) if row.total_rkap else 0
            })
        
        cursor.close()
        
        return {
            'by_holding': by_holding,
            'by_payment_type': by_payment_type,
            'top_costs': top_costs
        }
    
    @staticmethod
    def get_available_periodes(conn) -> list:
        """Get list of available periodes in database"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT periode
            FROM cost_data
            ORDER BY periode DESC
        """)
        
        periodes = [row.periode for row in cursor.fetchall()]
        cursor.close()
        
        return periodes
    
    @staticmethod
    def get_visualization_data(conn, upload_id: int) -> dict:
       
        cursor = conn.cursor()
        
        # 1. Total REAL vs RKAP (all 4 values)
        cursor.execute("""
            SELECT 
                SUM(real_bulan_ini) as total_real,
                SUM(rkap_bulan_ini) as total_rkap,
                SUM(real_sd) as total_real_sd,
                SUM(rkap_sd) as total_rkap_sd
            FROM cost_data
            WHERE upload_id = ?
        """, (upload_id,))
        
        totals = cursor.fetchone()
        
        # 2. By Holding - ✅ NOW WITH 4 VALUES
        cursor.execute("""
            SELECT 
                holding,
                SUM(real_bulan_ini) as total_real,
                SUM(rkap_bulan_ini) as total_rkap,
                SUM(real_sd) as total_real_sd,
                SUM(rkap_sd) as total_rkap_sd
            FROM cost_data
            WHERE upload_id = ?
            GROUP BY holding
            ORDER BY holding
        """, (upload_id,))
        
        by_holding = []
        for row in cursor.fetchall():
            by_holding.append({
                'holding': row.holding,
                'total_real': float(row.total_real) if row.total_real else 0,
                'total_rkap': float(row.total_rkap) if row.total_rkap else 0,
                'total_real_sd': float(row.total_real_sd) if row.total_real_sd else 0,
                'total_rkap_sd': float(row.total_rkap_sd) if row.total_rkap_sd else 0
            })
        
        # 3. By Payment Type - ✅ NOW WITH 4 VALUES
        cursor.execute("""
            SELECT 
                payment_type,
                SUM(real_bulan_ini) as total_real,
                SUM(rkap_bulan_ini) as total_rkap,
                SUM(real_sd) as total_real_sd,
                SUM(rkap_sd) as total_rkap_sd
            FROM cost_data
            WHERE upload_id = ?
            GROUP BY payment_type
            ORDER BY payment_type
        """, (upload_id,))
        
        by_payment = []
        for row in cursor.fetchall():
            by_payment.append({
                'payment_type': row.payment_type,
                'total_real': float(row.total_real) if row.total_real else 0,
                'total_rkap': float(row.total_rkap) if row.total_rkap else 0,
                'total_real_sd': float(row.total_real_sd) if row.total_real_sd else 0,
                'total_rkap_sd': float(row.total_rkap_sd) if row.total_rkap_sd else 0
            })
        
        # 4. Top 10 Costs - ✅ NOW WITH 4 VALUES
        cursor.execute("""
            SELECT TOP 10
                cost_description,
                SUM(real_bulan_ini) as total_real,
                SUM(rkap_bulan_ini) as total_rkap,
                SUM(real_sd) as total_real_sd,
                SUM(rkap_sd) as total_rkap_sd
            FROM cost_data
            WHERE upload_id = ?
            GROUP BY cost_description
            ORDER BY SUM(real_bulan_ini) DESC
        """, (upload_id,))
        
        top_costs = []
        for row in cursor.fetchall():
            top_costs.append({
                'cost_description': row.cost_description,
                'total_real': float(row.total_real) if row.total_real else 0,
                'total_rkap': float(row.total_rkap) if row.total_rkap else 0,
                'total_real_sd': float(row.total_real_sd) if row.total_real_sd else 0,
                'total_rkap_sd': float(row.total_rkap_sd) if row.total_rkap_sd else 0
            })
        
        cursor.close()
        
        return {
            'totals': {
                'total_real': float(totals.total_real) if totals.total_real else 0,
                'total_rkap': float(totals.total_rkap) if totals.total_rkap else 0,
                'total_real_sd': float(totals.total_real_sd) if totals.total_real_sd else 0,
                'total_rkap_sd': float(totals.total_rkap_sd) if totals.total_rkap_sd else 0
            },
            'by_holding': by_holding,
            'by_payment': by_payment,
            'top_costs': top_costs
            }
    
    @staticmethod
    def get_available_years(conn) -> list:
        """Get list of available years from cost data"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT YEAR(periode) as year
            FROM cost_data
            WHERE periode IS NOT NULL AND periode != ''
            ORDER BY year DESC
        """)
        
        years = [int(row.year) for row in cursor.fetchall()]
        cursor.close()
        
        return years
    
    @staticmethod
    def get_yearly_dashboard_data(conn, year: int) -> dict:
      
        cursor = conn.cursor()
        year_str = str(year)
        
        # ========== 1. TOTALS ==========
        cursor.execute("""
            WITH LatestUploads AS (
                SELECT periode, MAX(upload_id) as latest_upload_id
                FROM cost_data
                WHERE YEAR(periode) = ?
                GROUP BY periode
            )
            SELECT 
                SUM(cd.real_bulan_ini) as total_real,
                SUM(cd.rkap_bulan_ini) as total_rkap,
                SUM(cd.real_sd) as total_real_sd,
                SUM(cd.rkap_sd) as total_rkap_sd
            FROM cost_data cd
            INNER JOIN LatestUploads lu 
                ON cd.periode = lu.periode 
                AND cd.upload_id = lu.latest_upload_id
        """, (year_str,))
        
        totals_row = cursor.fetchone()
        
        if not totals_row or not totals_row[0]:
            cursor.close()
            logger.warning(f"No data found for year {year}")
            return None
        
        totals = {
            'total_real': float(totals_row[0]) if totals_row[0] else 0,
            'total_rkap': float(totals_row[1]) if totals_row[1] else 0,
            'total_real_sd': float(totals_row[2]) if totals_row[2] else 0,
            'total_rkap_sd': float(totals_row[3]) if totals_row[3] else 0
        }
        
        # ========== 2. MONTHLY TREND ==========
        cursor.execute("""
            WITH LatestUploadPerMonth AS (
                SELECT 
                    MONTH(periode) as month_num,
                    MAX(upload_id) as latest_upload_id
                FROM cost_data
                WHERE YEAR(periode) = ?
                GROUP BY MONTH(periode)
            )
            SELECT 
                lum.month_num,
                SUM(cd.real_bulan_ini) as monthly_real,
                SUM(cd.rkap_bulan_ini) as monthly_rkap,
                SUM(cd.real_sd) as monthly_real_sd,
                SUM(cd.rkap_sd) as monthly_rkap_sd
            FROM cost_data cd
            INNER JOIN LatestUploadPerMonth lum 
                ON MONTH(cd.periode) = lum.month_num
                AND cd.upload_id = lum.latest_upload_id
            GROUP BY lum.month_num
            ORDER BY lum.month_num
        """, (year,)) 

        monthly_data = cursor.fetchall()

        # Format month labels
        month_abbr = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        monthly = {
            'labels': [],
            'real_values': [],
            'real_sd_values': [],
            'rkap_values': [],
            'rkap_sd_values': []
        }

        for row in monthly_data:
            month_num = int(row[0])  # month_num
            monthly['labels'].append(month_abbr[month_num - 1])
            monthly['real_values'].append(float(row[1]) if row[1] else 0)
            monthly['rkap_values'].append(float(row[2]) if row[2] else 0)
            monthly['real_sd_values'].append(float(row[3]) if row[3] else 0)
            monthly['rkap_sd_values'].append(float(row[4]) if row[4] else 0)
            
            # ========== 3. BY HOLDING ==========
        cursor.execute("""
                WITH LatestUploads AS (
                    SELECT periode, MAX(upload_id) as latest_upload_id
                    FROM cost_data
                    WHERE YEAR(periode) = ?
                    GROUP BY periode
                )
                SELECT 
                    cd.holding,
                    SUM(cd.real_bulan_ini) as total_real,
                    SUM(cd.rkap_bulan_ini) as total_rkap,
                    SUM(cd.real_sd) as total_real_sd,
                    SUM(cd.rkap_sd) as total_rkap_sd
                FROM cost_data cd
                INNER JOIN LatestUploads lu 
                    ON cd.periode = lu.periode 
                    AND cd.upload_id = lu.latest_upload_id
                GROUP BY cd.holding
                ORDER BY cd.holding
            """, (year_str,))
            
        holdings_data = cursor.fetchall()
            
        holdings = {
                'labels': [],
                'real_values': [],
                'real_sd_values': [],
                'rkap_values': [],
                'rkap_sd_values': []
            }
            
        for row in holdings_data:
                holdings['labels'].append(row[0])
                holdings['real_values'].append(float(row[1]) if row[1] else 0)
                holdings['rkap_values'].append(float(row[2]) if row[2] else 0)
                holdings['real_sd_values'].append(float(row[3]) if row[3] else 0)
                holdings['rkap_sd_values'].append(float(row[4]) if row[4] else 0)
        
        # ========== 4. BY PAYMENT TYPE ==========
        cursor.execute("""
            WITH LatestUploads AS (
                SELECT periode, MAX(upload_id) as latest_upload_id
                FROM cost_data
                WHERE YEAR(periode) = ?
                GROUP BY periode
            )
            SELECT 
                cd.payment_type,
                SUM(cd.real_bulan_ini) as total_real,
                SUM(cd.rkap_bulan_ini) as total_rkap,
                SUM(cd.real_sd) as total_real_sd,
                SUM(cd.rkap_sd) as total_rkap_sd
            FROM cost_data cd
            INNER JOIN LatestUploads lu 
                ON cd.periode = lu.periode 
                AND cd.upload_id = lu.latest_upload_id
            GROUP BY cd.payment_type
            ORDER BY SUM(cd.real_bulan_ini) DESC
        """, (year_str,))
        
        payment_data = cursor.fetchall()
        
        payment_types = {
            'labels': [],
            'real_values': [],
            'real_sd_values': [],
            'rkap_values': [],
            'rkap_sd_values': []
        }
        
        for row in payment_data:
            payment_types['labels'].append(row[0])
            payment_types['real_values'].append(float(row[1]) if row[1] else 0)
            payment_types['rkap_values'].append(float(row[2]) if row[2] else 0)
            payment_types['real_sd_values'].append(float(row[3]) if row[3] else 0)
            payment_types['rkap_sd_values'].append(float(row[4]) if row[4] else 0)
        
        # ========== 5. TOP 10 COSTS ==========
        cursor.execute("""
            WITH LatestUploads AS (
                SELECT periode, MAX(upload_id) as latest_upload_id
                FROM cost_data
                WHERE YEAR(periode) = ?
                GROUP BY periode
            )
            SELECT TOP 10
                cd.cost_description,
                SUM(cd.real_bulan_ini) as total_real
            FROM cost_data cd
            INNER JOIN LatestUploads lu 
                ON cd.periode = lu.periode 
                AND cd.upload_id = lu.latest_upload_id
            GROUP BY cd.cost_description
            ORDER BY SUM(cd.real_bulan_ini) DESC
        """, (year_str,))
        
        top_data = cursor.fetchall()
        
        top_costs = {
            'labels': [row[0] for row in top_data],
            'values': [float(row[1]) if row[1] else 0 for row in top_data]
        }
        
        cursor.close()
        
        logger.info(f"✅ Loaded yearly data for {year}: {len(monthly['labels'])} months, {len(holdings['labels'])} holdings")
        
        return {
            'totals': totals,
            'monthly': monthly,
            'holdings': holdings,
            'payment_types': payment_types,
            'top_costs': top_costs
        }

    @staticmethod
    def get_payment_type_summary(conn, year: int) -> list:
        """Get summary by payment type for a year"""
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                payment_type,
                SUM(real_bulan_ini) as total_real,
                SUM(rkap_bulan_ini) as total_rkap
            FROM cost_data
            WHERE YEAR(periode) = ?
            GROUP BY payment_type
            ORDER BY SUM(real_bulan_ini) DESC
        """, (year,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'payment_type': row.payment_type,
                'total_real': float(row.total_real) if row.total_real else 0,
                'total_rkap': float(row.total_rkap) if row.total_rkap else 0
            })
        
        cursor.close()
        return results
    

    @staticmethod
    def get_top_costs(conn, year: int, limit: int = 10) -> list:
        """Get top N cost descriptions by REAL value"""
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT TOP ({limit})
                cost_description,
                SUM(real_bulan_ini) as total_real,
                SUM(rkap_bulan_ini) as total_rkap
            FROM cost_data
            WHERE YEAR(periode) = ?
            GROUP BY cost_description
            ORDER BY SUM(real_bulan_ini) DESC
        """, (year,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'cost_description': row.cost_description,
                'total_real': float(row.total_real) if row.total_real else 0,
                'total_rkap': float(row.total_rkap) if row.total_rkap else 0
            })
        
        cursor.close()
        return results

class CostOutputFiles:
    """Model untuk table output_files"""
    
    @staticmethod
    def insert(
        conn,
        upload_id: int,
        filename: str,
        file_content: bytes,
        file_size_kb: float,
        mime_type: str = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ) -> int:
        """Save file to database"""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO output_files
            (upload_id, filename, file_content, file_size_kb, mime_type)
            VALUES (?, ?, ?, ?, ?)
        """, (
            upload_id,
            filename,
            file_content,
            file_size_kb,
            mime_type
        ))
        conn.commit()
        
        cursor.execute("SELECT @@IDENTITY")
        file_id = cursor.fetchone()[0]
        cursor.close()
        
        logger.info(f"✅ File saved to database (ID: {file_id}, Size: {file_size_kb:.2f} KB)")
        
        return file_id
    
    @staticmethod
    def get_file_content(conn, upload_id: int) -> tuple:
        """
        Get file from database
        
        Returns:
            tuple: (filename, file_content, mime_type) or None
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT filename, file_content, mime_type FROM output_files WHERE upload_id = ?",
            (upload_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        
        if row:
            return row.filename, row.file_content, row.mime_type
        return None
    
    @staticmethod
    def get_by_upload_id(conn, upload_id: int) -> list:
        """Get file metadata by upload_id"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, upload_id, filename, file_size_kb, mime_type
            FROM output_files
            WHERE upload_id = ?
        """, (upload_id,))
        
        rows = cursor.fetchall()
        cursor.close()
        
        return [
            {
                'id': row.id,
                'upload_id': row.upload_id,
                'filename': row.filename,
                'file_size_kb': row.file_size_kb,
                'mime_type': row.mime_type
            }
            for row in rows
        ]
    
    @staticmethod
    def check_exists(conn, upload_id: int) -> bool:
        """Check if file exists in database"""
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM output_files WHERE upload_id = ?", (upload_id,))
        count = cursor.fetchone()[0]
        cursor.close()
        
        return count > 0