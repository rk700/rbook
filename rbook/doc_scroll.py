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


class DocScroll(wx.ScrolledWindow):
    def __init__(self, parent, current_page_idx):
        self.scroll_unit = 10.0
        wx.ScrolledWindow.__init__(self, parent)
        self.parent = parent
        self.vscroll_wid = float(wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X))
        w_width, w_height = self.parent.main_frame.GetSize()
        if parent.show_outline > 0:
            w_width -= 200
        scale = round((w_width-self.vscroll_wid-self.parent.GetSashSize())/self.width-0.005, 2)
        if not self.parent.scale == 0:
            self.scale = self.parent.scale
        elif scale > self.parent.min_scale and scale < self.parent.max_scale:
            self.scale = scale
        else:
            self.scale = 1.0

        self.panel = wx.Panel(self, -1)
        self.set_current_page(current_page_idx, scroll=self.parent.init_pos)
       
        self.panel.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_SCROLLWIN_LINEDOWN, 
                  lambda event:self.parent.vertical_scroll(1))
        self.Bind(wx.EVT_SCROLLWIN_LINEUP, 
                  lambda event:self.parent.vertical_scroll(-1))
        self.panel.Bind(wx.EVT_KEY_DOWN, lambda event:wx.PostEvent(self.parent.main_frame, event))

    def __del__(self):
        self.parent.view_start = self.GetViewStart()


    def on_size(self, event):
        scroll_x, scroll_y = self.GetViewStart()
        self.Scroll(0, 0)
        self.put_center()
        self.Scroll(scroll_x, scroll_y)

    def on_paint(self, event):
        dc = wx.BufferedPaintDC(self.panel, self.buffer)

    def set_current_page(self, current_page_idx, draw, scroll, scale):
        raise NotImplementedError()

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


    def setup_drawing(self, hitbbox, scroll):
        self.panel.SetSize((self.width, self.height))
        self.SetVirtualSize((self.width, self.height))
        self.SetScrollbars(self.scroll_unit, self.scroll_unit, 
                           self.width/self.scroll_unit, 
                           self.height/self.scroll_unit)
        self.put_center()
        if scroll:
            self.Scroll(scroll[0], scroll[1])

    def set_page_size(self):
        raise NotImplementedError()

    def new_scale_setup_drawing(self):
        raise NotImplementedError()

    def set_scale(self, scale, scroll=None):
        if not self.scale == scale:
            self.scale = scale
            p_width, p_height = self.panel.GetSize()
            scroll_x, scroll_y = self.GetViewStart()
            x = 1.0*scroll_x/p_width
            y = 1.0*scroll_y/p_height
            self.set_page_size()
            self.new_scale_setup_drawing()

            if not scroll:
                self.Scroll(int(x*self.width), int(y*self.height))
        if scroll:
            self.Scroll(scroll[0], scroll[1])

    def get_hitbbox(self, s):
        raise NotImplementedError()

    def scroll_to_next_found(self, hit):
        raise NotImplementedError()

    def search_in_page(self, current_page_idx, s, ori):
        self.hitbbox = self.get_hitbbox(s)
        while len(self.hitbbox) == 0:
            current_page_idx += ori
            if current_page_idx == self.parent.n_pages:
                current_page_idx = 0
            elif current_page_idx == -1:
                current_page_idx = self.parent.n_pages-1

            if not current_page_idx == self.parent.current_page_idx:
                self.set_current_page(current_page_idx, False)
                self.hitbbox = self.get_hitbbox(s)
            else:
                break
        if len(self.hitbbox) == 0: #not found
            hit = -1
            self.set_current_page(current_page_idx)
            self.parent.main_frame.statusbar.SetStatusText('!Error: "%s" not found' % s)
        else:
            if ori < 0:
                hit = len(self.hitbbox)-1
            else:
                hit = 0
            self.parent.current_page_idx = current_page_idx
            self.parent.main_frame.update_statusbar(self.parent)
            self.scroll_to_next_found(hit)

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
                self.search_in_current(newhit)

        return newhit

    def search_in_current(self, newhit):
        raise NotImplementedError()
