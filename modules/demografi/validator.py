"""
modules/demografi/validator.py
==============================
Validation functions for demografi conversion
- Company coverage validation
- Data consistency validation
"""

import json
import logging
from typing import Dict, List, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


class ValidationResult:
    """Container for validation results"""
    
    def __init__(self):
        self.total_companies = 0
        self.processed_companies = 0
        self.missing_companies = []
        self.validation_warnings = []
        self.company_coverage_percent = 0.0
        self.status = 'success'  # success, warning, failed
        self.config_key_to_name = {}
    
    def to_dict(self):
        """Convert to dictionary for database storage"""
        return {
            'total_companies': self.total_companies,
            'processed_companies': self.processed_companies,
            'missing_companies': json.dumps(self.missing_companies, ensure_ascii=False),
            'validation_warnings': json.dumps(self.validation_warnings, ensure_ascii=False),
            'company_coverage_percent': round(self.company_coverage_percent, 2),
            'status': self.status
        }
    
    def get_status_label(self):
        """Get human-readable status label"""
        labels = {
            'success': 'Berhasil',
            'warning': 'Warning',
            'failed': 'Gagal'
        }
        return labels.get(self.status, self.status)


def validate_company_coverage(
    dataframes: Dict[str, pd.DataFrame],
    expected_companies: List[str]
) -> Tuple[int, List[str], Dict[str, str]]:
   
    from modules.demografi.config import get_config
    config = get_config()
    
    # Build mapping: kode_perusahaan (from data) → config key
    # and config key → nama perusahaan
    data_code_to_config_key = {}
    config_key_to_name = {}
    
    for config_key, company_data in config.data['perusahaan'].items():
        kode = company_data.get('kode_perusahaan', '')
        nama = company_data.get('nama', config_key)
        
        # Map both ways
        if kode:
            data_code_to_config_key[kode] = config_key
        config_key_to_name[config_key] = nama
    
    logger.info(f"📋 Config has {len(config_key_to_name)} companies")
    logger.info(f"📋 Mapping example: {list(data_code_to_config_key.items())[:3]}")
    
    # Get unique companies from gender data
    processed_data_codes = set()
    
    if 'gender' in dataframes and not dataframes['gender'].empty:
        if 'kode_perusahaan' in dataframes['gender'].columns:
            processed_data_codes = set(dataframes['gender']['kode_perusahaan'].unique())
            logger.info(f"📊 Processed data codes: {list(processed_data_codes)[:5]}...")
    
    # Map processed data codes to config keys
    processed_config_keys = set()
    for data_code in processed_data_codes:
        config_key = data_code_to_config_key.get(data_code)
        if config_key:
            processed_config_keys.add(config_key)
        else:
            logger.warning(f"⚠️  Unknown data code: {data_code}")
    
    # Find missing companies (in config keys)
    expected_set = set(expected_companies)
    missing_config_keys = sorted(list(expected_set - processed_config_keys))
    
    processed_count = len(processed_config_keys)
    
    logger.info(f"📊 Company coverage: {processed_count}/{len(expected_companies)} companies processed")
    
    if missing_config_keys:
        missing_names = [config_key_to_name.get(k, k) for k in missing_config_keys]
        logger.warning(f"⚠️  Missing companies: {missing_names[:5]}...")
    
    return processed_count, missing_config_keys, config_key_to_name

def validate_data_consistency(dataframes: Dict[str, pd.DataFrame]) -> List[str]:
    
    warnings = []
    
    # Get totals per dimension
    totals = {}
    for dim_name, df in dataframes.items():
        if not df.empty and 'jumlah' in df.columns:
            totals[dim_name] = int(df['jumlah'].sum())
    
    logger.info(f"📊 Data totals: {totals}")
    
    # Rule 1: Pendidikan = Usia
    if 'pendidikan' in totals and 'usia' in totals:
        if totals['pendidikan'] != totals['usia']:
            diff = abs(totals['pendidikan'] - totals['usia'])
            warnings.append({
                'type': 'data_mismatch',
                'message': f"Jumlah data Pendidikan ({totals['pendidikan']:,}) tidak sama dengan Usia ({totals['usia']:,}). Selisih: {diff:,}",
                'dimensions': ['pendidikan', 'usia'],
                'values': {
                    'pendidikan': totals['pendidikan'],
                    'usia': totals['usia']
                }
            })
            logger.warning(f"⚠️  Pendidikan ≠ Usia: {totals['pendidikan']} ≠ {totals['usia']}")
    
    # Rule 2: Gender = Tren = Unit Kerja
    reference_dims = ['gender', 'tren', 'unit_kerja']
    available_dims = [d for d in reference_dims if d in totals]
    
    if len(available_dims) >= 2:
        # Get reference value (first available)
        ref_dim = available_dims[0]
        ref_value = totals[ref_dim]
        
        # Check others against reference
        mismatched_dims = []
        for dim in available_dims[1:]:
            if totals[dim] != ref_value:
                mismatched_dims.append(dim)
        
        if mismatched_dims:
            dims_str = ', '.join([ref_dim] + mismatched_dims)
            values_str = ', '.join([f"{d}={totals[d]:,}" for d in [ref_dim] + mismatched_dims])
            
            warnings.append({
                'type': 'data_mismatch',
                'message': f"Jumlah data tidak konsisten: {values_str}",
                'dimensions': [ref_dim] + mismatched_dims,
                'values': {d: totals[d] for d in [ref_dim] + mismatched_dims}
            })
            logger.warning(f"⚠️  Data mismatch: {dims_str} - {values_str}")
    
    return warnings


