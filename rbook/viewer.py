#!/usr/bin/env python
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

from poppler import document_new_from_file
import wx
from wx.lib.wxcairo import ContextFromDC


class DocScroll(wx.ScrolledWindow):
    def __init__(self, parent, width, height, scale, current_page):
        self.scroll_unit = scroll_unit = 10.0
        wx.ScrolledWindow.__init__(self, parent)
        self.cairo = None
        self.parent = parent
        self.width = width
        self.height = height
        self.scale = scale
        self.current_page = current_page
        p_width = width*scale
        p_height = height*scale
        self.panel = wx.Panel(self, size=(p_width, p_height))
        self.SetVirtualSize((p_width, p_height))
        self.SetScrollbars(scroll_unit, scroll_unit, 
                           p_width/scroll_unit, p_height/scroll_unit)
        self.put_center()

        self.buffer = wx.EmptyBitmap(p_width, p_height)
        dc = wx.BufferedDC(wx.ClientDC(self.panel), self.buffer)
        self.do_drawing(dc)

        self.panel.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_SCROLLWIN_LINEDOWN, 
                  lambda event:self.vertical_scroll(1))
        self.Bind(wx.EVT_SCROLLWIN_LINEUP, 
                  lambda event:self.vertical_scroll(-1))
        self.panel.Bind(wx.EVT_KEY_DOWN, self.parent.on_key_down)
        self.panel.SetFocus()

    def on_paint(self, event):
        dc = wx.BufferedPaintDC(self.panel, self.buffer, wx.BUFFER_VIRTUAL_AREA)

    def do_drawing(self, dc):
        self.cairo = ContextFromDC(dc)
        self.cairo.set_source_rgb(1, 1, 1)
        if self.scale != 1:
            self.cairo.scale(self.scale, self.scale)
        self.cairo.rectangle(0, 0, self.width, self.height)
        self.cairo.fill()
        self.current_page.render(self.cairo)

    def update_drawing(self):
        dc = wx.BufferedDC(wx.ClientDC(self.panel), self.buffer)
        self.do_drawing(dc)
        self.panel.Refresh()

    def set_current_page(self, current_page):
        self.width, self.height = current_page.get_size()
        width = self.width*self.scale
        height = self.height*self.scale
        self.Scroll(0, 0)
        self.current_page = current_page
        self.panel.SetSize((width, height))
        self.put_center()
        self.buffer = wx.EmptyBitmap(width, height)
        self.update_drawing()
        self.SetVirtualSize((width, height))

    def set_scale(self, scale):
        self.scale = scale
        width = self.width*scale
        height = self.height*scale
        scroll_x, scroll_y = self.GetViewStart()
        p_width, p_height = self.panel.GetSize()
        x = 1.0*scroll_x/p_width
        y = 1.0*scroll_y/p_height
        self.Scroll(0, 0)
        self.panel.SetSize((width, height))
        self.put_center()
        self.buffer = wx.EmptyBitmap(width, height)
        self.update_drawing()
        self.SetVirtualSize((width, height))
        self.Scroll(int(x*width), int(y*height))
        self.parent.set_zoom_tools()

    def on_size(self, event):
        scroll_x, scroll_y = self.GetViewStart()
        self.Scroll(0, 0)
        self.put_center()
        self.Scroll(scroll_x, scroll_y)
    def put_center(self):
        w_width, w_height = self.GetSize()
        p_width, p_height = self.panel.GetSize()
        h_move = 0
        v_move = 0
        if w_width > p_width:
            if w_height < p_height:
                h_move = (w_width-self.parent.vscroll_wid-p_width)/2
            else:
                h_move = (w_width-p_width)/2
        if w_height > p_height:
            v_move = (w_height-p_height)/2
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

        self.vscroll_wid = wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
        wx.Frame.__init__(self, parent, title=file_ele.get('title'), 
                          size=(800,700))
        self.parent = parent
        filepath = file_ele.get('path')
        self.uri = "file://" + filepath
        self.current_page_idx = int(file_ele.get('current_page'))
        self.document = document_new_from_file(self.uri, None)
        self.n_pages = self.document.get_n_pages()

        self.marks = {}
        self.page_back = []
        self.page_fwd = []
        self.prev_key = []
        self.prev_num = []
        self.prev_cmd = [False, False, []]

        current_page = self.document.get_page(self.current_page_idx)
        self.width, self.height = current_page.get_size()
        self.scale = round((800.0-self.vscroll_wid)/self.width-0.005, 2)

        button_size = (24, 24)

        self.toolbar = self.CreateToolBar(wx.TB_HORIZONTAL | 
                                          wx.NO_BORDER | 
                                          wx.TB_FLAT)
        self.toolbar.SetToolBitmapSize(button_size)
        button_prev = self.toolbar.AddLabelTool(
                        1, 'Previous', 
                        wx.ArtProvider.GetBitmap('gtk-go-up', 
                                                 size=(24, 24)),
                        shortHelp='Go to previous page')
        button_next = self.toolbar.AddLabelTool(
                        2, 'Next', 
                        wx.ArtProvider.GetBitmap('gtk-go-down', 
                                                 size=(24, 24)),
                        shortHelp='Go to next page')
        button_back = self.toolbar.AddLabelTool(
                        3, 'Backward', 
                        wx.ArtProvider.GetBitmap('gtk-go-back', 
                                                 size=(24, 24)),
                        shortHelp='Go back')
        button_fwd = self.toolbar.AddLabelTool(
                        4, 'Forward', 
                        wx.ArtProvider.GetBitmap('gtk-go-forward',
                                                 size=(24, 24)), 
                        shortHelp='Go fowrard')

        self.entry1 = wx.TextCtrl(self.toolbar, 
                                  value=str(self.current_page_idx+1), 
                                  style=wx.TE_PROCESS_ENTER, size=(50,-1))
        self.toolbar.AddControl(self.entry1)
        self.total_pages = wx.StaticText(self.toolbar, 
                                         label=' of %d' % self.n_pages)
        self.toolbar.AddControl(self.total_pages)
        self.toolbar.AddSeparator()

        button_zin = self.toolbar.AddLabelTool(
                        5, 'Zoom in', 
                        wx.ArtProvider.GetBitmap('gtk-zoom-in', 
                                                 size=(24, 24)),
                        shortHelp='Zoom in')
        button_zout = self.toolbar.AddLabelTool(
                        6, 'Zoom out', 
                        wx.ArtProvider.GetBitmap('gtk-zoom-out', 
                                                 size=(24, 24)),
                        shortHelp='Zoom out')
        button_fwid = self.toolbar.AddLabelTool(
                        -1, 'Zoom fit', 
                        wx.ArtProvider.GetBitmap('gtk-zoom-fit',
                                                 size=(24, 24)),
                        shortHelp='Fit width')
        
        self.entry2 = wx.TextCtrl(self.toolbar, value=str(self.scale), 
                                  style=wx.TE_PROCESS_ENTER, size=(50,-1))
        self.toolbar.AddControl(self.entry2)
        self.toolbar.AddSeparator()
        button_refresh = self.toolbar.AddLabelTool(
                            -1, 'Refresh', 
                            wx.ArtProvider.GetBitmap('gtk-refresh',
                                                     size=(24, 24)),
                            shortHelp='Refresh')

        self.set_page_tools()
        self.set_zoom_tools()
        
        self.win = DocScroll(self, self.width, self.height, 
                             self.scale, current_page)
        self.Bind(wx.EVT_TOOL, self.on_prev_page, button_prev)
        self.Bind(wx.EVT_TOOL, self.on_next_page, button_next)
        self.Bind(wx.EVT_TOOL, self.on_zoom_in, button_zin)
        self.Bind(wx.EVT_TOOL, self.on_zoom_out, button_zout)
        self.Bind(wx.EVT_TOOL, self.fit_width, button_fwid)
        self.Bind(wx.EVT_TOOL, self.on_page_back, button_back)
        self.Bind(wx.EVT_TOOL, self.on_page_fwd, button_fwd)
        self.Bind(wx.EVT_TOOL, self.on_refresh, button_refresh)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.entry1.Bind(wx.EVT_TEXT_ENTER, self.on_page_changed)
        self.entry2.Bind(wx.EVT_TEXT_ENTER, self.on_scale_changed)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.Show()

    def on_refresh(self, event):
        self.document = document_new_from_file(self.uri, None)
        self.n_pages = self.document.get_n_pages()
        if self.n_pages > self.current_page_idx:
            current_page_idx = self.current_page_idx
        else:
            current_page_idx = self.n_pages - 1

        self.marks = {}
        self.page_back = []
        self.page_fwd = []
        self.prev_key = []
        self.prev_num = []
        self.prev_cmd = [False, False, []]
        
        pos = self.win.GetViewStart()
        self.set_current_page(current_page_idx)
        self.win.Scroll(pos[0], pos[1])
        self.total_pages.SetLabel(' of %d' % self.n_pages)
        self.toolbar.Realize()

    def set_current_page(self, current_page_idx):
        self.current_page_idx = current_page_idx
        current_page = self.document.get_page(current_page_idx)
        self.width, self.height = current_page.get_size()
        self.win.set_current_page(current_page)
        self.entry1.SetValue(str(current_page_idx+1))
        self.set_page_tools()

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

    def fit_width(self, event):
        w_width, w_height = self.win.GetSize()
        scale = round((w_width-self.vscroll_wid)/self.width-0.005, 2)
        if scale > self.min_scale and scale < self.max_scale:
            self.scale = scale
            self.win.set_scale(scale)

    def set_zoom_tools(self):
        self.entry2.SetValue(str(self.scale))
        if self.scale < self.max_scale:
            self.toolbar.EnableTool(5, True)
        else:
            self.toolbar.EnableTool(5, False)
        if self.scale > self.min_scale:
            self.toolbar.EnableTool(6, True)
        else:
            self.toolbar.EnableTool(6, False)

    def on_zoom_in(self, event):
        if self.scale < self.max_scale:
            self.scale += 0.2
            self.win.set_scale(self.scale)
            
    def on_zoom_out(self, event):
        if self.scale > self.min_scale:
            self.scale -= 0.2
            self.win.set_scale(self.scale)

    def set_page_tools(self):
        if self.current_page_idx == 0:
            self.toolbar.EnableTool(1, False)
        else:
            self.toolbar.EnableTool(1, True)
        if self.current_page_idx == self.n_pages-1:
            self.toolbar.EnableTool(2, False)
        else:
            self.toolbar.EnableTool(2, True)
        if len(self.page_back) == 0:
            self.toolbar.EnableTool(3, False)
        else:
            self.toolbar.EnableTool(3, True)
        if len(self.page_fwd) == 0:
            self.toolbar.EnableTool(4, False)
        else:
            self.toolbar.EnableTool(4, True)

    def on_page_changed(self, event):
        self.win.panel.SetFocus()
        try:
            page_idx = int(self.entry1.GetValue())-1
        except ValueError:
            pass
        else:
            self.change_page(page_idx)

    def on_scale_changed(self, event):
        self.win.panel.SetFocus()
        try:
            scale = float(self.entry2.GetValue())
        except ValueError:
            pass
        else:
            if scale > self.min_scale and scale < self.max_scale:
                self.scale = scale
                self.win.set_scale(scale)

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
        elif (rawkeycode > 96 and rawkeycode < 123) or\
             (rawkeycode > 64 and rawkeycode < 91):#press letters
            if len(self.prev_key) > 0: #check if it's part of a cmd
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
				self.fit_width(None)
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
        elif keycode > 47 and keycode < 58:#press digit
            if len(self.prev_key) > 0:
                self.prev_key = []
            else:
                self.prev_num.append(keycode)
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
        elif keycode == 46: #. repeat cmd
            for key in self.prev_cmd[2]:
                self.handle_keys(key, key, self.prev_cmd[0], self.prev_cmd[1])

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
            self.win.Scroll(point[0], point[1])
            self.marks[96] = mark

    def change_page(self, page_idx):
        if page_idx > -1 and page_idx < self.n_pages:
            self.page_back.append(self.current_page_idx)
            self.page_fwd = []
            self.set_current_page(page_idx)
