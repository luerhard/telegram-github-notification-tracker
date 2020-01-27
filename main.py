from configparser import ConfigParser
import time
import issuetracker
from issuetracker import IssueTracker, get_chatid, get_logger
import asyncio


def main():

    config = ConfigParser()
    config.read(issuetracker.PATH / "config.ini")

    logger = get_logger()

    if config["telegram"].get("chat_id"):
        logger.info("Using chat_id from config file")
        chat_id = config["telegram"]["chat_id"]
    else:
        logger.info("""Could not find chat_id in config file. 
        I am using the last chat_id from the last message to the bot instead. """)

        chat_id = get_chatid(issuetracker.PATH / "config.ini")

    logger.info(f"Responding to Chat ID: {chat_id}")

    def run(logger):
        tracker = IssueTracker(github_access_token=config["github"]["access_token"], repo=config["github"]["repo"],
            update_interval_sec=int(config["github"]["update_interval"]),
            telegram_access_token=config["telegram"]["access_token"], response_chat_id=chat_id,
            bot_name=config["github"]["bot_name"],
            logger=logger)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(tracker.chat_observer())
        loop.run_until_complete(tracker.run())

    while True:
        try:
            run(logger)
        except Exception as e:
            logger.error(f"ERROR: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
