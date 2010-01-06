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

print '<html><head><link rel="stylesheet" type="text/css" href="css/style.css"/></head><body>'

debug = False
debp = ''
if os.environ['QUERY_STRING'].find('debug') > 0:
    debug = True
    debp = '&debug'
    print '[debug mode on]<table border=1><tr><td><pre>'

page = 'Home'
page_opt = 'view'
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
    if debug:
        print '$ %s' % ' '.join(run)
        o,e = p.communicate()
        print o.replace('\n', '<br/>'), e.replace('\n', '<br/>'),
        print '<br/>rcode=%d'%p.returncode

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
else:
    try:
        fp = open('%s' % page)
        data = fp.read()
        fp.close()
    except:
        data = 'File doesn\'t exist, create one <a href="/%s:edit%s">here</a>' % (page,debp)
    #		$text = preg_replace('@([^:])(https?://([-\w\.]+)+(:\d+)?(/([%-\w/_\.]*(\?\S+)?)?)?)@', '$1<a href="$2">$2</a>', $text);
    if page != 'Home':
        data = '<notextile>| [Home] | [%s] | <a href="/%s:edit%s">edit</a> |</notextile>\n\n'%(page,page,debp)+data
    else:
        data = '<notextile>| [%s] | <a href="/%s:edit%s">edit</a> | </notextile>\n\n' % (page,page,debp) + data
 
    #data = re.sub(r'([^:])(https?://([-\w\.]+)+(:\d+)?(/([%-\w/_\.]*(\?\S+)?)?)?)', r'\1<a href="\2">\2</a>', data)
    data = re.sub(r'\[([A-Z]\w+)\]', r'<a href="/\1%s">\1</a>' % debp, data)
    data = re.sub(r'\[([A-Z]\w+)\|([\w\s]+)\]', r'<a href="/\1%s">\2</a>' % debp, data)

    print textile.textile(data)
print '<br/><br/><i><font size=2><a href="/source.py">[source code]</a></font></i></body></html>'
