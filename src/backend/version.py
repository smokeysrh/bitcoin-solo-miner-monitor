"""
Bitcoin Solo Miner Monitor - Version Information
"""

__version__ = "0.9.1"
__version_info__ = (0, 9, 1)

# Version history
VERSION_HISTORY = {
    "0.9.1": "Bug fixes and code cleanup - Fixed MinerDetail page refresh bug",
    "0.9.0": "Network topology page and enhanced monitoring features",
    "0.5.0": "Initial stable release with core monitoring features",
}

def get_version():
    """Return the current version string."""
    return __version__

def get_version_info():
    """Return the version as a tuple."""
    return __version_info__
