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
import fitz


class DocScroll(wx.ScrolledWindow):
    def __init__(self, parent, current_page_idx):
        self.scroll_unit = 10.0
        wx.ScrolledWindow.__init__(self, parent)
        self.parent = parent
        self.ctx = self.parent.ctx
        self.vscroll_wid = wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
        current_page = self.parent.document.load_page(current_page_idx)
        width = current_page.bound_page().get_width()
        w_width, w_height = self.parent.main_frame.GetSize()
        if parent.show_outline > 0:
            w_width -= 200
        scale = round((w_width-self.vscroll_wid-self.parent.GetSashSize())/width-0.005, 2)
        if not self.parent.scale == 0:
            self.scale = self.parent.scale
        elif scale > self.parent.min_scale and scale < self.parent.max_scale:
            self.scale = scale
        else:
            self.scale = 1.0

        self.panel = wx.Panel(self, -1)
        self.set_current_page(current_page_idx, scroll=self.parent.init_pos)
       
        self.panel.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.parent.on_size)
        self.Bind(wx.EVT_SCROLLWIN_LINEDOWN, 
                  lambda event:self.parent.vertical_scroll(1))
        self.Bind(wx.EVT_SCROLLWIN_LINEUP, 
                  lambda event:self.parent.vertical_scroll(-1))
        self.panel.Bind(wx.EVT_KEY_DOWN, lambda event:wx.PostEvent(self.parent.main_frame, event))
        self.panel.Bind(wx.EVT_MOTION, self.on_motion)
        self.panel.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)

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
            if self.link_context[0] == fitz.FZ_LINK_GOTO:
                # after change page, link_context becomes None,
                # so we need to record the pos
                pos = self.link_context[3]
                flag = self.link_context[2]
                self.parent.change_page(self.link_context[1])
                if flag & fitz.fz_link_flag_t_valid:
                    pos = self.trans.transform_point(pos)
                    self.Scroll(-1, (self.height-pos.y)/self.scroll_unit)
            elif self.link_context[0] == fitz.FZ_LINK_URI:
                subprocess.Popen(('xdg-open', self.link_context[4]))
        event.Skip()

    def on_paint(self, event):
        dc = wx.BufferedPaintDC(self.panel, self.buffer)

    def set_page_size(self):
        self.trans = fitz.scale_matrix(self.scale, self.scale)
        self.rect = self.trans.transform_rect(self.page_rect) #page_rect is the unscaled one
        self.bbox = self.rect.round_rect()

        self.width = self.bbox.get_width()
        self.height = self.bbox.get_height()

    def do_drawing(self):
        self.buffer = wx.BitmapFromBufferRGBA(self.pix.get_width(),
                                              self.pix.get_height(), 
                                              self.pix.get_samples())
        dc = wx.BufferedDC(wx.ClientDC(self.panel), 
                           self.buffer)

    def set_current_page(self, current_page_idx, draw=True, scroll=None, scale=None):
        self.hitbbox = []
        if scale:
            self.scale = scale
        current_page = self.parent.document.load_page(current_page_idx)
        self.page_rect = current_page.bound_page()
        self.orig_width = self.page_rect.get_width()
        self.set_page_size()

        self.text_sheet = self.ctx.new_text_sheet()
        self.text_page = self.ctx.new_text_page(self.page_rect)

        self.display_list = self.ctx.new_display_list()
        mdev = self.display_list.new_list_device()
        current_page.run_page(mdev, fitz.fz_identity, None)


        self.links = current_page.load_links()
        self.link_context = None

        tdev = self.text_page.new_text_device(self.text_sheet)
        self.display_list.run_display_list(tdev, fitz.fz_identity, self.rect, None)

        if draw:
            self.setup_drawing(scroll=scroll)


    def setup_drawing(self, hitbbox=None, scroll=None):
        self.panel.SetSize((self.width, self.height))
        self.SetVirtualSize((self.width, self.height))
        self.SetScrollbars(self.scroll_unit, self.scroll_unit, 
                           self.width/self.scroll_unit, 
                           self.height/self.scroll_unit)
        self.parent.put_center(self)
        if scroll:
            self.Scroll(scroll[0], scroll[1])

        self.pix = self.ctx.new_pixmap_with_irect(fitz.fz_device_rgb, self.bbox)
        self.pix.clear_pixmap(255);
        dev = self.pix.new_draw_device()
        self.display_list.run_display_list(dev, self.trans, self.rect, None)
        if hitbbox:
            for bbox in hitbbox:
                self.pix.invert_pixmap(self.trans.transform_irect(bbox))

        self.do_drawing()

    def set_scale(self, scale, scroll=None):
        if not self.scale == scale:
            self.scale = scale
            p_width, p_height = self.panel.GetSize()
            scroll_x, scroll_y = self.GetViewStart()
            x = 1.0*scroll_x/p_width
            y = 1.0*scroll_y/p_height
            self.set_page_size()
            try:
                hitbbox = self.hitbbox[self.parent.hit]
                self.setup_drawing(hitbbox)
            except IndexError:
                self.setup_drawing()
            if not scroll:
                self.Scroll(int(x*self.width), int(y*self.height))
        if scroll:
            self.Scroll(scroll[0], scroll[1])

    def search_in_page(self, current_page_idx, s, ori):
        self.hitbbox = self.text_page.search(s, self.parent.main_frame.settings['ic'])
        while len(self.hitbbox) == 0:
            current_page_idx += ori
            if current_page_idx == self.parent.n_pages:
                current_page_idx = 0
            elif current_page_idx == -1:
                current_page_idx = self.parent.n_pages-1

            if not current_page_idx == self.parent.current_page_idx:
                self.set_current_page(current_page_idx, False)
                self.hitbbox = self.text_page.search(s, self.parent.main_frame.settings['ic'])
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
            trans_hitbbox = self.trans.transform_irect(self.hitbbox[hit][0])
            self.setup_drawing(self.hitbbox[hit], 
                               (trans_hitbbox.x0/self.scroll_unit,
                                trans_hitbbox.y0/self.scroll_unit))

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
                old_hitbbox = self.hitbbox[self.parent.hit]
                for bbox in old_hitbbox:
                    self.pix.invert_pixmap(self.trans.transform_irect(bbox))
                new_hitbbox = self.hitbbox[newhit]
                for bbox in new_hitbbox:
                    self.pix.invert_pixmap(self.trans.transform_irect(bbox))
                self.do_drawing()
                self.Scroll(new_hitbbox[0].x0/self.scroll_unit, 
                            new_hitbbox[0].y0/self.scroll_unit)
        return newhit
