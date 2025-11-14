import configparser
from utils.logger import get_internationalized_logger
import logging
import os

logger = get_internationalized_logger()

def parse_depots_ini():
    """
    Parses the depots.ini file to create a dictionary of known depot descriptions.

    Returns:
        dict: A dictionary mapping depot IDs (as strings) to their descriptions.
              Returns an empty dictionary if the file is not found or is invalid.
    """
    ini_path = 'config/depots.ini'
    depot_descriptions = {}

    if not os.path.exists(ini_path):
        logger.warning(f"'{ini_path}' not found. Will rely on LUA and API for depot names.")
        return depot_descriptions

    try:
        config = configparser.ConfigParser()
        # Read the file with 'utf-8' encoding to handle a wide range of characters.
        config.read(ini_path, encoding='utf-8')
        
        if 'depots' in config:
            for depot_id, description in config['depots'].items():
                depot_descriptions[depot_id] = description.strip()
            logger.info(f"Successfully parsed {len(depot_descriptions)} depot descriptions from '{ini_path}'.")
        else:
            logger.warning(f"No [depots] section found in '{ini_path}'.")

    except configparser.Error as e:
        logger.error(f"Error parsing '{ini_path}': {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading '{ini_path}': {e}", exc_info=True)
        
    return depot_descriptions
