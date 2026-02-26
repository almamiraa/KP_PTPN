"""
database/init_db.py
===================
Initialize BOTH databases (DBdemografi + DBcost) from scratch
- Creates databases if not exist
- Drops all existing tables (fresh start)
- Creates tables with latest schema
- Config loaded from .env file
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import pyodbc
from dotenv import load_dotenv
from database.models.demografi import CREATE_DEMOGRAFI_TABLES
from database.models.cost import CREATE_COST_TABLES
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Load environment variables
load_dotenv()

# ✅ Get config from .env
DB_SERVER = os.getenv('DB_SERVER', 'localhost')
DB_DRIVER = os.getenv('DB_DRIVER', '{ODBC Driver 17 for SQL Server}')
DB_DEMOGRAFI = os.getenv('DB_DEMOGRAFI', 'DBdemografi')
DB_COST = os.getenv('DB_COST', 'DBcost')

# Authentication
DB_AUTH_TYPE = os.getenv('DB_AUTH_TYPE', 'windows').lower()
DB_USERNAME = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

USE_WINDOWS_AUTH = DB_AUTH_TYPE == 'windows'

print(f"📋 Configuration:")
print(f"   Server: {DB_SERVER}")
print(f"   Driver: {DB_DRIVER}")
print(f"   Auth: {'Windows' if USE_WINDOWS_AUTH else 'SQL Server'}")
print(f"   Demografi DB: {DB_DEMOGRAFI}")
print(f"   Cost DB: {DB_COST}")


def get_connection_string(database: str = 'master'):
    """Build connection string from environment config"""
    conn_str = f"DRIVER={DB_DRIVER};SERVER={DB_SERVER};DATABASE={database};"
    
    if USE_WINDOWS_AUTH:
        conn_str += "Trusted_Connection=yes;"
    else:
        conn_str += f"UID={DB_USERNAME};PWD={DB_PASSWORD};"
    
    return conn_str


def create_database_if_not_exists(db_name: str):
    """Create database if it doesn't exist"""
    print(f"\n🔍 Checking database: {db_name}")
    
    try:
        # Connect to master with autocommit
        conn_str = get_connection_string('master')
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"""
            SELECT database_id 
            FROM sys.databases 
            WHERE name = '{db_name}'
        """)
        
        if cursor.fetchone():
            print(f"✓ Database '{db_name}' already exists")
        else:
            print(f"📦 Creating database '{db_name}'...")
            cursor.execute(f"CREATE DATABASE [{db_name}]")
            print(f"✓ Database '{db_name}' created")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error with database '{db_name}': {e}")
        return False


def get_connection(db_name: str):
    """Get connection to specific database"""
    conn_str = get_connection_string(db_name)
    return pyodbc.connect(conn_str)


def drop_all_demografi_tables(conn):
    """Drop all demografi tables (for fresh start)"""
    print("\n🗑️  Dropping existing demografi tables...")
    
    cursor = conn.cursor()
    
    # Drop in correct order (foreign keys first)
    tables = [
        'data_gender',
        'data_pendidikan',
        'data_usia',
        'data_unit_kerja',
        'data_tren',
        'output_files',
        'conversion_history'
    ]
    
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS [{table}]")
            print(f"   ✓ Dropped '{table}'")
        except Exception as e:
            if "does not exist" not in str(e).lower():
                print(f"   ⚠ '{table}': {e}")
    
    conn.commit()
    cursor.close()
    print("✓ All demografi tables dropped\n")


def drop_all_cost_tables(conn):
    """Drop all cost tables (for fresh start)"""
    print("\n🗑️  Dropping existing cost tables...")
    
    cursor = conn.cursor()
    
    # Drop in correct order (foreign keys first)
    tables = [
        'cost_data',
        'output_files',
        'upload_history'
    ]
    
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS [{table}]")
            print(f"   ✓ Dropped '{table}'")
        except Exception as e:
            if "does not exist" not in str(e).lower():
                print(f"   ⚠ '{table}': {e}")
    
    conn.commit()
    cursor.close()
    print("✓ All cost tables dropped\n")


