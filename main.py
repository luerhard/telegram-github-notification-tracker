from configparser import ConfigParser
import time
from issue_tracker import IssueTracker


def main():
    config = ConfigParser()
    config.read("config.ini")
    tracker = IssueTracker(
        github_access_token=config["github"]["access_token"],
        repo="luerhard/anton_test",
        update_interval_sec=30,
        telegram_access_token=config["telegram"]["access_token"],
        response_chat_id=config["telegram"]["chat_id"]
    )

    while True:
        time.sleep(tracker.update_interval)
        tracker.logger.info("starting new update cycle")
        tracker.update()

if __name__ == "__main__":
    main()
