#!/usr/bin/env python
#-*- coding: utf8 -*-
#
# Copyright (C) 2012 Ruikai Liu <lrk700@gmail.com>
#
# This file is part of rbook.
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
import sys

import wx
import wx.lib.agw.flatnotebook as fnb

import utils
from viewer import DocViewer

class MainFrame(wx.Frame):
    def __init__(self, parent, docfiles):
        utils.init_dir()
        wx.Frame.__init__(self, parent, title='rbook', size=(800, 700))
        self.notebook = fnb.FlatNotebook(self, agwStyle=fnb.FNB_X_ON_TAB | \
                                                        fnb.FNB_NO_X_BUTTON | \
                                                        fnb.FNB_NO_NAV_BUTTONS | \
                                                        fnb.FNB_NO_TAB_FOCUS)
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(2)
        self.settings = {'ic':0, 
                         'showoutline': 1, 
                         'quitonlast': 1,
                         'storepages': 1, 
                         'autochdir': 1}
        self.currentdir = os.path.expanduser('~')
        self.init_settings()
        if self.settings['storepages']:
            self.init_pages()
        self.textctrl = wx.TextCtrl(self, size=(0,0))
        for docfile in docfiles:
            docname, ext = os.path.splitext(os.path.basename(docfile))
            try:
                doc_viewer = DocViewer(self.notebook, os.path.abspath(docfile),
                                       ext.lower(), self.settings['showoutline'])
                self.notebook.AddPage(doc_viewer, docname)
            except IOError as inst:
                self.statusbar.SetStatusText('!Error: %s' % inst.args)
        
        if self.notebook.GetPageCount() > 0:
            doc_viewer = self.notebook.GetPage(0)
            doc_viewer.doc_scroll.panel.SetFocus()
            if self.settings['autochdir']:
                self.currentdir = os.path.dirname(doc_viewer.filepath)
            self.update_statusbar(self.notebook.GetPage(0))
        else:
            self.textctrl.SetFocus()

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CHANGED, self.on_page_changed, self.notebook)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CLOSED, self.on_page_closed, self.notebook)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CLOSING, self.on_page_closing, self.notebook)
        self.textctrl.Bind(wx.EVT_TEXT, self.on_text)
        self.textctrl.Bind(wx.EVT_KEY_DOWN, self.text_key_down)

        sizer = wx.BoxSizer()
        sizer.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.SetAutoLayout(True)
   
    def init_settings(self):
        configfile = os.path.expanduser('~/.rbook/rbookrc')
        if os.path.exists(configfile):
            try:
                f = open(configfile)
                lines = f.readlines()
                f.close()
            except IOError:
                lines = []

            for line in lines:
                text = line.strip().split('#')[0]
                if not text == '':
                    self.handle_new_setting(text)
    
    def init_pages(self):
        pages = os.path.expanduser('~/.rbook/pages')
        if not os.path.exists(pages):
            f = open(pages, 'w')
            self.pages = {}
            f.close()
        else:
            try:
                f = open(pages)
                lines = f.readlines()
                f.close()
            except IOError:
                lines = []
            self.pages = utils.lines2dict(lines)

    def text_key_down(self, event):
        if self.notebook.GetPageCount() > 0:
            doc_viewer = self.notebook.GetCurrentPage()
        else:
            doc_viewer = None
        text = self.textctrl.GetValue()
        if event.GetKeyCode() == wx.WXK_BACK:
            if (not doc_viewer is None) and len(self.textctrl.GetValue()) == 1:
                doc_viewer.doc_scroll.panel.SetFocus()
        elif event.GetKeyCode() == wx.WXK_RETURN:
            self.textctrl.Clear()
            self.statusbar.SetStatusText(text)
            if text[0] == ':':
                self.handle_new_cmd(text, doc_viewer)
            elif not doc_viewer is None:
                self.handle_new_search(text, doc_viewer)
                doc_viewer.doc_scroll.panel.SetFocus()
        elif event.GetKeyCode() == wx.WXK_TAB:
            if text[0:3] == ':o ' or text[0:4] == ':to ':
                if self.settings['autochdir']:
                    self.do_completion(text, lambda s:utils.path_completions(s, self.currentdir))
                else:
                    self.do_completion(text, utils.path_completions)
            elif text[0:4] == ':se ':
                self.do_completion(text, utils.cmd_completions)
        elif event.GetKeyCode() == wx.WXK_ESCAPE:
            self.textctrl.Clear()
            if not doc_viewer is None:
                doc_viewer.doc_scroll.panel.SetFocus()
        elif self.textctrl.GetValue() == 'Z':
            if event.GetRawKeyCode() == 90:
                self.on_close(None)
            else:
                self.textctrl.Clear()
        event.Skip()

    def on_text(self, event):
        self.completion = 0
        text = self.textctrl.GetValue()
        if self.notebook.GetPageCount() == 0 and len(text) == 1 \
                and not text[0] == ':' \
                and not text[0] == 'Z':
            self.textctrl.Clear()
        else:
            self.statusbar.SetStatusText(self.textctrl.GetValue())

    def on_page_closed(self, event):
        if self.notebook.GetPageCount() == 0:
            if self.settings['quitonlast']:
                self.on_close(None)
            else:
                self.textctrl.SetFocus()
        event.Skip()

    def on_page_closing(self, event):
        if self.settings['storepages']:
            self.notebook.GetCurrentPage().save_page()
        event.Skip()

    def on_page_changed(self, event, n=-1):
        if n == -1:
            n = event.GetSelection()
        self.statusbar.SetStatusText('')
        doc_viewer = self.notebook.GetPage(n)
        if self.settings['autochdir']:
            self.currentdir = os.path.dirname(doc_viewer.filepath)
        doc_viewer.doc_scroll.panel.SetFocus()
        self.update_statusbar(doc_viewer)

    def on_close(self, event):
        if self.settings['storepages']:
            n = self.notebook.GetPageCount()
            i = 0
            while i < n:
                self.notebook.GetPage(i).save_page()
                i += 1

            pages = os.path.expanduser('~/.rbook/pages')
            try:
                f = open(pages, 'w')
                f.writelines(utils.dict2lines(self.pages))
                f.close()
            except IOError:
                pass
        self.Destroy()

    def update_statusbar(self, doc_viewer):
        self.statusbar.SetStatusText('%d/%d    %d%%' % 
                                     (doc_viewer.current_page_idx+1, 
                                      doc_viewer.n_pages,
                                      int(100*doc_viewer.scale)), 
                                     1)

    def handle_new_setting(self, text):
        try:
            key, value = text.split('=')
        except ValueError:
            self.statusbar.SetStatusText('!Error: format should be key=value')
        else:
            try:
                value = int(value)
            except ValueError:
                self.statusbar.SetStatusText('!Error: value should be 1 or 0')
            else:
                if key in self.settings:
                    self.settings[key] = value
                else:
                    self.statusbar.SetStatusText('!Error: %s is not a valid key' % key)
            
    def open_document(self, path):
        if self.settings['autochdir']:
            fullpath = os.path.normpath(os.path.join(self.currentdir,
                                                 os.path.expanduser(path)))
        else:
            fullpath = os.path.abspath(os.path.expanduser(path))
        try:
            docname, ext = os.path.splitext(os.path.basename(fullpath))
            doc_viewer = DocViewer(self.notebook,
                                   str(fullpath),
                                   ext.lower(),
                                   self.settings['showoutline'])
            return (docname, doc_viewer)
        except IOError as inst:
            raise inst

    def handle_new_cmd(self, text, docviewer):
        if text[0:4] == ':to ': #open file in new tab
            try:
                docname, doc_viewer = self.open_document(text[4:].strip())
                self.notebook.AddPage(doc_viewer, docname, True)
            except IOError as inst:
                self.statusbar.SetStatusText('!Error: %s' % inst.args)
                if not docviewer is None:
                    docviewer.doc_scroll.panel.SetFocus()
        elif text[0:3] == ':o ': #open file
            try:
                docname, doc_viewer = self.open_document(text[3:].strip())
                n = self.notebook.GetSelection()
                if n > -1:
                    self.notebook.InsertPage(n, doc_viewer, docname, True)
                    self.notebook.DeletePage(n+1)
                else:
                    self.notebook.AddPage(doc_viewer, docname, True)
            except IOError as inst:
                self.statusbar.SetStatusText('!Error: %s' % inst.args)
                if not docviewer is None:
                    docviewer.doc_scroll.panel.SetFocus()
        elif text[0:4] == ':se ':
            self.handle_new_setting(text[4:].strip())
            if not docviewer is None:
                docviewer.doc_scroll.panel.SetFocus()
        elif text[0:4] == ':sc ':
            if docviewer is None:
                self.statusbar.SetStatusText('!Error: no document and cannot set scale.')
            else:
                try:
                    docviewer.set_scale(float(text[4:].strip()))
                except ValueError as inst:
                    self.statusbar.SetStatusText('!Error: %s.' % inst.args)
                docviewer.doc_scroll.panel.SetFocus()
        elif text.strip() == ':q': #close a tab
            if self.notebook.GetPageCount() == 0:
                self.on_close(None)
            else:
                self.notebook.DeletePage(self.notebook.GetSelection())
        elif text.strip() == ':qa': #quit
            self.on_close(None)
        elif text.strip() == ':h': #show manual
            try:
                docname, doc_viewer = self.open_document('/usr/share/rbook/manual.pdf')
                self.notebook.AddPage(doc_viewer, docname, True)
            except IOError:
                self.statusbar.SetStatusText('!Error: cannot open manual: /usr/share/rbook/manual.pdf')
                if not docviewer is None:
                    docviewer.doc_scroll.panel.SetFocus()
        else:#not valid cmd
            self.statusbar.SetStatusText('!Error: %s not a valid command.' % text)
            if not docviewer is None: 
                docviewer.doc_scroll.panel.SetFocus()
    
    def handle_new_search(self, text, doc_viewer):
        if len(text) > 1:
            doc_viewer.search_text = str(text[1:])
            if text[0] == '/':
                doc_viewer.search(1)
                doc_viewer.ori = 1
            else:
                doc_viewer.search(-1)
                doc_viewer.ori = -1

    def handle_keys(self, event, doc_viewer):
        keycode = event.GetKeyCode()
        rawkeycode = event.GetRawKeyCode()
        ctrl_down = event.ControlDown()
        shift_down = event.ShiftDown()
        text = self.statusbar.GetStatusText()
        if len(text) > 0 and \
                (text[0] == '/' or \
                 text[0] == ':' or \
                 text[0] == '!' or \
                 text[0] == '?'):
            text = ''
        try:
            if ctrl_down and keycode == 78: #c-n 
                n = (self.notebook.GetSelection()+1)%self.notebook.GetPageCount()
                self.notebook.SetSelection(n)
                self.on_page_changed(None, n)
            elif ctrl_down and keycode == 80: #c-p
                n = (self.notebook.GetSelection()-1)%self.notebook.GetPageCount()
                self.notebook.SetSelection(n)
                self.on_page_changed(None, n)
            elif ctrl_down and keycode == 70: #c-f
                doc_viewer.on_next_page(None)
                doc_viewer.prev_cmd = 'self.on_next_page(None)'
            elif ctrl_down and keycode == 66: #c-b
                doc_viewer.on_prev_page(None)
                doc_viewer.prev_cmd = 'self.on_prev_page(None)'
            elif ctrl_down and keycode == 79: #c-o
                doc_viewer.on_page_back(None)
                doc_viewer.prev_cmd = 'self.on_page_back(None)'
            elif ctrl_down and keycode == 73: #c-i
                doc_viewer.on_page_fwd(None)
                doc_viewer.prev_cmd = 'self.on_page_fwd(None)'
            elif ctrl_down and keycode == 85: #c-u
                doc_viewer.vertical_scroll(-20)
                doc_viewer.prev_cmd = 'self.vertical_scroll(-20)'
            elif (ctrl_down and keycode == 68) or\
                 keycode == wx.WXK_SPACE:#c-d or space
                doc_viewer.vertical_scroll(20)
                doc_viewer.prev_cmd = 'self.vertical_scroll(20)'
            elif keycode > 64 and keycode < 91:#press letters
                if len(text) > 0: #it's part of a cmd
                    self.statusbar.SetStatusText('')
                    if text[-1] == 'g':#prev is g
                        if rawkeycode == 103:#press another g
                            if len(text) == 1:#no nums
                                doc_viewer.change_page(0)#it's gg
                            else:
                                    doc_viewer.change_page(int(text[0:-1])-1)#it's num gg
                    elif text == 'm':#prev is m
                        doc_viewer.marks[rawkeycode] = (doc_viewer.current_page_idx,
                                                        doc_viewer.scale, 
                                                        doc_viewer.doc_scroll.GetViewStart())
                    elif text == 'Z' and rawkeycode == 90:#prev is Z, press another Z
                        self.on_close(None)
                    elif text == "'" or text == '`':#prev is ' or `
                        doc_viewer.retrive_mark(rawkeycode)
                    elif text[0].isdigit(): #prev are all nums 
                        if rawkeycode == 103:#press g
                            self.statusbar.SetStatusText(text+'g')
                        elif keycode == 74:#press j
                            doc_viewer.change_page(doc_viewer.current_page_idx + int(text))
                            doc_viewer.prev_cmd = 'self.change_page(self.current_page_idx+%s)' % text
                        elif keycode == 75:#press k
                            doc_viewer.change_page(doc_viewer.current_page_idx - int(text))
                            doc_viewer.prev_cmd = 'self.change_page(self.current_page_idx-%s)' % text
                elif rawkeycode == 103 or rawkeycode == 109 or rawkeycode == 90: 
                #no prev key, no nums, press g or m or Z
                    self.statusbar.SetStatusText(chr(rawkeycode))
                elif keycode == 82: # press r
                    doc_viewer.on_refresh(None)
                elif keycode == 87: # press w
                    doc_viewer.on_fit_width(None)
                elif keycode == 68:#press D or d
                    self.notebook.DeletePage(self.notebook.GetSelection())
                elif rawkeycode == 71:#press G
                    doc_viewer.change_page(doc_viewer.n_pages-1)
                elif keycode == 74:#press j
                    doc_viewer.vertical_scroll(1)
                    doc_viewer.prev_cmd = 'self.vertical_scroll(1)'
                elif keycode == 75:#press k
                    doc_viewer.vertical_scroll(-1)
                    doc_viewer.prev_cmd = 'self.vertical_scroll(-1)'
                elif rawkeycode == 104:#press h
                    doc_viewer.horizontal_scroll(-1)
                    doc_viewer.prev_cmd = 'self.horizontal_scroll(-1)'
                elif rawkeycode == 108:#press l
                    doc_viewer.horizontal_scroll(1)
                    doc_viewer.prev_cmd = 'self.horizontal_scroll(1)'
                elif rawkeycode == 72:#press H
                    doc_viewer.doc_scroll.Scroll(-1, 0)
                elif rawkeycode == 76:#press L
                    doc_viewer.doc_scroll.Scroll(-1, doc_viewer.doc_scroll.GetScrollRange(wx.VERTICAL))
                elif rawkeycode == 110:#press n
                    doc_viewer.search_next(1)
                elif rawkeycode == 78:#press N
                    doc_viewer.search_next(-1)
                elif keycode == 70:#press f
                    fullscreen = self.IsFullScreen()
                    self.ShowFullScreen(not fullscreen)
                    if fullscreen:
                        self.notebook.ShowTabs()
                    else:
                        self.notebook.HideTabs()
                elif keycode == 86:#press v
                    if doc_viewer.show_outline == 1:
                        doc_viewer.doc_scroll.panel.SetFocus()
                        doc_viewer.Unsplit(doc_viewer.outline_tree)
                        doc_viewer.show_outline = -1
                    elif doc_viewer.show_outline == -1:
                        doc_viewer.SplitVertically(doc_viewer.outline_tree, doc_viewer.doc_scroll, 200)
                        doc_viewer.show_outline = 1

            elif rawkeycode > 47 and rawkeycode < 58:#press digit
                if len(text) > 0 and text[-1].isalpha():
                    self.statusbar.SetStatusText('')
                else:
                    self.statusbar.SetStatusText(text+chr(rawkeycode))

            elif rawkeycode == 96 or rawkeycode == 39:#press ' or `
                if len(text) == 0:
                    self.statusbar.SetStatusText(chr(rawkeycode))
                elif text[-1] == "'" or text[-1] == '`':
                    doc_viewer.retrive_mark(96)
                    self.statusbar.SetStatusText('')
                else:
                    self.statusbar.SetStatusText('')

            elif rawkeycode == 43:# +, zoom in
                doc_viewer.on_zoom_in(None)
                doc_viewer.prev_cmd = 'self.on_zoom_in(None)'
            elif rawkeycode == 45:# -, zoom out
                doc_viewer.on_zoom_out(None)
                doc_viewer.prev_cmd = 'self.on_zoom_out(None)'
            elif keycode == wx.WXK_ESCAPE:
                self.statusbar.SetStatusText('')
            elif keycode == 46: #. repeat cmd
                doc_viewer.repeat_cmd()
            elif rawkeycode == 47 or rawkeycode == 63: # press / or ?
                self.textctrl.WriteText(chr(rawkeycode))
                self.textctrl.SetFocus()
                self.textctrl.SetInsertionPointEnd()
            elif rawkeycode == 58: #press :
                self.textctrl.WriteText(':')
                self.textctrl.SetFocus()
                self.textctrl.SetInsertionPointEnd()
        except ValueError as inst:
            self.statusbar.SetStatusText('!Error: %s' % inst.args)

    def do_completion(self, text, complete_cb):
        completion = self.completion
        if completion == 0:
            n = text.find(' ')+1
            self.text = text[0:n]
            self.completions = complete_cb(text[n:].strip())
            if len(self.completions) == 1:
                completion = -1
            else:
                completion = iter(self.completions)
                self.textctrl.SetValue(self.text+completion.next())
        elif not completion == -1:
            try:
                self.textctrl.SetValue(self.text+completion.next())
            except StopIteration:
                completion = iter(self.completions)
                self.textctrl.SetValue(self.text+completion.next())
        self.completion = completion
        self.textctrl.SetInsertionPointEnd()


class Run:
    def __init__(self):
        app = wx.App(False)
        frame = MainFrame(None, sys.argv[1:])
        frame.Show()
        app.MainLoop()