def determine_status(coverage_percent: float, has_warnings: bool) -> str:
    
    if coverage_percent < 90:
        return 'failed'
    elif coverage_percent < 100:
        return 'warning'
    elif has_warnings:
        return 'warning'
    else:
        return 'success'


def validate_conversion(
    dataframes: Dict[str, pd.DataFrame],
    expected_companies: List[str]
) -> ValidationResult:
 
    result = ValidationResult()
    
    # 1. Validate company coverage
    result.total_companies = len(expected_companies)
    processed_count, missing_config_keys, config_key_to_name = validate_company_coverage(
        dataframes,
        expected_companies
    )
    result.processed_companies = processed_count
    result.missing_companies = missing_config_keys  # Store config keys
    
    # ✅ NEW: Store mapping for display purposes
    result.config_key_to_name = config_key_to_name
    
    # Calculate coverage percentage
    if result.total_companies > 0:
        result.company_coverage_percent = (processed_count / result.total_companies) * 100
    
    # 2. Validate data consistency
    data_warnings = validate_data_consistency(dataframes)
    result.validation_warnings = data_warnings
    
    # 3. Determine final status
    result.status = determine_status(
        result.company_coverage_percent,
        len(data_warnings) > 0
    )
    
    # Log summary
    logger.info(f"✅ Validation complete:")
    logger.info(f"   - Coverage: {result.company_coverage_percent:.1f}% ({processed_count}/{result.total_companies})")
    logger.info(f"   - Missing companies: {len(missing_config_keys)}")
    logger.info(f"   - Data warnings: {len(data_warnings)}")
    logger.info(f"   - Final status: {result.status.upper()}")
    
    return result


def parse_validation_data(history_record: dict) -> dict:
   
    parsed = {
        'has_validation': False,
        'total_companies': 0,
        'processed_companies': 0,
        'missing_companies': [],
        'validation_warnings': [],
        'company_coverage_percent': 0.0,
        'status': history_record.get('status', 'success')
    }
    
    # Check if validation data exists
    if history_record.get('total_companies') is not None:
        parsed['has_validation'] = True
        parsed['total_companies'] = history_record.get('total_companies', 0)
        parsed['processed_companies'] = history_record.get('processed_companies', 0)
        parsed['company_coverage_percent'] = history_record.get('company_coverage_percent', 0.0)
        
        # Parse JSON fields
        try:
            if history_record.get('missing_companies'):
                parsed['missing_companies'] = json.loads(history_record['missing_companies'])
        except:
            parsed['missing_companies'] = []
        
        try:
            if history_record.get('validation_warnings'):
                parsed['validation_warnings'] = json.loads(history_record['validation_warnings'])
        except:
            parsed['validation_warnings'] = []
    
    return parsed


def get_status_badge_class(status: str) -> str:
   
    classes = {
        'success': 'bg-soft-success',
        'warning': 'bg-soft-warning',
        'failed': 'bg-soft-danger'
    }
    return classes.get(status, 'bg-soft-info')


def get_status_icon(status: str) -> str:

    icons = {
        'success': 'fas fa-check-circle',
        'warning': 'fas fa-exclamation-triangle',
        'failed': 'fas fa-times-circle'
    }
    return icons.get(status, 'fas fa-info-circle')


def format_validation_summary(validation_data: dict) -> str:

    if not validation_data['has_validation']:
        return "No validation data"
    
    summary_parts = []
    
    # Company coverage
    coverage = validation_data['company_coverage_percent']
    processed = validation_data['processed_companies']
    total = validation_data['total_companies']
    
    summary_parts.append(f"{processed}/{total} perusahaan ({coverage:.1f}%)")
    
    # Missing companies
    if validation_data['missing_companies']:
        count = len(validation_data['missing_companies'])
        summary_parts.append(f"{count} perusahaan hilang")
    
    # Data warnings
    if validation_data['validation_warnings']:
        count = len(validation_data['validation_warnings'])
        summary_parts.append(f"{count} warning konsistensi data")
    
    return " • ".join(summary_parts)