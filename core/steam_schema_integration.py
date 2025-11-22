import os
import re
import shutil
import subprocess
from utils.logger import get_internationalized_logger
from utils.i18n import tr

logger = get_internationalized_logger("SteamSchema")

# SLScheevo handles its own login - no need for Bifrost login system


class SteamSchemaIntegration:
    def __init__(self):
        self.schema_generator_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data"
        )
        self.default_output_dir = os.path.join(self.schema_generator_path, "bins")

    def get_game_schema_steam_client(self, app_id):
        """Generate stats and schema files using SLScheevo directly"""
        logger.info(f"{tr('SteamSchema', 'Generating stats schema for game ID')} {app_id} using SLScheevo")

        # Convert app_id to int
        try:
            app_id_int = int(app_id)
        except ValueError:
            logger.error(f"Invalid app_id format: {app_id}")
            return False

        # Run SLScheevo directly
        return self._run_slscheevo_for_schema(app_id_int)

    def _get_available_slscheevo_usernames(self, slscheevo_dir):
        """Extract available usernames from SLScheevo saved_logins.encrypted"""
        try:
            saved_logins_path = os.path.join(
                slscheevo_dir, "data", "saved_logins.encrypted"
            )
            if not os.path.exists(saved_logins_path):
                logger.debug("No saved_logins.encrypted found")
                return []

            # Try to run SLScheevo in non-interactive mode to get accounts
            slscheevo_exec = os.path.join(slscheevo_dir, "SLScheevo")
            if not os.path.exists(slscheevo_exec):
                return []

            try:
                # Run SLScheevo with very short timeout to get account list
                # Use environment variable to prevent interactive prompts
                env = os.environ.copy()
                env["TERM"] = "dumb"  # Prevent terminal control codes

                result = subprocess.run(
                    [slscheevo_exec],
                    input="\n",  # Send newline then EOF
                    capture_output=True,
                    text=True,
                    timeout=3,
                    cwd=slscheevo_dir,
                    env=env,
                )

                # Parse output for available accounts - look for various patterns
                usernames = []
                output_lines = result.stdout.split("\n") + result.stderr.split("\n")

                for line in output_lines:
                    line = line.strip()
                    # Pattern 1: "[1]: username"
                    if re.search(r"\[\d+\]:\s*\w+", line):
                        match = re.search(r"\[\d+\]:\s*(\w+)", line)
                        if match:
                            username = match.group(1)
                            if username and username not in usernames:
                                usernames.append(username)

                    # Pattern 2: "Available accounts:" followed by list
                    elif "Available accounts:" in line:
                        # Look in next few lines for usernames
                        continue

                    # Pattern 3: Just username with number prefix
                    elif re.match(r"^\[\d+\]:", line):
                        parts = line.split("]:", 1)
                        if len(parts) == 2:
                            username = parts[1].strip()
                            if username and username not in usernames:
                                usernames.append(username)

                # Alternative: Try to extract from encrypted file using strings
                if not usernames:
                    try:
                        strings_result = subprocess.run(
                            ["strings", saved_logins_path],
                            capture_output=True,
                            text=True,
                            timeout=2,
                        )

                        # Look for potential usernames (alphanumeric strings 3-20 chars)
                        for line in strings_result.stdout.split("\n"):
                            line = line.strip()
                            if (
                                re.match(r"^[a-zA-Z0-9_]{3,20}$", line)
                                and not line.isdigit()
                                and line not in usernames
                            ):
                                usernames.append(line)

                    except Exception:
                        pass  # strings command not available or failed

                logger.debug(f"Found SLScheevo usernames: {usernames}")
                return usernames[:5]  # Limit to first 5 usernames

            except subprocess.TimeoutExpired:
                logger.debug("SLScheevo timeout while getting usernames")
                # Try fallback method
                return self._fallback_username_extraction(slscheevo_dir)
            except Exception as e:
                logger.debug(f"Error getting SLScheevo usernames: {e}")
                return []

        except Exception as e:
            logger.debug(f"Error accessing SLScheevo data: {e}")
            return []

    def _fallback_username_extraction(self, slscheevo_dir):
        """Fallback method to extract usernames from file analysis"""
        try:
            saved_logins_path = os.path.join(
                slscheevo_dir, "data", "saved_logins.encrypted"
            )

            # Try reading as text and look for patterns
            with open(saved_logins_path, "rb") as f:
                data = f.read()

            # Try to decode as UTF-8 with errors ignored
            try:
                text_data = data.decode("utf-8", errors="ignore")
                # Look for alphanumeric patterns that could be usernames
                potential_usernames = re.findall(r"\b[a-zA-Z0-9_]{3,20}\b", text_data)

                # Filter out common non-username words
                filtered_usernames = []
                for word in potential_usernames:
                    if (
                        not word.isdigit()
                        and word.lower()
                        not in ["steam", "user", "login", "pass", "account"]
                        and len(word) >= 3
                    ):
                        filtered_usernames.append(word)

                return list(set(filtered_usernames))[
                    :3
                ]  # Remove duplicates, limit to 3

            except Exception:
                pass

            return []

        except Exception:
            return []

    def _run_slscheevo_for_schema(self, app_id_int):
        """Run SLScheevo directly for schema generation - SLScheevo handles its own login!"""
        from utils.i18n import tr
        
        try:
            # Path to SLScheevo BUILD (local copy)
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            slscheevo_build = os.path.join(current_dir, "slscheevo_build", "SLScheevo")

            if not os.path.exists(slscheevo_build):
                logger.error(f"SLScheevo build not found at {slscheevo_build}")
                return False

            # Check if SLScheevo is executable
            if not os.access(slscheevo_build, os.X_OK):
                logger.error(f"SLScheevo is not executable: {slscheevo_build}")
                # Try to make it executable
                try:
                    os.chmod(slscheevo_build, 0o755)
                    logger.info("Made SLScheevo executable")
                except Exception as e:
                    logger.error(f"Could not make SLScheevo executable: {e}")
                    return False

            # Change to SLScheevo build directory and run it
            original_cwd = os.getcwd()
            slscheevo_dir = os.path.dirname(slscheevo_build)

            try:
                os.chdir(slscheevo_dir)

                # Set environment variables to prevent Windows-specific commands
                env = os.environ.copy()
                env["TERM"] = "xterm"  # Proper terminal type
                env["SHELL"] = "/bin/bash"  # Force bash shell

                # Create a wrapper script to handle Windows cls command on Linux
                wrapper_script = f'''#!/bin/bash
# Create alias for Windows cls command
cls() {{
    clear
}}
export -f cls

# Run SLScheevo with original arguments
exec "{slscheevo_build}" "$@"
'''

                # Write wrapper script to temporary file
                import tempfile

                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".sh", delete=False
                ) as f:
                    f.write(wrapper_script)
                    wrapper_path = f.name

                # Make wrapper executable
                os.chmod(wrapper_path, 0o755)

                # Get available usernames dynamically
                usernames = self._get_available_slscheevo_usernames(slscheevo_dir)

                # Try to get username from settings first, then use first available
                username = None
                try:
                    from utils.settings import get_settings

                    settings = get_settings()
                    username = settings.value(
                        "slscheevo_username", "", type=str
                    ).strip()
                    if username and username not in usernames:
                        logger.warning(
                            f"Configured username '{username}' not found in SLScheevo accounts"
                        )
                        username = None
                except Exception as e:
                    logger.debug(f"Error getting SLScheevo username from settings: {e}")

                # Use first available username if no specific one configured
                if not username and usernames:
                    username = usernames[0]
                    logger.info(f"Using first available SLScheevo username: {username}")

                # Build SLScheevo command for specific app_id using wrapper
                cmd = [
                    wrapper_path,
                    "--silent",  # Silent mode - no interactive prompts
                    "--appid",
                    str(app_id_int),  # Specify the app ID
                ]

                # Add username if available
                if username:
                    cmd.extend(["--login", username])
                    logger.info(f"{tr('SteamSchema', 'Using SLScheevo username')}: {username}")
                else:
                    logger.warning(
                        "No SLScheevo username available - will try without login"
                    )

                logger.info(f"{tr('SteamSchema', 'Running SLScheevo')}: {' '.join(cmd)}")
                logger.info(tr("SteamSchema", "SLScheevo will use saved credentials if available"))

                # Run SLScheevo with output capture for better error handling
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    env=env,  # Use modified environment
                )

                # Clean up wrapper script
                try:
                    os.unlink(wrapper_path)
                except (AttributeError, TypeError):
                    pass

                # Log output for debugging
                if result.stdout:
                    logger.debug(f"SLScheevo stdout: {result.stdout}")
                if result.stderr:
                    logger.debug(f"SLScheevo stderr: {result.stderr}")

                # Check return codes
                if result.returncode == 0:
                    logger.info(
                        f"[OK] SLScheevo completed successfully for AppID {app_id_int}"
                    )
                    # Copy generated bins to Bifrost data directory
                    self._copy_slscheevo_bins_to_bifrost(slscheevo_dir)
                    return True
                elif result.returncode == 2:  # EXIT_NO_ACHIEVEMENTS
                    logger.info(
                        f"[INFO] Game {app_id_int} has no achievements - this is normal"
                    )
                    # Check if any files were generated anyway
                    if self._check_slscheevo_success(slscheevo_dir, app_id_int):
                        self._copy_slscheevo_bins_to_bifrost(slscheevo_dir)
                        return True
                    return True  # Not an error - just no achievements
                elif result.returncode == 5:  # EXIT_NO_ACCOUNT_ID
                    logger.error("SLScheevo needs login credentials!")
                    logger.error(
                        "Please run SLScheevo manually first to set up your Steam login:"
                    )
                    logger.error(f"  cd {slscheevo_dir}")
                    logger.error("  ./SLScheevo")
                    logger.error(
                        "After logging in once, your credentials will be saved and Bifrost can use SLScheevo automatically."
                    )
                    return False
                elif result.returncode == 6:  # EXIT_INVALID_APPID
                    logger.error(f"Invalid AppID {app_id_int} provided to SLScheevo")
                    return False
                else:
                    # Check if SLScheevo actually succeeded despite the exit code
                    if self._check_slscheevo_success(slscheevo_dir, app_id_int):
                        logger.info(
                            f"[OK] SLScheevo completed successfully for AppID {app_id_int} (exit code {result.returncode})"
                        )
                        # Copy generated bins to Bifrost data directory
                        self._copy_slscheevo_bins_to_bifrost(slscheevo_dir)
                        return True

                    # Check if this is a "no achievements" case
                    stdout_lower = result.stdout.lower()
                    if (
                        "no achievement" in stdout_lower
                        or "no schema" in stdout_lower
                        or "has no achievements" in stdout_lower
                        or "no stats" in stdout_lower
                    ):
                        logger.info(f"[INFO] Game {app_id_int} has no achievements")
                        return True

                    logger.error(
                        f"[X] {tr('SteamSchema', 'SLScheevo failed with return code')} {result.returncode}"
                    )
                    if result.stderr:
                        # Filter out common Linux warnings
                        stderr_filtered = result.stderr.replace(
                            "sh: line 1: cls: command not found\n", ""
                        )
                        stderr_filtered = stderr_filtered.replace(
                            "TERM environment variable not set.\n", ""
                        )
                        if stderr_filtered.strip():
                            logger.error(f"Error details: {stderr_filtered}")
                    return False

            finally:
                os.chdir(original_cwd)

        except subprocess.TimeoutExpired:
            logger.error("SLScheevo execution timed out")
            return False
        except Exception as e:
            logger.error(f"Error running SLScheevo: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def _copy_slscheevo_bins_to_bifrost(self, slscheevo_path):
        """Copy generated bin files from SLScheevo to Bifrost"""
        try:
            slscheevo_data_dir = os.path.join(slscheevo_path, "data", "bins")
            bifrost_data_dir = self.default_output_dir

            if not os.path.exists(slscheevo_data_dir):
                logger.warning(
                    f"SLScheevo bins directory not found: {slscheevo_data_dir}"
                )
                return

            # Create Bifrost data directory if it doesn't exist
            os.makedirs(bifrost_data_dir, exist_ok=True)

            # Copy all bin files
            copied_count = 0
            for file_path in os.listdir(slscheevo_data_dir):
                if file_path.endswith(".bin"):
                    src_file = os.path.join(slscheevo_data_dir, file_path)
                    dst_file = os.path.join(bifrost_data_dir, file_path)

                    shutil.copy2(src_file, dst_file)
                    copied_count += 1
                    logger.info(f"Copied {file_path} for SLScheevo integration")

            logger.info(f"Copied {copied_count} bin files for SLScheevo integration")

        except Exception as e:
            logger.error(f"Error copying SLScheevo bins: {e}")

    def _check_slscheevo_success(self, slscheevo_dir, app_id_int):
        """Check if SLScheevo actually succeeded by looking for generated files"""
        from utils.i18n import tr
        
        try:
            slscheevo_data_dir = os.path.join(slscheevo_dir, "data", "bins")

            # Check for the specific schema file
            schema_file = os.path.join(
                slscheevo_data_dir, f"UserGameStatsSchema_{app_id_int}.bin"
            )
            stats_file = os.path.join(
                slscheevo_data_dir, f"UserGameStats_104148900_{app_id_int}.bin"
            )

            if os.path.exists(schema_file) and os.path.exists(stats_file):
                logger.info(f"[OK] Found generated schema files for AppID {app_id_int}")
                return True
            else:
                logger.warning(f"{tr('SteamSchema', 'Schema files not found for AppID')} {app_id_int}")
                return False

        except Exception as e:
            logger.error(f"Error checking SLScheevo success: {e}")
            return False

    def get_game_schema(self, app_id):
        # SLScheevo handles its own login - no credential check needed
        return self.get_game_schema_steam_client(app_id)

    def generate_schema_for_downloaded_game(self, app_id):
        logger.info(f"Generating schema for downloaded game {app_id}")
        return self.get_game_schema(app_id)

    def is_available(self):
        return True
