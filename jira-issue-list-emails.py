
from jira import JIRA
import urllib3
import re


options = {
    "server": "http://jira.clavister.com"
}
jira = JIRA(options = options, basic_auth = ("readonly", "NotSecret"), proxies = {"http": "http://proxy.clavister.com:8080"}, timeout=10)


issues = jira.search_issues("project = COP AND created >= -7d", maxResults=1000)



import re
def isearch(pattern, string):
    return re.search(pattern, string, re.IGNORECASE)



# scoring of priorities
prioscores = {}  # [id] = score
priorities = jira.priorities()
for idx,prio in enumerate(priorities):
    prioscores[prio.id] = ( len(priorities) - 1 - idx ) * 5     # 0, 5, 10, ...

string_scorepatterns = {  # remember, several entry lines can match and will get added
    r'(vuln|attack|hack)': 7,
    r'(crash|hang|freeze)': 7,
    r'(fail|overflow|stops? work)': 3,
    r'(bug|overflow|exception|watchdog|lockdown)': 5,
    r'emergenc': 10
}

label_scorepatterns = {  # remember, several entry lines can match and will get added
    r'support_need': 5,
    r'^support': 5,
    r'emergenc': 10
}

def scorestring(string, patterns = None):
    if not patterns:
        patterns = string_scorepatterns
    ret = 0
    for pattern,score in patterns.items():
        if re.search(pattern, string, re.IGNORECASE):
            ret += score
    return ret

issuescores = {}

for issue in issues:
    f = issue.fields
    score = len(f.issuelinks) + f.watches.watchCount + f.votes.votes
    score += scorestring(f.summary)
    score += scorestring(f.description)
    score += prioscores[f.priority.id]
    for label in f.labels:
        score += scorestring(label, label_scorepatterns)
    for link in f.issuelinks:
        li = getattr(link, "inwardIssue", None) or getattr(link, "outwardIssue", None)
        score += scorestring(li.fields.issuetype.name)
        score += scorestring(li.fields.summary)
    setattr(issue, "score", score)

for issue in sorted(issues, key=lambda i: i.score, reverse=True):
    print(issue.key, issue.score)
