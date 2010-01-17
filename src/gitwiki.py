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
import ConfigParser

cgitb.enable()
form = cgi.FieldStorage()

# Configuration - these should be made into constants, later
USER = os.environ['REMOTE_USER']
QUERY_STRING = os.environ['QUERY_STRING']
user = USER

config = ConfigParser.ConfigParser()
config.read('config.cfg')

git_location = config.get('gitwiki','git_location',0)
http_dir     = config.get('gitwiki','http_dir',0)
git_push_dir = config.get('gitwiki', 'git_push_dir', 0)
git_dir      = config.get('gitwiki', 'git_dir', 0)
git_config   = config.get('gitwiki', 'git_config', 0, {'user': user})
myenv = {'GIT_DIR': git_dir, 'GIT_CONFIG': git_config}

CONTENT_TYPE = "Content-Type: text/html\r\n\r\n"
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


TOOLTIP_INCLUDE = '<script type="text/javascript" src="/wz_tooltip.js"></script>'
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

ACTIONS = {}
PAGES   = {}

def action(name):
   def fnrun(fn):
     ACTIONS[name] = fn
     return fn
   return fnrun

def page(name):
   def fnrun(fn):
     PAGES[name] = fn
     return fn
   return fnrun

class GitWiki:
  def __init__(self):
    self.debug = False
    self.debp = ''
    self.html = ''
    self.debug_html = ''
    self.page = 'Home'
    self.page_opt = 'blame'

  def set_debug(self):
    if QUERY_STRING.find('debug') > 0:
        self.debug = True
        self.debp = '&debug'
        self.add_debug(START_DEBUG)

  def set_page(self, form):
    if form.has_key("r"):
        # This is happening for no good reason.
        if type(form['r']) == type([]):
            page_parts = form["r"][0].value.split(':')
        else:
            page_parts = form["r"].value.split(':')
        self.page = page_parts[0]
        if len(page_parts) > 1:
            self.page_opt = page_parts[1]
            if self.page_opt.find('&debug') > 0:
                self.page_opt = self.page_opt.split('&')[0]

  def add_html(self, data):
    self.html = '%s%s' % (self.html,data)

  def add_debug(self, data):
    if self.debug:
        self.debug_html += data

  def save(self, form):
    page = self.page
    if page.find('..') >= 0 or page.find('/') >= 0:
        self.add_html('Invalid filename')
    else:
        if form.has_key('data'):
            self.add_debug('saving %s, len(data) = %d' % (page,len(form['data'].value)))
            fp = open('%s' % page, 'w')
            fp.write(form['data'].value)
            fp.close()
        else:
            self.add_debug('no data found in form for save!')
        self.git([git_location, 'add', page])
        self.git([git_location, 'commit','-a','-m','changed page %s via website' % page])
        self.git([git_location, 'push', git_push_dir])

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
                    self.git([git_location, 'add', file])
                if file == page:
                    self.git([git_location, 'mv', page, new_name])
        self.git([git_location, 'commit','-a','-m',
                  'renaming %s to %s via website' % (page,new_name)])
        self.git([git_location, 'push', git_push_dir])

  def git(self, run, debug=False):
      self.add_debug( '$ %s' % ' '.join(run))
      p = subprocess.Popen(run, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=myenv)
      o,e = p.communicate()
      self.add_debug( o.replace('\n', '<br/>') + e.replace('\n', '<br/>') )
      self.add_debug( '<br/>rcode=%d' % p.returncode)
      return o

  @action('edit')
  def action_edit(self):
      page = self.page
      debp = self.debp
      data = ''
      try:
          fp = open('%s' % page)
          data = fp.read()
          fp.close()
      except:
          pass
      self.add_html("""
      <form action="/%(page)s:rename%(debp)s" method="post">
      Editing <input name="new_name" value="%(page)s"/>
      <input type="hidden" name="r" value="%(page)s:rename%(debp)s"/>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<input type="submit" value="Rename">
      </form>
      <form action="/%(page)s:save%(debp)s" method="post">
      <input type="hidden" name="r" value="%(page)s:save%(debp)s"/>
      <textarea name="data" cols="90" rows="40">%(data)s</textarea><br/>
      <input type="submit" value="save">
      </form>
      """ % { "page" : page, "debp" : debp, "data" : data })

  @action('blame')
  def action_blame(self):
      if not os.path.exists(self.page):
          self.add_html('File doesn\'t exist, create one <a href="/%s:edit%s">here</a>' % (self.page,self.debp))
          return
      data = self.git([git_location,'blame','-c',self.page], self.debug)
      lines = data.split('\r\n')
      data = ''
      blamery = {}
      for i,line in enumerate(lines):
          tabs = line.split('\t')
          if len(tabs) >= 4:
              k = tabs[3].find(')')
              if len(tabs[3][k+1:]) == 0 or tabs[3][-1] == '|':
                  data = data + tabs[3][k+1:]+'\n'
              else:
                  tag = 'thisisanendoflineforline-%s-'%i
                  data = data + tabs[3][k+1:]+'%s\n'%tag
                  blamery[tag] = [tabs[0], tabs[1][1:].strip(), tabs[2]]
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
                 blob = blob.replace(blob[j+3:k+len(tag)],
"""<span class="line" onmouseover="Tip(\'User: %s<br/>Date/Time: %s<br/>Revision: %s\')" onmouseout="UnTip()">%s</span>""" %                                    (blamery[tag][1], blamery[tag][2], blamery[tag][0], blob[j+3:k]) )
      self.add_html(links(blob, self.debp))

  @action('view')
  def action_show(self):
      try:
          fp = open('%s' % self.page)
          data = fp.read()
          fp.close()
      except:
          data = 'File doesn\'t exist, create one <a href="/%s:edit%s">here</a>' % (self.page,self.debp)
      self.add_html(textile.textile(links(data,self.debp,'view')))

  @page('log')
  def page_log(self):
    data = self.git([git_location,'log'])
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
    self.add_html('<pre>%s</pre>' % data)

  @page('diff')
  def page_diff(self):
    if form.has_key('a') and form.has_key('b'):
        data = self.git([git_location,'diff',form['a'].value,form['b'].value])
    	data = re.sub(r'diff --git a/([A-Z]\w*) ', r'diff --git a/<a href="/\1%s">\1</a> ' % (self.debp), data)
        self.add_html(links(data.replace('\n','<br/>'),self.debp))

  def add_links(self):
    page = self.page
    page_opt = self.page_opt
    debp = self.debp

    s ='| [%s] <!-- | <a href="/%s:blame%s">blame</a> --> | <a href="/log">log</a> | <a href="/%s:edit%s">edit</a> |<br/><br/>\n' % (page,page,debp,page,debp)
    if page != 'Home':
        s = '| [Home] '+s
    linksopt = self.page_opt
    if self.page_opt == 'edit' or self.page_opt == 'blame' or self.page_opt == 'save' or self.page_opt == 'rename':
        linksopt = ''
    self.add_html(links(s,debp,linksopt))

  def run(self):
    self.set_debug()
    self.set_page(form)

    self.add_html(CONTENT_TYPE)
    self.add_html(START_HTML)
    self.add_html(TOOLTIP_INCLUDE)

    self.add_debug(':: user=%s'%user)
    self.add_debug( '$ cat %s' % git_config)
    if not os.path.exists(git_config):
        open(git_config).write("""[user]
        name = %s
        email = %s@theinternetneverlies.com""" % (user,user) )
    self.add_debug( open(git_config).read())
    self.add_debug( ':: page=%s, page_opt=%s<br/>' % (self.page, self.page_opt))

    # an actual chdir
    self.add_debug( '$ cd %s' % (http_dir))
    os.chdir(http_dir)

    # git renew the directory. It should really just be git checkout and git
    # pull, forget the stashing
    self.git([git_location, 'stash'])
    self.git([git_location, 'pull', git_push_dir])
    self.git([git_location, 'stash','clear'])

    # Actions : no printing HTML gets done here
    if self.page_opt == 'save':
        self.save(form)
    elif self.page_opt == 'rename':
        self.rename(form)

    self.add_links()

    # Controller - basically, choose what to do and then execute and print html
    if PAGES.has_key(self.page):
        PAGES[self.page](self)
    elif ACTIONS.has_key( self.page_opt ):
        ACTIONS[self.page_opt](self)
    else:
        self.action_show()

    self.add_debug(END_DEBUG)
    self.add_html(self.debug_html)
    self.add_html(END_HTML)
    print self.html

#if __name__ == "__main__":
gw = GitWiki()
gw.run()

