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

view_only = True
print "Content-Type: text/html\n"

print '<html><head><link rel="stylesheet" type="text/css" href="css/style.css"/></head><body>'

page = 'Home'
page_opt = 'view'
if form.has_key("r"):
    page_parts = form["r"].value.split(':')
    page = page_parts[0]
    if len(page_parts) > 1:
        page_opt = page_parts[1]

git_dir = '/var/www/vhosts/bobfrank.org/subdomains/pygitwiki/httpdocs/data/.git'
git_config = '/var/www/vhosts/bobfrank.org/subdomains/pygitwiki/gitconfig'
myenv = {'GIT_DIR': git_dir, 'GIT_CONFIG': git_config}

def git(run):
    p = subprocess.Popen(run, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=myenv)

os.chdir("/var/www/vhosts/bobfrank.org/subdomains/pygitwiki/httpdocs/data")

git(['/usr/bin/git', 'init'])
git(['/usr/bin/git', 'stash'])
git(['/usr/bin/git', 'pull','/home/git/pygitwiki.git'])
git(['/usr/bin/git', 'stash','clear'])

try:
    fp = open('%s' % page)
    data = fp.read()
    fp.close()
except:
    data = 'File doesn\'t exist, create one <a href="/%s:edit">here</a>' % (page)
#		$text = preg_replace('@([^:])(https?://([-\w\.]+)+(:\d+)?(/([%-\w/_\.]*(\?\S+)?)?)?)@', '$1<a href="$2">$2</a>', $text);
if page != 'Home':
    data = '<notextile>| [Home] | [%s] | </notextile>\n\n'%(page)+data
else:
    data = '<notextile>| [%s] | </notextile>\n\n' % (page) + data

#data = re.sub(r'([^:])(https?://([-\w\.]+)+(:\d+)?(/([%-\w/_\.]*(\?\S+)?)?)?)', r'\1<a href="\2">\2</a>', data)
data = re.sub(r'\[([A-Z]\w+)\]', r'<a href="/\1">\1</a>', data)
data = re.sub(r'\[([A-Z]\w+)\|([\w\s]+)\]', r'<a href="/\1">\2</a>', data)

print textile.textile(data)
print '</body></html>'
