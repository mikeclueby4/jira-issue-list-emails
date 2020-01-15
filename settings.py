#!/usr/bin/env python
"""
settings.py

User-modified settings, patterns, groupings, report queries...
This file can be executed to instantly generate all "output-myreportname.html" in current directory
"""

from typing import Any, Callable, Dict

from jira import JIRA
from markupsafe import Markup, escape
from datetime import date, datetime, timedelta

from makereport import makecategoryreporter
import makereport
from myutils import isearch

debug = print if (__name__ == "__main__") else lambda _ : _   # settings.py executed directly? more console output!
makereport.debug = debug


# options for EMAIL SENDING

emailoptions = {
    "from": "JIRA <jira@clavister.com>",
    # "include_own_server_url": "http://jira.clavister.com:81",   # (base of) URL to include in emails for update/dynamic version of sent mails
    "include_own_server_url": "http://127.0.0.1:81",
    "mailserver_ip": "127.0.0.1",
    "mailserver_port": 25,
}


# options for JIRA REST API CONNECTION  - see https://jira.readthedocs.io/en/master/examples.html#initialization

jiraoptions = {
    "server": "http://jira.clavister.com",
    "basic_auth": ("readonly", "NotSecret"),
    "proxies": {"http": "http://proxy.clavister.com:8080"},
    "timeout": 10
}

makereport.basehref = jiraoptions["server"]    # <base href=""> for generated reports - "always" same as base of REST service

jiraconnection = JIRA(**jiraoptions)

makereport.jiraconnection = jiraconnection


########################################################################
#
# SCORING RELATED
#


# scoring of PRIORITIES  -> .prioscores[id] = adjust

priorities = jiraconnection.priorities()   # this is already sorted highest (idx 0) to lowest

debug("\nScoring adjust for Priorities:")
for idx,prio in enumerate(priorities):

    score = ( len(priorities) - 1 - idx ) * 10     # 0, 10, 20, ...

    if isearch("emergenc", prio.name):
        score += 30                                # +30 for emergencies

    debug("    {prio.name} (id {prio.id}) = +{score}".format(**locals()))
    makereport.prioscores[prio.id] = score


# regexp-based scoring of STRINGS - text in Summary and Description

makereport.string_scorepatterns = {  # remember, several entry lines can match and will get summed
    r"(emergenc[yies]*|critical|catastroph)": 10,
    r"(vuln[erableity]*|attack|hack[sed]*|\bd?dos(:d|'d|ed|ing)?\b)": 7,
    r"(crash|\bhang[ings]*|freezes?|frozen?|interrupt|mem[ory]* leak|out.of.memory)": 7,
    r"(danger[ous]*|severe|unsafe)": 5,   # not 'severely', it's too common in that form
    r"(\bbug[gedin]*|overflow[ings]*|exception[eds]*|watchdog[inged]*|lock[ed ]*down|lock[seding]* (me |you | us )?out|assert[sing]*)": 5,
    r"[!?]": 2,
    r"(fail[ingureds]*|does[' ]no?t work|(won't|not|stops?|stopped) work[sing]*|breaks?|broken?|erron[eou]+s[ley]*|incorrect[ley]*|[ui]nstable|unexpected)": 3,
    r"(conflict[sing]*|error[sing]*|problem[satic]*)": 2,
    r"(random[ly]*|sudden[ly]*|confus[ionges]*|miss[inges]*|unable|impossibl[ey]|not[- ]([a-z]+[- ])?(good|useful)|weird|strange|should[' ]no?t|can't|cannot|\bnot\b|sometimes|actual)": 2,
}
# TODO: pattern for multiple ! ?  ... but that needs exlusion of bolding (skip any long match?)


# regexp-based scoring of LABELS

makereport.label_scorepatterns = {  # remember, several entry lines can match and will get summed
    r'support_need': 5,
    r'^support': 5,
    r'(emergenc[yies]*|critical|vuln)': 10
}


# regexp-based scoring of ISSUE TYPE

makereport.issuetype_scorepatterns = {
    r'(defect|\bbug\b|vuln)': 20,
    r'(rfe|enhanc)': 15,
    r'(epic)': 10,
    r'(story)': -10,
}


# regexp-based scoring of LINKED ISSUE TYPES - per linked issue!

makereport.linked_issuetype_scorepatterns = {
    r'(defect|\bbug\b|vuln)': 10,
    r'(rfe)': 10,
}


# additional CUSTOMIZED scoring - called after everything else

def mycustomscore(score, issue):
    f = issue.fields
    if f.resolution and f.resolution.name.lower() in ["duplicate", "rejected", "invalid"]:
        score.set(-1, "Duplicate/Rejected/Invalid")

makereport.customscore = mycustomscore


# ISSUE GROUPING  - return group key for the given issue; a tuple (sortkey,grouptext)

