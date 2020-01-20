
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

    #
    # Grab lists of statuses for queries
    # There is no jira-python API for this, so we call _get_json() manually
    #

    statuses = {
        "newopen":[],                               # custom
        "indeterminate":[], "done":[], "new":[]     # these come straight from statusCategory.key
    }
    for issuetype in jiraconnection._get_json("project/TIC/statuses"):
        if issuetype["name"].lower()=="ticket":
            for status in issuetype["statuses"]:
                statuses[ status["statusCategory"]["key"] ].append(status["name"])
                if isearch(r"open.*1st", status["name"]) or status["statusCategory"]["key"]=="new":
                    statuses["newopen"].append(status["name"])
    for k,v in statuses.items():
        statuses[k] = '("' + '","'.join(v) + '")'   # Turn arrays into '("Foo","Bar")'
        print("... statuses[{}] = {}".format(k, statuses[k]))


    #
    # Go to work: loop dates!
    #

    print("Querying {} -- {}, every {} days".format(fromdate,todate,step))

    for day in daterange(fromdate, todate, step=step):

        if day==date.today():
            print("SKIPPING today to not store incomplete data.")
            continue

        def issuecount(jql):
            return jiraconnection.search_issues("""project = TIC AND issuetype = Ticket AND """ + jql,
                fields="none", expand="none", maxResults=1,
            ).total

        daystr = day.isoformat()

        fields = {
            "innewopen": ( issuecount, """status WAS IN {} ON "{}" """.format(statuses["newopen"], daystr) ),
            "innewopen_lowmed": ( issuecount, """Priority IN ("Low","Medium") AND status WAS IN {} ON "{}" """.format(statuses["newopen"], daystr) ),
            "innewopen_07": ( issuecount, """status WAS IN {} ON "{} 07:00" """.format(statuses["newopen"], daystr) ),
            "innewopen_12": ( issuecount, """status WAS IN {} ON "{} 12:30" """.format(statuses["newopen"], daystr) ),
            "innewopen_17": ( issuecount, """status WAS IN {} ON "{} 17:30" """.format(statuses["newopen"], daystr) ),
            "toprogress": ( issuecount, """status CHANGED TO {} ON "{}" """.format(statuses["indeterminate"], daystr) ),
            "toresolved": ( issuecount, """resolution CHANGED FROM "" ON "{}" """.format(daystr) ),
            "innew": ( issuecount, """status WAS IN {} ON "{}" """.format(statuses["new"], daystr) ),
            "numcreated": ( issuecount, """created >= {today} AND created < {tomorrow} """.format(today=day.isoformat(), tomorrow=(day + timedelta(1)).isoformat()) )
        }
        
        he = {
            "day": daystr,
            "vacation": "",
            "weekday": day.strftime("%a")
        }

        have =  history.get(daystr, {})
        for k,v in fields.items():
            if k in have and have[k]!=0:
                he[k] = have[k]
            else:
                func,args = v
                he[k] = func(args)



        year=day.year
        if date(year,6,15) <= day <= date(year,8,15):
            he["vacation"]="Summer"
        elif date(year,12,23) <= day:
            he["vacation"]="Xmas"
        elif day <= date(year,1,2):
            he["vacation"]="NewYear"

        history[daystr] = he
        print(he)

    return history



if __name__ == "__main__":

    try:
        with open("tic-status-counts.json", "r") as f:
            history = json.load(f)
    except FileNotFoundError:
        history = {}

    def daysago(days):
        return date.today() - timedelta(days=days)


    # getstatuscounts(daysago(i*7), daysago(i*7-6), history=history, step=1)
    getstatuscounts(daysago(65), daysago(1), history=history, step=1)

    if False:
        for i in range(4*52, 0, -1):
            print(i)
            getstatuscounts(daysago(i*7), daysago(i*7-6), history=history, step=1)

            with open("tic-status-counts.json", "w") as f:
                json.dump(history, f, indent=1)

    with open("tic-status-counts.json", "w") as f:
        json.dump(history, f, indent=1)
