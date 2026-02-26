"""
modules/cost/validator.py
=========================
Validation for Cost uploads
- Company coverage validation only (no data consistency check)
- Status: success (100%), warning (90-99%), failed (<90%)
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
        self.validation_warnings = []  # Empty for cost (no data consistency check)
        self.company_coverage_percent = 0.0
        self.status = 'success'
        self.config_key_to_name = {}
    
    def to_dict(self):
        """Convert to dictionary for database storage"""
        return {
            'total_companies': self.total_companies,
            'processed_companies': self.processed_companies,
            'missing_companies': json.dumps(self.missing_companies, ensure_ascii=False),
            'validation_warnings': None,  # Always NULL for cost
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
    dataframe: pd.DataFrame,
    expected_companies: List[str]
) -> Tuple[int, List[str], Dict[str, str]]:

    from modules.cost.config import ConfigLoader
    config = ConfigLoader("config/cost.json")
    
    # Build mapping: kode_perusahaan (from data) → config key
    # and config key → nama perusahaan
    data_code_to_config_key = {}
    config_key_to_name = {}
    
    for config_key, company_data in config.get_perusahaan().items():
        kode = company_data.get('kode_perusahaan', '')
        nama = company_data.get('nama', config_key)
        
        # Map both ways
        if kode:
            data_code_to_config_key[kode] = config_key
        config_key_to_name[config_key] = nama
    
    logger.info(f"📋 Config has {len(config_key_to_name)} companies")
    
    # Get unique companies from data
    processed_data_codes = set()
    
    if not dataframe.empty and 'kode_perusahaan' in dataframe.columns:
        processed_data_codes = set(dataframe['kode_perusahaan'].unique())
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


def determine_status(coverage_percent: float) -> str:

    if coverage_percent < 90:
        return 'failed'
    elif coverage_percent < 100:
        return 'warning'
    else:
        return 'success'


def validate_upload(
    dataframe: pd.DataFrame,
    expected_companies: List[str]
) -> ValidationResult:

    result = ValidationResult()
    
    # Validate company coverage
    result.total_companies = len(expected_companies)
    processed_count, missing_config_keys, config_key_to_name = validate_company_coverage(
        dataframe,
        expected_companies
    )
    result.processed_companies = processed_count
    result.missing_companies = missing_config_keys
    result.config_key_to_name = config_key_to_name
    
    # Calculate coverage percentage
    if result.total_companies > 0:
        result.company_coverage_percent = (processed_count / result.total_companies) * 100
    
    # No data consistency check for cost
    result.validation_warnings = []
    
    # Determine final status (based on coverage only)
    result.status = determine_status(result.company_coverage_percent)
    
    # Log summary
    logger.info(f"✅ Validation complete:")
    logger.info(f"   - Coverage: {result.company_coverage_percent:.1f}% ({processed_count}/{result.total_companies})")
    logger.info(f"   - Missing companies: {len(missing_config_keys)}")
    logger.info(f"   - Final status: {result.status.upper()}")
    
    return result


def parse_validation_data(history_record: dict) -> dict:

    missing_companies = []
    if history_record.get('missing_companies'):
        try:
            missing_companies = json.loads(history_record['missing_companies'])
        except:
            pass
    
    return {
        'has_validation': history_record.get('total_companies') is not None,
        'total_companies': history_record.get('total_companies', 0),
        'processed_companies': history_record.get('processed_companies', 0),
        'missing_companies': missing_companies,
        'validation_warnings': [],  # Always empty for cost
        'company_coverage_percent': history_record.get('company_coverage_percent', 0.0)
    }


def get_status_badge_class(status: str) -> str:
    """Get CSS class for status badge"""
    classes = {
        'success': 'bg-soft-success',
        'warning': 'bg-soft-warning',
        'failed': 'bg-soft-danger'
    }
    return classes.get(status, 'bg-soft-info')


def get_status_icon(status: str) -> str:
    """Get FontAwesome icon for status"""
    icons = {
        'success': 'fa-check-circle',
        'warning': 'fa-exclamation-triangle',
        'failed': 'fa-times-circle'
    }
    return icons.get(status, 'fa-info-circle')