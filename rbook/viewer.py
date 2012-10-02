#!/usr/bin/env python
# -*- coding: utf8 -*-
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
        self.set_current_page(current_page, 1)
       
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

    def search_fwd(self, s):
        pass

    def search_back(self, s):
        pass

    def on_motion(self, event):
        link = self.link
        cx, cy = event.GetPositionTuple()
        while not link is None:
            rect = self.trans.transform_rect(link.get_rect())
            if cx >= rect.x0 and cx <= rect.x1 and \
               cy >= rect.y0 and cy <= rect.y1:
                break
            link = link.get_next()
        if not link is None:
            self.panel.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
            self.cursor_on_link = (link.get_kind(), \
                                   link.get_page(), \
                                   link.get_page_lt(), \
                                   link.get_uri())
        else:
            self.panel.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
            self.cursor_on_link = None

    def on_left_down(self, event):
        if not self.cursor_on_link is None:
            if self.cursor_on_link[0] == FZ_LINK_GOTO:
                page_idx = self.cursor_on_link[1]
                pos = self.cursor_on_link[2]
                self.parent.change_page(page_idx)
                pos = self.trans.transform_point(pos)
                self.Scroll(-1, pos.y/self.scroll_unit)
            elif self.cursor_on_link[0] == FZ_LINK_URI:
                subprocess.call(('xdg-open', self.cursor_on_link[3]))

    def fit_width_scale(self, current_page):
        rect = current_page.bound_page()
        width = rect.get_width()
        w_width, w_height = self.parent.GetSize()
        scale = round((w_width-self.vscroll_wid)/width-0.005, 2)
        if scale > self.parent.min_scale and scale < self.parent.max_scale:
            self.scale = scale
        else:
            self.scale = 1.0

    def on_paint(self, event):
        dc = wx.BufferedPaintDC(self.panel, self.buffer, wx.BUFFER_VIRTUAL_AREA)

    def set_page_size(self):
        self.trans = scale_matrix(self.scale, self.scale)
        self.page_rect = self.current_page.bound_page()
        rect = self.trans.transform_rect(self.page_rect)
        self.bbox = rect.round_rect()

        self.width = self.bbox.get_width()
        self.height = self.bbox.get_height()

#    def draw_pixmap(self, hitbbox=None):
        #self.pix = new_pixmap_with_bbox(self.ctx, fz_device_rgb, self.bbox)
        #self.pix.clear_pixmap_with_value(255);
        #dev = new_draw_device(self.pix)
        #self.display_list.run_display_list(dev, self.trans,
                                           #self.bbox, None)
        #if not hitbbox is None:
            #self.pix.invert_pixmap_rect(self.trans.transform_bbox(hitbbox))
        #do_drawing()

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

        self.link = current_page.load_links()
        self.cursor_on_link = None

        self.display_list = new_display_list(self.ctx)
        mdev = new_list_device(self.display_list)
        current_page.run_page(mdev, fz_identity, None)

        tdev = new_text_device(self.text_sheet, self.text_page)
        self.display_list.run_display_list(tdev, fz_identity, 
                                           fz_infinite_bbox, None)

        if draw:
            self.setup_drawing()
