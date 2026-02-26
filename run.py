"""
run.py
======
Main launcher for PTPN Unified Converter
Jalankan file ini untuk start aplikasi: python run.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment")

# Import Flask app
from web.app import create_app

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🌿 PTPN UNIFIED CONVERTER")
    print("="*70)
    print("Starting application...")
    
    # Create app
    app = create_app()
    
    # Server settings from .env
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"\n📍 Server Configuration:")
    print(f"   URL: http://localhost:{port}")
    print(f"   Host: {host}")
    print(f"   Debug: {'ON' if debug else 'OFF'}")
    print(f"   Environment: {os.getenv('FLASK_ENV', 'production')}")
    print(f"\n📂 Active Modules:")
    
    # Check which features are enabled
    feature_demografi = os.getenv('FEATURE_DEMOGRAFI', 'True').lower() == 'true'
    feature_cost = os.getenv('FEATURE_COST', 'True').lower() == 'true'
    
    if feature_demografi:
        print(f"   ✓ Demografi SDM (Database: {os.getenv('DB_DEMOGRAFI', 'DBdemografi')})")
    else:
        print(f"   ✗ Demografi SDM (Disabled)")
    
    if feature_cost:
        print(f"   ✓ Cost Management (Database: {os.getenv('DB_COST', 'DBcost')})")
    else:
        print(f"   ✗ Cost Management (Disabled)")
    
    print(f"\n{'='*70}")
    print("🚀 Starting Flask development server...")
    print("   Press CTRL+C to quit")
    print(f"{'='*70}\n")
    
    try:
        # Run Flask app
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug  # Auto-reload on code changes if debug=True
        )
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("👋 Server stopped by user")
        print("="*70)
        sys.exit(0)
    except Exception as e:
        print("\n\n" + "="*70)
        print(f"❌ Server failed to start: {e}")
        print("="*70)
        import traceback
        traceback.print_exc()
        sys.exit(1)