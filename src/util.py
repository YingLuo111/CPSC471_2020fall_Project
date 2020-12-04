import logging
import sys

def setup_logger():
    """ Setup logger to print out program information for server and client.

        :returns: <Logger> The logger object with setups.
    """

    #create logger object
    logger = logging.getLogger()

    #set logging level
    logger.setLevel(logging.INFO)

    #set logging destination to stdout
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)

    #set logging format as <logging time> - <logging level> - <logging message>
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)

    #apply settings to logger object
    logger.addHandler(ch)
    
    return logger