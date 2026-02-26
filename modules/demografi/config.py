"""
modules/demografi/config.py
===========================
Configuration loader for Demografi module
ORIGINAL CODE + Hot-reload support added
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class Config:

    _instance = None
    _last_modified = None
    
    def __new__(cls, config_path: str = "config/demografi.json"):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: str = "config/demografi.json"):
        # Only initialize once
        if not hasattr(self, 'config_path'):
            self.config_path = Path(config_path)
            self.data = self._load()
    
    def _load(self, force: bool = False) -> dict:
        """Load config with hot-reload support"""
        if not self.config_path.exists():
            print(f"⚠️  Config tidak ditemukan: {self.config_path}")
            logger.warning(f"Config not found: {self.config_path}")
            return {}
        
        try:
            # Check file modification time
            current_mtime = os.path.getmtime(self.config_path)
            
            # Skip reload if file hasn't changed (unless forced)
            if not force and self._last_modified == current_mtime and hasattr(self, 'data') and self.data:
                return self.data
            
            # Load JSON
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Update last modified time
            self._last_modified = current_mtime
            
            if force:
                print(f"🔄 Config reloaded: {self.config_path}")
                logger.info(f"Config reloaded: {self.config_path}")
            else:
                print(f"✅ Config loaded: {self.config_path}")
                logger.info(f"Config loaded: {self.config_path}")
            
            return data
            
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            logger.error(f"Error loading config: {e}")
            return {}
    
    def reload(self) -> bool:
        """Force reload config from file"""
        try:
            self.data = self._load(force=True)
            return True
        except Exception as e:
            logger.error(f"❌ Reload failed: {e}")
            return False
    
    def auto_reload_if_changed(self) -> bool:
        """Auto-reload config if file was modified"""
        try:
            if not self.config_path.exists():
                return False
            
            current_mtime = os.path.getmtime(self.config_path)
            
            if current_mtime != self._last_modified:
                logger.info("📝 Config file changed, auto-reloading...")
                self.data = self._load(force=True)
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"⚠️  Auto-reload check failed: {e}")
            return False
    
    def save_config(self, config_data: Dict) -> bool:
        """Save config to JSON file"""
        try:
            # Backup current file
            backup_path = str(self.config_path) + '.backup'
            if self.config_path.exists():
                import shutil
                shutil.copy2(self.config_path, backup_path)
            
            # Write new config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            # Force reload
            self.data = self._load(force=True)
            
            logger.info("💾 Config saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Save config failed: {e}")
            # Restore backup if save failed
            if os.path.exists(backup_path):
                import shutil
                shutil.copy2(backup_path, self.config_path)
            return False
    
    def get_companies_dict(self) -> Dict:
        """Get companies as dictionary (for admin API)"""
        self.auto_reload_if_changed()
        return self.data.get('perusahaan', {})
    
    def get_companies_count(self) -> int:
        """Get total count of companies"""
        self.auto_reload_if_changed()
        return len(self.data.get('perusahaan', {}))

    def summary(self) -> Dict:
        """Get config summary"""
        self.auto_reload_if_changed()
        companies = self.data.get('perusahaan', {})
        return {
            'total_companies': len(companies),
            'companies': list(companies.keys()),
            'companies_data': list(companies.values())
        }
    

    def get_company(self, nama: str) -> Optional[Dict]:
        """Get company config (auto-reload if changed)"""
        self.auto_reload_if_changed()
        return self.data.get('perusahaan', {}).get(nama)
    
    def get_mapping_tetap(self, kelompok_jabatan: str, level_bod: str, 
                         dimensi: str) -> Optional[Dict]:
        self.auto_reload_if_changed()
        try:
            mapping = self.data.get('mapping_cell', {}).get('TETAP', {})
            return (mapping
                   .get(kelompok_jabatan, {})
                   .get(level_bod, {})
                   .get(dimensi))
        except (KeyError, AttributeError):
            return None
    
    def get_mapping_tidak_tetap(self, kelompok_jabatan: str, 
                               kategori_jabatan: str, 
                               dimensi: str) -> Optional[Dict]:
        self.auto_reload_if_changed()
        try:
            mapping = self.data.get('mapping_cell', {}).get('TIDAK TETAP', {})
            return (mapping
                   .get(kelompok_jabatan, {})
                   .get(kategori_jabatan, {})
                   .get(dimensi))
        except (KeyError, AttributeError):
            return None
    
    def get_level_definitions(self, status_pegawai: str) -> List[Dict]:
        """          
            >>> config.get_level_definitions('TETAP')
            [
                {'kelompok_jabatan': 'KARPEL', 'level_bod': 'BOD-6'},
                {'kelompok_jabatan': 'KARPEL', 'level_bod': 'BOD-5'},
                ...
            ]
        """
        self.auto_reload_if_changed()
        return (self.data.get('level_definitions', {})
               .get(status_pegawai, []))
    
    def get_available_dimensions(self, status_pegawai: str, 
                                kelompok_jabatan: str,
                                level_bod: str = None,
                                kategori_jabatan: str = None) -> List[str]:
        """
        Get list of available dimensions untuk specific level.

            status_pegawai: 'TETAP' atau 'TIDAK TETAP'
            kelompok_jabatan: 'KARPEL' atau 'KARPIM'
            level_bod: Required for TETAP ('BOD-1' to 'BOD-6')
            kategori_jabatan: Required for TIDAK TETAP ('PKWT', etc)

            >>> config.get_available_dimensions('TETAP', 'KARPEL', level_bod='BOD-6')
            ['usia', 'gender', 'pendidikan', 'unit_kerja']
            
            >>> config.get_available_dimensions('TIDAK TETAP', 'KARPIM', kategori_jabatan='PKWT')
            ['gender', 'unit_kerja']
        """
        self.auto_reload_if_changed()
        try:
            mapping = self.data.get('mapping_cell', {}).get(status_pegawai, {})
            
            if status_pegawai == 'TETAP':
                target = (mapping
                         .get(kelompok_jabatan, {})
                         .get(level_bod, {}))
            else:  # TIDAK TETAP
                target = (mapping
                         .get(kelompok_jabatan, {})
                         .get(kategori_jabatan, {}))
            
            return list(target.keys())
        except:
            return []
    
    def get_companies_list(self) -> list:
        """Get list of company names (auto-reload if changed)"""
        self.auto_reload_if_changed()
        return list(self.data.get('perusahaan', {}).keys())
    
    def has_company(self, nama: str) -> bool:
        """Check if company exists (auto-reload if changed)"""
        self.auto_reload_if_changed()
        return nama in self.data.get('perusahaan', {})


_config_instance: Optional[Config] = None


def load_config(config_path: str = "config/demografi.json") -> Config:
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


def get_config() -> Config:
    global _config_instance
    if _config_instance is None:
        _config_instance = load_config()
    return _config_instance


def reload_config() -> bool:
    """Force reload config from file"""
    config = get_config()
    return config.reload()