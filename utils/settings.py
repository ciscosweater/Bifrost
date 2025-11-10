from PyQt6.QtCore import QSettings

# --- Constants for QSettings ---
APP_NAME = "ACCELA"
ORG_NAME = "ACCELA"

# --- Steam Schema Generator Settings ---
STEAM_SCHEMA_SETTINGS = {
    "enabled": {
        "default": True,
        "type": bool,
        "description": "Enable automatic Steam Schema generation after downloads"
    },
    "mode": {
        "default": "update",
        "type": str,
        "description": "Schema handling mode: 'overwrite', 'update', or 'skip'"
    },
    "auto_setup_credentials": {
        "default": False,
        "type": bool,
        "description": "Automatically prompt for Steam API credentials if not configured"
    }
}

# --- SLSsteam Integration Settings ---
# Note: Only slssteam_mode is currently implemented and functional

# --- Logging Settings ---
LOGGING_SETTINGS = {
    "simple_mode": {
        "default": True,
        "type": bool,
        "description": "Enable simplified log format (less verbose)"
    },
    "level": {
        "default": "WARNING",
        "type": str,
        "description": "Minimum log level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    }
}

def get_settings():
    """
    Provides a global access point to the application's QSettings object.
    """
    return QSettings(ORG_NAME, APP_NAME)

def get_steam_schema_setting(key, default=None):
    """
    Get a Steam Schema Generator setting with proper type conversion.
    
    Args:
        key (str): Setting key
        default: Default value if setting not found
        
    Returns:
        Setting value with proper type
    """
    settings = get_settings()
    setting_config = STEAM_SCHEMA_SETTINGS.get(key, {})
    
    if not setting_config:
        return default
    
    value = settings.value(f"steam_schema/{key}", setting_config["default"])
    
    # Type conversion
    if setting_config["type"] == bool:
        return bool(value)
    elif setting_config["type"] == int:
        return int(value) if value is not None else setting_config["default"]
    else:
        return value



def set_steam_schema_setting(key, value):
    """
    Set a Steam Schema Generator setting.
    
    Args:
        key (str): Setting key
        value: Setting value
    """
    settings = get_settings()
    settings.setValue(f"steam_schema/{key}", value)

def is_steam_schema_enabled():
    """Check if Steam Schema generation is enabled."""
    return get_steam_schema_setting("enabled", True)

def should_auto_setup_credentials():
    """Check if credentials should be auto-configured."""
    return get_steam_schema_setting("auto_setup_credentials", False)

def get_logging_setting(key, default=None):
    """
    Get a logging setting with proper type conversion.
    
    Args:
        key (str): Setting key
        default: Default value if setting not found
        
    Returns:
        Setting value with proper type
    """
    settings = get_settings()
    setting_config = LOGGING_SETTINGS.get(key, {})
    
    if not setting_config:
        return default
    
    value = settings.value(f"logging/{key}", setting_config["default"])
    
    # Type conversion
    if setting_config["type"] == bool:
        return bool(value)
    elif setting_config["type"] == int:
        return int(value) if value is not None else setting_config["default"]
    else:
        return value

def set_logging_setting(key, value):
    """
    Set a logging setting.
    
    Args:
        key (str): Setting key
        value: Setting value
    """
    settings = get_settings()
    setting_config = LOGGING_SETTINGS.get(key, {})
    
    if setting_config:
        # Type validation
        if setting_config["type"] == bool and not isinstance(value, bool):
            value = bool(value)
        elif setting_config["type"] == int and not isinstance(value, int):
            value = int(value) if value is not None else setting_config["default"]
    
    settings.setValue(f"logging/{key}", value)
    settings.sync()
