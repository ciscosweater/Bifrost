import logging
from utils.logger import get_internationalized_logger
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml

logger = get_internationalized_logger()


class SlssteamStatus(Enum):
    """SLSsteam installation status enumeration"""

    NOT_INSTALLED = "not_installed"
    INSTALLED_BAD_CONFIG = "installed_bad_config"
    INSTALLED_GOOD_CONFIG = "installed_good_config"
    ERROR = "error"


class SlssteamChecker:
    """
    SLSsteam installation and configuration checker for Bifrost.

    Verifies:
    1. SLSsteam installation in ~/.local/share/SLSsteam/
    2. SLSsteam.so library presence
    3. config.yaml existence and validity
    4. PlayNotOwnedGames setting (must be 'yes')
    """

    def __init__(self):
        self.home_dir = Path.home()
        self.slssteam_dir = self.home_dir / ".local/share/SLSsteam"
        self.slssteam_lib = self.slssteam_dir / "SLSsteam.so"
        self.config_dir = self.home_dir / ".config/SLSsteam"
        self.config_file = self.config_dir / "config.yaml"
        self.project_root = Path(__file__).parent.parent
        self.slssteam_any_dir = self.project_root / "SLSsteam-Any"
        self.setup_script = self.slssteam_any_dir / "setup.sh"

    def check_installation(self) -> Tuple[SlssteamStatus, Dict[str, Any]]:
        """
        Perform complete SLSsteam installation and configuration check.

        Returns:
            Tuple of (status, details_dict)
        """
        details = {
            "installed": False,
            "library_exists": False,
            "config_exists": False,
            "config_valid": False,
            "play_not_owned_games": None,
            "config_path": str(self.config_file),
            "library_path": str(self.slssteam_lib),
            "error_message": None,
        }

        try:
            # Check 1: Installation directory
            if not self.slssteam_dir.exists():
                details["error_message"] = "SLSsteam directory not found"
                return SlssteamStatus.NOT_INSTALLED, details

            # Check 2: Library file
            if not self.slssteam_lib.exists():
                details["error_message"] = "SLSsteam.so library not found"
                return SlssteamStatus.NOT_INSTALLED, details

            details["installed"] = True
            details["library_exists"] = True

            # Check 3: Config file
            if not self.config_file.exists():
                details["error_message"] = "config.yaml not found"
                return SlssteamStatus.INSTALLED_BAD_CONFIG, details

            details["config_exists"] = True

            # Check 4: Config content and PlayNotOwnedGames
            config_status = self._check_config()
            details.update(config_status["details"])

            if config_status["valid"] and config_status["play_not_owned_games"]:
                return SlssteamStatus.INSTALLED_GOOD_CONFIG, details
            else:
                return SlssteamStatus.INSTALLED_BAD_CONFIG, details

        except Exception as e:
            logger.error(f"Error checking SLSsteam installation: {e}")
            details["error_message"] = str(e)
            return SlssteamStatus.ERROR, details

    def _check_config(self) -> Dict[str, Any]:
        """
        Check SLSsteam configuration file.

        Returns:
            Dict with validation results
        """
        result = {
            "valid": False,
            "play_not_owned_games": False,
            "details": {
                "config_valid": False,
                "play_not_owned_games": None,
                "error_message": None,
            },
        }

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict):
                result["details"]["error_message"] = "Invalid config format"
                return result

            # Check PlayNotOwnedGames setting
            play_not_owned = config.get("PlayNotOwnedGames", "no")
            result["details"]["play_not_owned_games"] = play_not_owned

            # Must be "yes" (case-insensitive) or boolean True
            if (
                isinstance(play_not_owned, str) and play_not_owned.lower() == "yes"
            ) or play_not_owned is True:
                result["play_not_owned_games"] = True
                result["details"]["config_valid"] = True
                result["valid"] = True
            else:
                result["details"]["error_message"] = (
                    f"PlayNotOwnedGames is '{play_not_owned}', must be 'yes'"
                )

        except yaml.YAMLError as e:
            result["details"]["error_message"] = f"YAML parsing error: {e}"
        except Exception as e:
            result["details"]["error_message"] = f"Config read error: {e}"

        return result

    def can_install(self) -> bool:
        """Check if SLSsteam installation is possible"""
        return self.slssteam_any_dir.exists() and self.setup_script.exists()

    def get_installation_commands(self) -> Dict[str, str]:
        """
        Get commands for SLSsteam installation.

        Returns:
            Dict with command descriptions and actual commands
        """
        if not self.can_install():
            return {}

        return {
            "install": f"cd {self.slssteam_any_dir} && ./setup.sh install",
            "uninstall": f"cd {self.slssteam_any_dir} && ./setup.sh uninstall",
        }

    def fix_play_not_owned_games(self) -> bool:
        """
        Fix PlayNotOwnedGames setting in config.yaml.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.config_file.exists():
                return False

            with open(self.config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict):
                return False

            # Update the setting
            config["PlayNotOwnedGames"] = "yes"

            # Write back to file
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            logger.info("Successfully updated PlayNotOwnedGames to 'yes'")
            return True

        except Exception as e:
            logger.error(f"Failed to update PlayNotOwnedGames: {e}")
            return False

    def get_status_message(
        self, status: SlssteamStatus, details: Dict[str, Any]
    ) -> str:
        """Get human-readable status message"""
        messages = {
            SlssteamStatus.NOT_INSTALLED: "SLSsteam not installed",
            SlssteamStatus.INSTALLED_BAD_CONFIG: "SLSsteam installed but misconfigured",
            SlssteamStatus.INSTALLED_GOOD_CONFIG: "SLSsteam ready for use",
            SlssteamStatus.ERROR: f"Error checking SLSsteam: {details.get('error_message', 'Unknown')}",
        }
        return messages.get(status, "Unknown status")

    def get_status_description(
        self, status: SlssteamStatus, details: Dict[str, Any]
    ) -> str:
        """Get detailed status description"""
        if status == SlssteamStatus.NOT_INSTALLED:
            return "SLSsteam is required for Bifrost to function. Click 'Install' to continue."

        elif status == SlssteamStatus.INSTALLED_BAD_CONFIG:
            pno_setting = details.get("play_not_owned_games", "unknown")
            if details.get("config_exists") and not details.get("config_valid"):
                return f"Invalid configuration. PlayNotOwnedGames is '{pno_setting}', should be 'yes'."
            else:
                return "Configuration file not found or invalid."

        elif status == SlssteamStatus.INSTALLED_GOOD_CONFIG:
            return "SLSsteam is properly installed and configured. PlayNotOwnedGames is active."

        elif status == SlssteamStatus.ERROR:
            return f"An error occurred: {details.get('error_message', 'Unknown error')}"
