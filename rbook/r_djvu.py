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


import wx
import doc_scroll
import djvu.decode

class DocScroll(doc_scroll.DocScroll):
    def __init__(self, parent, current_page_idx):
        self.fmt = djvu.decode.PixelFormatRgb()
        self.fmt.rows_top_to_bottom = 1 
        self.fmt.y_top_to_bottom = 1


        self.width = parent.document.pages[current_page_idx].decode(True).width
        
        doc_scroll.DocScroll.__init__(self, parent, current_page_idx)

    def set_current_page(self, current_page_idx, draw=True, scroll=None, scale=None):
        self.hitbbox = []
        self.current_page = self.parent.document.pages[current_page_idx].decode(True)
        self.orig_width = self.current_page.width
        if scale:
            self.scale = scale
        self.set_page_size()

        self.text = self.parent.document.pages[current_page_idx].text.sexpr
        if draw:
            self.setup_drawing(scroll=scroll)

    def setup_drawing(self, hitbbox=None, scroll=None):
        doc_scroll.DocScroll.setup_drawing(self, hitbbox, scroll)

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
                           self.buffer)

    def new_scale_setup_drawing(self):
        self.setup_drawing()

    def set_page_size(self):
        self.width = int(self.scale*self.current_page.width)
        self.height = int(self.scale*self.current_page.height)

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

    def get_hitbbox(self, s):
        return self.search(self.text, s)

    def scroll_to_next_found(self, hit):
        hitbbox = self.hitbbox[hit]
        self.setup_drawing(hitbbox, 
                           (self.scale*hitbbox[0]/self.scroll_unit, 
                            self.scale*hitbbox[3]/self.scroll_unit))

    def search_in_current(self, newhit):
        image = wx.EmptyImage(self.width, self.height)
        image.SetData(self.invert_rect(self.hitbbox[newhit]))
        self.buffer = wx.BitmapFromImage(image)
        dc = wx.BufferedDC(wx.ClientDC(self.panel), self.buffer)
        self.Scroll(-1, self.hitbbox[newhit][3]*self.scale/self.scroll_unit)

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

    def on_refresh(self):
        self.parent.document = self.parent.ctx.new_document(djvu.decode.FileURI(self.parent.filepath))
        self.parent.document.decoding_job.wait()
        self.parent.n_pages = len(self.parent.document.pages)
