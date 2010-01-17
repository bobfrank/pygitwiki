#!/usr/bin/python

import textile
import cgi
import subprocess
import re
import os
import base64
import zlib
import pickle
import Cookie
import sys
import cgitb
cgitb.enable()

form = cgi.FieldStorage()

# Configuration - these should be made into constants, later
USER = os.environ['REMOTE_USER']
QUERY_STRING = os.environ['QUERY_STRING']
user = USER

base_dir = '/var/repos/dontbiteme/'
http_dir = '/var/www/data/'
git_dir = '%s/.git' % (base_dir)
git_config = '%s/%s.gitconfig' % (base_dir, user)
myenv = {'GIT_DIR': git_dir, 'GIT_CONFIG': git_config}


CONTENT_TYPE = "Content-Type: text/html\n"
START_HTML = """
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
END_HTML = """
</div>
<div id='footer'>
<br/><br/><i><font size=2><a href="/source.py">[source code]</a></font></i></div></body></html>
"""


TOOLTIP_INCLUDE = '<script type="text/javascript" src="wz_tooltip.js"></script>'
START_DEBUG = '[debug mode on]<table border=1><tr><td><pre>'
END_DEBUG = '</pre></td></tr></table>'

# Generate links
def links(data,debp,mode=None):
    if not mode or mode == 'edit':
       mode = ''
    elif len(mode) > 1 and mode[0] != ':':
       mode = ':'+mode
    #           $text = preg_replace('@([^:])(https?://([-\w\.]+)+(:\d+)?(/([%-\w/_\.]*(\?\S+)?)?)?)@', '$1<a href="$2">$2</a>', $text);
    #data = re.sub(r'([^:])(https?://([-\w\.]+)+(:\d+)?(/([%-\w/_\.]*(\?\S+)?)?)?)', r'\1<a href="\2">\2</a>', data)
    data = re.sub(r'\[([A-Z]\w+)\]', r'<a href="/\1%s%s">\1</a>' % (mode,debp), data)
    data = re.sub(r'\[([A-Z]\w+)\|([\w\s]+)\]', r'<a href="/\1%s%s">\2</a>' % (mode,debp), data)
    return data


class GitWiki():
  def __init__(self):
    self.debug = False
    self.debp = ''
    self.html = ''
    self.page = 'Home'
    self.page_opt = 'blame'


  def set_debug(self):
    if QUERY_STRING.find('debug') > 0:
        self.debug = True
        self.debp = '&debug'
        self.add_html(START_DEBUG)

  def set_page(self, form):
    if form.has_key("r"):
        page_parts = form["r"].value.split(':')
        page = page_parts[0]
        if len(page_parts) > 1:
            page_opt = page_parts[1]
            if page_opt.find('&debug') > 0:
                page_opt = page_opt.split('&')[0]
            self.page_opt = page_opt
        self.page = page

  def add_html(self, data):
    self.html += data

  def save(self, form):
    page = self.page
    if page.find('..') >= 0 or page.find('/') >= 0:
        self.add_html('Invalid filename')
    else:
        if form.has_key('data'):
            if self.debug:
                self.add_html('saving %s, len(data) = %d' % (page,len(form['data'].value)))
            fp = open('%s' % page, 'w')
            fp.write(form['data'].value)
            fp.close()
        elif self.debug:
            self.add_html('no data found in form for save!')
        self.git(['/usr/bin/git', 'add', page])
        self.git(['/usr/bin/git', 'commit','-a','-m','changed page %s via website' % page])
        self.git(['/usr/bin/git', 'push', git_dir])

  def rename(self, form):
    page = self.page
    new_name = form['new_name'].value
    if new_name.find('..') >= 0 or new_name.find('/') >= 0:
        self.add_html('Invalid filename')
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
                    self.git(['/usr/bin/git', 'add', file])
                if file == page:
                    self.git(['/usr/bin/git', 'mv', page, new_name])
        self.git(['/usr/bin/git', 'commit','-a','-m',
                  'renaming %s to %s via website' % (page,new_name)])
        self.git(['/usr/bin/git', 'push', git_dir])


  def git(self, run, debug=False):
      p = subprocess.Popen(run, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=myenv)
      o,e = p.communicate()
      if self.debug or debug:
          self.add_html( '$ %s' % ' '.join(run))
          self.add_html( o.replace('\n', '<br/>'), e.replace('\n', '<br/>'),)
          self.add_html( '<br/>rcode=%d'%p.returncode)
      return o

  def action_edit(self):
      page = self.page
      debp = self.debp
      data = ''
      try:
          fp = open('%s' % page)
          data = fp.read()
          fp.close()
      except:
          data = ''
      self.add_html('<form action="/%s:rename%s" method="post">' % (page,debp))
      self.add_html('Editing <input name="new_name" value="%s"/>' % page)
      self.add_html('<input type="hidden" name="r" value="%s:rename%s"/>' % (page,debp))
      self.add_html('&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<input type="submit" value="Rename">')
      self.add_html('</form>')
      self.add_html('<form action="/%s:save%s" method="post">' % (page,debp))
      self.add_html('<textarea name="data" cols="90" rows="40">%s</textarea><br/>' % data)
      self.add_html('<input type="submit" value="save">')
      self.add_html('</form>')

  def action_rename(self):
      page = self.page
      new_name = form['new_name'].value
      self.add_html('renaming from %s to %s<br/>' % (page, new_name))
      page = new_name
      self.add_html('finished renaming (including adjustments needed to other pages),' +
                  ' please continue to <a href="%s%s">%s</a>' % (page,debp,page))

  def action_blame(self):
      data = self.git(['/usr/bin/git','blame','-c',self.page], self.debug)
      lines = data.split('\r\n')
  #    print '<pre>'
      data = ''
      blamery = {}
      for i,line in enumerate(lines):
          tabs = line.split('\t')
          if len(tabs) >= 4:
  #            print i+1,tabs
              k = tabs[3].find(')')
              if len(tabs[3][k+1:]) == 0:
                  data = data + tabs[3][k+1:]+'\n'
              else:
                  tag = 'thisisanendoflineforline-%s-'%i
                  data = data + tabs[3][k+1:]+'%s\n'%tag
                  blamery[tag] = [tabs[0], tabs[1][1:].strip(), tabs[2]]
  #    print '</pre>'
      blob = textile.textile(data)
      for tag in blamery:
         k = blob.find(tag)
         if k >= 0:
             j = max(blob.rfind('li>',0,k),
                     blob.rfind('h2>',0,k),
                     blob.rfind('h3>',0,k),
                     blob.rfind('h1>',0,k),
                     blob.rfind('<p>',0,k))
             if j >= 0:
                 blob = blob.replace(blob[j+3:k+len(tag)],"""
                                     <span class="line"
                                     onmouseover="Tip(\'User: %s<br/>Date/Time:
                                     %s<br/>Revision: %s\')"
                                     onmouseout="UnTip()">%s</span>""" %
                                    (blamery[tag][1], blamery[tag][2], blamery[tag][0], blob[j+3:k]) )
      self.add_html(links(blob, self.debp))

  def action_show(self):
      try:
          fp = open('%s' % self.page)
          data = fp.read()
          fp.close()
      except:
          data = 'File doesn\'t exist, create one <a href="/%s:edit%s">here</a>' % (self.page,self.debp)
      self.add_html(textile.textile(links(data,self.debp,'view')))


  def add_links(self):
    page = self.page
    page_opt = self.page_opt
    debp = self.debp

    s ='| [%s] <!-- | <a href="/%s:blame%s">blame</a> --> | <a href="/log">log</a> | <a href="/%s:edit%s">edit</a> |<br/><br/>\n' % (page,page,debp,page,debp)
    if page != 'Home':
        s = '| [Home] '+s
    linksopt = page_opt
    if page_opt == 'edit' or page_opt == 'blame' or page_opt == 'save' or page_opt == 'rename':
        linksopt = ''
    self.add_html(links(s,debp,linksopt))

def main():
    gw = GitWiki()
    gw.set_debug()
    gw.set_page(form)

    gw.add_html(CONTENT_TYPE)
    gw.add_html(START_HTML)
    gw.add_html(TOOLTIP_INCLUDE)

    if gw.debug:
        gw.add_html(':: user=%s'%user)
        gw.add_html( '$ cat %s' % git_config)
        gw.add_html( open(git_config).read())
        gw.add_html( ':: page=%s, page_opt=%s<br/>' % (gw.page, gw.page_opt))

    if gw.debug:
        gw.add_html( '$ cd %s' % (http_dir))


    # an actual chdir
    os.chdir(http_dir)

    # git renew the directory. It should really just be git checkout and git
    # pull, forget the stashing
    gw.git(['/usr/bin/git', 'stash'])
    gw.git(['/usr/bin/git', 'pull', git_dir])
    gw.git(['/usr/bin/git', 'stash','clear'])

    # Actions : no printing HTML gets done here
    if gw.page_opt == 'save':
        gw.save(form)
    elif gw.page_opt == 'rename':
        gw.rename(form)

    if gw.debug:
        gw.add_html(END_DEBUG)

    gw.add_links()

    # Controller - basically, choose what to do and then execute and print html
    if gw.page_opt == 'edit':
        gw.action_edit()
    elif gw.page_opt == 'rename':
        gw.action_rename()
    elif gw.page == 'log':
        data = gw.git(['/usr/bin/git','log'])
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
        gw.add_html('<pre>%s</pre>' % data)
    elif gw.page == 'diff':
        if form.has_key('a') and form.has_key('b'):
            data = gw.git(['/usr/bin/git','diff',form['a'].value,form['b'].value])
            gw.add_html(data.replace('\n','<br/>'))
    elif gw.page_opt == 'blame':
        gw.action_blame()
    else:
        gw.action_show()

    gw.add_html(END_HTML)
    print gw.html

if __name__ == "__main__":
  main()
