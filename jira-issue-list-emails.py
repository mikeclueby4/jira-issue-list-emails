
from jira import JIRA        # pip install jira
from myutils import *
import jira_issues_to_html


# https://jira.readthedocs.io/en/master/examples.html#initialization
options = {
    "server": "http://jira.clavister.com",
    "basic_auth": ("readonly", "NotSecret"),
    "proxies": {"http": "http://proxy.clavister.com:8080"},
    "timeout": 10
}


jiraconnection = JIRA(**options)


#
# scoring functions and patterns
#

# scoring of PRIORITIES
jira_issues_to_html.prioscores = {}  # [id] = score
priorities = jiraconnection.priorities()
print("")
print("Scoring adjust for Priorities:")
for idx,prio in enumerate(priorities):
    score = ( len(priorities) - 1 - idx ) * 10     # 0, 10, 20, ...
    if isearch("emergenc", prio.name):
        score += 30
    jira_issues_to_html.prioscores[prio.id] = score
    print(f"    {prio.name} (id {prio.id}) = +{score}")

# scoring of STRINGS
jira_issues_to_html.string_scorepatterns = {  # remember, several entry lines can match and will get added
    r"(emergenc[yies]*|critical|catastroph)": 10,
    r"(vuln[erableity]*|attack|hack[sed]*|\bd?dos(:d|'d|ed|ing)?\b)": 7,
    r"(crash|\bhang[ings]*|freezes?|frozen?|interrupt)": 7,
    r"(danger[ous]*|severe)": 5,   # not 'severely', it's too common in that form
    r"(bug[gedin]*|overflow[ings]*|exception[eds]*|watchdog[inged]*|lock[ed ]*down)": 5,
    r"(fail[ingureds]*|does[' ]no?t work|(won't|not|stops?|stopped) work[sing]*|breaks?|broken?|erron[eou]+s[ley]*|incorrect[ley]*)": 3,
    r"(random[ly]*|sudden[ly]*|confus[ionges]*|miss[inges]*|error[sing]*|unable|impossible|not[- ]([a-z]+[- ])?useful|weird|strange|problem|should[' ]no?t)": 2,
}

# scoring of LABELS
jira_issues_to_html.label_scorepatterns = {  # remember, several entry lines can match and will get added
    r'support_need': 5,
    r'^support': 5,
    r'(emergenc[yies]*|critical|vuln)': 10
}

# additional customized scoring
def mycustomscore(score, issue):
    f = issue.fields
    if f.resolution and f.resolution.name.lower() in ["duplicate", "rejected", "invalid"]:
        score.set(-1, "Duplicate/Rejected/Invalid")
jira_issues_to_html.customscore = mycustomscore

# custom issue grouping
def mycustomgroup(issue):
    f = issue.fields
    if f.resolution:
        if isearch(r"fixed", f.resolution.name):
            return 3,"Resolved: Fixed"
        return  4,"Resolved: Other"

    if isearch(r"(need|wait|on[-_ .]?hold)", f.status.name):
        return 1,"Waiting for something"

    if f.status.statusCategory.key=='new' and not isearch(r"(confirmed|accepted)", f.status.name):
        return 0,"Unconfirmed / To Do / New"

    return 2,"Confirmed / Progressing"
jira_issues_to_html.customgroup = mycustomgroup




#
# Query and build HTML!
#

issues = jiraconnection.search_issues("project = COP AND created >= -20d", maxResults=1000)

html = jira_issues_to_html.getheader(basehref = options['server'])
html += jira_issues_to_html.render(jiraconnection, issues)
html += jira_issues_to_html.getfooter()







f = open("output.html", "w", encoding="utf-8")
f.write(html)
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