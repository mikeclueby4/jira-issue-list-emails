#!/usr/bin/env python
"""
# settings.py
#
# User-modified settings, patterns, groupings, report queries...
# This file can be executed to instantly generate all "output-myreportname.html" in current directory
"""

from jira import JIRA        # pip install jira
from myutils import isearch
from typing import Dict,Callable
from markupsafe import Markup, escape
import makereport

debug = print if (__name__ == "__main__") else lambda _ : _   # execute settings.py directly to test

# options for email sending
emailoptions = {
    "from": "JIRA <jira@clavister.com>",
    "include_own_server_url": "http://jira.clavister.com:81",   # (base of) URL to include in emails for update/dynamic version of sent mails
    "mailserver_ip": "127.0.0.1",
    "mailserver_port": 25,
}

# See https://jira.readthedocs.io/en/master/examples.html#initialization
jiraoptions = {
    "server": "http://jira.clavister.com",
    "basic_auth": ("readonly", "NotSecret"),
    "proxies": {"http": "http://proxy.clavister.com:8080"},
    "timeout": 10
}

makereport.basehref = jiraoptions["server"]

jiraconnection = JIRA(**jiraoptions)

makereport.jiraconnection = jiraconnection


#
# scoring functions and patterns
#

# scoring of PRIORITIES
priorities = jiraconnection.priorities()   # this is already sorted highest (idx 0) to lowest

debug("\nScoring adjust for Priorities:")
for idx,prio in enumerate(priorities):
    score = ( len(priorities) - 1 - idx ) * 10     # 0, 10, 20, ...
    if isearch("emergenc", prio.name):
        score += 30                                # +30 for emergencies

    debug(f"    {prio.name} (id {prio.id}) = +{score}")
    makereport.prioscores[prio.id] = score

# scoring of STRINGS
makereport.string_scorepatterns = {  # remember, several entry lines can match and will get summed
    r"(emergenc[yies]*|critical|catastroph)": 10,
    r"(vuln[erableity]*|attack|hack[sed]*|\bd?dos(:d|'d|ed|ing)?\b)": 7,
    r"(crash|\bhang[ings]*|freezes?|frozen?|interrupt)": 7,
    r"(danger[ous]*|severe|unsafe)": 5,   # not 'severely', it's too common in that form
    r"(\bbug[gedin]*|overflow[ings]*|exception[eds]*|watchdog[inged]*|lock[ed ]*down|lock[seding]* (me |you | us )?out)": 5,
    r"[!?]": 2,
    r"(fail[ingureds]*|does[' ]no?t work|(won't|not|stops?|stopped) work[sing]*|breaks?|broken?|erron[eou]+s[ley]*|incorrect[ley]*|[ui]nstable|unexpected)": 3,
    r"(random[ly]*|sudden[ly]*|confus[ionges]*|miss[inges]*|error[sing]*|unable|impossible|not[- ]([a-z]+[- ])?(good|useful)|weird|strange|problem|should[' ]no?t|can't|cannot|\bnot\b|sometimes|actual[ly]*)": 2,
}

# scoring of LABELS
makereport.label_scorepatterns = {  # remember, several entry lines can match and will get summed
    r'support_need': 5,
    r'^support': 5,
    r'(emergenc[yies]*|critical|vuln)': 10
}

# scoring of issue types
makereport.issuetype_scorepatterns = {
    r'(defect|\bbug\b|vuln)': 20,
    r'(rfe)': 15,
    r'(epic)': 10,
    r'(story)': -10,
}

# scoring of LINKED issue types
makereport.linked_issuetype_scorepatterns = {
    r'(defect|\bbug\b|vuln)': 10,
    r'(rfe)': 10,
}


# additional customized scoring
def mycustomscore(score, issue):
    f = issue.fields
    if f.resolution and f.resolution.name.lower() in ["duplicate", "rejected", "invalid"]:
        score.set(-1, "Duplicate/Rejected/Invalid")
makereport.customscore = mycustomscore