#            self.panel.SetSize((self.width, self.height))
            #self.SetVirtualSize((self.width, self.height))
            #self.SetScrollbars(self.scroll_unit, self.scroll_unit, 
                               #self.width/self.scroll_unit, 
                               #self.height/self.scroll_unit)
            #self.Scroll(0, 0)
            #self.put_center()
            #self.draw_pixmap()

    def setup_drawing(self, hitbbox=None):
        self.panel.SetSize((self.width, self.height))
        self.SetVirtualSize((self.width, self.height))
        self.SetScrollbars(self.scroll_unit, self.scroll_unit, 
                           self.width/self.scroll_unit, 
                           self.height/self.scroll_unit)
        self.Scroll(0, 0)
        self.put_center()

        self.pix = new_pixmap_with_bbox(self.ctx, fz_device_rgb, self.bbox)
        self.pix.clear_pixmap_with_value(255);
        dev = new_draw_device(self.pix)
        self.display_list.run_display_list(dev, self.trans,
                                           self.bbox, None)
        if not hitbbox is None:
            self.pix.invert_pixmap_rect(self.trans.transform_bbox(hitbbox))

        self.do_drawing()

    def set_scale(self, scale):
        self.scale = scale
        p_width, p_height = self.panel.GetSize()
        self.set_page_size()
        scroll_x, scroll_y = self.GetViewStart()
        x = 1.0*scroll_x/p_width
        y = 1.0*scroll_y/p_height
        self.setup_drawing()
        self.Scroll(int(x*self.width), int(y*self.height))

    def on_size(self, event):
        scroll_x, scroll_y = self.GetViewStart()
        self.Scroll(0, 0)
        self.put_center()
        self.Scroll(scroll_x, scroll_y)

    def put_center(self):
        w_width, w_height = self.parent.GetSize()
        h_move = 0
        v_move = 0
        if w_width > self.width:
            if w_height < self.height:
                h_move = (w_width-self.vscroll_wid-self.width)/2
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
                self.go_home()
            else:
                if self.parent.current_page_idx == 0:
                    isfirstpage = True
                else:
                    isfirstpage = False
                self.parent.on_prev_page(None)
                if not isfirstpage:
                    self.Scroll(0, self.GetScrollRange(wx.VERTICAL))
        elif y > bottom:
            if self.GetViewStart()[1] < bottom:
                self.go_end()
            else:
                self.parent.on_next_page(None)
        else:
            self.Scroll(-1, y)

    def horizontal_scroll(self, move):
        x = self.GetViewStart()[0] + move
        self.Scroll(x, -1)

    def go_home(self):
        self.Scroll(-1, 0)

    def go_end(self):
        self.Scroll(-1, self.GetScrollRange(wx.VERTICAL))


