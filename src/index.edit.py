import textile
import cgi
import subprocess
import re
import os
import base64
import zlib
import pickle
import Cookie

form = cgi.FieldStorage()

print "Content-Type: text/html\n"
print """
<html>
<head>
<link rel="stylesheet" type="text/css" href="css/style.css"/>
<link rel="stylesheet" type="text/css" href="css/no-reset.css"/>
<link rel="stylesheet" type="text/css" href="css/wiki.css"/>
</head>
<body>
<div id="header"> </div>
<div id="content">
"""

print '<script type="text/javascript" src="wz_tooltip.js"></script>'

debug = False
debp = ''
if os.environ['QUERY_STRING'].find('debug') > 0:
    debug = True
    debp = '&debug'
    print '[debug mode on]<table border=1><tr><td><pre>'

page = 'Home'
page_opt = 'blame'
if form.has_key("r"):
    page_parts = form["r"].value.split(':')
    page = page_parts[0]
    if len(page_parts) > 1:
        page_opt = page_parts[1]
        if page_opt.find('&debug') > 0:
            page_opt = page_opt.split('&')[0]

user = os.environ['REMOTE_USER']
git_dir = '/var/www/vhosts/theinternetneverlies.com/subdomains/but/httpdocs/data/wigit/.git'
git_config = '/var/www/vhosts/theinternetneverlies.com/subdomains/but/httpdocs/%s.gitconfig' % user
myenv = {'GIT_DIR': git_dir, 'GIT_CONFIG': git_config}

if debug:
    print ':: user=%s'%user
    print '$ cat %s' % git_config
    print open(git_config).read()
    print ':: page=%s, page_opt=%s<br/>' % (page, page_opt)

def git(run, debug=False):
    p = subprocess.Popen(run, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=myenv)
    o,e = p.communicate()
    if debug:
        print '$ %s' % ' '.join(run)
        print o.replace('\n', '<br/>'), e.replace('\n', '<br/>'),
        print '<br/>rcode=%d'%p.returncode
    return o

if debug:
    print '$ cd /var/www/vhosts/theinternetneverlies.com/subdomains/but/httpdocs/data/wigit'
os.chdir("/var/www/vhosts/theinternetneverlies.com/subdomains/but/httpdocs/data/wigit")

git(['/usr/bin/git', 'stash'], debug)
git(['/usr/bin/git', 'pull','/home/git/wigit'], debug)
git(['/usr/bin/git', 'stash','clear'], debug)

if page_opt == 'save':
    if page.find('..') >= 0 or page.find('/') >= 0:
        print 'Invalid filename'
    else:
        if form.has_key('data'):
            if debug:
                print 'saving %s, len(data) = %d' % (page,len(form['data'].value))
            fp = open('%s' % page, 'w')
            fp.write(form['data'].value)
            fp.close()
        elif debug:
            print 'no data found in form for save!'
        git(['/usr/bin/git', 'add', page], debug)
        git(['/usr/bin/git', 'commit','-a','-m','changed page %s via website' % page], debug)
        git(['/usr/bin/git', 'push', '/home/git/wigit/.git'], debug)
elif page_opt == 'rename':
    new_name = form['new_name'].value
    if new_name.find('..') >= 0 or new_name.find('/') >= 0:
        print 'Invalid filename'
    else:
        for file in os.listdir('.'):
            if file.find('.') < 0:
                f=open(file)
                data = f.read()
                f.close()
                if data.find('[%s]'%page) > 0:
                    data = data.replace('[%s]'%page,'[%s]'%new_name)
                    f=open(file,'w')
                    f.write(data)
                    f.close()
                    git(['/usr/bin/git', 'add', file], debug)
                if file == page:
                    git(['/usr/bin/git', 'mv', page, new_name], debug)
        git(['/usr/bin/git', 'commit','-a','-m','renaming %s to %s via website' % (page,new_name)], debug)
        git(['/usr/bin/git', 'push', '/home/git/wigit/.git'], debug)

if debug:
    print '</pre></td></tr></table>'

def links(data,mode=None):
    if not mode or mode == 'edit':
       mode = ''
    elif len(mode) > 1 and mode[0] != ':':
       mode = ':'+mode
    #		$text = preg_replace('@([^:])(https?://([-\w\.]+)+(:\d+)?(/([%-\w/_\.]*(\?\S+)?)?)?)@', '$1<a href="$2">$2</a>', $text);
    #data = re.sub(r'([^:])(https?://([-\w\.]+)+(:\d+)?(/([%-\w/_\.]*(\?\S+)?)?)?)', r'\1<a href="\2">\2</a>', data)
    data = re.sub(r'\[([A-Z]\w+)\]', r'<a href="/\1%s%s">\1</a>' % (mode,debp), data)
    data = re.sub(r'\[([A-Z]\w+)\|([\w\s]+)\]', r'<a href="/\1%s%s">\2</a>' % (mode,debp), data)
    return data

