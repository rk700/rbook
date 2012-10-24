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
        wx.Frame.__init__(self, parent, title='rbook', size=(800, 700))
        self.notebook = fnb.FlatNotebook(self, agwStyle=fnb.FNB_X_ON_TAB | \
                                                        fnb.FNB_NO_X_BUTTON | \
                                                        fnb.FNB_NO_NAV_BUTTONS | \
                                                        fnb.FNB_NO_TAB_FOCUS)
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(2)
        self.settings = {'ic':0, 'showoutline': 1, 'quitonlast': 1,
                'storepages': 1, 'autochdir': 1}
        self.currentdir = os.path.expanduser('~')
        self.init_settings()
        if self.settings['storepages']:
            self.init_pages()
        self.textctrl = wx.TextCtrl(self, size=(0,0))
        for docfile in docfiles:
            docname, ext = os.path.splitext(os.path.basename(docfile))
            try:
                doc_viewer = DocViewer(self.notebook, docfile, docname, 
                                       ext.lower(), self.settings['showoutline'])
                self.notebook.AddPage(doc_viewer, docname)
            except IOError as inst:
                print(inst)
        
        if self.notebook.GetPageCount() > 0:
            self.notebook.GetPage(0).doc_scroll.panel.SetFocus()
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
            self.pages = utils.read_pages(lines)

    def text_key_down(self, event):
        if self.notebook.GetPageCount() > 0:
            doc_viewer = self.notebook.GetCurrentPage()
        else:
            doc_viewer = None
        if event.GetKeyCode() == wx.WXK_BACK:
            if (not doc_viewer is None) and len(self.textctrl.GetValue()) == 1:
                doc_viewer.doc_scroll.panel.SetFocus()
        elif event.GetKeyCode() == wx.WXK_RETURN:
            text = self.textctrl.GetValue()
            if text[0] == ':':
                self.handle_new_cmd(text, doc_viewer)
            elif not doc_viewer is None:
                self.handle_new_search(text, doc_viewer)
                doc_viewer.doc_scroll.panel.SetFocus()
        elif event.GetKeyCode() == wx.WXK_TAB:
            text = self.textctrl.GetValue()
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
                f.writelines(utils.pageslist(self.pages))
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
                try:
                    self.settings[key] = value
                except KeyError:
                    self.statusbar.SetStatusText('!Error: %s is not a valid key' % key)
            
    def handle_new_cmd(self, text, docviewer):
        self.textctrl.Clear()
        if text[0:4] == ':to ': #open file in new tab
            try:
                docfile = os.path.expanduser(text[4:].strip())
                docname, ext = os.path.splitext(os.path.basename(docfile))
                doc_viewer = DocViewer(self.notebook, 
                                       str(os.path.abspath(docfile)), 
                                       docname, ext.lower(),
                                       self.settings['showoutline'])
                self.notebook.AddPage(doc_viewer, docname, True)
            except IOError as inst:
                self.statusbar.SetStatusText('!Error: %s' % inst.args)
                if not docviewer is None:
                    docviewer.doc_scroll.panel.SetFocus()
        elif text[0:3] == ':o ': #open file
            try:
                docfile = os.path.expanduser(text[3:].strip())
                docname, ext = os.path.splitext(os.path.basename(docfile))
                doc_viewer = DocViewer(self.notebook, 
                                       str(os.path.abspath(docfile)), 
                                       docname, ext.lower(),
                                       self.settings['showoutline'])
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
        elif text.strip() == ':q': #close a tab
            if self.notebook.GetPageCount() == 0:
                self.on_close(None)
            else:
                self.notebook.DeletePage(self.notebook.GetSelection())
        elif text.strip() == ':qa' or text == 'ZZ': #quit
            self.on_close(None)
    
    def handle_new_search(self, text, doc_viewer):
        self.textctrl.Clear()
        if len(text) > 1:
            doc_viewer.search_text = str(text[1:])
            if text[0] == '/':
                doc_viewer.search(doc_viewer.search_text, 1)
                doc_viewer.ori = 1
            else:
                doc_viewer.search(doc_viewer.search_text, -1)
                doc_viewer.ori = -1

    def handle_keys(self, event, doc_viewer):
        keycode = event.GetKeyCode()
        rawkeycode = event.GetRawKeyCode()
        ctrl_down = event.ControlDown()
        shift_down = event.ShiftDown()
        text = self.statusbar.GetStatusText()

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
        elif (ctrl_down and keycode == 85) or\
             (not ctrl_down and keycode == wx.WXK_PAGEUP):#c-u
            doc_viewer.doc_scroll.vertical_scroll(-20)
            doc_viewer.prev_cmd = 'self.doc_scroll.vertical_scroll(-20)'
        elif (ctrl_down and keycode == 68) or\
             (not ctrl_down and keycode == wx.WXK_PAGEDOWN) or\
             keycode == wx.WXK_SPACE:#c-d
            doc_viewer.doc_scroll.vertical_scroll(20)
            doc_viewer.prev_cmd = 'self.doc_scroll.vertical_scroll(20)'
        elif keycode > 64 and keycode < 91:#press letters
            if len(text) > 0 and (not text[-1].isdigit()) \
                             and text[0].isalnum(): 
                #check if it's part of a cmd
                if text[-1] == 'g':#prev is g
                    if rawkeycode == 103:#press another g
                        if len(text) == 1:#no nums
                            doc_viewer.marks[96] = (doc_viewer.current_page_idx, 
                                                    doc_viewer.scale, 
                                                    doc_viewer.doc_scroll.GetViewStart())
                            doc_viewer.doc_scroll.Scroll(-1, 0)
                        else:
                            doc_viewer.marks[96] = (doc_viewer.current_page_idx, 
                                                    doc_viewer.scale, 
                                                    doc_viewer.doc_scroll.GetViewStart())
                            doc_viewer.change_page(int(text[0:-1])-1)#it's num gg
                elif text[-1] == 'm':#prev is m
                    doc_viewer.marks[rawkeycode] = (doc_viewer.current_page_idx,
                                                    doc_viewer.scale, 
                                                    doc_viewer.doc_scroll.GetViewStart())
                    self.statusbar.SetStatusText('')
                elif text[-1] == 'Z':#prev is Z
                    self.on_close(None)
                else:#prev is ' or `
                    doc_viewer.retrive_mark(rawkeycode)
                self.statusbar.SetStatusText('')
            elif len(text) > 0 and text[0].isdigit():#no prev key, has nums
                if rawkeycode == 103:#press g
                    self.statusbar.SetStatusText(self.statusbar.GetStatusText()+'g')
                else:
                    if rawkeycode == 106:#press j
                        doc_viewer.change_page(doc_viewer.current_page_idx + int(text))
                        doc_viewer.prev_cmd = 'self.change_page(self.current_page_idx+%s)' % text
                    elif rawkeycode == 107:#press k
                        doc_viewer.change_page(doc_viewer.current_page_idx - int(text))
                        doc_viewer.prev_cmd = 'self.change_page(self.current_page_idx-%s)' % text
                    self.statusbar.SetStatusText('')
            elif rawkeycode == 103 or rawkeycode == 109 or rawkeycode == 90: 
            #no prev key, no nums, press g or m or Z
                self.statusbar.SetStatusText(chr(rawkeycode))
            elif rawkeycode == 114: # press r
                doc_viewer.on_refresh(None)
            elif rawkeycode == 119: # press w
                doc_viewer.on_fit_width(None)
            elif keycode == 68:#press D or d
                self.notebook.DeletePage(self.notebook.GetSelection())
            elif rawkeycode == 71:#press G
                doc_viewer.marks[96] = (doc_viewer.current_page_idx, 
                                        doc_viewer.scale, 
                                        doc_viewer.doc_scroll.GetViewStart())
                doc_viewer.doc_scroll.Scroll(-1, doc_viewer.doc_scroll.GetScrollRange(wx.VERTICAL))
            elif rawkeycode == 106:#press j
                doc_viewer.doc_scroll.vertical_scroll(1)
                doc_viewer.prev_cmd = 'self.doc_scroll.vertical_scroll(1)'
            elif rawkeycode == 107:#press k
                doc_viewer.doc_scroll.vertical_scroll(-1)
                doc_viewer.prev_cmd = 'self.doc_scroll.vertical_scroll(-1)'
            elif rawkeycode == 104:#press h
                doc_viewer.doc_scroll.horizontal_scroll(-1)
                doc_viewer.prev_cmd = 'self.doc_scroll.horizontal_scroll(-1)'
            elif rawkeycode == 108:#press l
                doc_viewer.doc_scroll.horizontal_scroll(1)
                doc_viewer.prev_cmd = 'self.doc_scroll.horizontal_scroll(1)'
            elif rawkeycode == 110:#press n
                doc_viewer.search_next(1)
            elif rawkeycode == 78:#press N
                doc_viewer.search_next(-1)
            elif rawkeycode == 118:#press v
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

        elif keycode == wx.WXK_DOWN:
            doc_viewer.doc_scroll.vertical_scroll(1)
        elif keycode == wx.WXK_UP:
            doc_viewer.doc_scroll.vertical_scroll(-1)
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
