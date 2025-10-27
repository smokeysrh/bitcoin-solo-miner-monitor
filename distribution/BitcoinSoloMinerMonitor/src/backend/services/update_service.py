"""
Update Service

This module provides update checking functionality against GitHub releases API.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

import aiohttp
from packaging import version

from src.backend.utils.app_paths import get_app_paths
from src.backend.exceptions import AppError

logger = logging.getLogger(__name__)


class UpdateService:
    """
    Service for checking application updates from GitHub releases.
    """
    
    def __init__(self):
        """
        Initialize the UpdateService.
        """
        self.github_repo = "smokeysrh/bitcoin-solo-miner-monitor"
        self.github_api_url = f"https://api.github.com/repos/{self.github_repo}/releases"
        self.current_version = self._get_current_version()
        self.cache_duration = timedelta(hours=1)  # Cache for 1 hour
        self.cache_file = get_app_paths().data_path / "update_cache.json"
        self._session = None
        
        logger.info(f"UpdateService initialized for repo: {self.github_repo}")
        logger.info(f"Current version: {self.current_version}")
    
    def _get_current_version(self) -> str:
        """
        Get the current application version.
        
        Returns:
            str: Current version string
        """
        try:
            # Try to read version from package.json in frontend
            app_paths = get_app_paths()
            frontend_package_json = app_paths.base_path / "src" / "frontend" / "package.json"
            
            if frontend_package_json.exists():
                with open(frontend_package_json, 'r') as f:
                    package_data = json.load(f)
                    return package_data.get('version', '0.1.0')
            
            # Fallback to default version
            return '0.1.0'
            
        except Exception as e:
            logger.warning(f"Could not determine current version: {e}")
            return '0.1.0'
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create HTTP session.
        
        Returns:
            aiohttp.ClientSession: HTTP session
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                'User-Agent': f'Bitcoin-Solo-Miner-Monitor/{self.current_version}',
                'Accept': 'application/vnd.github.v3+json'
            }
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
        return self._session
    
    async def close(self):
        """
        Close the HTTP session.
        """
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _load_cache(self) -> Optional[Dict[str, Any]]:
        """
        Load cached update information.
        
        Returns:
            Optional[Dict[str, Any]]: Cached data or None
        """
        try:
            if not self.cache_file.exists():
                return None
            
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cache is still valid
            cache_time = datetime.fromisoformat(cache_data.get('timestamp', ''))
            if datetime.now() - cache_time < self.cache_duration:
                logger.debug("Using cached update information")
                return cache_data
            else:
                logger.debug("Cache expired, will fetch fresh data")
                return None
                
        except Exception as e:
            logger.warning(f"Failed to load update cache: {e}")
            return None
    
    def _save_cache(self, data: Dict[str, Any]):
        """
        Save update information to cache.
        
        Args:
            data (Dict[str, Any]): Data to cache
        """
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            # Ensure cache directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            logger.debug("Update information cached successfully")
            
        except Exception as e:
            logger.warning(f"Failed to save update cache: {e}")
    
    async def check_for_updates(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Check for available updates from GitHub releases.
        
        Args:
            force_refresh (bool): Force refresh ignoring cache
            
        Returns:
            Dict[str, Any]: Update information
        """
        try:
            # Try to use cache first unless forced refresh
            if not force_refresh:
                cached_data = self._load_cache()
                if cached_data:
                    return cached_data['data']
            
            logger.info("Checking for updates from GitHub releases API")
            
            session = await self._get_session()
            
            # Fetch latest releases
            async with session.get(self.github_api_url) as response:
                if response.status == 200:
                    releases = await response.json()
                    
                    if not releases:
                        logger.info("No releases found")
                        return {
                            'update_available': False,
                            'current_version': self.current_version,
                            'message': 'No releases found'
                        }
                    
                    # Find the latest stable release (not pre-release)
                    latest_release = None
                    for release in releases:
                        if not release.get('prerelease', False) and not release.get('draft', False):
                            latest_release = release
                            break
                    
                    if not latest_release:
                        logger.info("No stable releases found")
                        return {
                            'update_available': False,
                            'current_version': self.current_version,
                            'message': 'No stable releases found'
                        }
                    
                    # Parse version information
                    latest_version = latest_release['tag_name'].lstrip('v')
                    current_version_clean = self.current_version.lstrip('v')
                    
                    # Compare versions
                    try:
                        is_newer = version.parse(latest_version) > version.parse(current_version_clean)
                    except Exception as e:
                        logger.warning(f"Version comparison failed: {e}")
                        # Fallback to string comparison
                        is_newer = latest_version != current_version_clean
                    
                    # Prepare update information
                    update_info = {
                        'update_available': is_newer,
                        'current_version': self.current_version,
                        'latest_version': latest_version,
                        'release_name': latest_release.get('name', latest_version),
                        'release_notes': latest_release.get('body', ''),
                        'release_date': latest_release.get('published_at', ''),
                        'download_url': latest_release.get('html_url', ''),
                        'assets': self._parse_release_assets(latest_release.get('assets', [])),
                        'checked_at': datetime.now().isoformat()
                    }
                    
                    # Cache the result
                    self._save_cache(update_info)
                    
                    if is_newer:
                        logger.info(f"Update available: {self.current_version} -> {latest_version}")
                    else:
                        logger.info(f"Application is up to date: {self.current_version}")
                    
                    return update_info
                
                elif response.status == 403:
                    # Rate limited
                    logger.warning("GitHub API rate limit exceeded")
                    return {
                        'update_available': False,
                        'current_version': self.current_version,
                        'error': 'Rate limit exceeded. Please try again later.',
                        'checked_at': datetime.now().isoformat()
                    }
                
                else:
                    logger.error(f"GitHub API request failed: {response.status}")
                    return {
                        'update_available': False,
                        'current_version': self.current_version,
                        'error': f'Failed to check for updates (HTTP {response.status})',
                        'checked_at': datetime.now().isoformat()
                    }
        
        except asyncio.TimeoutError:
            logger.error("Timeout while checking for updates")
            return {
                'update_available': False,
                'current_version': self.current_version,
                'error': 'Timeout while checking for updates',
                'checked_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return {
                'update_available': False,
                'current_version': self.current_version,
                'error': f'Error checking for updates: {str(e)}',
                'checked_at': datetime.now().isoformat()
            }
    
    def _parse_release_assets(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse release assets for download information.
        
        Args:
            assets (List[Dict[str, Any]]): Raw asset data from GitHub API
            
        Returns:
            List[Dict[str, Any]]: Parsed asset information
        """
        parsed_assets = []
        
        for asset in assets:
            parsed_asset = {
                'name': asset.get('name', ''),
                'size': asset.get('size', 0),
                'download_count': asset.get('download_count', 0),
                'download_url': asset.get('browser_download_url', ''),
                'content_type': asset.get('content_type', ''),
                'created_at': asset.get('created_at', ''),
                'updated_at': asset.get('updated_at', '')
            }
            
            # Determine platform based on filename
            filename = asset.get('name', '').lower()
            if 'windows' in filename or filename.endswith('.exe'):
                parsed_asset['platform'] = 'windows'
            elif 'macos' in filename or 'darwin' in filename or filename.endswith('.dmg'):
                parsed_asset['platform'] = 'macos'
            elif 'linux' in filename or filename.endswith('.deb') or filename.endswith('.rpm') or filename.endswith('.appimage'):
                parsed_asset['platform'] = 'linux'
            else:
                parsed_asset['platform'] = 'unknown'
            
            parsed_assets.append(parsed_asset)
        
        return parsed_assets
    
    async def get_update_status(self) -> Dict[str, Any]:
        """
        Get current update status (uses cache if available).
        
        Returns:
            Dict[str, Any]: Update status information
        """
        # Try to get cached data first
        cached_data = self._load_cache()
        if cached_data:
            return cached_data['data']
        
        # If no cache, perform a quick check
        return await self.check_for_updates()
    
    def get_download_instructions(self, platform: str = None) -> Dict[str, Any]:
        """
        Get download and installation instructions for updates.
        
        Args:
            platform (str): Target platform (windows, macos, linux)
            
        Returns:
            Dict[str, Any]: Download instructions
        """
        instructions = {
            'windows': {
                'title': 'Windows Update Instructions',
                'steps': [
                    '1. Download the latest Windows installer (.exe file)',
                    '2. Close the Bitcoin Solo Miner Monitor application',
                    '3. Run the downloaded installer as Administrator',
                    '4. Follow the installation wizard prompts',
                    '5. The installer will automatically update your existing installation',
                    '6. Launch the application to verify the update'
                ],
                'notes': [
                    'Your miner configurations and settings will be preserved',
                    'Windows may show security warnings for unsigned software - this is normal for open-source applications',
                    'If Windows Defender blocks the installer, add an exception or temporarily disable real-time protection'
                ]
            },
            'macos': {
                'title': 'macOS Update Instructions',
                'steps': [
                    '1. Download the latest macOS disk image (.dmg file)',
                    '2. Close the Bitcoin Solo Miner Monitor application',
                    '3. Open the downloaded .dmg file',
                    '4. Drag the application to your Applications folder (replace existing)',
                    '5. Launch the updated application from Applications',
                    '6. Verify the new version in the About dialog'
                ],
                'notes': [
                    'Your miner configurations and settings will be preserved',
                    'macOS may require you to allow the application in Security & Privacy settings',
                    'The application is not notarized, so you may need to right-click and select "Open" the first time'
                ]
            },
            'linux': {
                'title': 'Linux Update Instructions',
                'steps': [
                    '1. Download the appropriate package for your distribution (.deb, .rpm, or .AppImage)',
                    '2. Close the Bitcoin Solo Miner Monitor application',
                    '3. Install the package using your package manager or run the AppImage',
                    '4. For .deb: sudo dpkg -i bitcoin-solo-miner-monitor_*.deb',
                    '5. For .rpm: sudo rpm -U bitcoin-solo-miner-monitor-*.rpm',
                    '6. For AppImage: make executable and run directly',
                    '7. Launch the updated application'
                ],
                'notes': [
                    'Your miner configurations and settings will be preserved',
                    'Package installation may require administrator privileges',
                    'AppImage provides a portable option that doesn\'t require installation'
                ]
            }
        }
        
        if platform and platform in instructions:
            return instructions[platform]
        
        return {
            'title': 'Update Instructions',
            'message': 'Please visit the GitHub releases page for platform-specific download and installation instructions.',
            'platforms': list(instructions.keys())
        }