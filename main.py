from configparser import ConfigParser
import time
from issuetracker import IssueTracker, get_chatid, get_logger


def main():

    config = ConfigParser()
    config.read("config.ini")

    logger = get_logger()

    if config["telegram"].get("chat_id"):
        logger.info("Using chat_id from config file")
        chat_id = config["telegram"]["chat_id"]
    else:
        logger.info("""Could not find chat_id in config file. 
        I am using the last chat_id from the last message to the bot instead. """)

        chat_id = get_chatid("config.ini")

    logger.info(f"Responding to Chat ID: {chat_id}")

    tracker = IssueTracker(
        github_access_token=config["github"]["access_token"],
        repo=config["github"]["repo"],
        update_interval_sec=int(config["github"]["update_interval"]),
        telegram_access_token=config["telegram"]["access_token"],
        response_chat_id=chat_id,
        logger=logger
    )
    while True:
        time.sleep(tracker.update_interval)
        tracker.logger.debug("starting new update cycle")
        try:
            tracker.update()
        except Exception as e:
            logger.error(e)

if __name__ == "__main__":
    main()
