from markupsafe import Markup, escape
import re


#
# Defaults expected to be overriden from main script
#

string_scorepatterns = {
    # dict of regexp:scoreadjust
    # note that several may match at the same time, they are then simply summed
    # Examples:
    #   r'(reallybad|othercatastrophe)': 15,
    #   r'(slightly noticeable)': 5,
    #   r'(internal only|minor)': -10
}

label_scorepatterns = {
    # see string_scorepatterns
}

prioscores = {
    # dict of id:scoreadjust
}


def customscore(score, issue):
    '''Any additional scoring adjustments/overrides needed
    Override this function to implement your own functionality!
    '''
    pass

def customgroup(issue):
    '''Determine what group an issue should be listed under.
    Override this function to implement your own functionality!

    Return tuple of:
        sortkey: number,
        displayname: string
    '''
    return (0, "Issues")

#
# "Score" class
#
# Holds current score + log of what went into it
#

class Score:
    def __init__(self,
                score=0,    # type: int
                text=None   # type: Optional[str]
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
        return "".join(outs)
    return myoutputter, myfinalizer


def isearch(pattern, string):
    '''Shorthand case-independent re.search'''
    return re.search(pattern, string, re.IGNORECASE)





#
# HTML page header
#
# Important note on .format(**locals()) throughout: f-strings don't work with markupsafe, escaping doesn't happen!
#


def getheader(title = "", basehref = "http://jira/", outputter = None, finalizer = None):
    '''Return default HTML header as a string. Caller can polish/append as needed.

    For outputter/finalizer, see make_outputter()
    '''
    (out,finalizer) = make_outputter(outputter, finalizer)

    out(Markup("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <base href="{basehref}" target="_blank">
    <style type="text/css">
""").format(**locals()))

    # separate non-formatted section for CSS because lots of { }
    out(Markup("""
        li {
            list-style: none;
            display: block;
            margin-bottom: 5px;
        }
        body {
            font-family: BlinkMacSystemFont,"Segoe UI","Roboto","Oxygen","Ubuntu","Fira Sans","Droid Sans","Helvetica Neue",sans-serif;
            font-size: 14px;
            color: #555;
        }
        b {
            font-weight: 550;
            color: #111;
        }
        pre {
            margin: 0;
            font-size: 10px;
            font-family: lucida console, courier;
            white-space: pre-wrap;
        }
        .groupheader {
            font-weight: 500;
            letter-spacing: -1px;
        }
        .description {
            font-size: smaller;
            display: inline-block;
        }
        .collapsibledescription {
            /* collapsible stuff that integrates with toggle and label */
            max-height: 2.1rem;
            overflow: hidden;
            transition: max-height .25s ease-in-out;
        }
        .description-toggle {
            display: none;
        }
        .description-toggle:checked + .collapsibledescription {
            max-height: 100em;
        }
        .description-toggle:checked + .collapsibledescription > .description-fader {
            display: none;
        }
        .description-fader {
            content:'';
            width: 100%;
            height: 50%;
            position: absolute;
            left:0;
            bottom: 0;
            background:linear-gradient(#ffffff60 0%, #ffffffff 100%);
        }
        .label {
            font-size: 12px;
            display: inline-block;
            border: 1px solid #ccc;
            background-color: #f5f5f5;
            color: #555;
            padding: 1px 5px;
            border-radius: 3px;
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
            white-space: nowrap;
            text-overflow: ellipsis;
            overflow: hidden;
            max-width: 10em;
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
            display: block;
            font-size: 10px;
            font-weight: 600;
            margin-left: 10px;
        }
        .numcomments {
            display: block;
            font-size: 10px;
            margin-left: 10px;
        }
        .subbox {
            padding: 2px;
        }
        .subbox-left {
            min-width: 8.5em;
            padding-right: 0.5em;
            line-height: 11px;
        }
        .subbox-middle {
            border-left: 1px #ddd solid;
            padding-right: 0.5em;
        }
        .subbox-right {
            position: relative;  /* IMPORTANT: for description-fader positioning to work */
            max-width: 130em;
        }
        .score {
            padding-left: 1em;
            padding-right: 1em;
            color: #ccc;
            font-size: 8px;
        }
        .tooltip {
            position: relative;
        }
        .tooltip .tooltiptext {
            visibility: hidden;
            background-color: #eee;
            color: #555;
            padding: 5px;
            width: max-content;
            border-radius: 3px;
            position: absolute;
            z-index: 1;
            opacity: 0;
            transition: opacity 0.3s;
            white-space: pre-wrap;
            font-size: 10px;
        }
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
    """))

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

def render(jiraconnection, issues, groupheadertag = "h2", outputter = None, finalizer = None):
    '''Render given list of issues into HTML.

    For outputter/finalizer, see make_outputter()
    '''
    (out,finalizer) = make_outputter(outputter, finalizer)

    #
    # Loop through and score the returned issues
    #

    for issue in issues:
        issue.numcomments = len(jiraconnection.comments(issue.key))
        f = issue.fields
        score = Score()
        score += (len(f.issuelinks), "Linked issues")
        score += (f.watches.watchCount, "Watchers")
        score += (f.votes.votes * 2, "2 x Votes")
        score += (issue.numcomments, "Comments")
        score.patterns(f.summary, string_scorepatterns, "Summary pattern ")
        score.patterns(f.description, string_scorepatterns, "Description pattern ")
        score += (prioscores[f.priority.id], "Priority " + f.priority.name)
        for label in f.labels:
            score.patterns(label, label_scorepatterns, "Label pattern ")
        for link in f.issuelinks:
            li = getattr(link, "inwardIssue", None) or getattr(link, "outwardIssue", None)
            score.patterns(li.fields.issuetype.name, string_scorepatterns, f"Linked issue type '{li.fields.issuetype.name}' pattern ")
            score.patterns(li.fields.summary, string_scorepatterns, f"Linked issue summary '{li.fields.summary}' pattern ")

        customscore(score, issue)

        setattr(issue, "score", score)


    #
    # Group issues per status/resolution
    #

    groups = {
        # (sort,groupname) = list of issues
    }
    for issue in issues:
        group = customgroup(issue)

        if not group in groups:
            groups[group] = []

        groups[group].append(issue)


    #
    # Loop the groups&issues and generate HTML!
    #

    print("")
    print("Outputting issue groups:")

    for groupidx,issues in sorted(groups.items()):
        (sort,groupname) = groupidx
        print(f"   {sort} {groupname} - {len(issues)} issues")

        out(Markup("""
    <{groupheadertag} class="groupheader">{groupname}</{groupheadertag}>
    <ul>
    """).format(**locals()))

        for issue in sorted(issues, key=lambda i: i.score.score, reverse=True):
            f = issue.fields
            description = f.description.strip()
            description = re.sub(r"(\r?\n)+", "\n", description)
            description = str(escape(description))   # str to not trigger escaping in re.sub()
            summary = str(escape(f.summary))     # str to not trigger escaping in re.sub()
            for pattern,score in string_scorepatterns.items():
                if score>0:
                    summary = re.sub(pattern, r"<b>\g<0></b>", summary, flags=re.IGNORECASE)
                    description = re.sub(pattern, r"<b>\g<0></b>", description, flags=re.IGNORECASE)

            summary = Markup(summary)
            description = re.sub(r"({noformat}|{code[^}]*}) *\n*(.*?)\n *({noformat}|{code}) *\n?", r"<pre>\g<2></pre>", description, flags=re.DOTALL)
            description = Markup( description.replace("\n", Markup("<br>")) )

            if not f.resolution:
                resolution = ""
            else:
                resolution = f"Resolution: {f.resolution.name}"
            scoretooltip = "\n".join(issue.score.log)
            out(Markup("""
                <li>
                <img src="{f.issuetype.iconUrl}" height="16" width="16" border="0" align="absmiddle" alt="{f.issuetype.name}">
                <a class="issue-link" href="/browse/{issue.key}">{issue.key}</a>
                <img src="{f.priority.iconUrl}" alt="{f.priority.name}" height="16" width="16" border"0" align="absmiddle">
                <span class="summary">{summary}</span>
                <span class="score tooltip">{issue.score.score}<span class="tooltiptext">{scoretooltip}</span></span>
                """).format(**locals()))
            for label in f.labels:
                out(Markup("""
                <span class="label">{label}</span>
                """).format(**locals()))
            out(Markup("""
                <br>
                <table class="subbox"><tbody><tr valign=top>
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

            if description.count("<br>")>=2:
                out(Markup("""
                    <input id="description-toggle-{issue.id}" class="description-toggle" type="checkbox">
                    <label for="description-toggle-{issue.id}" class="description collapsibledescription">
                    {description}<div class="description-fader"></div></label>
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
