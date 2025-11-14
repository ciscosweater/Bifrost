import zipfile
import re
import os
from ui.assets import DEPOT_BLACKLIST
from core.steam_api import get_depot_info_from_api
from core.ini_parser import parse_depots_ini
from utils.logger import get_internationalized_logger
from utils.i18n import tr

logger = get_internationalized_logger("ProcessZip")

KNOWN_DEPOT_DESCRIPTIONS = parse_depots_ini()

class ProcessZipTask:
    def _parse_lua(self, content, game_data):
        logger.debug("Starting LUA content parsing...")
        try:
            all_app_matches = list(re.finditer(r'addappid\((.*?)\)(.*)', content, re.IGNORECASE))
            if not all_app_matches:
                raise ValueError("LUA file is invalid; no 'addappid' entries found.")

            first_app_match = all_app_matches.pop(0)
            first_app_args = first_app_match.group(1).strip()
            game_data['appid'] = first_app_args.split(',')[0].strip()
            
            comment_part = first_app_match.group(2)
            game_name_match = re.search(r'--\s*(.*)', comment_part)
            game_data['game_name'] = game_name_match.group(1).strip() if game_name_match else f"App_{game_data['appid']}"

            game_data['depots'] = {}
            game_data['dlcs'] = {}
            for match in all_app_matches:
                args_str = match.group(1).strip()
                args = [arg.strip() for arg in args_str.split(',')]
                app_id = args[0]
                
                comment_part = match.group(2)
                desc_match = re.search(r'--\s*(.*)', comment_part)
                desc = desc_match.group(1).strip() if desc_match else f"Depot {app_id}"

                if len(args) > 2 and args[2].strip('"'):
                    depot_key = args[2].strip('"') 
                    game_data['depots'][app_id] = {'key': depot_key, 'desc': desc}
                else:
                    game_data['dlcs'][app_id] = desc
        except Exception as e:
            logger.error(f"Critical error during LUA parsing: {e}", exc_info=True)
            raise

    def run(self, zip_path):
        logger.info(tr("ProcessZip", "Starting zip processing task for") + f": {zip_path}")
        game_data = {}
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                lua_files = [f for f in zip_ref.namelist() if f.endswith('.lua')]
                if not lua_files:
                    raise FileNotFoundError("No .lua file found in the zip archive.")
                
                # Processar manifest files com streaming para economizar memória
                manifest_files = {}
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith('.manifest'):
                        with zip_ref.open(file_info) as manifest_file:
                            manifest_content = manifest_file.read()
                            manifest_files[os.path.basename(file_info.filename)] = manifest_content
                
                for depot_id_manifest in manifest_files:
                    parts = depot_id_manifest.replace('.manifest', '').split('_')
                    if len(parts) == 2:
                        game_data.setdefault('manifests', {})[parts[0]] = parts[1]

                # Ler arquivo LUA com streaming para evitar carregar arquivos grandes em memória
                with zip_ref.open(lua_files[0]) as lua_file:
                    # Ler em chunks para arquivos muito grandes
                    lua_content = ""
                    while True:
                        chunk = lua_file.read(8192)  # 8KB chunks
                        if not chunk:
                            break
                        lua_content += chunk.decode('utf-8')
                
                self._parse_lua(lua_content, game_data)
                
                if game_data.get('dlcs'):
                    enriched_dlcs = {}
                    for dlc_id, lua_desc in game_data['dlcs'].items():
                        enriched_dlcs[dlc_id] = KNOWN_DEPOT_DESCRIPTIONS.get(dlc_id, lua_desc)
                    game_data['dlcs'] = enriched_dlcs

                unfiltered_depots = game_data.get('depots', {})
                if not unfiltered_depots:
                    logger.warning("LUA parsing did not identify any depots with keys.")
                else:
                    logger.debug(f"LUA parsing found {len(unfiltered_depots)} depots before filtering.")
                    
                    string_blacklist = {str(item) for item in DEPOT_BLACKLIST}
                    filtered_depots = {
                        depot_id: data
                        for depot_id, data in unfiltered_depots.items()
                        if depot_id not in string_blacklist
                    }
                    if len(unfiltered_depots) > len(filtered_depots):
                        logger.debug(f"Removed {len(unfiltered_depots) - len(filtered_depots)} depots based on blacklist.")
                    
                    game_data['depots'] = filtered_depots
                    
                    if not filtered_depots:
                        logger.warning("All depots were filtered out. No depots to download.")
                    else:
                        api_data = get_depot_info_from_api(game_data['appid']) if game_data.get('appid') else {}
                        
                        # --- MODIFICATION START ---
                        if api_data.get('installdir'):
                            game_data['installdir'] = api_data['installdir']
                            logger.debug(f"Found official install directory: {game_data['installdir']}")
                        
                        # Update game name from Steam API if available
                        if api_data.get('game_name'):
                            game_data['game_name'] = api_data['game_name']
                            logger.debug(f"Found game name from Steam API: {game_data['game_name']}")
                        
                        api_details = api_data.get('depots', {})
                        
                        # Transfer depot sizes to game_data
                        depot_sizes = api_data.get('depot_sizes', {})
                        if depot_sizes:
                            game_data['depot_sizes'] = depot_sizes
                            logger.debug(f"Transferred {len(game_data['depot_sizes'])} depot size entries to game_data")
                        else:
                            logger.warning(tr("SteamApi", "Empty depot_sizes in api_data"))
                            game_data['depot_sizes'] = {}
                        
                        # Transfer total game size to game_data
                        total_game_size = api_data.get('total_game_size', 0)
                        if total_game_size > 0:
                            game_data['total_game_size'] = total_game_size
                            logger.debug(f"Transferred total game size: {total_game_size} bytes ({total_game_size/1024/1024/1024:.2f} GB)")
                        else:
                            logger.warning("Empty total_game_size in api_data")
                            game_data['total_game_size'] = 0
                        # --- MODIFICATION END ---

                        if not api_details:
                            logger.warning("Could not retrieve supplementary details from Steam API.")
                        
                        enriched_depots = {}
                        for depot_id, lua_data in filtered_depots.items():
                            final_depot_data = {'key': lua_data['key']}
                            details = api_details.get(str(depot_id))
                            base_description = KNOWN_DEPOT_DESCRIPTIONS.get(depot_id, lua_data['desc'])
                            
                            if details:
                                tags = []
                                if details.get('oslist'): tags.append(f"[{details['oslist'].upper()}]")
                                if details.get('steamdeck'): tags.append("[DECK]")
                                if details.get('language'): base_description += f" ({details['language'].capitalize()})"
                                final_description = ' '.join(tags) + ' ' + base_description if tags else base_description
                            else:
                                final_description = base_description

                            lower_desc = final_description.lower()
                            if "soundtrack" in lower_desc or re.search(r'\bost\b', lower_desc):
                                logger.debug(f"Filtering out soundtrack depot {depot_id} ('{final_description}').")
                                continue

                            final_depot_data['desc'] = final_description
                            enriched_depots[depot_id] = final_depot_data
                            
                        game_data['depots'] = enriched_depots
                
                manifest_dir = os.path.join(os.getcwd(), 'manifest')
                os.makedirs(manifest_dir, exist_ok=True)
                for name, content in manifest_files.items():
                    with open(os.path.join(manifest_dir, name), 'wb') as f: f.write(content)

            logger.info(tr("ProcessZip", "Zip processing task completed successfully"))
            return game_data
        except Exception as e:
            logger.error(f"Zip processing failed: {e}", exc_info=True)
            raise