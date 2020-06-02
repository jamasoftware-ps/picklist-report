import os
import sys
import logging
import datetime
import configparser
from typing import Callable, Union

from py_jama_rest_client.client import JamaClient
from py_jama_rest_client.client import APIException

logger = logging.getLogger(__name__)


def init_logging():
    try:
        os.makedirs('logs')
    except FileExistsError:
        pass
    current_date_time = datetime.datetime.now().strftime("%Y-%m-%d %H_%M_%S")
    log_file = 'logs/harm-severity-updater_' + str(current_date_time) + '.log'
    logging.basicConfig(filename=log_file, level=logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def parse_config():
    if len(sys.argv) != 2:
        logger.error("Incorrect number of arguments supplied.  Expecting path to config file as only argument.")
        exit(1)
    current_dir = os.path.dirname(__file__)
    path_to_config = sys.argv[1]
    if not os.path.isabs(path_to_config):
        path_to_config = os.path.join(current_dir, path_to_config)

    # Parse config file.
    configuration = configparser.ConfigParser()
    configuration.read_file(open(path_to_config))
    return configuration


def create_jama_client(config: configparser.ConfigParser):
    url = None
    user_id = None
    user_secret = None
    oauth = None
    verify_ssl_cert = None
    try:
        url = config.get('CLIENT_SETTINGS', 'jama_connect_url').strip()
        # Clean up URL field
        while url.endswith('/') and url != 'https://' and url != 'http://':
            url = url[0:len(url) - 1]
        # If http or https method not specified in the url then add it now.
        if not (url.startswith('https://') or url.startswith('http://')):
            url = 'https://' + url
        oauth = config.getboolean('CLIENT_SETTINGS', 'oauth')
        user_id = config.get('CLIENT_SETTINGS', 'user_id').strip()
        user_secret = config.get('CLIENT_SETTINGS', 'user_secret').strip()
        verify_ssl_cert = config.get('CLIENT_SETTINGS', 'verify_ssl_cert', fallback=False).strip()
    except configparser.Error as config_error:
        logger.error("Unable to parse CLIENT_SETTINGS from config file because: {}, "
                     "Please check config file for errors and try again."
                     .format(str(config_error)))
        exit(1)

    return JamaClient(url, (user_id, user_secret), oauth=oauth, verify=verify_ssl_cert)


def generate_report(client: JamaClient):
    # Get the pick-list info
    try:
        picklists = client.get_pick_lists()
    except APIException as error:
        logger.error("Failed to fetch pick-list data.")
        logger.error(error)
        return

    # Open a File for writing
    try:
        with open("picklist-report.txt", "w") as report:
            # process each picklist
            for picklist in picklists:
                # Print the Picklist info
                pl_name = picklist.get('name')
                pl_id = picklist.get('id')
                report.write('======================================\n')
                report.write('Pick-list:\n')
                report.write('Name: ' + pl_name + '\n')
                report.write('ID: ' + str(pl_id) + '\n')

                # Fetch and print the picklist option info for this picklist
                try:
                    picklist_options = client.get_pick_list_options(pl_id)
                    # Write each picklist option
                    for pl_option in picklist_options:
                        plo_name = pl_option.get('name')
                        plo_id = pl_option.get('id')
                        report.write('*****\n')
                        report.write('\tPick-list Option:\n')
                        report.write('\tName: ' + plo_name + '\n')
                        report.write('\tID: ' + str(plo_id) + '\n')

                except APIException as api_error:
                    logger.error("Unable to fetch pick-list options")
                    logger.error(api_error)

    except IOError as file_error:
        logger.error("Unable to write file")
        logger.error(file_error)


# Execute this as a script.
if __name__ == "__main__":
    # Setup logging
    init_logging()

    # Get Config File Path
    conf = parse_config()

    # Create Jama Client
    jama_client = create_jama_client(conf)

    # Begin business logic
    generate_report(jama_client)

    logger.info("Done.")
