import os
import sys
import time
import shutil
import tempfile
import subprocess
import logging
import itertools
import re

logger = logging.getLogger(__name__)

# SLScheevo handles its own login - no need for ACCELA login system

class SteamSchemaIntegration:
    def __init__(self):
        self.schema_generator_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
        self.default_output_dir = os.path.join(self.schema_generator_path, 'bins')
        
        # SLScheevo handles its own login - no need for old steam-schema-generator configs
        
        # Steam IDs with public profiles that own a lot of games (same as SLScheevo)
        self.TOP_OWNER_IDS = [
            76561198028121353, 76561197979911851, 76561198017975643, 76561197993544755,
            76561198355953202, 76561198001237877, 76561198237402290, 76561198152618007,
            76561198355625888, 76561198213148949, 76561197969050296, 76561198217186687,
            76561198037867621, 76561198094227663, 76561198019712127, 76561197963550511,
            76561198134044398, 76561198001678750, 76561197973009892, 76561198044596404,
            76561197976597747, 76561197969810632, 76561198095049646, 76561198085065107,
            76561198864213876, 76561197962473290, 76561198388522904, 76561198033715344,
            76561197995070100, 76561198313790296, 76561198063574735, 76561197996432822,
            76561197976968076, 76561198281128349, 76561198154462478, 76561198027233260,
            76561198842864763, 76561198010615256, 76561198035900006, 76561198122859224,
            76561198235911884, 76561198027214426, 76561197970825215, 76561197968410781,
            76561198104323854, 76561198001221571, 76561198256917957, 76561198008181611,
            76561198407953371, 76561198062901118,
        ]
        
        # SLScheevo handles its own login - no need for .env file loading

    

    def get_stats_schema(self, client, game_id, owner_id):
        """Request the stats schema for a game from a specific owner"""
        try:
            from steam.core.msg import MsgProto
            from steam.enums.emsg import EMsg
        except ImportError:
            return None
            
        logger.debug(f"Creating ClientGetUserStats request for game_id={game_id}, owner_id={owner_id}")
        msg = MsgProto(EMsg.ClientGetUserStats)
        msg.body.game_id = game_id  # Don't convert to int - use as-is like SLScheevo
        msg.body.schema_local_version = -1
        msg.body.crc_stats = 0
        msg.body.steam_id_for_user = owner_id

        logger.debug(f"Sending request to Steam for owner {owner_id}")
        client.send(msg)
        logger.debug(f"Waiting for response (timeout=5s) from owner {owner_id}")
        response = client.wait_msg(EMsg.ClientGetUserStatsResponse, timeout=5)
        
        if response is None:
            logger.debug(f"TIMEOUT: No response within 10s from owner {owner_id}")
        else:
            logger.debug(f"RESPONSE RECEIVED from owner {owner_id}")
            
        return response

    def check_single_owner(self, game_id, owner_id, client):
        """Return schema bytes or None"""
        try:
            logger.debug(f"=== CHECKING OWNER {owner_id} ===")
            out = self.get_stats_schema(client, game_id, owner_id)
            
            if out is None:
                logger.debug(f"NO RESPONSE: Steam did not respond to owner {owner_id}")
                return None
                
            # Log detailed response information
            eresult = getattr(out.body, 'eresult', 'N/A')
            has_schema = hasattr(out.body, 'schema')
            schema_len = len(out.body.schema) if has_schema and out.body.schema else 0
            crc_stats = getattr(out.body, 'crc_stats', 'N/A')
            
            logger.debug(f"RESPONSE DETAILS from owner {owner_id}:")
            logger.debug(f"  - eresult: {eresult}")
            logger.debug(f"  - has_schema: {has_schema}")
            logger.debug(f"  - schema_len: {schema_len}")
            logger.debug(f"  - crc_stats: {crc_stats}")
            
            if out and has_schema and out.body.schema:
                if len(out.body.schema) > 0:
                    logger.debug(f"SUCCESS: Valid schema found for owner {owner_id} with {len(out.body.schema)} bytes")
                    return out.body.schema
                else:
                    logger.debug(f"Empty schema for owner {owner_id}")
            
            # Check for the specific "no schema" response pattern
            if (out and hasattr(out.body, 'eresult') and out.body.eresult == 2 and
                hasattr(out.body, 'crc_stats') and out.body.crc_stats == 0):
                logger.debug(f"NO_SCHEMA PATTERN: eresult=2, crc_stats=0 for owner {owner_id}")
                return "NO_SCHEMA"  # Special indicator for no schema
                
            # Check for other error conditions
            if out and hasattr(out.body, 'eresult'):
                eresult = out.body.eresult
                if eresult != 1:  # 1 = OK
                    logger.debug(f"ERROR RESPONSE: eresult={eresult} for owner {owner_id}")
                    return None
                    
        except Exception as e:
            logger.debug(f"EXCEPTION for owner {owner_id}: {e}")
            import traceback
            logger.debug(f"TRACEBACK: {traceback.format_exc()}")
        return None

    def setup_credentials(self, api_key=None, steam_id=None):
        logger.debug(f"setup_credentials called with api_key={bool(api_key)}, steam_id={bool(steam_id)}")
        
        if api_key:
            self.api_key = api_key
        if steam_id:
            # Basic validation for Steam ID
            steam_id = steam_id.strip()
            if steam_id and len(steam_id) > 0:
                self.steam_id = steam_id
                logger.debug(f"Steam ID set to: {self.steam_id}")
        
        # Save credentials to .env file
        try:
            env_vars = {}
            if os.path.exists(self.dotenv_path):
                logger.debug(f"Loading existing .env file: {self.dotenv_path}")
                with open(self.dotenv_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            env_vars[key] = value
            else:
                logger.debug(f"Creating new .env file: {self.dotenv_path}")
                # Create .env file with default content if it doesn't exist
                with open(self.dotenv_path, 'w') as f:
                    f.write("# Steam API Configuration\n")
                    f.write("# Get your API key from: https://steamcommunity.com/dev/apikey\n")
                    f.write("STEAM_API_KEY='YOUR_STEAM_API_KEY_HERE'\n")
                    f.write("\n")
                    f.write("# Steam User ID (optional)\n")
                    f.write("# Find your Steam ID from: https://steamid.io/\n")
                    f.write("STEAM_USER_ID='YOUR_STEAM_USER_ID_HERE'\n")
            
            # Update with new values
            if api_key:
                env_vars['STEAM_API_KEY'] = api_key
                logger.debug(f"Setting STEAM_API_KEY in .env")
            if steam_id and steam_id.strip():
                env_vars['STEAM_USER_ID'] = steam_id.strip()  # Changed from STEAM_ID to STEAM_USER_ID
                logger.debug(f"Setting STEAM_USER_ID in .env: {steam_id.strip()}")
            
            # Write back to .env file
            with open(self.dotenv_path, 'w') as f:
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
            
            logger.info("Steam credentials saved to .env file successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving Steam credentials: {e}")
            return False

    def deep_merge(self, source, destination):
        for key, value in source.items():
            if isinstance(value, dict):
                node = destination.setdefault(key, {})
                self.deep_merge(value, node)
            else:
                destination[key] = value
        return destination

    def get_game_schema_steam_client(self, app_id):
        """Generate stats and schema files using SLScheevo directly"""
        logger.info(f"Generating stats schema for game ID {app_id} using SLScheevo")
        
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
            saved_logins_path = os.path.join(slscheevo_dir, "data", "saved_logins.encrypted")
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
                env['TERM'] = 'dumb'  # Prevent terminal control codes
                
                result = subprocess.run(
                    [slscheevo_exec],
                    input="\n",  # Send newline then EOF
                    capture_output=True,
                    text=True,
                    timeout=3,
                    cwd=slscheevo_dir,
                    env=env
                )
                
                # Parse output for available accounts - look for various patterns
                usernames = []
                output_lines = result.stdout.split('\n') + result.stderr.split('\n')
                
                for line in output_lines:
                    line = line.strip()
                    # Pattern 1: "[1]: username"
                    if re.search(r'\[\d+\]:\s*\w+', line):
                        match = re.search(r'\[\d+\]:\s*(\w+)', line)
                        if match:
                            username = match.group(1)
                            if username and username not in usernames:
                                usernames.append(username)
                    
                    # Pattern 2: "Available accounts:" followed by list
                    elif "Available accounts:" in line:
                        # Look in next few lines for usernames
                        continue
                    
                    # Pattern 3: Just username with number prefix
                    elif re.match(r'^\[\d+\]:', line):
                        parts = line.split(']:', 1)
                        if len(parts) == 2:
                            username = parts[1].strip()
                            if username and username not in usernames:
                                usernames.append(username)
                
                # Alternative: Try to extract from encrypted file using strings
                if not usernames:
                    try:
                        strings_result = subprocess.run(
                            ['strings', saved_logins_path],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        
                        # Look for potential usernames (alphanumeric strings 3-20 chars)
                        for line in strings_result.stdout.split('\n'):
                            line = line.strip()
                            if (re.match(r'^[a-zA-Z0-9_]{3,20}$', line) and 
                                not line.isdigit() and 
                                line not in usernames):
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
            saved_logins_path = os.path.join(slscheevo_dir, "data", "saved_logins.encrypted")
            
            # Try reading as text and look for patterns
            with open(saved_logins_path, 'rb') as f:
                data = f.read()
            
            # Try to decode as UTF-8 with errors ignored
            try:
                text_data = data.decode('utf-8', errors='ignore')
                # Look for alphanumeric patterns that could be usernames
                potential_usernames = re.findall(r'\b[a-zA-Z0-9_]{3,20}\b', text_data)
                
                # Filter out common non-username words
                filtered_usernames = []
                for word in potential_usernames:
                    if (not word.isdigit() and 
                        word.lower() not in ['steam', 'user', 'login', 'pass', 'account'] and
                        len(word) >= 3):
                        filtered_usernames.append(word)
                
                return list(set(filtered_usernames))[:3]  # Remove duplicates, limit to 3
                
            except Exception:
                pass
            
            return []
            
        except Exception:
            return []

    def _run_slscheevo_for_schema(self, app_id_int):
        """Run SLScheevo directly for schema generation - SLScheevo handles its own login!"""
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
                env['TERM'] = 'xterm'  # Proper terminal type
                env['SHELL'] = '/bin/bash'  # Force bash shell
                
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
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
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
                    username = settings.value("slscheevo_username", "", type=str).strip()
                    if username and username not in usernames:
                        logger.warning(f"Configured username '{username}' not found in SLScheevo accounts")
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
                    "--silent",        # Silent mode - no interactive prompts
                    "--appid", str(app_id_int)  # Specify the app ID
                ]
                
                # Add username if available
                if username:
                    cmd.extend(["--login", username])
                    logger.info(f"Using SLScheevo username: {username}")
                else:
                    logger.warning("No SLScheevo username available - will try without login")
                
                logger.info(f"Running SLScheevo: {' '.join(cmd)}")
                logger.info("SLScheevo will use saved credentials if available")
                
                # Run SLScheevo with output capture for better error handling
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    env=env  # Use modified environment
                )
                
                # Clean up wrapper script
                try:
                    os.unlink(wrapper_path)
                except:
                    pass
                
                # Log output for debugging
                if result.stdout:
                    logger.debug(f"SLScheevo stdout: {result.stdout}")
                if result.stderr:
                    logger.debug(f"SLScheevo stderr: {result.stderr}")
                
                # Check return codes
                if result.returncode == 0:
                    logger.info(f"[OK] SLScheevo completed successfully for AppID {app_id_int}")
                    # Copy generated bins to ACCELA data directory
                    self._copy_slscheevo_bins_to_accela(slscheevo_dir)
                    return True
                elif result.returncode == 2:  # EXIT_NO_ACHIEVEMENTS
                    logger.info(f"[INFO] Game {app_id_int} has no achievements - this is normal")
                    # Check if any files were generated anyway
                    if self._check_slscheevo_success(slscheevo_dir, app_id_int):
                        self._copy_slscheevo_bins_to_accela(slscheevo_dir)
                        return True
                    return True  # Not an error - just no achievements
                elif result.returncode == 5:  # EXIT_NO_ACCOUNT_ID
                    logger.error("SLScheevo needs login credentials!")
                    logger.error("Please run SLScheevo manually first to set up your Steam login:")
                    logger.error(f"  cd {slscheevo_dir}")
                    logger.error(f"  ./SLScheevo")
                    logger.error("After logging in once, your credentials will be saved and ACCELA can use SLScheevo automatically.")
                    return False
                elif result.returncode == 6:  # EXIT_INVALID_APPID
                    logger.error(f"Invalid AppID {app_id_int} provided to SLScheevo")
                    return False
                else:
                    # Check if SLScheevo actually succeeded despite the exit code
                    if self._check_slscheevo_success(slscheevo_dir, app_id_int):
                        logger.info(f"[OK] SLScheevo completed successfully for AppID {app_id_int} (exit code {result.returncode})")
                        # Copy generated bins to ACCELA data directory
                        self._copy_slscheevo_bins_to_accela(slscheevo_dir)
                        return True
                    
                    # Check if this is a "no achievements" case
                    stdout_lower = result.stdout.lower()
                    stderr_lower = result.stderr.lower()
                    if ("no achievement" in stdout_lower or "no schema" in stdout_lower or 
                        "has no achievements" in stdout_lower or "no stats" in stdout_lower):
                        logger.info(f"[INFO] Game {app_id_int} has no achievements")
                        return True
                    
                    logger.error(f"[X] SLScheevo failed with return code {result.returncode}")
                    if result.stderr:
                        # Filter out common Linux warnings
                        stderr_filtered = result.stderr.replace("sh: line 1: cls: command not found\n", "")
                        stderr_filtered = stderr_filtered.replace("TERM environment variable not set.\n", "")
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
    
    def _get_slscheevo_accounts(self, slscheevo_data_dir):
        """Try to extract available account names from SLScheevo data"""
        try:
            # This is a simple heuristic - in reality, the accounts are encrypted
            # For now, we'll return empty list and let SLScheevo handle account selection
            return []
        except Exception:
            return []
    
    def _check_slscheevo_success(self, slscheevo_dir, app_id_int):
        """Check if SLScheevo actually generated files for the app"""
        try:
            bins_dir = os.path.join(slscheevo_dir, "data", "bins")
            if not os.path.exists(bins_dir):
                return False
            
            # Look for any files related to this app_id
            app_files = []
            for filename in os.listdir(bins_dir):
                if str(app_id_int) in filename:
                    app_files.append(filename)
            
            if app_files:
                logger.debug(f"Found generated files for AppID {app_id_int}: {app_files}")
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking SLScheevo success: {e}")
            return False

    def _copy_slscheevo_bins_to_accela(self, slscheevo_path):
        """Copy generated bin files from SLScheevo to ACCELA"""
        try:
            slscheevo_data_dir = os.path.join(slscheevo_path, "data", "bins")
            accela_data_dir = self.default_output_dir
            
            if not os.path.exists(slscheevo_data_dir):
                logger.warning(f"SLScheevo bins directory not found: {slscheevo_data_dir}")
                return
            
            # Create ACCELA data directory if it doesn't exist
            os.makedirs(accela_data_dir, exist_ok=True)
            
            # Copy all bin files
            copied_count = 0
            for file_path in os.listdir(slscheevo_data_dir):
                if file_path.endswith('.bin'):
                    src_file = os.path.join(slscheevo_data_dir, file_path)
                    dst_file = os.path.join(accela_data_dir, file_path)
                    
                    shutil.copy2(src_file, dst_file)
                    copied_count += 1
                    logger.info(f"Copied {file_path} for SLScheevo integration")
            
            logger.info(f"Copied {copied_count} bin files for SLScheevo integration")
            
        except Exception as e:
            logger.error(f"Error copying SLScheevo bins: {e}")
    
    def _check_slscheevo_success(self, slscheevo_dir, app_id_int):
        """Check if SLScheevo actually succeeded by looking for generated files"""
        try:
            slscheevo_data_dir = os.path.join(slscheevo_dir, "data", "bins")
            
            # Check for the specific schema file
            schema_file = os.path.join(slscheevo_data_dir, f"UserGameStatsSchema_{app_id_int}.bin")
            stats_file = os.path.join(slscheevo_data_dir, f"UserGameStats_104148900_{app_id_int}.bin")
            
            if os.path.exists(schema_file) and os.path.exists(stats_file):
                logger.info(f"[OK] Found generated schema files for AppID {app_id_int}")
                return True
            else:
                logger.warning(f"Schema files not found for AppID {app_id_int}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking SLScheevo success: {e}")
            return False

    def get_game_schema(self, app_id, mode='update'):
        # SLScheevo handles its own login - no credential check needed
        return self.get_game_schema_steam_client(app_id)

    def generate_schema_for_downloaded_game(self, app_id, mode=None):
        logger.info(f"Generating schema for downloaded game {app_id}")
        return self.get_game_schema(app_id)

    def is_available(self):
        return True
