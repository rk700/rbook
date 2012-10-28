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

import os
import glob


def lines2dict(lines):
    res = {}
    for line in lines:
        line = line.strip()
        try:
            inode, page, path = line.split(' ')
        except ValueError:
            continue
        else:
            res[int(inode)] = (int(page), path)
    return res

def dict2lines(pages):
    res = []
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

def init_dir():
    configdir = os.path.expanduser('~/.rbook')
    if not os.path.exists(configdir):
        os.makedirs(configdir, 0755)
        configfile = os.path.join(configdir, 'rbookrc')
        fout = open(configfile, 'w')
        lines = ['#ignore case when searching, default false\n',
                 '#ic=0\n',
                 '\n',
                 '#show outline if available, default true\n',
                 '#showoutline=1\n',
                 '\n',
                 '#quit rbook when closing the last tab, default true\n',
                 '#quitonlast=1\n', 
                 '\n',
                 '#store page index for next time, default true\n', 
                 '#storepages=1\n', 
                 '\n',
                 '#automatically change the dir to the dir containing the current document\n', 
                 '#autochdir=1\n'] 
        fout.writelines(lines)
        fout.close()

