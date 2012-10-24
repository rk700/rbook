#!/usr/bin/env python2
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


#import subprocess

import wx
import djvu.decode

class DocScroll(wx.ScrolledWindow):
    def __init__(self, parent, current_page_idx, show_outline):
        self.fmt = djvu.decode.PixelFormatRgb()
        self.fmt.rows_top_to_bottom = 1 
        self.fmt.y_top_to_bottom = 1
        self.scroll_unit = 10.0
        wx.ScrolledWindow.__init__(self, parent)
        self.parent = parent
        self.vscroll_wid = float(wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X))
        current_page = self.parent.document.pages[current_page_idx].decode(True)
        width = current_page.width
        w_width, w_height = self.parent.main_frame.GetSize()
        if parent.show_outline and show_outline:
            w_width = 600
        scale = round((w_width-self.vscroll_wid-self.parent.GetSashSize())/width-0.005, 2)
        if scale > self.parent.min_scale and scale < self.parent.max_scale:
            self.scale = scale
        else:
            self.scale = 1.0

        self.panel = wx.Panel(self, -1)
        self.set_current_page(current_page_idx, True)
       
        self.panel.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_SCROLLWIN_LINEDOWN, 
                  lambda event:self.vertical_scroll(1))
        self.Bind(wx.EVT_SCROLLWIN_LINEUP, 
                  lambda event:self.vertical_scroll(-1))
        #self.panel.Bind(wx.EVT_KEY_DOWN, self.parent.on_key_down)
        self.panel.Bind(wx.EVT_KEY_DOWN, lambda event:self.parent.main_frame.handle_keys(event, self.parent))
        #self.Bind(wx.EVT_KEY_DOWN, self.son_key_down)
        #self.panel.SetFocus()

