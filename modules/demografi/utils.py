"""
Utils - Utility Functions and Helper Classes
=============================================
Complete implementation dengan semua helper yang dibutuhkan
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, field


def setup_logger(log_file: str = None, level: str = "INFO") -> logging.Logger:
    
    logger = logging.getLogger("sdm_converter")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        ensure_dir(Path(log_file).parent)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger() -> logging.Logger:
    """Get existing logger instance."""
    logger = logging.getLogger("sdm_converter")
    
    # Initialize jika belum ada
    if not logger.handlers:
        logger = setup_logger()
    
    return logger


@dataclass
class ValidationResult:
    """Result dari validasi input."""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, message: str):
        """Add error message."""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add warning message."""
        self.warnings.append(message)


@dataclass
class ConversionResult:
    """Result dari konversi data."""
    success: bool = False
    message: str = ""
    total_rows: int = 0
    data: dict = field(default_factory=dict)  # {'gender': df, 'usia': df, ...}
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dict untuk JSON response."""
        return {
            'success': self.success,
            'message': self.message,
            'total_rows': self.total_rows,
            'errors': self.errors,
            'warnings': self.warnings,
            'duration': round(self.duration, 2),
            'sheets': list(self.data.keys()) if self.data else []
        }


class ProgressTracker:

    
    def __init__(self, total: int):
        self.total = total
        self.current = 0
        self.start_time = datetime.now()
    
    def update(self, increment: int = 1):
        """Update progress."""
        self.current += increment
    
    @property
    def percentage(self) -> float:
        """Get percentage completion."""
        if self.total == 0:
            return 100.0
        return (self.current / self.total) * 100
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        return (datetime.now() - self.start_time).total_seconds()
    
    def __str__(self) -> str:
        return f"Progress: {self.current}/{self.total} ({self.percentage:.1f}%)"


def parse_date(date_str: str) -> str:
   
    date_str = date_str.strip()
    
    # List of formats to try
    formats = [
        '%Y-%m-%d',      # 2024-12-01
        '%d/%m/%Y',      # 01/12/2024
        '%d-%m-%Y',      # 01-12-2024
        '%Y%m%d',        # 20241201
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    raise ValueError(
        f"Format tanggal '{date_str}' tidak valid. "
        f"Gunakan format: YYYY-MM-DD, DD/MM/YYYY, atau DD-MM-YYYY"
    )


# ============================================================================
# SAFE CONVERSIONS
# ============================================================================

def safe_int(value, default: int = 0) -> int:

    if value is None or value == '':
        return default
    
    try:
        # Handle float
        if isinstance(value, float):
            return int(value)
        
        # Handle string
        if isinstance(value, str):
            # Remove whitespace dan commas
            value = value.strip().replace(',', '')
            
            # Check jika kosong setelah strip
            if not value:
                return default
            
            # Convert
            return int(float(value))
        
        # Direct int conversion
        return int(value)
        
    except (ValueError, TypeError):
        return default

def ensure_dir(path: Path):
   
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)


def get_unique_filename(base_path: str, extension: str = None) -> str:
  
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if extension:
        if not extension.startswith('.'):
            extension = f'.{extension}'
        return f"{base_path}_{timestamp}{extension}"
    
    return f"{base_path}_{timestamp}"


class SDMConverterError(Exception):
    """Base exception untuk SDM Converter."""
    pass


class ValidationError(SDMConverterError):
    """Exception untuk validation errors."""
    pass


class FileError(SDMConverterError):
    """Exception untuk file operation errors."""
    pass


class ConversionError(SDMConverterError):
    """Exception untuk conversion errors."""
    pass


def validate_excel_extension(filename: str) -> bool:
    """Check if file has valid Excel extension."""
    return filename.lower().endswith(('.xlsx', '.xlsm'))


def format_number(num: int) -> str:
    """
    Format number dengan thousand separator.
    
    Args:
        num: Number to format
    
    Returns:
        str: Formatted number (e.g., '1,234,567')
    """
    return f"{num:,}"


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        str: Formatted duration (e.g., '2m 30s', '45s')
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes}m {remaining_seconds}s"