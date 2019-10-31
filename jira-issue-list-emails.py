
from jira import JIRA        # pip install jira
import jira_issues_to_html
import re


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
    score = ( len(priorities) - 1 - idx ) * 5     # 0, 5, 10, ...
    jira_issues_to_html.prioscores[prio.id] = score
    print(f"    {prio.name} (id {prio.id}) = +{score}")

# scoring of STRINGS
jira_issues_to_html.string_scorepatterns = {  # remember, several entry lines can match and will get added
    r'(vuln[erableity]*|attack|hack[sed]*)': 7,
    r'(crash|\bhang[ings]*|freezes?|frozen?)': 7,
    r"(fail[ingureds]*|overflow|stops? work|does['not ]*work[sing]*|not work[sing]*|breaks?|broken?|erron[eou]?sl[ey]*)": 3,
    r'(bug[gedin]*|overflow[ings]*|exception[eds]*|watchdog[inged]*|lock[ed ]*down)': 5,
    r'(random[ly]*|sudden[ly]*|confus[ionges]*|miss[inges]*|error[sing]*)': 1,
    r'(emergenc[yies]*)': 10
}

# scoring of LABELS
jira_issues_to_html.label_scorepatterns = {  # remember, several entry lines can match and will get added
    r'support_need': 5,
    r'^support': 5,
    r'emergenc': 10
}

# additional customized scoring
def mycustomscore(issue, score):
    f = issue.fields
    if f.resolution and f.resolution.name.lower() in ["duplicate", "rejected", "invalid"]:
        score = -1
    return score
jira_issues_to_html.customscore = mycustomscore

# custom issue grouping, see jira_issues_to_html.py for example
def mycustomgroup(issue):
     return 0, "Group heading text"
# uncomment to use: jira_issues_to_html.customgroup = mycustomgroup




#
# Query and build HTML!
#

issues = jiraconnection.search_issues("project = COP AND created >= -7d", maxResults=1000)

html = jira_issues_to_html.getheader(basehref = options['server'])
html += jira_issues_to_html.render(issues)
html += jira_issues_to_html.getfooter()







f = open("output.html", "w")
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