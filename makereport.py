from markupsafe import Markup, escape
from typing import List, Set, Dict, Tuple, Optional
import jira
import makereport
import re
from myutils import *


#
# Defaults expected to be overriden from main script
#

def debug(text):
    pass

# We expect a working JIRA() object here before out methods are called
jiraconnection = None   # type: jira.client.JIRA

# <base href> for all report emails (default settings.py will set this = the REST jira server url)
basehref = "http://jira/"   # type: str


string_scorepatterns = {
    # dict of regexp:scoreadjust
    # note that several may match at the same time, they are then simply summed
    # Examples:
    #   r'(reallybad|othercatastrophe)': 15,
    #   r'(slightly noticeable)': 5,
    #   r'(internal only|minor)': -10

} # type: Dict[str,int]

label_scorepatterns = {
    # see string_scorepatterns

} # type: Dict[str,int]

issuetype_scorepatterns = {

} # type: Dict[str,int]

linked_issuetype_scorepatterns = {

} # type: Dict[str, int]

prioscores = {
    #  123: -5,

} # type: Dict[int, int]



def customscore(score,   # type: Score
                issue    # type: jira.resources.Issue
                ):
    '''Any additional scoring adjustments/overrides needed
    Override this function to implement your own functionality!
    '''
    pass

def customgroup(issue       # type: jira.resources.Issue
                ):
    # type: Tuple[text,string]
    '''Determine what group an issue should be listed under.
    Override this function to implement your own functionality!

    Return tuple of:
        sortkey: number,
        displayname: string
    '''
    return (0, "Issues")



#
# utils
#

def make_outputter(outputter = None, finalizer = None):
    '''Returns an output(str) and finalizer() function if not supplied as input.
    Internals of functionality do not matter
    '''
    # Both functions supplied? Use them.
    if outputter and finalizer:
        def outwrapper(str):
            str = escape(str).replace("\xa0", Markup("&nbsp;"))
            outputter(str)
        return outwrapper, finalizer

    # Define our own spooler that deallocates itself when the function references go out of scope
    outs = []
    def myoutputter(str):
        str = escape(str).replace("\xa0", Markup("&nbsp;"))
        outs.append(str)    # instead of raw append on string = expensiiiive
    def myfinalizer():
        return Markup("").join(outs)
    return myoutputter, myfinalizer



#
# "Score" class
#
# Holds current score + log of what went into it
#

class Score:
    def __init__(self,
                score=0,    # type: int
                text=None   # type: str
                ):
        self.score = score
        self.log = []
        if text:
            self.log += text

    def __iadd__(self,
                adjust_and_text     # type: Tuple[int, str]
                ):
        (adjust,text) = adjust_and_text
        if adjust!=0:
            self.score += adjust
            self.log.append(f"""{"+" if adjust>=0 else ""}{adjust}: {text}""")
        return self

    def set(self,
            score,  # type: int
            text    # type: str
            ):
        self.score = score
        self.log.append(f"Force: {score}: {text}")

    def patterns(self,  # type: Score
            text,       # type: str
            patterns,   # type: Dict[str,int]
            prefix      # type: str
            ):
        '''Iterate over a dict of regex:scoreadjust and apply those that match text'''
        for pattern,adjust in patterns.items():
            if re.search(pattern, text, flags=re.IGNORECASE):
                self += (adjust, prefix + pattern)


def scoreissues(issues):
    """ Loop through and score the given issues
    Score is stored in the .score attribute of each issue as a "Score" object
    """

    for issue in issues:
        f = issue.fields
        assert hasattr(f, "comment"), """Did you forget to add ", fields='*all'" in your .search_issues() ?"""
        issue.numcomments = f.comment.total

        score = Score()
        score += (len(f.issuelinks), "Linked issues")
        score += (f.watches.watchCount, "Watchers")
        score += (f.votes.votes * 2, "2 x Votes")
        score += (len(f.versions) * 2, "2 x Versions")
        score += (len(f.fixVersions) * 2, "2 x FixVersions")
        score += (issue.numcomments, "Comments")
        score += (len(f.attachment), "Attachments")
        score += (len(f.components) * 3, "3 x Components")
        score.patterns(f.issuetype.name, issuetype_scorepatterns, f"Type '{f.issuetype.name}' pattern ")
        score.patterns(f.summary, string_scorepatterns, "Summary pattern ")
        score.patterns(f.description, string_scorepatterns, "Description pattern ")
        score += (prioscores[f.priority.id], "Priority " + f.priority.name)
        for label in f.labels:
            score.patterns(label, label_scorepatterns, "Label pattern ")
        for link in f.issuelinks:
            li = getattr(link, "inwardIssue", None) or getattr(link, "outwardIssue", None)
            score.patterns(li.fields.issuetype.name, linked_issuetype_scorepatterns, f"Linked issue type '{li.fields.issuetype.name}' pattern ")
            score.patterns(li.fields.summary, string_scorepatterns, f"Linked issue summary {li.fields.issuetype.name} '{li.fields.summary}' pattern ")

        customscore(score, issue)

        setattr(issue, "score", score)