s ='| [%s] <!-- | <a href="/%s:blame%s">blame</a> --> | <a href="/log">log</a> | <a href="/%s:edit%s">edit</a> |<br/><br/>\n' % (page,page,debp,page,debp)
if page != 'Home':
    s = '| [Home] '+s
linksopt = page_opt
if page_opt == 'edit' or page_opt == 'blame' or page_opt == 'save' or page_opt == 'rename':
    linksopt = ''
print links(s,linksopt)

if page_opt == 'edit':
    data = ''
    try:
        fp = open('%s' % page)
        data = fp.read()
        fp.close()
    except:
        data = ''
    print '<form action="/%s:rename%s" method="post">' % (page,debp)
    print 'Editing <input name="new_name" value="%s"/>' % page
    print '<input type="hidden" name="r" value="%s:rename%s"/>' % (page,debp)
    print '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<input type="submit" value="Rename">'
    print '</form>'
    print '<form action="/%s:save%s" method="post">' % (page,debp)
    print '<input type="hidden" name="r" value="%s:save%s"/>' % (page,debp)
    print '<textarea name="data" cols="90" rows="40">%s</textarea><br/>' % data
    print '<input type="submit" value="save">'
    print '</form>'
elif page_opt == 'rename':
    new_name = form['new_name'].value
    print 'renaming from %s to %s<br/>' % (page, new_name)
    page = new_name
    print 'finished renaming (including adjustments needed to other pages), please continue to <a href="%s%s">%s</a>' % (page,debp,page)
elif page == 'log':
    data = git(['/usr/bin/git','log'], debug)
    k = -2
    last = ''
    diffs = {}
    while True:
        k = data.find('commit', k+2)
        if k >= 0:
            j = data.find('\n',k)
            if j >= 0:
                commit = data[k+7:j]
                if len(commit) > 10:
                    if last != '':
                        diffs[last] = commit
                    last = commit
        else:
            break
    for a in diffs:
        b = diffs[a]
        data = data.replace(a, '<a href="diff&b=%s&a=%s">%s</a>'%(a.upper(),b.upper(),a.upper()))
    print '<pre>%s</pre>' % data
elif page == 'diff':
    if form.has_key('a') and form.has_key('b'):
        data = git(['/usr/bin/git','diff',form['a'].value,form['b'].value], debug)
        print data.replace('\n','<br/>')
elif page_opt == 'blame':
    data = git(['/usr/bin/git','blame','-c',page])
    lines = data.split('\r\n')
#    print '<pre>'
    data = ''
    blamery = {}
    for i,line in enumerate(lines):
        tabs = line.split('\t')
        if len(tabs) >= 4:
#            print i+1,tabs
            k = tabs[3].find(')')
            if len(tabs[3][k+1:]) == 0 or tabs[3][-1] == '|':
                data = data + tabs[3][k+1:]+'\n'
            else:
                tag = ' /thisisanendoflineforline%s/ '%i
                data = data + tabs[3][k+1:]+'%s\n'%tag
                blamery[tag] = [tabs[0], tabs[1][1:].strip(), tabs[2]]
#    print '</pre>'
    blob = textile.textile(data)
    for tag in blamery:
       k = blob.find(tag)
       if k >= 0:
           j = max(blob.rfind('li>',0,k), blob.rfind('h2>',0,k), blob.rfind('h3>',0,k), blob.rfind('h1>',0,k), blob.rfind('<p>',0,k))
           if j >= 0:
               blob = blob.replace( blob[j+3:k+len(tag)], '<span class="line" onmouseover="Tip(\'User: %s<br/>Date/Time: %s<br/>Revision: %s\')" onmouseout="UnTip()">%s</span>' % (blamery[tag][1], blamery[tag][2], blamery[tag][0], blob[j+3:k]) )
    print links(blob)
else:
    try:
        fp = open('%s' % page)
        data = fp.read()
        fp.close()
    except:
        data = 'File doesn\'t exist, create one <a href="/%s:edit%s">here</a>' % (page,debp)
    print textile.textile(links(data,'view'))
print "</div>"
print "<div id='footer'>"
print '<br/><br/><i><font size=2><a href="/source.py">[source code]</a></font></i></div></body></html>'

