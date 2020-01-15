import re

#
# utils
#

def isearch(pattern, string):
    '''Shorthand case-independent re.search'''
    return re.search(pattern, string, re.IGNORECASE)

def daterange(date1, date2): # sigh python why do I need this
    for n in range(int ((date2 - date1).days)+1):
        yield date1 + timedelta(n)