# custom issue grouping
def mycustomgroup(issue):
    f = issue.fields
    if f.resolution:
        if isearch(r"(fixed|done)", f.resolution.name):
            return 3,"Resolved: Fixed/Done"
        return  4,"Resolved: Other"

    if isearch(r"(need|wait|on[-_ .]?hold|defer)", f.status.name):
        return 1,"Waiting for something"

    if f.status.statusCategory.key=='new' and not isearch(r"(confirmed|accepted)", f.status.name):
        return 0,"Unconfirmed / To Do / New"

    return 2,"Confirmed / Progressing"
makereport.customgroup = mycustomgroup




#
# Callouts that create our HTML reports (= mail content or served-up pages)
#

reports = {}   # type: Dict[str,Callable[[], str]]
defaulthours = 7*24 + 4

def cop(hours=defaulthours):
    issues = jiraconnection.search_issues(f"project = COP AND created >= -{hours}h", maxResults=1000)

    html = makereport.getheader(title="COP issues")
    html += Markup("<h1>cOS Core</h1>\n")
    html += makereport.render(issues)
    html += makereport.getfooter()

    return html
reports["cop"] = cop

def icc(hours=defaulthours):
    issues = jiraconnection.search_issues(f"project = ICC AND created >= -{hours}h", maxResults=1000)

    html = makereport.getheader(title="ICC issues")
    html += Markup("<h1>InControl</h1>\n")
    html += makereport.render(issues)
    html += makereport.getfooter()

    return html
reports["icc"] = icc

def ssm(hours=defaulthours):
    issues = jiraconnection.search_issues(f"project = SSM AND created >= -{hours}h", maxResults=1000)

    html = makereport.getheader(title="SSM issues")
    html += Markup("<h1>cOS Stream</h1>\n")
    html += makereport.render(issues)
    html += makereport.getfooter()

    return html
reports["ssm"] = ssm

def ems(hours=defaulthours):
    issues = jiraconnection.search_issues(f"project = EMS AND created >= -{hours}h", maxResults=1000)

    html = makereport.getheader(title="EMS issues")
    html += Markup("<h1>InCenter</h1>\n")
    html += makereport.render(issues)
    html += makereport.getfooter()

    return html
reports["ems"] = ems

def otherengineering(hours=defaulthours):
    html = makereport.getheader(title="All other product issues")

    categoryfilter = r"""(core|stream|centralized|products|mfa)"""
    skippedcategories = {}

    for project in jiraconnection.projects():

        if not hasattr(project, "projectCategory"):
            debug(f"      {project.key} ({project.name}) - No. No category.")
        elif not isearch(categoryfilter, project.projectCategory.name):
            skippedcategories[project.projectCategory.name] = project.key + " - " + project.name
            debug(f"      {project.key} ({project.name}) - No. \"{project.projectCategory.name}\" does not match.")
        elif project.key in ("COP,SSM,EMS,ICC"):
            pass # did these in separate reports
        else:
            debug(f"      {project.key} ({project.name}) category {project.projectCategory.name} ...")
            issues = jiraconnection.search_issues(f"project = {project.key} AND created >= -{hours}h", maxResults=1000)
            html += Markup("<h1>{}</h1>\n").format(project.name)
            html += makereport.render(issues)

    html += Markup("""<div class="footer">Skipped project categories:<ul>""")
    for cat,example in skippedcategories.items():
        if cat=="":
            cat="(none)"
        html += Markup("""<li> "{}" e.g. {}</li>""").format(cat,example)
    html += Markup("</ul></div>")
    html += makereport.getfooter()


    return html

reports["otherengineering"] = otherengineering


#
# Executing settings.py for test purposes?
#

if __name__ == "__main__":
    with open("output-otherengineering.html", "w", encoding="utf-8") as f:
        f.write(otherengineering(24*60))

elif __name__ == "__main__":

    debug("\nRunning all registered reports and dumping to HTML files:")

    for name,function in reports.items():
        outname = f"output-{name}.html"
        debug(f"    {outname} ...")
        html = function()

        with open(outname, "w", encoding="utf-8") as f:
            f.write(html)