"""
database/connection.py
======================
Multi-database connection manager
Supports: DBdemografi (demografi), DBcost (cost)
"""

import pyodbc
import os
from dotenv import load_dotenv
from typing import Optional, Literal
import logging

logger = logging.getLogger(__name__)
load_dotenv()

DatabaseType = Literal['demografi', 'cost']


class DatabaseConnection:
    """
    Multi-database connection manager
    Manages connections to both demografi and cost databases
    """
    
    def __init__(self, db_type: DatabaseType):
        """
        Initialize connection for specific database
        
        Args:
            db_type: 'demografi' or 'cost'
        """
        self.db_type = db_type
        self.server = os.getenv('DB_SERVER', 'localhost')
        self.port = os.getenv('DB_PORT', '1433')
        self.driver = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
        self.auth_type = os.getenv('DB_AUTH_TYPE', 'windows').lower()
        
        # Select database based on type
        if db_type == 'demografi':
            self.database = os.getenv('DB_DEMOGRAFI', 'DBdemografi')
        elif db_type == 'cost':
            self.database = os.getenv('DB_COST', 'DBcost')
        else:
            raise ValueError(f"Invalid db_type: {db_type}. Must be 'demografi' or 'cost'")
        
        # SQL Auth (optional)
        self.username = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        
        self.connection: Optional[pyodbc.Connection] = None
        
        logger.info(f"DatabaseConnection initialized for '{db_type}' → {self.database}")
    
    def get_connection_string(self) -> str:
        """Build connection string"""
        base = f"DRIVER={{{self.driver}}};SERVER={self.server},{self.port};DATABASE={self.database};"
        
        if self.auth_type == 'windows':
            conn_str = base + "Trusted_Connection=yes;TrustServerCertificate=yes;"
            logger.debug(f"Using Windows Auth for {self.database}")
        else:
            if not self.username or not self.password:
                raise ValueError("DB_USER and DB_PASSWORD required for SQL auth")
            conn_str = base + f"UID={self.username};PWD={self.password};"
            logger.debug(f"Using SQL Auth for {self.database}")
        
        return conn_str
    
    def connect(self) -> pyodbc.Connection:
        """Create and return database connection"""
        try:
            conn_str = self.get_connection_string()
            self.connection = pyodbc.connect(conn_str, timeout=10)
            self.connection.autocommit = False
            logger.info(f"✓ Connected to {self.db_type}: {self.server}/{self.database}")
            return self.connection
        
        except pyodbc.Error as e:
            error_msg = f"Failed to connect to {self.database}: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_connection(self) -> pyodbc.Connection:
        """Get existing connection or create new one"""
        if self.connection is None:
            return self.connect()
        
        try:
            self.connection.execute("SELECT 1")
            return self.connection
        except:
            logger.warning(f"Connection to {self.database} lost, reconnecting...")
            return self.connect()
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info(f"Connection to {self.database} closed")
            self.connection = None
    
    def __enter__(self):
        """Context manager entry"""
        return self.get_connection()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if exc_type:
            if self.connection:
                self.connection.rollback()
        else:
            if self.connection:
                self.connection.commit()
        # Don't close connection - reuse it


# Singleton instances for each database
_db_demografi: Optional[DatabaseConnection] = None
_db_cost: Optional[DatabaseConnection] = None


def get_db(db_type: DatabaseType = 'demografi') -> DatabaseConnection:
    """
    Get database connection singleton
    
    Args:
        db_type: 'demografi' or 'cost'
    
    Returns:
        DatabaseConnection instance for specified database
    """
    global _db_demografi, _db_cost
    
    if db_type == 'demografi':
        if _db_demografi is None:
            _db_demografi = DatabaseConnection('demografi')
        return _db_demografi
    
    elif db_type == 'cost':
        if _db_cost is None:
            _db_cost = DatabaseConnection('cost')
        return _db_cost
    
    else:
        raise ValueError(f"Invalid db_type: {db_type}")


def close_all():
    """Close all database connections"""
    global _db_demografi, _db_cost
    
    if _db_demografi:
        _db_demografi.close()
        _db_demografi = None
    
    if _db_cost:
        _db_cost.close()
        _db_cost = None
    
    logger.info("All database connections closed")


if __name__ == "__main__":
    # Test connections
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*70)
    print("MULTI-DATABASE CONNECTION TEST")
    print("="*70 + "\n")
    
    # Test Demografi
    print("Testing DEMOGRAFI database...")
    try:
        db_demo = get_db('demografi')
        conn = db_demo.connect()
        print(f"✓ Demografi connected: {db_demo.database}")
        db_demo.close()
    except Exception as e:
        print(f"✗ Demografi failed: {e}")
    
    print()
    
    # Test Cost
    print("Testing COST database...")
    try:
        db_cost = get_db('cost')
        conn = db_cost.connect()
        print(f"✓ Cost connected: {db_cost.database}")
        db_cost.close()
    except Exception as e:
        print(f"✗ Cost failed: {e}")
    
    print("\n" + "="*70)