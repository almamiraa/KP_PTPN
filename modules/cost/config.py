"""
modules/cost/config.py
======================
Configuration loader for Cost module with hot-reload support
Merged with original helper methods
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
   
    _instance = None
    _config_data = None
    _last_modified = None
    _config_path = None
    
    def __new__(cls, config_path: str = None):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: str = "config/cost.json"):
      
        # Only set path if not already set
        if self._config_path is None:
            self._config_path = Path(config_path)
        
        # Load config on first init
        if self._config_data is None:
            self._load_and_validate()
    
    def _load_and_validate(self, force: bool = False) -> None:
       
        try:
            # Check if file exists
            if not self._config_path.exists():
                raise FileNotFoundError(f"Config file not found: {self._config_path}")
            
            # Check file modification time
            current_mtime = os.path.getmtime(self._config_path)
            
            # Skip reload if file hasn't changed (unless forced)
            if not force and self._last_modified == current_mtime and self._config_data is not None:
                return
            
            # Load JSON file
            with open(self._config_path, 'r', encoding='utf-8') as f:
                self._config_data = json.load(f)
            
            # Update last modified time
            self._last_modified = current_mtime
            
            if force:
                logger.info(f"🔄 Config force reloaded from: {self._config_path}")
            else:
                logger.info(f"✓ Config loaded from: {self._config_path}")
            
            # Validasi struktur config
            self._validate_config_structure()
            
            # Log summary
            perusahaan_count = len(self._config_data.get('perusahaan', {}))
            row_mapping_count = len(self._config_data.get('row_mapping', {}))
            
            logger.info(f"✓ Config validation passed")
            logger.info(f"  - {perusahaan_count} perusahaan loaded")
            logger.info(f"  - {row_mapping_count} row mappings loaded")
            
            if not force:
                print(f"✓ Cost config loaded: {perusahaan_count} perusahaan, {row_mapping_count} row mappings")
            
        except FileNotFoundError:
            error_msg = f"Config file not found: {self._config_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in config file: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        except Exception as e:
            error_msg = f"Error loading config: {e}"
            logger.error(error_msg)
            raise
    
    def _validate_config_structure(self) -> None:
        """Validasi struktur config JSON"""
        if not isinstance(self._config_data, dict):
            raise ValueError("Config must be a dictionary")
        
        # Validasi key utama
        required_keys = ['perusahaan', 'row_mapping']
        for key in required_keys:
            if key not in self._config_data:
                raise ValueError(f"Missing required key in config: {key}")
        
        # Validasi struktur perusahaan
        perusahaan = self._config_data.get('perusahaan', {})
        if not isinstance(perusahaan, dict):
            raise ValueError("'perusahaan' must be a dictionary")
        
        for nama, data in perusahaan.items():
            required_fields = ['kode_perusahaan', 'nama', 'sheet_name', 'holding']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing '{field}' in perusahaan '{nama}'")
        
        # Validasi struktur row_mapping
        row_mapping = self._config_data.get('row_mapping', {})
        if not isinstance(row_mapping, dict):
            raise ValueError("'row_mapping' must be a dictionary")
        
        for row_num, data in row_mapping.items():
            # Validasi row number adalah angka
            try:
                int(row_num)
            except ValueError:
                raise ValueError(f"Row number must be numeric: {row_num}")
            
            # Validasi required fields
            required_fields = ['payment_type', 'cost_description']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing '{field}' in row_mapping '{row_num}'")
            
            # Validasi payment_type value
            valid_types = ['CASH', 'NON CASH']
            if data['payment_type'] not in valid_types:
                raise ValueError(
                    f"Invalid payment_type '{data['payment_type']}' in row {row_num}. "
                    f"Must be one of: {valid_types}"
                )
    
    def reload(self) -> bool:
        
        try:
            self._load_and_validate(force=True)
            return True
        except Exception as e:
            logger.error(f"❌ Reload failed: {e}")
            return False
    
    def auto_reload_if_changed(self) -> bool:
        
        try:
            if not self._config_path.exists():
                return False
            
            current_mtime = os.path.getmtime(self._config_path)
            
            if current_mtime != self._last_modified:
                logger.info("📝 Cost config file changed, auto-reloading...")
                self._load_and_validate(force=True)
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"⚠️  Auto-reload check failed: {e}")
            return False
    
    def save_config(self, config_data: Dict[str, Any]) -> bool:

        try:
            # Backup current file
            backup_path = str(self._config_path) + '.backup'
            if self._config_path.exists():
                import shutil
                shutil.copy2(self._config_path, backup_path)
            
            # Write new config
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            # Force reload
            self._load_and_validate(force=True)
            
            logger.info("💾 Cost config saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Save cost config failed: {e}")
            # Restore backup if save failed
            if os.path.exists(backup_path):
                import shutil
                shutil.copy2(backup_path, self._config_path)
            return False
    
    # ========================================================================
    # ORIGINAL HELPER METHODS (All preserved!)
    # ========================================================================
    
    def get_perusahaan(self) -> Dict[str, Dict[str, str]]:

        self.auto_reload_if_changed()
        return self._config_data.get('perusahaan', {})
    
    def get_row_mapping(self) -> Dict[str, Dict[str, str]]:

        self.auto_reload_if_changed()
        return self._config_data.get('row_mapping', {})
    
    def get_perusahaan_by_name(self, nama: str) -> Optional[Dict[str, str]]:

        perusahaan = self.get_perusahaan()
        return perusahaan.get(nama)
    
    def get_perusahaan_by_sheet(self, sheet_name: str) -> Optional[Dict[str, str]]:

        for perusahaan in self.get_perusahaan().values():
            if perusahaan['sheet_name'] == sheet_name:
                return perusahaan
        return None
    
    def get_perusahaan_by_kode(self, kode: str) -> Optional[Dict[str, str]]:

        for perusahaan in self.get_perusahaan().values():
            if perusahaan['kode_perusahaan'] == kode:
                return perusahaan
        return None
    
    def get_cost_info_by_row(self, row_num: int) -> Optional[Dict[str, str]]:

        row_mapping = self.get_row_mapping()
        return row_mapping.get(str(row_num))
    
    def get_all_sheet_names(self) -> list:

        perusahaan = self.get_perusahaan()
        return [p['sheet_name'] for p in perusahaan.values()]
    
    def get_holdings(self) -> list:

        perusahaan = self.get_perusahaan()
        holdings = set(p['holding'] for p in perusahaan.values())
        return sorted(list(holdings))
    
    def get_companies_count(self) -> int:

        self.auto_reload_if_changed()
        return len(self.get_perusahaan())

    def get_companies_list(self) -> list:

        self.auto_reload_if_changed()
        perusahaan = self.get_perusahaan()
        return list(perusahaan.keys())
    
    def summary(self) -> Dict[str, Any]:

        self.auto_reload_if_changed()
        
        perusahaan = self.get_perusahaan()
        row_mapping = self.get_row_mapping()
        
        # Count by payment type
        cash_count = sum(1 for r in row_mapping.values() if r['payment_type'] == 'CASH')
        non_cash_count = sum(1 for r in row_mapping.values() if r['payment_type'] == 'NON CASH')
        
        # Count by holding
        holding_counts = {}
        for p in perusahaan.values():
            holding = p['holding']
            holding_counts[holding] = holding_counts.get(holding, 0) + 1
        
        return {
            'total_perusahaan': len(perusahaan),
            'total_row_mappings': len(row_mapping),
            'cash_items': cash_count,
            'non_cash_items': non_cash_count,
            'holdings': self.get_holdings(),
            'holding_counts': holding_counts,
            'sheet_names': self.get_all_sheet_names()
        }

_config_instance = None


def get_config(config_path: str = None) -> ConfigLoader:
    """Get singleton config instance"""
    global _config_instance
    
    if _config_instance is None:
        if config_path:
            _config_instance = ConfigLoader(config_path)
        else:
            _config_instance = ConfigLoader()
    
    return _config_instance


def reload_config() -> bool:
    """Force reload config from file"""
    config = get_config()
    return config.reload()

if __name__ == "__main__":
    # Test config loader
    import logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        config = ConfigLoader("config/cost.json")
        
        print("\n" + "="*70)
        print("CONFIG SUMMARY")
        print("="*70)
        
        summary = config.summary()
        print(f"Total Perusahaan: {summary['total_perusahaan']}")
        print(f"Total Row Mappings: {summary['total_row_mappings']}")
        print(f"  - CASH items: {summary['cash_items']}")
        print(f"  - NON CASH items: {summary['non_cash_items']}")
        print(f"\nHoldings: {', '.join(summary['holdings'])}")
        print(f"\nPerusahaan per Holding:")
        for holding, count in summary['holding_counts'].items():
            print(f"  - {holding}: {count} perusahaan")
        
        print("\n" + "="*70)
        
        # Test reload
        print("\nTesting reload functionality...")
        success = config.reload()
        print(f"Reload: {'✓ Success' if success else '✗ Failed'}")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"Error: {e}")