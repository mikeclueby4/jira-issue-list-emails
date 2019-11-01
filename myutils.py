import re

#
# utils
#

def isearch(pattern, string):
    '''Shorthand case-independent re.search'''
    return re.search(pattern, string, re.IGNORECASE)
