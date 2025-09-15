"""
Application Path Management

This module provides centralized path management for the Bitcoin Solo Miner Monitoring App.
"""

import os
from pathlib import Path
from typing import Optional


class AppPaths:
    """
    Centralized path management for the application.
    
    This class provides a single source of truth for all application paths,
    using pathlib.Path objects for robust cross-platform path handling.
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize AppPaths with the base application directory.
        
        Args:
            base_path (Optional[Path]): Base application directory. 
                                      If None, uses the project root directory.
        """
        if base_path is None:
            # Get the project root directory (two levels up from this file)
            self._base_path = Path(__file__).parent.parent.parent.parent
        else:
            self._base_path = Path(base_path)
        
        # Ensure base path is absolute
        self._base_path = self._base_path.resolve()
    
    @property
    def base_path(self) -> Path:
        """Get the base application directory."""
        return self._base_path
    
    @property
    def src_path(self) -> Path:
        """Get the source code directory."""
        return self._base_path / "src"
    
    @property
    def backend_path(self) -> Path:
        """Get the backend source directory."""
        return self.src_path / "backend"
    
    @property
    def frontend_path(self) -> Path:
        """Get the frontend source directory."""
        return self.src_path / "frontend"
    
    @property
    def frontend_dist_path(self) -> Path:
        """Get the frontend distribution directory."""
        return self.frontend_path / "dist"
    
    @property
    def config_path(self) -> Path:
        """Get the configuration directory."""
        return self._base_path / "config"
    
    @property
    def data_path(self) -> Path:
        """Get the data directory."""
        return self._base_path / "data"
    
    @property
    def logs_path(self) -> Path:
        """Get the logs directory."""
        return self._base_path / "logs"
    
    @property
    def database_path(self) -> Path:
        """Get the database file path."""
        return self.data_path / "app.db"
    
    @property
    def log_file_path(self) -> Path:
        """Get the main log file path."""
        return self.logs_path / "app.log"
    
    def ensure_directories(self) -> None:
        """
        Ensure all required directories exist.
        
        Creates the data and logs directories if they don't exist.
        """
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
    
    def get_relative_path(self, path: Path) -> Path:
        """
        Get a path relative to the base application directory.
        
        Args:
            path (Path): Absolute path to make relative
            
        Returns:
            Path: Path relative to base directory
        """
        try:
            return path.relative_to(self._base_path)
        except ValueError:
            # Path is not relative to base, return as-is
            return path
    
    def resolve_path(self, path_str: str) -> Path:
        """
        Resolve a path string to an absolute Path object.
        
        Args:
            path_str (str): Path string (can be relative or absolute)
            
        Returns:
            Path: Resolved absolute path
        """
        path = Path(path_str)
        if path.is_absolute():
            return path
        else:
            return (self._base_path / path).resolve()
    
    def is_safe_path(self, path: Path) -> bool:
        """
        Check if a path is safe (within the application directory).
        
        Args:
            path (Path): Path to check
            
        Returns:
            bool: True if path is safe (within app directory)
        """
        try:
            resolved_path = path.resolve()
            resolved_path.relative_to(self._base_path)
            return True
        except ValueError:
            return False
    
    def get_config_file_path(self, filename: str) -> Path:
        """
        Get the path to a configuration file.
        
        Args:
            filename (str): Configuration file name
            
        Returns:
            Path: Path to configuration file
        """
        return self.config_path / filename
    
    def get_data_file_path(self, filename: str) -> Path:
        """
        Get the path to a data file.
        
        Args:
            filename (str): Data file name
            
        Returns:
            Path: Path to data file
        """
        return self.data_path / filename
    
    def get_log_file_path(self, filename: str) -> Path:
        """
        Get the path to a log file.
        
        Args:
            filename (str): Log file name
            
        Returns:
            Path: Path to log file
        """
        return self.logs_path / filename
    
    def __str__(self) -> str:
        """String representation of AppPaths."""
        return f"AppPaths(base_path={self._base_path})"
    
    def __repr__(self) -> str:
        """Detailed string representation of AppPaths."""
        return (
            f"AppPaths(\n"
            f"  base_path={self._base_path},\n"
            f"  data_path={self.data_path},\n"
            f"  logs_path={self.logs_path},\n"
            f"  config_path={self.config_path}\n"
            f")"
        )


# Global instance for easy access
_app_paths: Optional[AppPaths] = None


def get_app_paths(base_path: Optional[Path] = None) -> AppPaths:
    """
    Get the global AppPaths instance.
    
    Args:
        base_path (Optional[Path]): Base path for first initialization
        
    Returns:
        AppPaths: Global AppPaths instance
    """
    global _app_paths
    
    if _app_paths is None:
        _app_paths = AppPaths(base_path)
    
    return _app_paths


def set_app_paths(app_paths: AppPaths) -> None:
    """
    Set the global AppPaths instance.
    
    Args:
        app_paths (AppPaths): AppPaths instance to set as global
    """
    global _app_paths
    _app_paths = app_paths