def mycustomgroup(issue):
    f = issue.fields

    if isearch(r"(requirem)", f.issuetype.name):
        return 7, "Requirements"

    if f.resolution and not isearch(r"(fixed|done)", f.resolution.name):
        return  6, "Resolved: Other"

    if isearch(f.issuetype.name, "epic"):
        return 4, "Epic"

    if isearch(f.issuetype.name, "story"):
        return 5, "Story"

    if f.resolution:        # we test for "not fixed" above
        return 3,"Resolved: Fixed/Done"

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

mytimefilter = " AND created >= -172h"   # 7*24 + 4


def bap():
    issues = jiraconnection.search_issues("project = BAP {}".format(mytimefilter),
        fields="*all",      # Note "*all" so we also get comments!
        maxResults=1000)

    html = makereport.getheader(title="BAP issues")
    html += Markup("<h1>BAP - Business Application Projects</h1>\n")
    html += makereport.render(issues)
    html += makereport.getfooter()

    return html
reports["bap"] = bap


reports["core"] = makecategoryreporter(r"(core)", "Core issues", mytimefilter, reportskippedcategories=False)
reports["stream"] = makecategoryreporter(r"(stream)", "Stream issues", mytimefilter, reportskippedcategories=False)
reports["management"] = makecategoryreporter(r"(centralized)", "Centralized Management issues", mytimefilter, reportskippedcategories=False)
reports["otherproducts"] = makecategoryreporter(r"(products|\bmfa)", "Other products issues", mytimefilter, reportskippedcategories=True)

def tic_statustable():

    html = makereport.getheader(title="TIC status history")
    html += Markup("<h1>TIC status history</h1>\n")

    history = []
    today=date.today()

    columns = ["Date", "Vacation", "Weekday", "In New/Open", "(in Med/Low)", "(07:00)", "(12:00)", "In Fixed", "In New", "Created"]

    for day in daterange(today-timedelta(days=10), today):
        he = []

        he.append(day)

        year=day.year
        if date(year,6,15) <= day <= date(year,8,15):
            he.append("Summer")
        elif date(year,12,23) <= day:
            he.append("Xmas")
        elif day <= date(year,1,2):
            he.append("NewYear")
        else:
            he.append("")

        he.append(day.strftime("%a"))

        he.append( jiraconnection.search_issues("""project = TIC AND issuetype = Ticket
AND status WAS IN ("Ticket New Ticket", "Ticket Open 1st Line") ON "{}" """.format(day.isoformat()),
            fields="none", expand="none", maxResults=1,
        ).total )

        he.append( jiraconnection.search_issues("""project = TIC AND issuetype = Ticket AND Priority IN ("Low","Medium")
AND status WAS IN ("Ticket New Ticket", "Ticket Open 1st Line") ON "{}" """.format(day.isoformat()),
            fields="none", expand="none", maxResults=1,
        ).total )

        he.append( jiraconnection.search_issues("""project = TIC AND issuetype = Ticket
AND status WAS IN ("Ticket New Ticket", "Ticket Open 1st Line") ON "{} 07:00" """.format(day.isoformat()),
            fields="none", expand="none", maxResults=1,
        ).total )

        he.append( jiraconnection.search_issues("""project = TIC AND issuetype = Ticket
AND status WAS IN ("Ticket New Ticket", "Ticket Open 1st Line") ON "{} 12:00" """.format(day.isoformat()),
            fields="none", expand="none", maxResults=1,
        ).total )

        he.append( jiraconnection.search_issues("""project = TIC AND issuetype = Ticket
AND status CHANGED TO "Ticket Fixed" ON "{}" """.format(day.isoformat()),
            fields="none", expand="none", maxResults=1,
        ).total )

        he.append( jiraconnection.search_issues("""project = TIC AND issuetype = Ticket
AND status WAS IN ("Ticket New Ticket") ON "{}" """.format(day.isoformat()),
            fields="none", expand="none", maxResults=1,
        ).total )

        he.append( jiraconnection.search_issues("""project = TIC and type=Ticket
AND created >= {today} and created < {tomorrow} """.format(today=day.isoformat(), tomorrow=(day + timedelta(1)).isoformat()),
            fields="none", expand="none", maxResults=1,
        ).total )

        print(he)
        history.append(he)


    html += Markup("\n<table>\n")

    html+= Markup("<tr>")
    for colname in columns:
        html += Markup("<th>{}</th>").format(colname)
    html+= Markup("</tr>\n")

    for he in history:
        html += Markup("<tr>")
        for value in he:
            html += Markup("<td>{}</td>").format(value)
        html += Markup("</tr>\n")


    html += Markup("\n</table>\n")

    html += makereport.getfooter()

    return html

# reports["tic-statustable"] = tic_statustable

#
# Executing settings.py for test purposes?
#

if __name__ == "__main__":
    with open("output-tic-statustable.html", "w", encoding="utf-8") as f:
        f.write(tic_statustable())


elif __name__ == "__main__":

    debug("\nRunning all registered reports and dumping to HTML files:")

    for name,function in reports.items():
        outname = "output-{name}.html".format(**locals())
        debug("    {outname} ...".format(**locals()))
        html = function()

        with open(outname, "w", encoding="utf-8") as f:
            f.write(html)
