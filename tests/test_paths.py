"""Test script to check path detection"""
import sys
from pathlib import Path

# Test with local source
sys.path.insert(0, "src")

from backend.utils.app_paths import AppPaths

# Simulate Program Files installation
app_paths = AppPaths(Path(r"C:\Program Files (x86)\Bitcoin Solo Miner Monitor"))

print(f"Base path: {app_paths.base_path}")
print(f"Use user dirs: {app_paths._use_user_dirs}")
print(f"Data path: {app_paths.data_path}")
print(f"Logs path: {app_paths.logs_path}")
print(f"Database path: {app_paths.database_path}")

# Test resolve_path with relative paths
print(f"\nTesting resolve_path:")
data_db = app_paths.resolve_path('data/config.db')
logs_file = app_paths.resolve_path('logs/app.log')
config_file = app_paths.resolve_path('config/settings.json')
print(f"  'data/config.db' -> {data_db}")
print(f"  'logs/app.log' -> {logs_file}")
print(f"  'config/settings.json' -> {config_file}")

# Test is_safe_path
print(f"\nTesting is_safe_path:")
print(f"  data/config.db is safe: {app_paths.is_safe_path(data_db)}")
print(f"  logs/app.log is safe: {app_paths.is_safe_path(logs_file)}")
print(f"  config/settings.json is safe: {app_paths.is_safe_path(config_file)}")
print(f"  C:\\Windows\\System32\\evil.exe is safe: {app_paths.is_safe_path(Path('C:\\Windows\\System32\\evil.exe'))}")

# Test the readonly detection
base_str = str(app_paths.base_path).lower().replace('\\', '/')
print(f"\nBase string for detection: {base_str}")
print(f"Contains 'program files (x86)': {'program files (x86)' in base_str}")
