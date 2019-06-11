import textwrap

from github import Github
from telegram import Bot, ParseMode

class IssueTracker:
    
    def __init__(self, github_access_token, 
                       repo, 
                       telegram_access_token,
                       response_chat_id,
                       logger,
                       update_interval_sec=180
                       ):

        self.logger = logger
        
        self.github = Github(github_access_token)
        self.repo = self.github.get_repo(repo)
        self.update_interval = update_interval_sec

        self.telegram_bot = Bot(telegram_access_token)
        self.chat_id = response_chat_id
        
        try:
            self.latest_event = int(next(iter(self.repo.get_events())).id)
        except StopIteration:
            self.latest_event = 0

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
        try:
            self.logger.debug(f"Parsing payload for {event.type}\n{event.payload}")
            if event.type == "IssuesEvent":
                message = self.issues_event_message(event)
            elif event.type == "IssueCommentEvent":
                message = self.issues_comment_event_message(event)
            elif event.type == "PushEvent":
                message = self.push_event_message(event)
            elif event.type == "PullRequestEvent":
                message = self.pullrequest_event_message(event)
            else:
                raise Exception("Not Handled Event")
        except Exception as e:
            self.logger.error(f"""Exception {e}\n
            Error in handling event: {event.type}
            Payload:
            -------
            {event.payload}""")
    
        if message:
            self.logger.info(f"Sending message for event: {event.id}")
            self.send_message(message)

    def send_message(self, message):
        try:
            self.telegram_bot.send_message(self.chat_id,
                                            message,
                                            disable_notification=True,
                                            disable_web_page_preview=True)
        except Exception as e:
            self.logger.error(f"Error in send_message() from telegram: {e}")
    
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

    def push_event_message(self, event):
        
        payload = event.payload
        branch = payload["ref"].split("/")[-1]
        branches_to_watch = ["master"]

        if branch not in branches_to_watch:
            self.logger.debug(f"branch {branch} not in {branches_to_watch}  -- skipping Event-Notifications")
            return None

        new_push_event = textwrap.dedent("""
        {n_commits} new commit{plural} to {branch}
        {commit_message}""")

        new_commits = payload["commits"]
        n_commits = len(new_commits)
        plural = ""
        if n_commits > 1:
            plural = "s"

        commit_message = ""
        for commit in new_commits:
            url = commit['url'].replace("https://api.github.com/repos/", "https://github.com/").replace("/commits/", "/commit/")
            self.logger.debug(f"replaced url = {url}")
            commit_message += f"-----\nby {commit['author']['name']}\n{commit['message']} [visit here]({url})\n"
        
        message = new_push_event.format(
            n_commits=n_commits,
            plural=plural,
            branch=branch,
            commit_message=commit_message)
        
        return message
        
    @staticmethod
    def pullrequest_event_message(event):
        payload = event.payload
        number = payload["number"]
        action = payload["action"]
        pull_request = payload["pull_request"]
        url = pull_request["html_url"]
        user = pull_request["user"]["login"]
        title = pull_request["title"]
        body = pull_request ["body"]

        requested_reviewers = pull_request["requested_reviewers"]
        if requested_reviewers:
            requested_reviewers = "| requested reviewers: " + \
                ", ".join([rev["login"] for rev in requested_reviewers])
        else:
            requested_reviewers = ""

        new_pr = textwrap.dedent("""
        [PR #{number}]({url}) {action}
        by {user} {req_revs}
        {title}
        -----
        {body}""")

        message = new_pr.format(
            action=action,
            number=number,
            user=user,
            req_revs=requested_reviewers,
            url=url,
            title=title,
            body=body)
        
        return message