#    def pon_key_down(self, event):
        #print('pnl')
        #self.parent.on_key_down(event)
    #def son_key_down(self, event):
        #print('scl')
        #self.parent.on_key_down(event)
    def fit_width_scale(self):
        width = self.current_page.width
        if not self.parent.show_outline == 1:
            w_width, w_height = self.parent.main_frame.GetSize()
        else:
            w_width, w_height = self.parent.GetWindow2().GetSize()
        scale = round((w_width-self.vscroll_wid)/width-0.005, 2)
        if scale > self.parent.min_scale and scale < self.parent.max_scale:
            self.scale = scale
        else:
            self.scale = 1.0
        self.set_scale(scale)

    def on_paint(self, event):
        dc = wx.BufferedPaintDC(self.panel, self.buffer, wx.BUFFER_VIRTUAL_AREA)

    def set_current_page(self, current_page_idx, draw):
        self.hitbbox = []
        self.current_page = self.parent.document.pages[current_page_idx].decode(True)
        self.width = int(self.scale*self.current_page.width)
        self.height = int(self.scale*self.current_page.height)

        self.text = self.parent.document.pages[current_page_idx].text.sexpr
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

        try:
            self.data = self.current_page.render(djvu.decode.RENDER_COLOR, 
                                                 (0,0,self.width, self.height),
                                                 (0,0,self.width, self.height),
                                                 self.fmt)
            image = wx.EmptyImage(self.width, self.height)
            if not hitbbox is None:
                image.SetData(self.invert_rect(hitbbox))
            else:
                image.SetData(self.data)
            self.buffer = wx.BitmapFromImage(image)

        except djvu.decode.NotAvailable:
            self.data = ''
            self.buffer = wx.EmptyBitmap(self.width, self.height)
            dc = wx.MemoryDC(self.buffer)
            dc.SetBackground(wx.Brush('white'))
            dc.Clear()
            del dc

        dc = wx.BufferedDC(wx.ClientDC(self.panel), 
                           self.buffer,
                           wx.BUFFER_VIRTUAL_AREA)

    def set_scale(self, scale):
        self.scale = scale
        p_width, p_height = self.panel.GetSize()
        scroll_x, scroll_y = self.GetViewStart()
        x = 1.0*scroll_x/p_width
        y = 1.0*scroll_y/p_height

        self.width = scale*self.current_page.width
        self.height = scale*self.current_page.height
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

    def search(self, text, s):
        hitbbox = []
        page = iter(text)
        try:
            if page.next().as_string() == 'page':
                for i in range(3):
                    page.next()
                height = page.next().value
                while True:
                    try:
                        line = iter(page.next())
                        if line.next().as_string() == 'line':
                            for i in range(4):
                                line.next()
                            while True:
                                try:
                                    word = iter(line.next())
                                    if word.next().as_string() == 'word':
                                        rect = (word.next().value,
                                                height-word.next().value,
                                                word.next().value,
                                                height-word.next().value)
                                        string = word.next().value
                                        if not string.find(s) == -1:
                                            hitbbox.append(rect)
                                except StopIteration:
                                    break
                    except StopIteration:
                        break
        except StopIteration:
            pass
        return hitbbox

    def search_in_page(self, current_page_idx, s, ori):
        self.hitbbox = self.search(self.text, s)
        while len(self.hitbbox) == 0:
            current_page_idx += ori
            if current_page_idx == self.parent.n_pages:
                current_page_idx = 0
            elif current_page_idx == -1:
                current_page_idx = self.parent.n_pages-1

            if not current_page_idx == self.parent.current_page_idx:
                self.set_current_page(current_page_idx, False)
                self.hitbbox = self.search(self.text, s)
            else:
                break
        if len(self.hitbbox) == 0: #not found
            hit = -1
            self.set_current_page(current_page_idx, True)
            self.parent.main_frame.statusbar.SetStatusText('"%s" not found' % s)
        else:
            if ori < 0:
                hit = len(self.hitbbox)-1
            else:
                hit = 0
            self.parent.current_page_idx = current_page_idx
            self.parent.main_frame.update_statusbar(self.parent)
            self.setup_drawing(self.hitbbox[hit])
            self.Scroll(-1, self.scale*self.hitbbox[hit][3]/self.scroll_unit)

        return hit


    def search_next(self, current_page_idx, s, ori):
        if len(self.hitbbox) == 0:#a new page
            newhit = self.search_in_page(current_page_idx, s, ori)
        else:
            newhit = self.parent.hit + ori
            if newhit == len(self.hitbbox):# search in the next page
                page_index = current_page_idx + 1
                if page_index == self.parent.n_pages:
                    page_index = 0
                self.set_current_page(page_index, False)
                self.parent.current_page_idx = page_index
                newhit = self.search_in_page(page_index, s, ori)
            elif newhit == -1: #search in the prev page
                page_index = current_page_idx - 1
                if page_index == -1:
                    page_index = self.parent.n_pages - 1
                self.set_current_page(page_index, False)
                self.parent.current_page_idx = page_index
                newhit = self.search_in_page(page_index, s, ori)
            else:#search in the current page
                image = wx.EmptyImage(self.width, self.height)
                image.SetData(self.invert_rect(self.hitbbox[newhit]))
                self.buffer = wx.BitmapFromImage(image)
                dc = wx.BufferedDC(wx.ClientDC(self.panel), 
                                   self.buffer,
                                   wx.BUFFER_VIRTUAL_AREA)
                self.Scroll(-1, self.hitbbox[newhit][3]*self.scale/self.scroll_unit)
        return newhit

    def invert_rect(self, hitbbox):
        x0 = int(hitbbox[0]*self.scale) 
        y0 = int(hitbbox[3]*self.scale)
        x1 = int(hitbbox[2]*self.scale) 
        y1 = int(hitbbox[1]*self.scale)
        data = list(self.data)
        while y0 < y1:
            start = y0*self.width*3 + x0*3
            while start < y0*self.width*3 + x1*3:
                data[start] = chr(255 - ord(data[start]))
                start = start + 1
            y0 = y0 + 1

        return ''.join(data)