def init_demografi():
    """Initialize demografi database from scratch"""
    print("\n" + "="*70)
    print(f"INITIALIZING DEMOGRAFI DATABASE ({DB_DEMOGRAFI})")
    print("="*70)
    
    # 1. Create database if not exists
    if not create_database_if_not_exists(DB_DEMOGRAFI):
        return False
    
    # 2. Connect to database
    conn = get_connection(DB_DEMOGRAFI)
    
    # 3. Drop all existing tables (fresh start)
    drop_all_demografi_tables(conn)
    
    # 4. Create tables with latest schema
    print("📦 Creating demografi tables...")
    for table_name, create_sql in CREATE_DEMOGRAFI_TABLES.items():
        try:
            cursor = conn.cursor()
            statements = [s.strip() for s in create_sql.strip().split(';') if s.strip()]
            
            for statement in statements:
                if statement:  # Skip empty statements
                    cursor.execute(statement)
            
            conn.commit()
            cursor.close()
            print(f"✓ Table '{table_name}' created")
            
        except Exception as e:
            print(f"✗ Error creating '{table_name}': {e}")
            conn.rollback()
            raise
    
    conn.close()
    print(f"✓ Demografi database ({DB_DEMOGRAFI}) initialized successfully\n")
    return True


def init_cost():
    """Initialize cost database from scratch"""
    print("\n" + "="*70)
    print(f"INITIALIZING COST DATABASE ({DB_COST})")
    print("="*70)
    
    # 1. Create database if not exists
    if not create_database_if_not_exists(DB_COST):
        return False
    
    # 2. Connect to database
    conn = get_connection(DB_COST)
    
    # 3. Drop all existing tables (fresh start)
    drop_all_cost_tables(conn)
    
    # 4. Create tables with latest schema
    print("📦 Creating cost tables...")
    for table_name, create_sql in CREATE_COST_TABLES.items():
        try:
            cursor = conn.cursor()
            statements = [s.strip() for s in create_sql.strip().split(';') if s.strip()]
            
            for statement in statements:
                if statement:  # Skip empty statements
                    cursor.execute(statement)
            
            conn.commit()
            cursor.close()
            print(f"✓ Table '{table_name}' created")
            
        except Exception as e:
            print(f"✗ Error creating '{table_name}': {e}")
            conn.rollback()
            raise
    
    conn.close()
    print(f"✓ Cost database ({DB_COST}) initialized successfully\n")
    return True


def main():
    """Main initialization"""
    print("\n" + "="*70)
    print("PTPN CONVERTER - DATABASE INITIALIZATION")
    print("="*70)
    print("\n⚠️  WARNING: This will DROP all existing tables!")
    print("   All data will be DELETED and tables recreated from scratch.\n")
    
    print("Which database(s) to initialize?")
    print(f"1. Demografi only ({DB_DEMOGRAFI})")
    print(f"2. Cost only ({DB_COST})")
    print("3. Both (recommended for fresh setup)")
    
    choice = input("\nYour choice (1/2/3): ").strip()
    
    if choice not in ['1', '2', '3']:
        print("Invalid choice!")
        return False
    
    confirm = input("\n⚠️  Confirm: This will DELETE all existing data. Continue? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("Cancelled.")
        return False
    
    try:
        success = True
        
        if choice == '1':
            success = init_demografi()
        elif choice == '2':
            success = init_cost()
        elif choice == '3':
            success = init_demografi() and init_cost()
        
        if success:
            print("\n" + "="*70)
            print("✅ DATABASE INITIALIZATION COMPLETE!")
            print("="*70)
            print("\n🚀 You can now run the application:")
            print("   python run.py")
            print()
        
        return success
        
    except Exception as e:
        print(f"\n✗ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)