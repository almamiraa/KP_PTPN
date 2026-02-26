"""
database package
================
Database connection and models for PTPN Unified Converter
Supports multi-database architecture: DBdemografi + DBcost
"""

from .connection import (
    DatabaseConnection,
    get_db,
    close_all
)

from .models import (
    # Demografi models
    CREATE_DEMOGRAFI_TABLES,
    DROP_DEMOGRAFI_TABLES,
    DemografiConversionHistory,
    DataGender,
    DataPendidikan,
    DataUsia,
    DataUnitKerja,
    DataTren,
    DemografiOutputFiles,
    get_latest_data_by_periode,
    to_chart_data,
    get_all_data_by_conversion_id,
    get_data_statistics,
    
    # Cost models
    CREATE_COST_TABLES,
    DROP_COST_TABLES,
    CostUploadHistory,
    CostData,
    CostOutputFiles
)

__version__ = '2.0.0'

__all__ = [
    # Connection
    'DatabaseConnection',
    'get_db',
    'close_all',
    
    # Demografi
    'CREATE_DEMOGRAFI_TABLES',
    'DROP_DEMOGRAFI_TABLES',
    'DemografiConversionHistory',
    'DataGender',
    'DataPendidikan',
    'DataUsia',
    'DataUnitKerja',
    'DataTren',
    'DemografiOutputFiles',
    'to_chart_data',
    'get_latest_data_by_periode',
    'get_all_data_by_conversion_id',
    'get_data_statistics',
    
    # Cost
    'CREATE_COST_TABLES',
    'DROP_COST_TABLES',
    'CostUploadHistory',
    'CostData',
    'CostOutputFiles',
]