from markupsafe import Markup, escape


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


def customscore(issue, score):
    '''Any additional scoring adjustments/overrides needed
    Override this function to implement your own functionality!
    '''
    return score

def customgroup(issue):
    '''Determine what group an issue should be listed under.
    Override this function to implement your own functionality!

    Return tuple of:
        sortkey: number,
        displayname: string
    '''
    f = issue.fields
    if f.resolution:
        if isearch(r"fixed", f.resolution.name):
            return 3,"Resolved: Fixed"
        return  4,"Resolved: Other"

    if isearch(r"(need|wait|on[-_ .]?hold)", f.status.name):
        return 1,"Waiting for something"

    if f.status.statusCategory.key=='new' and not isearch(r"confirmed", f.status.name):
        return 0,"Unconfirmed / To Do / New"

    return 2,"Confirmed / Progressing"


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
            str = escape(str)
            outputter(str)
        return outwrapper, finalizer

    # Define our own spooler that deallocates itself when the function references go out of scope
    outs = []
    def myoutputter(str):
        str = escape(str)
        outs.append(str)    # instead of raw append on string = expensiiiive
    def myfinalizer():
        return "".join(outs)
    return myoutputter, myfinalizer


import re
def isearch(pattern, string):
    '''Shorthand case-independent re.search'''
    return re.search(pattern, string, re.IGNORECASE)


def scorestring(string, patterns):
    '''Iterate over a dict of regex:scoreadjust and return sum of those that match the input string'''
    ret = 0
    for pattern,score in patterns.items():
        if re.search(pattern, string, re.IGNORECASE):
            ret += score
    return ret



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
        li {  }
        body {
            font-family: BlinkMacSystemFont,"Segoe UI","Roboto","Oxygen","Ubuntu","Fira Sans","Droid Sans","Helvetica Neue",sans-serif;
            font-size: 14px;
        }
        .description {
            font-size: smaller;
            padding-top: 4px;
            display: inline-block;
            /* collapsible stuff that integrates with toggle and label */
            max-height: 3rem;
            overflow: hidden;
            transition: max-height .25s ease-in-out;
        }
        .description-toggle {
            display: none;
        }
        .description-toggle:checked + .description {
            max-height: 100em;
        }
        .description-toggle:checked + .description > .description-fader {
            display: none;
        }
        .description-fader {
            content:'';
            width: 100%;
            height: 1.2rem;
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
            padding-left: 10%;
            padding-top: 2px;
            margin-bottom: 1rem;
        }
        .score {
            padding-left: 2em;
            color: #ddd;
            font-size: 8px;
        }
        pre {
            font-size: 10px;
            font-family: lucida console, courier;
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

def render(issues, groupheadertag = "h2", outputter = None, finalizer = None):
    '''Render given list of issues into HTML.

    For outputter/finalizer, see make_outputter()
    '''
    (out,finalizer) = make_outputter(outputter, finalizer)

    #
    # Loop through and score the returned issues
    #

    for issue in issues:
        f = issue.fields
        score = len(f.issuelinks) + f.watches.watchCount + ( f.votes.votes * 2 )
        score += scorestring(f.summary, string_scorepatterns)
        score += scorestring(f.description, string_scorepatterns)
        score += prioscores[f.priority.id]
        for label in f.labels:
            score += scorestring(label, label_scorepatterns)
        for link in f.issuelinks:
            li = getattr(link, "inwardIssue", None) or getattr(link, "outwardIssue", None)
            score += scorestring(li.fields.issuetype.name, string_scorepatterns)
            score += scorestring(li.fields.summary, string_scorepatterns)

        score = customscore(issue, score)

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
    <{groupheadertag}>{groupname}</{groupheadertag}>
    <ul>
    """).format(**locals()))

        for issue in sorted(issues, key=lambda i: i.score, reverse=True):
            f = issue.fields
            shortdesc = f.description.strip()
            shortdesc = re.sub(r"(\r?\n)+", "\n", shortdesc)
            # shortdesc = shortdesc[0:200]
            shortdesc = str(escape(shortdesc))   # str to not trigger escaping in re.sub()
            summary = str(escape(f.summary))     # str to not trigger escaping in re.sub()
            for pattern,score in string_scorepatterns.items():
                if score>0:
                    summary = re.sub(pattern, r"<b>\g<0></b>", str(summary), flags=re.IGNORECASE)
                    shortdesc = re.sub(pattern, r"<b>\g<0></b>", str(shortdesc), flags=re.IGNORECASE)

            summary = Markup(summary)
            # shortdesc = Markup(shortdesc).split("\n")[0:3]
            # shortdesc = Markup("<br>").join( shortdesc ) + "..."
            shortdesc = re.sub(r"({noformat}|{code[^}]+}) *\n*(.*?)\n *({noformat}|{code}) *\n?", r"<pre>\g<2></pre>", shortdesc, flags=re.DOTALL)
            shortdesc = Markup( shortdesc.replace("\n", Markup("<br>")) )

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
                <div class="subbox" style="position: relative;"> <!-- silly position:relative has to be there for the fader to work -->
                <span class="status status-color-{f.status.statusCategory.colorName}">{f.status.name}</span> &nbsp;
                <span class="resolution">{resolution}</span>
                &nbsp; """).format(**locals()))

            for label in f.labels:
                out(Markup("""
                <span class="label">{label}</span>
                """).format(**locals()))

            out(Markup("""
                <br>
                <input id="description-toggle-{issue.id}" class="description-toggle" type="checkbox">
                <label for="description-toggle-{issue.id}" class="description">
                {shortdesc}<div class="description-fader"></div></label>

                </div>

                </li>
                """).format(**locals()))

        # End of group
        out(Markup("""
    </ul>
    """))

    return finalizer()


def getfooter(outputter = None, finalizer = None):
    (out,finalizer) = make_outputter(outputter, finalizer)

    out(Markup("""
    </body>
    </html>
    """))

    return finalizer()