class DocViewer(wx.Frame):
    def __init__(self, parent, file_ele):
        self.file_ele = file_ele
        self.min_scale = 0.2
        self.max_scale = 4.0

        wx.Frame.__init__(self, parent, title=file_ele.get('title'), 
                          size=(800,700))
        self.parent = parent
        self.filepath = file_ele.get('path')
        self.current_page_idx = int(file_ele.get('current_page'))
        self.ctx = new_context(FZ_STORE_UNLIMITED)
        self.document = open_document(self.ctx, self.filepath)
        self.n_pages = self.document.count_pages()
        
        current_page = self.document.load_page(self.current_page_idx)

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
        self.prev_cmd = [False, False, []]
        self.search_text = ''
        self.hitbbox = None
        self.hit = 0
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
                self.set_current_page(current_page_idx, 0)
                hitbbox = self.win.text_page.search(s, 0)
            else:
                break
        if len(hitbbox) == 0: #not found
            self.set_current_page(self.current_page_idx)
        else:
            self.hitbbox = hitbbox
            if ori < 0:
                self.hit = len(hitbbox)-1
            else:
                self.hit = 0
            self.current_page_idx = current_page_idx
            self.update_statusbar()
            self.win.setup_drawing(hitbbox[self.hit])

    def update_statusbar(self):
        self.statusbar.SetStatusText('%d/%d    %d%%' % 
                                     (self.current_page_idx+1, 
                                      self.n_pages,
                                      int(100*self.scale)), 
                                     1)

    def search_next(self, ori):
        if self.search_text == '':
            pass
        elif len(self.hitbbox) == 0:#a new page
            self.search(self.search_text, ori*self.ori)
        else:
            newhit = self.hit + self.ori*ori
            if newhit > len(self.hitbbox)-1:# search in the next page
                page_index = self.current_page_idx + 1
                if page_index == self.n_pages:
                    page_index = 0
                self.set_current_page(page_index, 0)
                self.current_page_idx = page_index
                self.search(self.search_text, ori*self.ori)
            elif newhit < 0: #search in the prev page
                page_index = self.current_page_idx - 1
                if page_index == -1:
                    page_index = self.n_pages - 1
                self.set_current_page(page_index, 0)
                self.current_page_idx = page_index
                self.search(self.search_text, ori*self.ori)
            else:
                self.win.pix.invert_pixmap_rect(self.win.trans.transform_bbox(
                                                    self.hitbbox[self.hit]))
                self.win.pix.invert_pixmap_rect(self.win.trans.transform_bbox(
                                                    self.hitbbox[newhit]))
                self.hit = newhit
                self.win.do_drawing()


    def set_current_page(self, current_page_idx, draw=1):
        current_page = self.document.load_page(current_page_idx)
        self.hitbbox = []
        self.win.set_current_page(current_page, draw)
        if draw:
            self.current_page_idx = current_page_idx
            self.update_statusbar()

    def on_page_back(self, event):
        if len(self.page_back) == 0:
            pass
        else:
            self.page_fwd.append(self.current_page_idx)
            self.set_current_page(self.page_back.pop())

    def on_page_fwd(self, event):
        if len(self.page_fwd) == 0:
            pass
        else:
            self.page_back.append(self.current_page_idx)
            self.set_current_page(self.page_fwd.pop())

    def on_fit_width(self, event):
        self.win.fit_width_scale(self.win.current_page)
        self.scale = self.win.scale
        self.set_zoom_tools()
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
        if ctrl_down and keycode == 70: #c-f
            self.on_next_page(None)
            self.prev_cmd = [True, False, [70]]
        elif ctrl_down and keycode == 66: #c-b
            self.on_prev_page(None)
            self.prev_cmd = [True, False, [66]]
        elif ctrl_down and keycode == 79: #c-o
            self.on_page_back(None)
            self.prev_cmd = [True, False, [79]]
        elif ctrl_down and keycode == 73: #c-i
            self.on_page_fwd(None)
            self.prev_cmd = [True, False, [73]]
        elif (ctrl_down and keycode == 85) or\
             (not ctrl_down and keycode == wx.WXK_PAGEUP):#c-u
            self.win.vertical_scroll(-20)
            self.prev_cmd = [True, False, [85]]
        elif (ctrl_down and keycode == 68) or\
             (not ctrl_down and keycode == wx.WXK_PAGEDOWN) or\
             keycode == wx.WXK_SPACE:#c-d
            self.win.vertical_scroll(20)
            self.prev_cmd = [True, False, [68]]
        elif (keycode == wx.WXK_RETURN):
            text = self.statusbar.GetStatusText()
            if text:
                self.search_text = str(text[1:])
                if text[0] == '/':
                    self.search(self.search_text, 1)
                    self.ori = 1
                elif text[0] == '?':
                    self.search(self.search_text, -1)
                    self.ori = -1
            self.prev_key = []
            self.prev_num = []
            self.statusbar.SetStatusText('')
        elif (rawkeycode > 96 and rawkeycode < 123) or\
             (rawkeycode > 64 and rawkeycode < 91):#press letters
            text = str(self.statusbar.GetStatusText())
            if text and (text[0] == '/' or text[0] == '?'): #search 
                self.statusbar.SetStatusText(text+chr(rawkeycode))
            elif len(self.prev_key) > 0: #check if it's part of a cmd
                if self.prev_key[0] == 103:#prev is g
                    if rawkeycode == 103:#press another g
                        if len(self.prev_num) == 0:#no nums
                            self.marks[96] = (self.current_page_idx, 
                                              self.scale, 
                                              self.win.GetViewStart())
                            self.win.go_home()
                            #self.prev_cmd = [False, False, [103, 103]]
                            self.prev_key = []
                        else:
                            self.marks[96] = (self.current_page_idx, 
                                              self.scale, 
                                              self.win.GetViewStart())
                            self.change_page(self.get_num()-1)#it's num gg
                            self.prev_key = []
                            self.prev_num = []
                    else:
                        self.prev_key = []
                        self.prev_num = []
                elif self.prev_key[0] == 90:#prev is Z
                    if rawkeycode == 90:#another Z
                        self.on_close(None)
                    else:
                        self.prev_key = []
                elif self.prev_key[0] == 109:#prev is m
                    self.marks[rawkeycode] = (self.current_page_idx,
                                              self.scale, 
                                              self.win.GetViewStart())
                    self.prev_key = []
                else:#prev is ' or `
                    self.retrive_mark(rawkeycode)
                    self.prev_key = []
            elif len(self.prev_num) > 0:#no prev key, has nums
                if rawkeycode == 106:#press j
                    self.change_page(self.current_page_idx + self.get_num())
                    self.prev_cmd = [False, False, self.prev_num+[106]]
                    self.prev_num = []
                elif rawkeycode == 107:#press k
                    self.change_page(self.current_page_idx - self.get_num())
                    self.prev_cmd = [False, False, self.prev_num+[107]]
                    self.prev_num = []
                elif rawkeycode == 103:#press g
                    self.prev_key.append(103)
                else:
                    self.prev_num = []
            elif rawkeycode == 103 or rawkeycode == 90 or rawkeycode == 109: 
            #no prev key, no nums, press g or Z or m
                self.prev_key.append(rawkeycode)
            elif rawkeycode == 114: # press r
                self.on_refresh(None)
            elif rawkeycode == 119: # press w
                self.on_fit_width(None)
            elif rawkeycode == 71:#press G
                self.marks[96] = (self.current_page_idx, 
                                  self.scale, 
                                  self.win.GetViewStart())
                self.win.go_end()
            elif rawkeycode == 106:#press j
                self.win.vertical_scroll(1)
                self.prev_cmd = [False, False, [106]]
            elif rawkeycode == 107:#press k
                self.win.vertical_scroll(-1)
                self.prev_cmd = [False, False, [107]]
            elif rawkeycode == 104:#press h
                self.win.horizontal_scroll(-1)
                self.prev_cmd = [False, False, [104]]
            elif rawkeycode == 108:#press l
                self.win.horizontal_scroll(1)
                self.prev_cmd = [False, False, [108]]
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
            elif len(self.prev_key) == 0:#no num, no key
                self.prev_key.append(96)
            elif self.prev_key[0] == 96:#prev is '
                self.retrive_mark(96)
                self.prev_key = []
            else:#prev is others
                self.prev_key = []
        elif keycode == wx.WXK_DOWN:
            self.win.vertical_scroll(1)
            self.prev_cmd = [False, False, [106]]
        elif keycode == wx.WXK_UP:
            self.win.vertical_scroll(-1)
            self.prev_cmd = [False, False, [107]]
        elif keycode == wx.WXK_LEFT:
            self.win.horizontal_scroll(-1)
            self.prev_cmd = [False, False, [104]]
        elif keycode == wx.WXK_RIGHT:
            self.win.horizontal_scroll(1)
            self.prev_cmd = [False, False, [108]]
        elif keycode == wx.WXK_HOME:
            self.win.go_home()
        elif keycode == wx.WXK_END:
            self.win.go_end()
        elif shift_down and keycode == 61:
            self.on_zoom_in(None)
            self.prev_cmd = [False, True, 61]
        elif keycode == 45:
            self.on_zoom_out(None)
            self.prev_cmd = [False, False, 45]
        elif keycode == wx.WXK_ESCAPE:
            self.prev_key = []
            self.prev_num = []
            self.statusbar.SetStatusText('', 0)
        elif keycode == 46: #. repeat cmd
            for key in self.prev_cmd[2]:
                self.handle_keys(key, key, self.prev_cmd[0], self.prev_cmd[1])
        elif rawkeycode == 47: # press /
            self.statusbar.SetStatusText('/', 0)
        elif rawkeycode == 63: #press ?
            self.statusbar.SetStatusText('?', 0)


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
            self.set_zoom_tools()
            self.win.Scroll(point[0], point[1])
            self.marks[96] = mark

    def change_page(self, page_idx):
        if page_idx > -1 and page_idx < self.n_pages:
            self.page_back.append(self.current_page_idx)
            self.page_fwd = []
            self.set_current_page(page_idx)
