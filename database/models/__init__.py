"""
database/models package
=======================
Database models untuk demografi dan cost modules
"""

# ============================================================================
# DEMOGRAFI MODELS
# ============================================================================

from .demografi import (
    # SQL Creation Queries
    CREATE_DEMOGRAFI_TABLES,
    DROP_DEMOGRAFI_TABLES,
    
    # Models
    DemografiConversionHistory,
    DataGender,
    DataPendidikan,
    DataUsia,
    DataUnitKerja,
    DataTren,
    DemografiOutputFiles,
    
    # Helper functions
    get_latest_data_by_periode,
    to_chart_data,
    get_all_data_by_conversion_id,
    get_data_statistics
)

# ============================================================================
# COST MODELS
# ============================================================================

from .cost import (
    # SQL Creation Queries
    CREATE_COST_TABLES,
    DROP_COST_TABLES,
    
    # Models
    CostUploadHistory,
    CostData,
    CostOutputFiles
)

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # ========== DEMOGRAFI ==========
    # SQL
    'CREATE_DEMOGRAFI_TABLES',
    'DROP_DEMOGRAFI_TABLES',
    
    # Models
    'DemografiConversionHistory',
    'DataGender',
    'DataPendidikan',
    'DataUsia',
    'DataUnitKerja',
    'DataTren',
    'DemografiOutputFiles',
    
    # Helpers
    'get_all_data_by_conversion_id',
    'get_data_statistics',
    
    # ========== COST ==========
    # SQL
    'CREATE_COST_TABLES',
    'DROP_COST_TABLES',
    
    # Models
    'CostUploadHistory',
    'CostData',
    'CostOutputFiles',
]