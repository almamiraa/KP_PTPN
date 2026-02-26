"""
column_detector.py
==================
Module untuk mendeteksi kolom REAL/RKAP berdasarkan periode input user
"""

from typing import Dict, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ColumnDetector:  
    def __init__(self, excel_reader, sheet):
        self.reader = excel_reader
        self.sheet = sheet
        self.period_headers = None
        self.type_headers = None
        self.detected_columns = None
    
    def detect_columns(self, target_period: str) -> Dict[str, int]:
        logger.info(f"Starting column detection for period: {target_period}")
        
        # 1. Parse periode target dari user
        target_year, target_month = self._parse_period(target_period)
        logger.info(f"Target: Year={target_year}, Month={target_month}")
        
        # 2. Parse SEMUA headers dari Excel (no validation yet!)
        try:
            header_data = self.reader.parse_period_header(self.sheet)
            all_periods = header_data.get('all_periods', [])
            self.type_headers = self.reader.parse_type_header(self.sheet)
        except Exception as e:
            error_msg = f"Failed to parse Excel headers: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Found {len(all_periods)} period headers in Excel")
        
        # 3. Filter: Cari periode yang MATCH dengan target
        matching_bulan = None
        matching_sd = None
        
        for period in all_periods:
            is_match = (period['year'] == target_year and period['month'] == target_month)
            
            if is_match:
                if period['type'] == 'bulan' and not matching_bulan:
                    matching_bulan = period
                    logger.info(f"✓ Found matching 'bulan': '{period['text']}' at cols {period['start_col']}-{period['end_col']}")
                elif period['type'] == 's.d.' and not matching_sd:
                    matching_sd = period
                    logger.info(f"✓ Found matching 's.d.': '{period['text']}' at cols {period['start_col']}-{period['end_col']}")
        
        # 4. Validasi: Apakah periode yang dicari ada?
        if not matching_bulan:
            available = [(p['year'], p['month'], p['text']) for p in all_periods if p['type'] == 'bulan']
            logger.error(f"Available periods: {available}")
            raise ValueError(
                f"Period {target_year}-{target_month:02d} not found in Excel! "
                f"Available: {', '.join([f'{y}-{m:02d}' for y, m, _ in available])}"
            )
        
        # Store hasil
        self.period_headers = {
            'bulan': matching_bulan,
            's.d.': matching_sd
        }
        
        # 5. Map kolom berdasarkan periode yang match
        columns = self._map_columns()
        
        # 6. Validasi semua kolom terdeteksi
        self._validate_columns(columns)
        
        # 7. Log hasil
        self._log_detection_result(columns, target_period)
        
        self.detected_columns = columns
        return columns
    
    def _parse_period(self, period: str) -> Tuple[int, int]:
        try:
            dt = datetime.strptime(period, '%Y-%m')
            return dt.year, dt.month
        except ValueError:
            raise ValueError(
                f"Invalid period format: '{period}'. "
                f"Expected format: 'YYYY-MM' (e.g., '2024-12')"
            )
    
    def _map_columns(self) -> Dict[str, Optional[int]]:
        columns = {}
        
        # Ambil range kolom untuk "Bulan Ini" (periode bulanan)
        bulan_header = self.period_headers.get('bulan', {})
        bulan_cols = self._get_columns_in_range(
            bulan_header['start_col'],
            bulan_header['end_col']
        )
        
        columns['REAL_BULAN_INI'] = bulan_cols.get('REAL')
        columns['RKAP_BULAN_INI'] = bulan_cols.get('RKAP')
        
        logger.info(f"Bulan ini columns: REAL={columns['REAL_BULAN_INI']}, "
                   f"RKAP={columns['RKAP_BULAN_INI']}")
        
        # Ambil range kolom untuk "s.d." (kumulatif)
        sd_header = self.period_headers.get('s.d.')
        
        if sd_header:
            sd_cols = self._get_columns_in_range(
                sd_header['start_col'],
                sd_header['end_col']
            )
            
            columns['REAL_SD'] = sd_cols.get('REAL')
            columns['RKAP_SD'] = sd_cols.get('RKAP')
            
            logger.info(f"S.d. columns: REAL={columns['REAL_SD']}, "
                       f"RKAP={columns['RKAP_SD']}")
        else:
            # Jika s.d. tidak ada, cari kolom REAL/RKAP berikutnya setelah bulan
            logger.warning("s.d. header not found, trying to detect next REAL/RKAP columns")
            
            next_real = None
            next_rkap = None
            
            # Cari kolom setelah bulan_header.end_col
            for col in range(bulan_header['end_col'] + 1, max(self.type_headers.keys()) + 1):
                type_name = self.type_headers.get(col)
                if type_name == 'REAL' and next_real is None:
                    next_real = col
                elif type_name == 'RKAP' and next_rkap is None:
                    next_rkap = col
                
                if next_real and next_rkap:
                    break
            
            columns['REAL_SD'] = next_real
            columns['RKAP_SD'] = next_rkap
            
            logger.info(f"S.d. columns (fallback): REAL={columns['REAL_SD']}, "
                       f"RKAP={columns['RKAP_SD']}")
        
        return columns
    
    def _get_columns_in_range(self, start_col: int, end_col: int) -> Dict[str, Optional[int]]:
        cols = {}
        
        for col in range(start_col, end_col + 1):
            type_name = self.type_headers.get(col)
            if type_name:
                cols[type_name] = col
                logger.debug(f"  Found {type_name} at column {col}")
        
        return cols
    
    def _validate_columns(self, columns: Dict[str, Optional[int]]) -> None:
        required_columns = ['REAL_BULAN_INI', 'RKAP_BULAN_INI', 'REAL_SD', 'RKAP_SD']
        missing = [k for k in required_columns if columns.get(k) is None]
        
        if missing:
            raise ValueError(
                f"Failed to detect columns: {', '.join(missing)}. "
                f"Please check Excel header structure at rows 7-8."
            )
        
        logger.info("✓ All required columns detected")
    
    def _log_detection_result(self, columns: Dict[str, int], period: str) -> None:
       
        print(f"\n✓ Columns detected for period {period}:")
        
        for key, col in columns.items():
            col_letter = self._col_index_to_letter(col)
            print(f"  {key:20s} → Column {col_letter:3s} (index {col})")
    
    def _col_index_to_letter(self, col: int) -> str:
        
        result = ""
        while col > 0:
            col -= 1
            result = chr(col % 26 + 65) + result
            col //= 26
        return result
    
    def get_column_info(self) -> Dict[str, str]:
        
        if not self.detected_columns:
            return {}
        
        info = {}
        for key, col in self.detected_columns.items():
            info[key] = {
                'column_index': col,
                'column_letter': self._col_index_to_letter(col),
                'header_text': self._get_header_text(col)
            }
        
        return info
    
    def _get_header_text(self, col: int) -> str:
      
        try:
            return str(self.sheet.cell(self.reader.TYPE_HEADER_ROW, col).value or "")
        except:
            return ""


if __name__ == "__main__":
    # Test column detector
    import logging
    import sys
    from pathlib import Path
    
    # Add parent directory to path for testing
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from modules.cost.excel_reader import ExcelReader
    
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*70)
    print("COLUMN DETECTOR TEST")
    print("="*70)
    
    try:
        # Setup
        reader = ExcelReader("data/input/test.xlsx")
        sheet = reader.get_sheet(reader.sheet_names[0])
        
        # Detect columns
        detector = ColumnDetector(reader, sheet)
        columns = detector.detect_columns("2024-12")
        
        # Show info
        info = detector.get_column_info()
        print("\nDetailed column info:")
        for key, data in info.items():
            print(f"  {key}:")
            print(f"    - Column: {data['column_letter']} (index {data['column_index']})")
            print(f"    - Header: {data['header_text']}")
        
        reader.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()