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

import subprocess

import wx
#import poppler
from fitz import *


class DocScroll(wx.ScrolledWindow):
    def __init__(self, parent, current_page):
        self.scroll_unit = 10.0
        wx.ScrolledWindow.__init__(self, parent)
        self.parent = parent
        self.ctx = self.parent.ctx
        self.vscroll_wid = wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
        self.fit_width_scale(current_page)
        self.panel = wx.Panel(self, -1)
        self.set_current_page(current_page, True)
       
        self.panel.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_SCROLLWIN_LINEDOWN, 
                  lambda event:self.vertical_scroll(1))
        self.Bind(wx.EVT_SCROLLWIN_LINEUP, 
                  lambda event:self.vertical_scroll(-1))
        self.panel.Bind(wx.EVT_KEY_DOWN, self.parent.on_key_down)
        self.panel.Bind(wx.EVT_MOTION, self.on_motion)
        self.panel.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)

        self.panel.SetFocus()

    def on_motion(self, event):
        cx, cy = event.GetPositionTuple()
        mouse_on_link = False
        for link in self.links:
            rect = self.trans.transform_rect(link.get_rect())
            if cx >= rect.x0 and cx <= rect.x1 and \
               cy >= rect.y0 and cy <= rect.y1:
                mouse_on_link = True
                break
        if mouse_on_link:
            self.panel.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
            self.link_context = (link.get_kind(), \
                                 link.get_page(), \
                                 link.get_page_lt(), \
                                 link.get_uri())
        else:
            self.panel.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
            self.link_context = None

    def on_left_down(self, event):
        if not self.link_context is None:
            if self.link_context[0] == FZ_LINK_GOTO:
                # after change page, link_context becomes None,
                # so we need to record the pos
                pos = self.link_context[2]
                self.parent.change_page(self.link_context[1])
                pos = self.trans.transform_point(pos)
                self.Scroll(-1, pos.y/self.scroll_unit)
            elif self.link_context[0] == FZ_LINK_URI:
                subprocess.Popen(('xdg-open', self.link_context[3]))

    def fit_width_scale(self, current_page):
        width = current_page.bound_page().get_width()
        w_width, w_height = self.parent.GetSize()
        scale = round((w_width-self.vscroll_wid)/width-0.005, 2)
        if scale > self.parent.min_scale and scale < self.parent.max_scale:
            self.scale = scale
        else:
            self.scale = 1.0

    def on_paint(self, event):
        dc = wx.BufferedPaintDC(self.panel, self.buffer, wx.BUFFER_VIRTUAL_AREA)

    def set_page_size(self):
        self.page_rect = self.current_page.bound_page()
        self.trans = scale_matrix(self.scale, self.scale)
        rect = self.trans.transform_rect(self.page_rect)
        self.bbox = rect.round_rect()

        self.width = self.bbox.get_width()
        self.height = self.bbox.get_height()

    def do_drawing(self):
        self.buffer = wx.BitmapFromBufferRGBA(self.pix.get_width(),
                                              self.pix.get_height(), 
                                              self.pix.get_samples())
        dc = wx.BufferedDC(wx.ClientDC(self.panel), 
                           self.buffer,
                           wx.BUFFER_VIRTUAL_AREA)

    def set_current_page(self, current_page, draw):
        self.current_page = current_page
        self.set_page_size()

        self.text_sheet = new_text_sheet(self.ctx)
        self.text_page = new_text_page(self.ctx, self.page_rect)

        self.links = current_page.load_links()
        self.link_context = None

        self.display_list = new_display_list(self.ctx)
        mdev = new_list_device(self.display_list)
        current_page.run_page(mdev, fz_identity, None)

        tdev = new_text_device(self.text_sheet, self.text_page)
        self.display_list.run_display_list(tdev, fz_identity, 
                                           self.bbox, None)

        if draw:
            self.setup_drawing()

    def setup_drawing(self, hitbbox=None):
        self.panel.SetSize((self.width, self.height))
        self.SetVirtualSize((self.width, self.height))
        self.SetScrollbars(self.scroll_unit, self.scroll_unit, 
                           self.width/self.scroll_unit, 
                           self.height/self.scroll_unit)
        self.Scroll(0, 0)
        self.put_center()

        self.pix = new_pixmap_with_bbox(self.ctx, fz_device_rgb, self.bbox)
        self.pix.clear_pixmap(255);
        dev = new_draw_device(self.pix)
        self.display_list.run_display_list(dev, self.trans,
                                           self.bbox, None)
        if not hitbbox is None:
            self.pix.invert_pixmap(self.trans.transform_bbox(hitbbox))

        self.do_drawing()

    def set_scale(self, scale):
        self.scale = scale
        p_width, p_height = self.panel.GetSize()
        scroll_x, scroll_y = self.GetViewStart()
        x = 1.0*scroll_x/p_width
        y = 1.0*scroll_y/p_height
        self.set_page_size()
        self.setup_drawing()
        self.Scroll(int(x*self.width), int(y*self.height))

    def on_size(self, event):
        scroll_x, scroll_y = self.GetViewStart()
        self.Scroll(0, 0)
        self.put_center()
        self.Scroll(scroll_x, scroll_y)

    def put_center(self):
        w_width, w_height = self.GetSize()
        h_move = 0
        v_move = 0
        if w_width > self.width:
            if w_height < self.height:
                h_move = max(0, w_width-self.vscroll_wid-self.width)/2
            else:
                h_move = (w_width-self.width)/2
        if w_height > self.height:
            v_move = (w_height-self.height)/2
        self.panel.Move((h_move, v_move))

    def vertical_scroll(self, move):
        bottom = int(round((self.GetVirtualSize()[1] - 
                            self.GetClientSize()[1])/self.scroll_unit))
        y = self.GetViewStart()[1] + move
        if y < 0:
            if self.GetViewStart()[1] > 0:
                self.Scroll(-1, 0)
            else:
                if self.parent.current_page_idx == 0:
                    pass
                else:
                    self.parent.on_prev_page(None)
                    self.Scroll(0, self.GetScrollRange(wx.VERTICAL))
        elif y > bottom:
            if self.GetViewStart()[1] < bottom:
                self.Scroll(-1, self.GetScrollRange(wx.VERTICAL)) 
            else:
                self.parent.on_next_page(None)
        else:
            self.Scroll(-1, y)

    def horizontal_scroll(self, move):
        x = self.GetViewStart()[0] + move
        self.Scroll(x, -1)



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
#        self.outline = self.document.load_outline()
        #if not self.outline is None:
            #item = self.outline.get_first()
            #item = item.get_next()
            #print(item.get_title())

        self.win = DocScroll(self, current_page);
        self.scale = self.win.scale
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(2)
        self.update_statusbar()
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.init()
        self.Show()

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
