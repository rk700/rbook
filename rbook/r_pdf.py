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
from fitz import *

class DocScroll(wx.ScrolledWindow):
    def __init__(self, parent, main_win, doc, current_page_idx):
        self.scroll_unit = 10.0
        wx.ScrolledWindow.__init__(self, parent)
        self.parent = main_win
        self.doc = doc
        self.ctx = self.parent.ctx
        self.vscroll_wid = wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
        current_page = self.doc.load_page(current_page_idx)
        width = current_page.bound_page().get_width()
        w_width, w_height = self.parent.GetSize()
        if hasattr(main_win, 'split_win'):
            w_width = w_width - 200 - self.parent.split_win.GetSashSize()
        scale = round((w_width-self.vscroll_wid)/width-0.005, 2)
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
                                 link.get_page_flags(), \
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
                pos = self.link_context[3]
                flag = self.link_context[2]
                self.parent.change_page(self.link_context[1])
                if flag & fz_link_flag_t_valid:
                    pos = self.trans.transform_point(pos)
                    self.Scroll(-1, (self.height-pos.y)/self.scroll_unit)
            elif self.link_context[0] == FZ_LINK_URI:
                subprocess.Popen(('xdg-open', self.link_context[4]))

    def fit_width_scale(self):
        width = self.current_page.bound_page().get_width()

        if not (hasattr(self.parent, 'split_win') and self.parent.split_win.IsSplit()):
            w_width, w_height = self.parent.GetSize()
        else:
            w_width, w_height = self.parent.split_win.GetWindow2().GetSize()
        scale = round((w_width-self.vscroll_wid)/width-0.005, 2)
        if scale > self.parent.min_scale and scale < self.parent.max_scale:
            self.scale = scale
        else:
            self.scale = 1.0
        self.set_scale(scale)

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

    def set_current_page(self, current_page_idx, draw):
        self.current_page = self.doc.load_page(current_page_idx)
        self.set_page_size()

        self.text_sheet = new_text_sheet(self.ctx)
        self.text_page = new_text_page(self.ctx, self.page_rect)

        self.display_list = new_display_list(self.ctx)
        mdev = new_list_device(self.display_list)
        self.current_page.run_page(mdev, fz_identity, None)

        self.links = self.current_page.load_links()
        self.link_context = None

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



