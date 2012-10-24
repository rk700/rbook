#!/usr/bin/env python
#-*- coding: utf8 -*-
#
# Copyright (C) 2012 Ruikai Liu <lrk700@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with rbook.  If not, see <http://www.gnu.org/licenses/>.

import os.path
import glob

def read_pages(lines):
    res = {}
    for line in lines:
        line = line.strip()
        if line == '':
            continue
        inode, page, path = line.split(' ')
        res[int(inode)] = (int(page), path)
    return res

def pageslist(pages):
    res = []
    item = pages.iteritems()
    for inode, info in pages.items():
        res.append('%s %s %s\n' % (str(inode), str(info[0]), info[1]))
    return res

def path_completions(s, currentdir=''):
    if currentdir == '':
        fullpath = os.path.abspath(os.path.expanduser(s))
    else:
        fullpath = os.path.normpath(os.path.join(currentdir,
                                                 os.path.expanduser(s)))
    if os.path.isdir(fullpath):
        fullpath = fullpath+'/'
    res = glob.glob(fullpath+'*')
    res.append(fullpath)
    return res

def cmd_completions(s):
    fullcmd = ['ic=', 'showoutline=', 'quitonlast=', 'storepages=', 'autochdir=']
    res = [cmd for cmd in fullcmd if cmd.find(s)==0]
    res.append(s)
    return res

