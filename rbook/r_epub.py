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

import os
import codecs
import re
import subprocess

import bs4
import wx.html

class DocScroll(wx.html.HtmlWindow):
    def __init__(self, parent, current_page_idx):
        wx.html.HtmlWindow.__init__(self, parent, style=wx.html.HW_NO_SELECTION)
        self.parent = parent
        if not self.parent.scale == 0:
            self.scale = self.parent.scale
        else:
            self.scale = 2.0
        self.panel = self.GetTargetWindow()
        self.scroll_unit = self.GetScrollPixelsPerUnit()[0]
        self.sel = wx.html.HtmlSelection()
        self.set_current_page(current_page_idx, self.parent.init_pos, self.scale)
        self.panel.Bind(wx.EVT_KEY_DOWN, lambda event:self.parent.main_frame.handle_keys(event, self.parent))
        #self.Show()
        #self.Scroll(10,1020)
        #self.ScrollToAnchor('scripting')
        #print(self.GetViewStart())
        #self.Refresh()

    def OnLinkClicked(self, link):
        subprocess.Popen(('xdg-open', link.GetHref()))
    
    def set_current_page(self, html_idx, scroll=None, scale=None):
        current_page_path = os.path.join(self.parent.extract_path, 
                                         self.parent.items[html_idx])
        self.SetPage(self.add_name_for_anchor(current_page_path).prettify())
        if scale:
            self.set_scale(scale)
        if type(scroll) is str:
            self.ScrollToAnchor(scroll)
        elif scroll:
            self.Scroll(scroll[0], scroll[1])
        self.panel.SetFocus()

    def add_name_for_anchor(self, file_path):
        soup = bs4.BeautifulSoup(codecs.open(file_path, encoding='utf-8').read())
        anchors = soup.find_all('a')
        for anchor in anchors:
            if (not 'name' in anchor.attrs) and \
               ('id' in anchor.attrs):
                anchor['name'] = anchor['id']
        return soup

    def set_scale(self, scale, scroll=None):
        if not self.scale == scale:
            self.scale = scale
            font_size = [int(i+(scale-self.parent.min_scale)*5) for i in range(7)]
            self.SetFonts('', '', font_size)
        if scroll:
            self.Scroll(scroll[0], scroll[1])

    def search(self, s, current_page_idx, ic):
        current_page_path = os.path.join(self.parent.extract_path, 
                                         self.parent.items[current_page_idx])
        soup = self.add_name_for_anchor(current_page_path)
        if ic:
            pattern = re.compile(s, re.I)
        else:
            pattern = re.compile(s)
        if soup.find(['p', 'span'], text=pattern): 
            self.SetPage(soup.prettify())
            top_cell = self.GetInternalRepresentation()
            hitbbox = []
            self.find_cell(top_cell, self.sel, hitbbox, s)
            return hitbbox
        else:
            return None

    def find_cell(self, cell, sel, l, s):
        if cell:
            cell = cell.GetFirstChild()
            while cell:
                text = cell.ConvertToText(sel)
                if text and text.find(s) > -1:
                    l.append(self.get_cell_pos(cell))
                self.find_cell(cell, sel, l, s)
                cell = cell.GetNext()

    def get_cell_pos(self, cell):
        x = 0
        y = 0
        while cell:
            x += cell.GetPosX()
            y += cell.GetPosY()
            cell = cell.GetParent()
        return (x, y)

    def search_in_page(self, current_page_idx, s, ori):
        ic = self.parent.main_frame.settings['ic']
        self.hitbbox = self.search(s, current_page_idx, ic)
        while not self.hitbbox:
            current_page_idx += ori
            if current_page_idx == self.parent.n_pages:
                current_page_idx = 0
            elif current_page_idx == -1:
                current_page_idx = self.parent.n_pages-1

            if not current_page_idx == self.parent.current_page_idx:
                self.hitbbox = self.search(s, current_page_idx, ic)
            else:
                break
        if not self.hitbbox: #not found
            hit = -1
            self.parent.main_frame.statusbar.SetStatusText('"%s" not found' % s)
        else:
            if ori < 0:
                hit = len(self.hitbbox)-1
            else:
                hit = 0
            self.parent.current_page_idx = current_page_idx
            self.parent.main_frame.update_statusbar(self.parent)
            self.SelectWord(self.hitbbox[hit])
            self.Scroll(int(self.hitbbox[hit][0]/self.scroll_unit), 
                        int(self.hitbbox[hit][1]/self.scroll_unit))
        return hit

    def search_next(self, current_page_idx, s, ori):
        if not self.hitbbox:#a new page
            newhit = self.search_in_page(current_page_idx, s, ori)
        else:
            newhit = self.parent.hit + ori
            if newhit == len(self.hitbbox):# search in the next page
                page_index = current_page_idx + 1
                if page_index == self.parent.n_pages:
                    page_index = 0
                self.parent.current_page_idx = page_index
                newhit = self.search_in_page(page_index, s, ori)
            elif newhit == -1: #search in the prev page
                page_index = current_page_idx - 1
                if page_index == -1:
                    page_index = self.parent.n_pages - 1
                self.parent.current_page_idx = page_index
                newhit = self.search_in_page(page_index, s, ori)
            else:#search in the current page
                self.Refresh()
                self.SelectWord(self.hitbbox[newhit])
                self.Scroll(int(self.hitbbox[newhit][0]/self.scroll_unit), 
                            int(self.hitbbox[newhit][1]/self.scroll_unit))
        return newhit

