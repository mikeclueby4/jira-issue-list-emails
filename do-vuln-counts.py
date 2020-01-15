
from asyncio.windows_events import NULL
from json.decoder import JSONDecodeError
from typing import Any, Callable, Dict
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta

from jira import JIRA
import settings
from myutils import isearch
from settings import jiraconnection

import json


def daterange(date1, date2, step=1): # sigh python why do I need this
    for n in range(0, int ((date2 - date1).days)+1, step):
        yield date1 + timedelta(n)


def getstatuscounts(fromdate, todate, history=None, step=1):

    if history is None:
        history = {}

    whatproject = "VULN"
    whatissuetype = "Vulnerability"
    basejql = f"""project = {whatproject!r} AND issuetype = {whatissuetype!r}"""

    #
    # Grab lists of statuses for queries
    # There is no jira-python API for this, so we call _get_json() manually
    #

    statusesByCategory = {
        "indeterminate":[], "done":[], "new":[]     # these come straight from statusCategory.key
    }
    statuses = []
    for issuetype in jiraconnection._get_json("project/" + whatproject + "/statuses"):
        if issuetype["name"] == whatissuetype:
            for status in issuetype["statuses"]:
                statuses.append(status["name"])
                statusesByCategory[ status["statusCategory"]["key"] ].append(status["name"])

    assert len(statuses)>0 , f"Could not list statuses for issuetype {whatissuetype!r} under /project/{whatproject}/statuses - misspelled? No permissions?"

    for k,v in statusesByCategory.items():
        statusesByCategory[k] = '("' + '","'.join(v) + '")'   # Turn arrays into '("Foo","Bar")'
        print("... statusesByCategory[{}] = {}".format(k, statusesByCategory[k]))


    components = [ x.name for x in jiraconnection.project_components("VULN") ]

    def issuecount(jql):
            return jiraconnection.search_issues(basejql + " AND ( " + jql + " )",
                fields="none", expand="none", maxResults=1,
            ).total

    def componentcount(jql):
        ret = { k:0 for k in components }
        for issue in jiraconnection.search_issues(basejql + " AND ( """ + jql + " )",
            fields="components", expand="none", maxResults=1000,
        ):
            for c in issue.fields.components:
                ret[c.name]+=1
        return ret


    #
    # Go to work: loop dates!
    #

    print("Querying {} -- {}, every {} days".format(fromdate,todate,step))

    for day in daterange(fromdate, todate, step=step):

        daystr = day.isoformat()

        he = {
            "day": daystr,
            "weekday": day.strftime("%a"),
            "statuschanged": issuecount("""status CHANGED ON "{}" """.format(daystr) ),
            "toresolved": issuecount("""resolution CHANGED FROM "" ON "{}" """.format(daystr) ),
        }
        for status in statuses:
            he[status] = issuecount("""status WAS IN ("{}") ON "{}" """.format(status, daystr) )
        he["percomponent"] = componentcount("""status WAS IN {} ON "{}" """.format(statusesByCategory["indeterminate"], daystr))

        history[daystr] = he
        print(he)

    return history



if __name__ == "__main__":

    try:
        with open("vuln-status-counts.json", "r") as f:
            history = json.load(f)
    except FileNotFoundError:
        history = {}

    def daysago(days):
        return date.today() - timedelta(days=days)


    if True:
        # getstatuscounts(date(2018,1,1), date(2018,1,16), history=history, step=1)
        getstatuscounts(daysago(7), daysago(0), history=history, step=1)
    else:
        for i in range(2*52, 0, -1):
            print(i)
            getstatuscounts(daysago(i*7), daysago(i*7-6), history=history, step=1)

            with open("vuln-status-counts.json", "w") as f:
                json.dump(history, f, indent=1)

    with open("vuln-status-counts.json", "w") as f:
        json.dump(history, f, indent=1)
