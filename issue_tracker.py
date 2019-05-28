import logging
import sys
import textwrap

from github import Github
from telegram import Bot, ParseMode

class IssueTracker:
    
    def __init__(self, github_access_token, 
                       repo, 
                       telegram_access_token,
                       response_chat_id,
                       update_interval_sec=180
                       ):


        self.logger = self.get_logger()
        
        self.github = Github(github_access_token)
        self.repo = self.github.get_repo(repo)
        self.update_interval = update_interval_sec

        self.telegram_bot = Bot(telegram_access_token)
        self.chat_id = response_chat_id
        
        try:
            self.latest_event = int(next(iter(self.repo.get_events())).id)
        except StopIteration:
            self.latest_event = 0
            
    @staticmethod
    def get_logger():
        """
        sets up logging.
        """
        logger = logging.getLogger("issue_tracker")
        f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        for handler in logger.handlers:
            logger.removeHandler(handler)

        stream_handler = logging.StreamHandler(stream=sys.stdout)
        logger.addHandler(stream_handler)
        logger.handlers[0].setFormatter(f_format)
            
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
                
        return logger
    
    
    def update(self):
        new_events = []
        for event in self.repo.get_events():
            if int(event.id) <= self.latest_event:
                break
            new_events.append(event)
        
        if new_events:
            new_events = sorted(new_events, key=lambda x: int(x.id))
            self.latest_event = int(new_events[-1].id)
            for event in new_events:
                self.notify(event)
                
    def notify(self, event):
        if event.type == "IssuesEvent":
            message = self.issues_event_message(event)
        elif event.type == "IssueCommentEvent":
            message = self.issues_comment_event_message(event)
        else:
            return
        
        if message:
            self.logger.info(f"Sending message for event: {event.id}")
            self.send_message(message)
    def send_message(self, message):
        self.telegram_bot.send_message(self.chat_id,
                                        message,
                                        parse_mode=ParseMode.MARKDOWN, 
                                        disable_notification=True,
                                        disable_web_page_preview=True)
    
    @staticmethod
    def issues_comment_event_message(event):
        new_comment = textwrap.dedent("""
        
        New Comment on Issue: [{issue}]({url})
        by {username}
        ------
        {body}""")
        
        payload = event.payload
        issue_number = payload["issue"]["number"]
        issue_title = payload["issue"]["title"]
        issue = f"#{issue_number} {issue_title}"
        username = event.actor.name
        body = payload["comment"]["body"]
        url = payload["issue"]["html_url"]
        
        message = new_comment.format(
            issue=issue,
            username=username,
            body=body,
            url=url,
            event_id=event.id)
        
        return message
    
    @staticmethod
    def issues_event_message(event):
        new_issue = textwrap.dedent("""
            Issue {action} by {username}
            Assignees: {assignees}
            Subject: {title} [#{number}]({url}) 
            -------
            {body}""")
        
        payload = event.payload
        action = payload["action"]
        url = payload["issue"]["html_url"]
        title = payload["issue"]["title"]
        number = payload["issue"]["number"]
        user = event.actor.name
        assignees = ", ".join([assignee["login"] for assignee in payload["issue"]["assignees"]])

        message = new_issue.format(
            action=action,
            username = user,
            assignees = assignees,
            title = title,
            number=number,
            body = payload["issue"]["body"],
            url=url)
        
        return message