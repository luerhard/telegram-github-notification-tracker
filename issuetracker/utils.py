from configparser import ConfigParser
import logging
from logging.handlers import TimedRotatingFileHandler
import telegram
import issuetracker

def get_chatid(config_file):
    config = ConfigParser()
    config.read(config_file)
    access_token = config["telegram"]["access_token"]

    bot = telegram.Bot(access_token)
    updates = list(bot.get_updates())
    update = updates[-1]

    return str(update.message.chat.id)

def get_logger():
    """
    sets up logging.
    """
    logger = logging.getLogger("issue_tracker")
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    for handler in logger.handlers:
        logger.removeHandler(handler)

    stream_handler = TimedRotatingFileHandler("issuetracker.log",
        when="d",
        interval=1,
        backupCount=3
    )
    logger.addHandler(stream_handler)
    logger.handlers[0].setFormatter(f_format)
        
    logger.setLevel(logging.INFO)
    logger.propagate = False
            
    return logger
