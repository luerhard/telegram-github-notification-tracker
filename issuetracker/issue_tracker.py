import bs4
from github import Github
import markdown
import re
import telegram
from telegram import Bot
from telegram.ext import Updater, CommandHandler
import textwrap
import asyncio
import time

class IssueTracker:

    def __init__(self, github_access_token, 
                 repo, telegram_access_token, response_chat_id, logger,
                 bot_name, update_interval_sec=180):

        self.logger = logger

        self.github = Github(github_access_token)
        self.repo = self.github.get_repo(repo)
        self.update_interval = update_interval_sec
        self.telegram_access_token = telegram_access_token
        self.telegram_bot = Bot(self.telegram_access_token)
        self.chat_id = response_chat_id
        self.bot_name = bot_name

        self.remove_from_message = [("(<p>)|(</p>)", ""), ("(<h[0-9]>)|(</h[0-9]>)", ""), ("<hr />", "\n"),
            ("(<blockquote>)|(</blockquote>)", "\n"), ("(<ol>)|(</ol>)", ""), ("(<ul>)|(</ul>)", ""),
            ("(<li>)|(</li>)", "")]

        try:
            self.latest_event = int(next(iter(self.repo.get_events())).id)
        except StopIteration:
            self.latest_event = 0

        self.latest_issue = 0

    @asyncio.coroutine
    def chat_observer(self):
        def send_message(message, name):
            message = message.lstrip("/r").strip()
            possible_issue_number = message.split()[0]
            if possible_issue_number.isnumeric():
                issue_number = int(possible_issue_number)
                message = message.lstrip(f"{possible_issue_number} ")
                self.logger.info(f"Telegram to github (specific refer): issue {issue_number} message: {message} by {name}")
            else:
                if self.latest_issue == 0:
                    self._send("Can't send. Don't know which Issue you mean...")
                    self.logger.warn("Illegal message (unknown Issue): {message} by {name}")
                    return
                issue_number = self.latest_issue
                self._send(f"referring to Issue #{issue_number}")
                self.logger.info(f"Telegram to github (auto refer): issue {issue_number} message: {message} by {name}")

            issue = self.repo.get_issue(issue_number)
            new_comment = textwrap.dedent("""
                **by {user} via telegram**
                {body}""")
            issue.create_comment(new_comment.format(user=name, body=message))

        def reply_action(update, context):
            self.logger.info(f"receiving message from {update.effective_user}")
            firstname = update.effective_user.first_name
            lastname = update.effective_user.last_name
            name = [name for name in [firstname, lastname] if name]
            try:
                name = " ".join(name).strip()
            except Exception as e:
                self.logger.debug("Name join failed")
                self.logger.debug(e)

            self.logger.debug(f"Created name {name}")
            send_message(update.effective_message.text, name)

        updater = Updater(token=self.telegram_access_token, use_context=True)
        dispatcher = updater.dispatcher
        reply_handler = CommandHandler("r", reply_action)
        dispatcher.add_handler(reply_handler)
        updater.start_polling()

    @asyncio.coroutine
    def run(self):
        while True:
            time.sleep(self.update_interval)
            self.logger.debug("starting new update cycle")
            self.update()

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
                if event.actor.login != self.bot_name:
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
    
    def format_message(self, message):
        message = markdown.markdown(message)

        for pattern, sub in self.remove_from_message:
            message = re.sub(pattern, sub, message)

        return message

    def _send(self, message):
        #shorten too long messages:
        if len(message) > 4096:
            message = message[:4095]
        self.telegram_bot.send_message(self.chat_id,
                                        message,
                                        parse_mode='HTML',
                                        disable_notification=True,
                                        disable_web_page_preview=True)
    def send_message(self, message):
        try:
            message = self.format_message(message)
            self._send(message)
        except telegram.TelegramError as e:
            soup = bs4.BeautifulSoup(message, "html5lib")
            message = f"rendered as raw:\n{soup.text}\n rendering error: {e}"
            self._send(message)
        except Exception as e:
            self.logger.error(f"Error in send_message() from telegram: {e}\nMessage that failed:\n{message}")
    
    def issues_comment_event_message(self, event):
        new_comment = textwrap.dedent("""
        
        New Comment on Issue: [{issue}]({url})
        by *{username}*
        {body}""")
        
        payload = event.payload
        number = payload["issue"]["number"]
        issue_title = payload["issue"]["title"]
        issue = f"#{number} {issue_title}"
        username = event.actor.name
        body = payload["comment"]["body"]
        url = payload["issue"]["html_url"]
        
        message = new_comment.format(
            issue=issue,
            username=username,
            body=body,
            url=url,
            event_id=event.id)
        
        self.latest_issue = number
        
        return message


    def issues_event_message(self, event):
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

        self.latest_issue = number

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



