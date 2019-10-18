
from jira import JIRA
import urllib3
import re


options = {
    "server": "http://jira.clavister.com"
}
jira = JIRA(options = options, basic_auth = ("readonly", "NotSecret"), proxies = {"http": "http://proxy.clavister.com:8080"}, timeout=10)


issues = jira.search_issues("project = COP AND created >= -7d", maxResults=1000)


#
# utils
#

import re
def isearch(pattern, string):
    return re.search(pattern, string, re.IGNORECASE)


#
# scoring functions and patterns
#


# scoring of PRIORITIES
prioscores = {}  # [id] = score
priorities = jira.priorities()
for idx,prio in enumerate(priorities):
    prioscores[prio.id] = ( len(priorities) - 1 - idx ) * 5     # 0, 5, 10, ...

# scoring of STRINGS
string_scorepatterns = {  # remember, several entry lines can match and will get added
    r'(vuln|attack|hack)': 7,
    r'(crash|\bhang|freeze)': 7,
    r'(fail|overflow|stops? work|break|broke)': 3,
    r'(bug|overflow|exception|watchdog|lock[ed ]*down)': 5,
    r'(emergenc)': 10
}

# scoring of LABELS
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


# Loop through and score the returned issues

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

    if f.resolution and f.resolution.name.lower() in ["duplicate", "rejected", "invalid"]:
        score = -1

    setattr(issue, "score", score)

#
# Build HTML!
#

from markupsafe import Markup, escape

outs = []
def out(str):
    str = escape(str)
    outs.append(str)    # instead of raw append on string = expensiiiive

out(Markup(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <base href="{options['server']}" target="_blank">
    <style type="text/css">
"""))
out(Markup("""
    li { padding: 10px; }
    body {
        font-family: BlinkMacSystemFont,"Segoe UI","Roboto","Oxygen","Ubuntu","Fira Sans","Droid Sans","Helvetica Neue",sans-serif;
        font-size: 14px;
    }
    .description {
        font-size: smaller;
        padding-top: 4px;
        display: inline-block;
    }
    .status {
        border-radius: 3px;
        border: 1px solid;
        display: inline-block;
        font-weight: bold;
        padding: 2px 8px;
        text-align: center;
        text-transform: uppercase;
        box-sizing: border-box;
        font-size: 11px;
        letter-spacing: 0;
    }
    .status-color-blue-gray {
        border-color: #e4e8ed;
        color: #4a6785;
    }
    .status-color-green {
        color: #14892c;
        border-color: #b2d8b9;
    }
    .status-color-yellow {
        border-color: #ffe28c;
        color: #594300;
    }
    .resolution {
        font-size: 11px;
        font-weight: bold;
    }
    .subbox {
        display: inline-block;
        padding-left: 8em;
        padding-top: 2px;
    }

    """))
out(Markup(f"""
    </style>
</head>
<body>
<ul>
"""))

for issue in sorted(issues, key=lambda i: i.score, reverse=True):
    f = issue.fields
    shortdesc = f.description[0:200].strip()
    shortdesc = re.sub(r"(\r?\n)+", "\n", shortdesc)
    shortdesc = Markup("<br>").join(shortdesc.split("\n")[0:3])
    shortdesc += "..."
    summary = escape(f.summary)
    for pattern,score in string_scorepatterns.items():
        if score>0:
            summary = re.sub(pattern, r"<b>\g<0></b>", summary, flags=re.IGNORECASE)
            shortdesc = re.sub(pattern, r"<b>\g<0></b>", shortdesc, flags=re.IGNORECASE)

    if not f.resolution:
        resolution = ""
    else:
        resolution = f"Resolution: {f.resolution.name}"
    out(Markup(f"""
<li>
<img src="{f.issuetype.iconUrl}" height="16" width="16" border="0" align="absmiddle" alt="{f.issuetype.name}">
<a class="issue-link" href="/browse/{issue.key}">{issue.key}</a>
<img src="{f.priority.iconUrl}" alt="{f.priority.name}" height="16" width="16" border"0" align="absmiddle">
<span class="summary">{summary}</span>
<br>
<div class="subbox">
<span class="status status-color-{f.status.statusCategory.colorName}">{f.status.name}</span> &nbsp;
<span class="resolution">{resolution}</span>
<br>
<span class="description">{shortdesc}</span></li>
</div>
"""))

out(Markup(f"""
</body>
</html>
"""))





f = open("output.html", "w")
for str in outs:
    f.write(str)
f.close()


if False:


    #
    # Send email!
    #

    from email.message import EmailMessage
    from email.utils import make_msgid
    import mimetypes

    msg = EmailMessage()

    # generic email headers
    msg['Subject'] = 'Hello there'
    msg['From'] = 'ABCD <abcd@xyz.com>'
    msg['To'] = 'PQRS <pqrs@xyz.com>'

    # set the plain text body
    msg.set_content('This is a plain text body.')

    # now create a Content-ID for the image
    image_cid = make_msgid(domain='xyz.com')
    # if `domain` argument isn't provided, it will
    # use your computer's name

    # set an alternative html body
    msg.add_alternative("""\
    <html>
        <body>
            <p>This is an HTML body.<br>
            It also has an image.
            </p>
            <img src="cid:{image_cid}">
        </body>
    </html>
    """.format(image_cid=image_cid[1:-1]), subtype='html')
    # image_cid looks like <long.random.number@xyz.com>
    # to use it as the img src, we don't need `<` or `>`
    # so we use [1:-1] to strip them off


    # now open the image and attach it to the email
    with open('path/to/image.jpg', 'rb') as img:

        # know the Content-Type of the image
        maintype, subtype = mimetypes.guess_type(img.name)[0].split('/')

        # attach it
        msg.get_payload()[1].add_related(img.read(),
                                            maintype=maintype,
                                            subtype=subtype,
                                            cid=image_cid)


    # the message is ready now
    # you can write it to a file
    # or send it using smtplib