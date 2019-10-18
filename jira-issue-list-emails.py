
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
    r'(vuln[erableity]*|attack|hack[sed]*)': 7,
    r'(crash|\bhang[ings]*|freezes?|frozen?)': 7,
    r"(fail[ingureds]*|overflow|stops? work|does['not ]*work[sing]*|not work[sing]*|breaks?|broken?|erron[eou]?sl[ey]*)": 3,
    r'(bug[gedin]*|overflow[ings]*|exception[eds]*|watchdog[inged]*|lock[ed ]*down)': 5,
    r'(random[ly]*|sudden[ly]*|confus[ionges]*|miss[inges]*|error[sing]*)': 1,
    r'(emergenc[yies]*)': 10
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
    score = len(f.issuelinks) + f.watches.watchCount + ( f.votes.votes * 2 )
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

out(Markup("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <base href="{server}" target="_blank">
    <style type="text/css">
""").format(server=options['server'], **locals()))
# separate non-formatted section for CSS because lots of { }
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
    .score {
        padding-left: 2em;
        color: #ddd;
        font-size: 8px;
    }

    """))
out(Markup("""
    </style>
</head>
<body>
"""))


# Group issues per status/resolution

groups = {
    # (sort,groupname) = list of issues
}
for issue in issues:
    f = issue.fields
    if f.resolution:
        if isearch(r"fixed", f.resolution.name):
            group=(3,"Resolved: Fixed")
        else:
            group=(4,"Resolved: Other")

    elif isearch(r"(need|wait)", f.status.name):
        group (1,"Waiting for something")

    elif f.status.statusCategory.key=='new' and not isearch(r"confirmed", f.status.name):
        group=(0,"Unconfirmed / To Do / New")

    else:
        group=(2,"Confirmed / Progressing")

    if not group in groups:
        groups[group] = []

    groups[group].append(issue)


# Loop the groups&issues and generate HTML!

for groupidx,issues in sorted(groups.items()):
    (sort,groupname) = groupidx
    print(sort, groupname, len(issues))

    out(Markup("""
<h2>{groupname}</h2>
<ul>
""").format(**locals()))

    for issue in sorted(issues, key=lambda i: i.score, reverse=True):
        f = issue.fields
        shortdesc = f.description.strip()
        shortdesc = re.sub(r"(\r?\n)+", "\n", shortdesc)
        shortdesc = shortdesc[0:200]
        shortdesc = str(escape(shortdesc))   # str to not trigger escaping in re.sub()
        summary = str(escape(f.summary))     # str to not trigger escaping in re.sub()
        for pattern,score in string_scorepatterns.items():
            if score>0:
                summary = re.sub(pattern, r"<b>\g<0></b>", str(summary), flags=re.IGNORECASE)
                shortdesc = re.sub(pattern, r"<b>\g<0></b>", str(shortdesc), flags=re.IGNORECASE)

        summary = Markup(summary)
        shortdesc = Markup(shortdesc).split("\n")[0:3]
        shortdesc = Markup("<br>").join( shortdesc ) + "..."

        if not f.resolution:
            resolution = ""
        else:
            resolution = f"Resolution: {f.resolution.name}"
        out(Markup("""
<li>
<img src="{f.issuetype.iconUrl}" height="16" width="16" border="0" align="absmiddle" alt="{f.issuetype.name}">
<a class="issue-link" href="/browse/{issue.key}">{issue.key}</a>
<img src="{f.priority.iconUrl}" alt="{f.priority.name}" height="16" width="16" border"0" align="absmiddle">
<span class="summary">{summary}</span><span class="score">{issue.score}</span>
<br>
<div class="subbox">
<span class="status status-color-{f.status.statusCategory.colorName}">{f.status.name}</span> &nbsp;
<span class="resolution">{resolution}</span>
<br>
<span class="description">{shortdesc}</span></li>
</div>
""").format(**locals()))

    # End of group
    out(Markup("""
</ul>
"""))

# All issues listed
out(Markup("""
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