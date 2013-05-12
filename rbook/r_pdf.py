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
import doc_scroll
import fitz


class DocScroll(doc_scroll.DocScroll):
    def __init__(self, parent, current_page_idx):

        self.ctx = parent.ctx
        self.width = parent.document.load_page(current_page_idx).bound_page().get_width()

        doc_scroll.DocScroll.__init__(self, parent, current_page_idx)

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
        doc_scroll.DocScroll.setup_drawing(self, hitbbox, scroll)

        self.pix = self.ctx.new_pixmap_with_irect(fitz.fz_device_rgb, self.bbox)
        self.pix.clear_pixmap(255);
        dev = self.pix.new_draw_device()
        self.display_list.run_display_list(dev, self.trans, self.rect, None)
        if hitbbox:
            for bbox in hitbbox:
                self.pix.invert_pixmap(self.trans.transform_irect(bbox))

        self.do_drawing()

    def new_scale_setup_drawing(self):
        try:
            hitbbox = self.hitbbox[self.parent.hit]
            self.setup_drawing(hitbbox)
        except IndexError:
            self.setup_drawing()

    def scroll_to_next_found(self, hit):
        trans_hitbbox = self.trans.transform_irect(self.hitbbox[hit][0])
        self.setup_drawing(self.hitbbox[hit], 
                           (trans_hitbbox.x0/self.scroll_unit,
                            trans_hitbbox.y0/self.scroll_unit))

    def get_hitbbox(self, s):
        return self.text_page.search(s, self.parent.main_frame.settings['ic'])

    def search_in_current(self, newhit):
        old_hitbbox = self.hitbbox[self.parent.hit]
        for bbox in old_hitbbox:
            self.pix.invert_pixmap(self.trans.transform_irect(bbox))
        new_hitbbox = self.hitbbox[newhit]
        for bbox in new_hitbbox:
            self.pix.invert_pixmap(self.trans.transform_irect(bbox))
        self.do_drawing()
        self.Scroll(new_hitbbox[0].x0/self.scroll_unit, 
                    new_hitbbox[0].y0/self.scroll_unit)


    def on_refresh(self):
        self.parent.document = self.ctx.open_document(self.parent.filepath)
        self.parent.n_pages = self.parent.document.count_pages()