#
# Issue grouping
#

def groupissues(issues):
    """Group issues per status/resolution. Calls customgroup() for every issue to get groupkey
    Returns an array of groupkey = array of Issues
    """

    groups = {
        # (sort,groupname) = list of issues
    } # type: Dict[Tuple[int,str] , List[jira.resources.Issue]]

    for issue in issues:
        groupkey = customgroup(issue)

        if not groupkey in groups:
            groups[groupkey] = []

        groups[groupkey].append(issue)

    return groups

#
# HTML page header
#
# Important note on .format(**locals()) throughout: f-strings don't work with markupsafe, escaping doesn't happen!
#


def getheader(title = "Issue list", mybasehref = None, outputter = None, finalizer = None):
    """Return default HTML header as a string. Caller can polish/append as needed.

    For outputter/finalizer, see make_outputter()
    """
    (out,finalizer) = make_outputter(outputter, finalizer)
    if mybasehref is None:
        mybasehref = basehref

    out(Markup("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <title>{title}</title>
    <base href="{mybasehref}" target="_blank" />
    <style type="text/css">
""").format(**locals()))

    with open("stylesheet.css", "r") as cssfile:
        out(Markup(cssfile.read()))

    out(Markup("""
    </style>
</head>
<body>
"""))

    return finalizer()



#
# Render issue list to HTML without header/footer
#
# Important note on .format(**locals()) throughout: f-strings don't work with markupsafe, escaping doesn't happen!
#

def render(issues, groupheadertag = "h2", outputter = None, finalizer = None):
    '''Render given list of issues into HTML.

    For outputter/finalizer, see make_outputter()
    '''
    (out,finalizer) = make_outputter(outputter, finalizer)

    scoreissues(issues)

    groups = groupissues(issues)



    #
    # Loop the groups&issues and generate HTML!
    #

    print("        Outputting issue groups:")

    for groupidx,issues in sorted(groups.items()):
        (sort,groupname) = groupidx
        print(f"           {sort} {groupname} - {len(issues)} issues")

        out(Markup("""
    <{groupheadertag} class="groupheader">{groupname}</{groupheadertag}>
    <ul>
    """).format(**locals()))

        for issue in sorted(issues, key=lambda i: i.score.score, reverse=True):
            f = issue.fields
            description = f.description.strip()
            description = re.sub(r"(\r?\n)+", "\n", description)
            description = re.sub(r"\x1B\x5B[\x21-\x3F]*?[\x40-\x7E]", "", description)  # strip common ansi escape sequences
            description = str(escape(description))   # str to not trigger escaping in re.sub()
            summary = str(escape(f.summary))     # str to not trigger escaping in re.sub()
            for pattern,score in string_scorepatterns.items():
                if score>0:
                    summary = re.sub(pattern, r"<b>\g<0></b>", summary, flags=re.IGNORECASE)
                    description = re.sub(pattern, r"<b>\g<0></b>", description, flags=re.IGNORECASE)

            summary = Markup(summary)
            description = re.sub(r"""({noformat}|{code[^}]*}) *\n*(.*?)({noformat}|{code}) *\n?""", r"""<span class="pre">\g<2></span>""", description, flags=re.DOTALL)
            description = re.sub(r"""({quote}) *\n*(.*?)({quote}) *\n?""", r"""<span class="quote">\g<2></span>""", description, flags=re.DOTALL)
            description = Markup( description.replace("\n", Markup("<br />")) )

            if not f.resolution:
                resolution = ""
            else:
                resolution = f"Resolution: {f.resolution.name}"
            scoretooltip = "\n".join(issue.score.log)
            out(Markup("""
                <li class="issue-li">
                <img src="{f.issuetype.iconUrl}" height="16" width="16" class="inlineicon" alt="{f.issuetype.name}" />
                <a class="issue-link" href="/browse/{issue.key}">{issue.key}</a>
                <img src="{f.priority.iconUrl}" alt="{f.priority.name}" height="16" width="16" class="inlineicon" />
                <span class="summary">{summary}</span>
                <span class="score tooltip">{issue.score.score}<span class="tooltiptext">{scoretooltip}</span></span>
                """).format(**locals()))
            for label in f.labels:
                out(Markup("""
                <span class="label">{label}</span>
                """).format(**locals()))
            out(Markup("""
                <br />
                <table class="subbox"><tbody><tr class="subbox-row">
                <td class="subbox-left">
                <span class="status status-color-{f.status.statusCategory.colorName}">{f.status.name}</span>
                <span class="resolution">{resolution}</span>
                """).format(**locals()))

            if issue.numcomments>0:
                out(Markup("""
                <span class="numcomments">{issue.numcomments}&nbsp;comments</span>
                """).format(**locals()))

            out(Markup("""
                </td>
                <td class="subbox-middle"></td>
                <td class="subbox-right">
            """))

            if description.count("<br")>=2:
                out(Markup("""
                    <input id="description-toggle-{issue.id}" class="description-toggle" type="checkbox" />
                    <label for="description-toggle-{issue.id}" class="description collapsibledescription">
                    {description}<span class="description-fader"></span></label>
                    """).format(**locals()))
            else:
                out(Markup("""
                    <div class="description">
                    {description}</div>
                    """).format(**locals()))

            out(Markup("""
                </td>
                </tr></tbody></table>
                </li>
            """))

        # End of group
        out(Markup("""
    </ul>
    """))

    return finalizer()


#
# HTML page footer
#
# Important note on .format(**locals()) throughout: f-strings don't work with markupsafe, escaping doesn't happen!
#

def getfooter(outputter = None, finalizer = None):
    (out,finalizer) = make_outputter(outputter, finalizer)

    out(Markup("""
</body>
</html>
    """))

    return finalizer()



#
# Settings utilities
#

def makecategoryreporter(categoryfilter, title, mytimefilter, reportskippedcategories=False):
    """Returns a freshly-created reporter function that works on projects in given category/ies"""
    def __func():
        reportskipped = reportskippedcategories
        html = makereport.getheader(title=title)

        skippedcategories = {}
        emptyprojects = []

        allprojects = jiraconnection.projects()
        totalnumprojects = len(allprojects)
        matchedprojects = 0

        for project in allprojects:

            if not hasattr(project, "projectCategory"):
                debug(f"      {project.key} ({project.name}) - No. No category.")
            elif not isearch(categoryfilter, project.projectCategory.name):
                skippedcategories[project.projectCategory.name] = project.key + " - " + project.name
                debug(f"      {project.key} ({project.name}) - No. \"{project.projectCategory.name}\" does not match.")
            else:
                matchedprojects += 1
                debug(f"      {project.key} ({project.name}) category {project.projectCategory.name} ...")
                print(f"  {project.name}...")
                issues = jiraconnection.search_issues(f"project = {project.key} {mytimefilter}",
                    fields="*all",      # Note "*all" so we also get comments!
                    maxResults=1000)
                reporthtml = makereport.render(issues)
                if len(reporthtml)<1:
                    emptyprojects.append(project.key + " - " + project.name)
                else:
                    html += Markup("<h1>{}</h1>\n").format(project.name)
                    html += reporthtml

        if totalnumprojects<1:
            html += Markup("""<p>&nbsp;<p>&nbsp
                <h1>Uh oh</h1>
                We can't see ANY projects in Jira. Permission problem?
            """).format(**locals())

        elif matchedprojects<1:
            html += Markup("""<p>&nbsp;<p>&nbsp
                <h1>Did someone change the categories under us?!?</h1>
                Our category filter "{categoryfilter}" matched NO projects out of total {totalnumprojects}
            """).format(**locals())
            reportskipped = True


        html += Markup("""<div class="footer">\n""")
        if len(emptyprojects)>0:
            html += Markup("""No issues in projects:<ul>\n""")
            for projtext in emptyprojects:
                html += Markup("""<li> {}</li>\n""").format(projtext)
            html += Markup("</ul>\n")

        if reportskipped and len(skippedcategories)>0:
            html += Markup("""Project categories not in listing:<ul>\n""")
            for cat,example in skippedcategories.items():
                if cat=="":
                    cat="(none)"
                html += Markup("""<li> "{}" e.g. {}</li>\n""").format(cat,example)
            html += Markup("</ul>\n")

        html += Markup("</div>\n")
        html += makereport.getfooter()

        return html
    return __func
