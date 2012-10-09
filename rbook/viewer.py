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


import wx
#import poppler
from fitz import *

from pdf import DocScroll


class DocViewer(wx.Frame):
    def __init__(self, parent, file_ele):
        self.file_ele = file_ele
        self.min_scale = 0.25
        self.max_scale = 4.0

        wx.Frame.__init__(self, parent, title=file_ele.get('title'), 
                          size=(800,700))
        self.parent = parent
        self.filepath = file_ele.get('path').encode('utf-8')
        self.current_page_idx = int(file_ele.get('current_page'))
        self.ctx = new_context(FZ_STORE_UNLIMITED)
        self.document = open_document(self.ctx, self.filepath)
        self.n_pages = self.document.count_pages()
        current_page = self.document.load_page(self.current_page_idx)
        self.outline = self.document.load_outline()

        if not self.outline is None:
            self.split_win = wx.SplitterWindow(self, -1, style=wx.SP_LIVE_UPDATE)
            self.win = DocScroll(self.split_win, self, current_page);
            self.outline_tree = wx.TreeCtrl(self.split_win, -1, 
                                            style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT)
            root = self.outline_tree.AddRoot('/')
            self.init_outline_tree(self.outline.get_first(), root)

            self.outline_tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_sel_changed)
            self.outline_tree.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
            self.split_win.SetMinimumPaneSize(180)
            self.split_win.SplitVertically(self.outline_tree, self.win, 200)
            self.show_outline = True
        else:
            self.win = DocScroll(self, self, current_page)

       
        self.scale = self.win.scale
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(2)
        self.update_statusbar()
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.init()
        self.Show()

    def on_sel_changed(self, event):
        item = event.GetItem()
        if item.IsOk():
            self.set_current_page(self.outline_tree.GetItemData(item).GetData())

    def init_outline_tree(self, outline_item, parent):
        child = self.outline_tree.AppendItem(parent, outline_item.get_title())
        self.outline_tree.SetItemData(child, wx.TreeItemData(outline_item.get_page()))
        downitem = outline_item.get_down()
        if not downitem is None:
            self.init_outline_tree(downitem, child)
        nextitem = outline_item.get_next()
        if not nextitem is None:
            self.init_outline_tree(nextitem, parent)

    def on_refresh(self, event):
        self.document = open_document(self.ctx, self.filepath)
        self.n_pages = self.document.count_pages()
        if self.n_pages > self.current_page_idx:
            current_page_idx = self.current_page_idx
        else:
            current_page_idx = self.n_pages - 1

        
        self.init()
        pos = self.win.GetViewStart()
        self.set_current_page(current_page_idx)
        self.win.Scroll(pos[0], pos[1])
        self.update_statusbar()

    def init(self):
        self.marks = {}
        self.page_back = []
        self.page_fwd = []
        self.prev_key = []
        self.prev_num = []
        self.statusbar.SetStatusText('', 0)
        self.prev_cmd = ''
        self.search_text = ''
        self.new_search = False
        self.hitbbox = None
        self.hit = -1
        self.ori = 1

    def search(self, s, ori):
        current_page_idx = self.current_page_idx
        hitbbox = self.win.text_page.search(s, 0)
        while len(hitbbox) == 0:
            current_page_idx += ori
            if current_page_idx == self.n_pages:
                current_page_idx = 0
            elif current_page_idx == -1:
                current_page_idx = self.n_pages-1

            if not current_page_idx == self.current_page_idx:
                self.set_current_page(current_page_idx, False)
                hitbbox = self.win.text_page.search(s, 0)
            else:
                break
        if len(hitbbox) == 0: #not found
            self.hit = -1
            self.set_current_page(self.current_page_idx)
            self.statusbar.SetStatusText('"%s" not found' % self.search_text)
        else:
            self.hitbbox = hitbbox
            if ori < 0:
                self.hit = len(hitbbox)-1
            else:
                self.hit = 0
            self.current_page_idx = current_page_idx
            self.update_statusbar()
            self.win.setup_drawing(hitbbox[self.hit])
            self.win.Scroll(-1, self.win.trans.transform_bbox(
                                hitbbox[self.hit]).y0/self.win.scroll_unit)

    def update_statusbar(self):
        self.statusbar.SetStatusText('%d/%d    %d%%' % 
                                     (self.current_page_idx+1, 
                                      self.n_pages,
                                      int(100*self.scale)), 
                                     1)

    def search_next(self, ori):
        if self.search_text == '':
            pass
        elif self.hit < 0:
            self.statusbar.SetStatusText('"%s" not found' % self.search_text)
        else:
            if len(self.hitbbox) == 0:#a new page
                self.search(self.search_text, ori*self.ori)
            else:
                newhit = self.hit + self.ori*ori
                if newhit == len(self.hitbbox):# search in the next page
                    page_index = self.current_page_idx + 1
                    if page_index == self.n_pages:
                        page_index = 0
                    self.set_current_page(page_index, False)
                    self.current_page_idx = page_index
                    self.search(self.search_text, ori*self.ori)
                elif newhit == -1: #search in the prev page
                    page_index = self.current_page_idx - 1
                    if page_index == -1:
                        page_index = self.n_pages - 1
                    self.set_current_page(page_index, False)
                    self.current_page_idx = page_index
                    self.search(self.search_text, ori*self.ori)
                else:
                    self.win.pix.invert_pixmap(self.win.trans.transform_bbox(
                                                        self.hitbbox[self.hit]))
                    new_hitbbox = self.win.trans.transform_bbox(self.hitbbox[newhit])
                    self.win.pix.invert_pixmap(new_hitbbox)
                    self.hit = newhit
                    self.win.do_drawing()
                    self.win.Scroll(-1, new_hitbbox.y0/self.win.scroll_unit)
            if self.ori > 0:
                self.statusbar.SetStatusText('/'+self.search_text);
            else:
                self.statusbar.SetStatusText('?'+self.search_text);


    def set_current_page(self, current_page_idx, draw=True):
        current_page = self.document.load_page(current_page_idx)
        self.hitbbox = []
        self.win.set_current_page(current_page, draw)
        if draw:
            self.current_page_idx = current_page_idx
            self.update_statusbar()

    def on_page_back(self, event):
        if len(self.page_back) > 0:
            self.page_fwd.append(self.current_page_idx)
            self.set_current_page(self.page_back.pop())

    def on_page_fwd(self, event):
        if len(self.page_fwd) > 0:
            self.page_back.append(self.current_page_idx)
            self.set_current_page(self.page_fwd.pop())

    def on_fit_width(self, event):
        self.win.fit_width_scale(self.win.current_page)
        self.scale = self.win.scale
        self.update_statusbar()
        self.win.set_scale(self.scale)

    def on_zoom_in(self, event):
        if self.scale < self.max_scale:
            self.scale += 0.2
            self.win.set_scale(self.scale)
            self.update_statusbar()
            
    def on_zoom_out(self, event):
        if self.scale > self.min_scale:
            self.scale -= 0.2
            self.win.set_scale(self.scale)
            self.update_statusbar()

    def on_close(self, event):
        self.parent.doc_list.remove(self)
        self.file_ele.set('current_page', str(self.current_page_idx))
        self.Destroy()

    def on_prev_page(self, event):
        self.change_page(self.current_page_idx-1)

    def on_next_page(self, event):
        self.change_page(self.current_page_idx+1)

    def on_key_down(self, event):
        keycode = event.GetKeyCode()
        rawkeycode = event.GetRawKeyCode()
        ctrl_down = event.ControlDown()
        shift_down = event.ShiftDown()
        self.handle_keys(keycode, rawkeycode, ctrl_down, shift_down)
        event.Skip()

    def handle_keys(self, keycode, rawkeycode, ctrl_down, shift_down):
        if self.new_search:
            text = self.statusbar.GetStatusText()
            if (keycode == wx.WXK_BACK):
                text = text[0:-1]
                self.statusbar.SetStatusText(text)
                if len(text) == 0:
                    self.new_search = False
            elif (keycode == wx.WXK_RETURN):
                if len(text) > 1:
                    self.search_text = str(text[1:])
                    if text[0] == '/':
                        self.search(self.search_text, 1)
                        self.ori = 1
                    elif text[0] == '?':
                        self.search(self.search_text, -1)
                        self.ori = -1
                self.prev_key = []
                self.new_search = False
            else:
                self.statusbar.SetStatusText(self.statusbar.GetStatusText()+\
                                             chr(rawkeycode))
        elif ctrl_down and keycode == 70: #c-f
            self.on_next_page(None)
            self.prev_cmd = 'self.on_next_page(None)'
        elif ctrl_down and keycode == 66: #c-b
            self.on_prev_page(None)
            self.prev_cmd = 'self.on_prev_page(None)'
        elif ctrl_down and keycode == 79: #c-o
            self.on_page_back(None)
            self.prev_cmd = 'self.on_page_back(None)'
        elif ctrl_down and keycode == 73: #c-i
            self.on_page_fwd(None)
            self.prev_cmd = 'self.on_page_fwd(None)'
        elif (ctrl_down and keycode == 85) or\
             (not ctrl_down and keycode == wx.WXK_PAGEUP):#c-u
            self.win.vertical_scroll(-20)
            self.prev_cmd = 'self.win.vertical_scroll(-20)'
        elif (ctrl_down and keycode == 68) or\
             (not ctrl_down and keycode == wx.WXK_PAGEDOWN) or\
             keycode == wx.WXK_SPACE:#c-d
            self.win.vertical_scroll(20)
            self.prev_cmd = 'self.win.vertical_scroll(20)'
        #elif (rawkeycode > 96 and rawkeycode < 123) or\
        elif keycode > 64 and keycode < 91:#press letters
            text = self.statusbar.GetStatusText()
            if len(self.prev_key) > 0: #check if it's part of a cmd
                if self.prev_key[0] == 103:#prev is g
                    if rawkeycode == 103:#press another g
                        if len(self.prev_num) == 0:#no nums
                            self.marks[96] = (self.current_page_idx, 
                                              self.scale, 
                                              self.win.GetViewStart())
                            self.win.Scroll(-1, 0)
                            #self.prev_cmd = 'self.win.Scroll(-1, 0)'
                            self.statusbar.SetStatusText('')
                            self.prev_key = []
                        else:
                            self.marks[96] = (self.current_page_idx, 
                                              self.scale, 
                                              self.win.GetViewStart())
                            self.change_page(self.get_num()-1)#it's num gg
                            self.prev_key = []
                            self.prev_num = []
                            self.statusbar.SetStatusText('')
                    else:
                        self.prev_key = []
                        self.prev_num = []
                        self.statusbar.SetStatusText('')
                elif self.prev_key[0] == 90:#prev is Z
                    if rawkeycode == 90:#another Z
                        self.on_close(None)
                    else:
                        self.prev_key = []
                        self.statusbar.SetStatusText('')
                elif self.prev_key[0] == 109:#prev is m
                    self.marks[rawkeycode] = (self.current_page_idx,
                                              self.scale, 
                                              self.win.GetViewStart())
                    self.prev_key = []
                    self.statusbar.SetStatusText('')
                else:#prev is ' or `
                    self.retrive_mark(rawkeycode)
                    self.prev_key = []
                    self.statusbar.SetStatusText('')
            elif len(self.prev_num) > 0:#no prev key, has nums
                if rawkeycode == 106:#press j
                    self.num = self.get_num()
                    self.change_page(self.current_page_idx + self.num)
                    self.prev_cmd = 'self.change_page(self.current_page_idx+\
                                    self.num)'
                    self.statusbar.SetStatusText('')
                    self.prev_num = []
                elif rawkeycode == 107:#press k
                    self.num = self.get_num()
                    self.change_page(self.current_page_idx - self.num)
                    self.prev_cmd = 'self.change_page(self.current_page_idx-\
                                    self.num)'
                    self.statusbar.SetStatusText('')
                    self.prev_num = []
                elif rawkeycode == 103:#press g
                    self.prev_key.append(103)
                    self.statusbar.SetStatusText(self.statusbar.GetStatusText()+\
                                                 'g')
                else:
                    self.statusbar.SetStatusText('')
                    self.prev_num = []
            elif rawkeycode == 103 or rawkeycode == 90 or rawkeycode == 109: 
            #no prev key, no nums, press g or Z or m
                self.prev_key.append(rawkeycode)
                self.statusbar.SetStatusText(chr(rawkeycode))
            elif rawkeycode == 114: # press r
                self.on_refresh(None)
            elif rawkeycode == 119: # press w
                self.on_fit_width(None)
            elif rawkeycode == 71:#press G
                self.marks[96] = (self.current_page_idx, 
                                  self.scale, 
                                  self.win.GetViewStart())
                self.win.Scroll(-1, self.win.GetScrollRange(wx.VERTICAL))
            elif rawkeycode == 106:#press j
                self.win.vertical_scroll(1)
                self.prev_cmd = 'self.win.vertical_scroll(1)'
            elif rawkeycode == 107:#press k
                self.win.vertical_scroll(-1)
                self.prev_cmd = 'self.win.vertical_scroll(-1)'
            elif rawkeycode == 104:#press h
                self.win.horizontal_scroll(-1)
                self.prev_cmd = 'self.win.horizontal_scroll(-1)'
            elif rawkeycode == 108:#press l
                self.win.horizontal_scroll(1)
                self.prev_cmd = 'self.win.horizontal_scroll(1)'
            elif rawkeycode == 110:#press n
                self.search_next(1)
            elif rawkeycode == 78:#press N
                self.search_next(-1)
            elif rawkeycode == 118:#press v
                if not self.outline is None:
                    if self.show_outline:
                        self.win.panel.SetFocus()
                        self.split_win.Unsplit(self.outline_tree)
                        self.show_outline = False
                    else:
                        self.split_win.SplitVertically(self.outline_tree, self.win, 200)
                        self.show_outline = True

        elif rawkeycode > 47 and rawkeycode < 58:#press digit
            #if len(self.prev_num) == 0:
                #self.statusbar.SetStatusText('', 0)
            if len(self.prev_key) > 0:
                self.prev_key = []
            else:
                self.prev_num.append(keycode)
                self.statusbar.SetStatusText(str(self.get_num()), 0)
        elif rawkeycode == 96 or rawkeycode == 39:#press ' or `
            if len(self.prev_num) > 0:#has num
                self.prev_num = []
                self.statusbar.SetStatusText('')
            elif len(self.prev_key) == 0:#no num, no key
                self.prev_key.append(96)
                self.statusbar.SetStatusText(chr(rawkeycode))
            elif self.prev_key[0] == 96:#prev is '
                self.retrive_mark(96)
                self.prev_key = []
                self.statusbar.SetStatusText('')
            else:#prev is others
                self.prev_key = []
                self.statusbar.SetStatusText('')
        elif keycode == wx.WXK_DOWN:
            self.win.vertical_scroll(1)
        elif keycode == wx.WXK_UP:
            self.win.vertical_scroll(-1)
        elif rawkeycode == 43:# +, zoom in
            self.on_zoom_in(None)
            self.prev_cmd = 'self.on_zoom_in(None)'
        elif rawkeycode == 45:# -, zoom out
            self.on_zoom_out(None)
            self.prev_cmd = 'self.on_zoom_out(None)'
        elif keycode == wx.WXK_ESCAPE:
            self.prev_key = []
            self.prev_num = []
            self.statusbar.SetStatusText('', 0)
        elif keycode == 46: #. repeat cmd
            if len(self.prev_cmd) > 0:
                eval(self.prev_cmd)
        elif rawkeycode == 47 or rawkeycode == 63: # press /
            self.new_search = True
            self.statusbar.SetStatusText(chr(rawkeycode), 0)

    def get_num(self):
        page = ''
        for digit in self.prev_num:
            page += chr(digit)
        return int(page)

    def retrive_mark(self, code):
        if code in self.marks:
            mark = (self.current_page_idx, self.scale, self.win.GetViewStart())
            page_idx, scale, point = self.marks[code]
            if mark[0] != page_idx:
                self.page_back.append(self.current_page_idx)
                self.page_fwd = []
                self.set_current_page(page_idx)
            self.scale = scale
            self.win.set_scale(scale)
            self.update_statusbar()
            self.win.Scroll(point[0], point[1])
            self.marks[96] = mark

    def change_page(self, page_idx):
        if page_idx > -1 and page_idx < self.n_pages:
            self.page_back.append(self.current_page_idx)
            self.page_fwd = []
            self.set_current_page(page_idx)
