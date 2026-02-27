"""
data_processor.py
=================
Module untuk memproses dan extract data dari Excel
"""

from typing import List, Dict, Any, Optional
import logging
from .column_detector import ColumnDetector
from datetime import datetime

logger = logging.getLogger(__name__)


class DataProcessor:
   
    
    def __init__(self, config_loader, excel_reader):

        self.config = config_loader
        self.reader = excel_reader
        self.processed_count = 0
        self.error_count = 0
        self.skipped_sheets = []
    
    def process_all_sheets(self, period_search: str, period_full: str = None) -> List[Dict[str, Any]]:

        # Jika period_full tidak diberikan, gunakan period_search
        if period_full is None:
            period_full = period_search
        
        logger.info(f"Starting to process all sheets for period: {period_search}")
        
        all_data = []
        perusahaan_list = self.config.get_perusahaan()
        
        total_perusahaan = len(perusahaan_list)
        processed = 0
        
        print(f"\n{'='*70}")
        print(f"PROCESSING {total_perusahaan} PERUSAHAAN")
        print(f"{'='*70}\n")
        
        for nama_perusahaan, perusahaan_data in perusahaan_list.items():
            processed += 1
            sheet_name = perusahaan_data['sheet_name']
            
            print(f"[{processed}/{total_perusahaan}] Processing: {sheet_name}...")
            
            try:
                # Check if sheet exists
                if not self.reader.sheet_exists(sheet_name):
                    logger.warning(f"Sheet '{sheet_name}' not found, skipping")
                    print(f"  ⚠ Sheet not found, skipped")
                    self.skipped_sheets.append(sheet_name)
                    continue
                
                # Process sheet - pass both periods
                sheet_data = self.process_sheet(sheet_name, perusahaan_data, period_search, period_full)
                all_data.extend(sheet_data)
                
                self.processed_count += 1
                print(f"  ✓ Processed {len(sheet_data)} rows")
                logger.info(f"Successfully processed {sheet_name}: {len(sheet_data)} rows")
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Error processing {sheet_name}: {e}", exc_info=True)
                print(f"  ✗ Error: {e}")
                continue
        
        # Print summary
        self._print_summary(all_data)
        
        return all_data
    
    def process_sheet(
        self, 
        sheet_name: str, 
        perusahaan_data: Dict[str, str], 
        period_search: str,
        period_full: str = None
    ) -> List[Dict[str, Any]]:

        if period_full is None:
            period_full = period_search
        
        logger.info(f"Processing sheet: {sheet_name}")
        
        # Get sheet
        sheet = self.reader.get_sheet(sheet_name)
        
        # Detect columns untuk periode ini (use period_search)
        detector = ColumnDetector(self.reader, sheet)
        columns = detector.detect_columns(period_search)
        
        # Get row mapping dari config
        row_mapping = self.config.get_row_mapping()
        
        # Extract data untuk setiap cost row
        data_rows = []
        
        for row_num_str, cost_info in row_mapping.items():
            row_num = int(row_num_str)
            
            # Extract values dari Excel
            try:
                real_bulan = self.reader.get_cell_value(
                    sheet, row_num, columns['REAL_BULAN_INI']
                )
                rkap_bulan = self.reader.get_cell_value(
                    sheet, row_num, columns['RKAP_BULAN_INI']
                )
                real_sd = self.reader.get_cell_value(
                    sheet, row_num, columns['REAL_SD']
                )
                rkap_sd = self.reader.get_cell_value(
                    sheet, row_num, columns['RKAP_SD']
                )
            except Exception as e:
                logger.warning(
                    f"Error reading row {row_num} in {sheet_name}: {e}. "
                    f"Using 0 for all values."
                )
                real_bulan = rkap_bulan = real_sd = rkap_sd = 0.0
            
            # Build output row (use period_full for output!)
            data_row = {
                'holding': perusahaan_data['holding'],
                'kode_perusahaan': perusahaan_data['kode_perusahaan'],
                'periode': period_full,
                'payment_type': cost_info['payment_type'],
                'cost_description': cost_info['cost_description'],
                'REAL': real_bulan,
                'RKAP': rkap_bulan,
                'REAL_SD': real_sd,
                'RKAP_SD': rkap_sd
            }
            
            data_rows.append(data_row)
            
            logger.debug(
                f"Row {row_num}: {cost_info['cost_description']} = "
                f"REAL:{real_bulan}, RKAP:{rkap_bulan}"
            )
        
        return data_rows
    
    def process_single_perusahaan(
        self, 
        nama_perusahaan: str, 
        period: str
    ) -> Optional[List[Dict[str, Any]]]:

        perusahaan_data = self.config.get_perusahaan_by_name(nama_perusahaan)
        
        if not perusahaan_data:
            logger.error(f"Perusahaan '{nama_perusahaan}' not found in config")
            return None
        
        sheet_name = perusahaan_data['sheet_name']
        
        try:
            return self.process_sheet(sheet_name, perusahaan_data, period)
        except Exception as e:
            logger.error(f"Error processing {nama_perusahaan}: {e}", exc_info=True)
            return None
    
    def _print_summary(self, all_data: List[Dict[str, Any]]) -> None:

        print(f"\n{'='*70}")
        print("PROCESSING SUMMARY")
        print(f"{'='*70}")
        print(f"✓ Successfully processed: {self.processed_count} sheets")
        print(f"✗ Errors: {self.error_count} sheets")
        
        if self.skipped_sheets:
            print(f"⚠ Skipped (not found): {len(self.skipped_sheets)} sheets")
            for sheet in self.skipped_sheets[:5]:
                print(f"    - {sheet}")
            if len(self.skipped_sheets) > 5:
                print(f"    ... and {len(self.skipped_sheets) - 5} more")
        
        print(f"\nTotal data rows generated: {len(all_data)}")
        
        # Group by holding
        if all_data:
            holdings = {}
            for row in all_data:
                holding = row['holding']
                holdings[holding] = holdings.get(holding, 0) + 1
            
            print(f"\nData by holding:")
            for holding, count in sorted(holdings.items()):
                print(f"  {holding}: {count} rows")
        
        print(f"{'='*70}\n")
    
    def get_statistics(self) -> Dict[str, Any]:

        return {
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'skipped_count': len(self.skipped_sheets),
            'skipped_sheets': self.skipped_sheets
        }
    
    def validate_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:

        issues = {
            'missing_values': 0,
            'negative_values': 0,
            'zero_rows': 0,
            'total_rows': len(data)
        }
        
        for row in data:
            # Check missing values
            if not all([
                row.get('holding'),
                row.get('kode_perusahaan'),
                row.get('periode'),
                row.get('payment_type'),
                row.get('cost_description')
            ]):
                issues['missing_values'] += 1
            
            # Check negative values
            numeric_fields = ['REAL', 'RKAP', 'REAL_SD', 'RKAP_SD']
            if any(row.get(field, 0) < 0 for field in numeric_fields):
                issues['negative_values'] += 1
            
            # Check zero rows (all numeric values are 0)
            if all(row.get(field, 0) == 0 for field in numeric_fields):
                issues['zero_rows'] += 1
        
        issues['is_valid'] = (
            issues['missing_values'] == 0 and 
            issues['negative_values'] == 0
        )
        
        return issues

if __name__ == "__main__":
    # Test data processor
    import logging
    import sys
    from pathlib import Path
    
    # Add parent directory to path for testing
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from modules.cost.config import ConfigLoader
    from modules.cost.excel_reader import ExcelReader
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*70)
    print("DATA PROCESSOR TEST")
    print("="*70)
    
    try:
        # Setup
        config = ConfigLoader()
        reader = ExcelReader("data/input/test.xlsx")
        
        # Process
        processor = DataProcessor(config, reader)
        data = processor.process_all_sheets("2024-12")
        
        # Validate
        print("\nValidating data...")
        validation = processor.validate_data(data)
        print(f"Validation results:")
        print(f"  Total rows: {validation['total_rows']}")
        print(f"  Missing values: {validation['missing_values']}")
        print(f"  Negative values: {validation['negative_values']}")
        print(f"  Zero rows: {validation['zero_rows']}")
        print(f"  Is valid: {validation['is_valid']}")
        
        # Show sample
        if data:
            print(f"\nSample data (first row):")
            first_row = data[0]
            for key, value in first_row.items():
                print(f"  {key}: {value}")
        
        reader.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()