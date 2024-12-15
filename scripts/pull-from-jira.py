#!/usr/bin/env python3
#
# automatic displaying of what is assigned to fixversion
# for current and next release

from jira import JIRA
jira = JIRA('https://armbian.atlassian.net')

from datetime import datetime
month = datetime.now().strftime('%m')
year = datetime.now().year

def icons(arg):
    if str(arg) == "Bug":
        return ("<img alt='Bug' src=https://armbian.atlassian.net/images/icons/issuetypes/bug.svg width=24>")
    if str(arg) == "Task":
        return ("<img alt='Task' src=https://armbian.atlassian.net/images/icons/issuetypes/task.svg width=24>")
    if str(arg) == "Story":
        return ("<img alt='Story' src=https://armbian.atlassian.net/images/icons/issuetypes/story.svg width=24>")
    if str(arg) == "Epic":
        return ("<img alt=Epic'' src=https://armbian.atlassian.net/images/icons/issuetypes/epic.svg width=24>")

if ( month <= "12" ):
   current_year=year+1
   current_month="02"
   next_month="05"
   next_year=year+1

if ( month <= "11" ):
   current_year=year
   current_month="11"
   next_month="02"
   next_year=year+1

if ( month <= "08" ):
   current_year=year
   current_month="08"
   next_month="11"
   next_year=year

if ( month <= "05" ):
   current_year=year
   current_month="05"
   next_month="08"
   next_year=year

if ( month <= "02" ):
   current_year=year
   current_month="02"
   next_month="05"
   next_year=year

# current
f = open("jira-current.html", "w")
current=str(current_year)[2:]+"."+current_month
f.write('<div style="color: #ccc;">\n<h1 style="color: #ccc;">Should be completed in '+current+'</h1>Sorted by priority<p>\n</div>\n')
f.write('<div style="color: #ccc;">\n<h5 style="color: #ccc;"><a href=https://github.com/armbian/build/pulls?q=is%3Apr+is%3Aopen+label%3A%22Needs+review%22+and+label%3A%22'+current_month+'%22>Check if you can review code that already waits at Pull reqests</a></h5>\n</div>\n')
f.write('<div class="icon-menu">\n')
for issue in jira.search_issues('project=AR and fixVersion="'+current+'" and status!="Done" and status!="Closed" order by Priority', maxResults=100):
    f.write('\n<a class="icon-menu__link" href=https://armbian.atlassian.net/browse/{}>{} {}: {}, <i>Assigned to: {}</i></a>'.format(issue.key, icons(issue.fields.issuetype), issue.fields.issuetype, issue.fields.summary, issue.fields.assignee ))
f.write('\n</div>\n');
f.close()

# next
f = open("jira-next.html", "w")
next=str(next_year)[2:]+"."+next_month
f.write('\n<div style="color: #ccc;">\n<h1 style="color: #ccc;">Planned for '+next+' and further</h1>Sorted by priority<p></div>\n<div class="icon-menu">')
for issue in jira.search_issues('project=AR and fixVersion="'+next+'" and status!="Done" and status!="Closed" order by priority desc', maxResults=100):
    f.write('\n<a class="icon-menu__link" href=https://armbian.atlassian.net/browse/{}>{} {}: {}, <i>Assigned to: {}</i></a>'.format(issue.key, icons(issue.fields.issuetype), issue.fields.issuetype, issue.fields.summary, issue.fields.assignee))
f.write('\n</div>\n');
f.close()
