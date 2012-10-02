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

import os

import wx
import wx.lib.agw.ultimatelistctrl as ULC
import wx.lib.mixins.listctrl as listmix

from viewer import DocViewer
from utils import InfoFrame, DirTreeFrame


class FileList(ULC.UltimateListCtrl, listmix.ColumnSorterMixin):
    def __init__(self, parent, wxid, dir_tree):
        ULC.UltimateListCtrl.__init__(self, parent, wxid, 
                                      agwStyle=ULC.ULC_REPORT)
        listmix.ColumnSorterMixin.__init__(self, 3)
        self.main_win = parent.GetParent()
        self.dir_tree = dir_tree
        self.itemDataMap = {}
        self.doc_list = []

        self.InsertColumn(0, 'Title')
        self.InsertColumn(1, 'Author')
        self.InsertColumn(2, 'Create Time')
        self.SetColumnWidth(0, 270)
        self.SetColumnWidth(1, 120)
        self.SetColumnWidth(2, 200)

        self.Bind(wx.EVT_LEFT_DCLICK, self.on_dclick)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.on_col_click)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.Bind(ULC.EVT_LIST_BEGIN_DRAG, self.on_begin_drag)
        self.Show()

    def on_begin_drag(self, event):
        if self.GetSelectedItemCount() > 0:
            data = wx.CustomDataObject(wx.CustomDataFormat('DnD'))
            data.SetData('f')
            drop_source = wx.DropSource(self)
            drop_source.SetData(data)
            drop_source.DoDragDrop()

    def GetListCtrl(self):
        return self

    def show_files(self, file_eles, dirs):
        i = 0
        dlen = len(dirs)
        for file_ele in file_eles:
            data = (file_ele.get('title'), file_ele.get('author'),
                    file_ele.get('create_time'))
            index = self.Append(data)
            self.itemDataMap[index] = data
            self.SetItemData(index, index)
            self.SetItemPyData(index, (file_ele, dirs[i]))
            if dlen > 1:
                i += 1
        self.SortListItems(0)

    def append_file_ele(self, file_ele, category):
        data = (file_ele.get('title'), file_ele.get('author'),
                file_ele.get('create_time'))
        index = self.Append(data)
        self.itemDataMap[index] = data
        self.SetItemData(index, index)
        self.SetItemPyData(index, (file_ele, category))
        self.Select(index)

    def on_open(self, event):
        doc = DocViewer(self, self.GetItemPyData(self.GetFirstSelected())[0])
        self.doc_list.append(doc)

    def open_file_ele(self, file_ele):
        doc = DocViewer(self, file_ele)
        self.doc_list.append(doc)

    def on_dclick(self, event):
        point = event.GetPosition()
        item, flag = self.HitTest(point)
        if item != -1:
            self.on_open(None)

    def on_right_down(self, event):
        point = event.GetPosition()
        item, flag = self.HitTest(point)
        if item != -1:
            if not self.IsSelected(item):
                self.select_item(item)
            self.right_down_menu()

    def select_item(self, item):
        #first unselect all the selected item
        self.unselect_all()
        self.Select(item)

    def unselect(self, item):
        self.Select(item, False)
        return item

    def unselect_all(self):
        self.traverse_selected(self.unselect)

    def right_down_menu(self):
        menu = wx.Menu()
        menu_open = menu.Append(1, 'Open')
        menu_openwith = menu.Append(2, 'Open with ...')
        menu_delete = menu.Append(3, 'Delete')
        menu_move = menu.Append(4, "Move to ...")
        menu_info = menu.Append(5, 'Info')
        self.Bind(wx.EVT_MENU, self.on_open, menu_open)
        self.Bind(wx.EVT_MENU, self.on_open_with, menu_openwith)
        self.Bind(wx.EVT_MENU, self.on_delete, menu_delete)
        self.Bind(wx.EVT_MENU, 
                  lambda event:DirTreeFrame(
                                   self, -1, (600, 500), 
                                   'Move to', self.dir_tree),
                  menu_move)
        self.Bind(wx.EVT_MENU, 
                  lambda event:InfoFrame(
                                   self, -1, 'Info', (550, 250), 
                                   self.GetItemPyData(self.GetFirstSelected())),
                  menu_info)
        if self.GetSelectedItemCount() > 1:
            menu.Enable(1, False)
            menu.Enable(2, False)
            menu.Enable(5, False)
        self.PopupMenu(menu)
        menu.Destroy()

    def traverse_selected(self, func):
        item = self.GetFirstSelected()
        while item != -1:
            new_item = func(item)
            item = self.GetNextItem(new_item, ULC.ULC_NEXT_ALL,
                                    ULC.ULC_STATE_SELECTED)
    def search_inode(self, inode):
        item = self.GetNextItem(-1, ULC.ULC_NEXT_ALL)
        while item != -1:
            if self.GetItemPyData(item)[0].get('inode') == inode:
                return item
            item = self.GetNextItem(item, ULC.ULC_NEXT_ALL)
    def on_delete(self, event):
        self.traverse_selected(self.delete_item_and_qv)

    def delete_item_and_qv(self, item):
        file_ele = self.GetItemPyData(item)[0]
        #check if the file in in qv_bar
        if int(file_ele.get('quick_visit')) > 0:
            data, index = self.main_win.find_qv_by(lambda d:d[1], file_ele, 'f')
            self.main_win.quickvisit_bar.DeleteTool(data[2])
            del self.main_win.qv_bar_data[index]
        self.dir_tree.GetPyData(self.GetItemPyData(item)[1]).remove(file_ele)
        self.DeleteItem(item)
        # after moving one item, all the items below it will get index-1
        return item-1

    def on_col_click(self, event):
        self.Refresh()
        event.Skip()

    def set_author(self, new_author):
        current_item = self.GetFirstSelected()
        self.itemDataMap[current_item] = (self.itemDataMap[current_item][0], 
                                          new_author, 
                                          self.itemDataMap[current_item][2])
        item = self.GetItem(current_item, 1)
        item.SetText(new_author)
        self.SetItem(item)

    def on_open_with(self, event):
        dlg = wx.FileDialog(self, message='Choose a program', 
                            defaultDir=os.getcwd())
        if dlg.ShowModal() == wx.ID_OK:
            os.system(
                dlg.GetPath()+' '+
                self.GetItemPyData(self.GetFirstSelected())[0].get('path')+' &')
        dlg.Destroy()

    def move_to(self, target_dir):
        if target_dir != self.dir_tree.GetSelection():
            target_dir_ele = self.dir_tree.GetPyData(target_dir)
            self.traverse_selected(lambda item:self.move_item(item, 
                                                              target_dir_ele,
                                                              target_dir))

    def move_item(self, item, target_dir_ele, target_dir):
        file_ele = self.GetItemPyData(item)[0]
        # if the file is in qv bar, update its longhelp
        if int(file_ele.get('quick_visit')) > 0:
            data, index = self.main_win.find_qv_by(lambda d:d[1], file_ele, 'f')
            self.main_win.quickvisit_bar.SetToolLongHelp(
                                             data[2],
                                             self.dir_tree.
                                             get_full_path(target_dir)+
                                             '/'+file_ele.get('title'))
        self.dir_tree.GetPyData(self.GetItemPyData(item)[1]).remove(file_ele)
        target_dir_ele.append(file_ele)
        self.DeleteItem(item) 
        # after moving one item, all the items below it will get index-1
        return item-1

    def on_key_down(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_DELETE:
            self.on_delete(None)
        elif keycode == wx.WXK_RETURN:
            if self.GetSelectedItemCount() == 1:
                self.on_open(None)
        elif keycode == wx.WXK_MENU:
            if self.GetSelectedItemCount() > 0:
                self.right_down_menu()
        else:
            event.Skip()
