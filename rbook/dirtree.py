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

import xml.etree.cElementTree as ET

import wx

from utils import DirTree, DirTreeDropTarget, DirTreeFrame


class MainDirTree(DirTree):
    def __init__(self, parent, wxid, style, element_tree):
        DirTree.__init__(self, parent, wxid, style)
        self.main_win = parent.GetParent()
        self.file_list = None
        self.element_tree = element_tree
        root_ele = element_tree.getroot()
        self.quickvisit = []

        self.SetPyData(self.root_dir, root_ele)
        self.init_dir_name(self.root_dir, root_ele)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.on_begin_drag)
        self.uncategorized, cookie = self.GetFirstChild(self.GetRootItem())
        self.Expand(self.root_dir)

        dtree_drop_target = DirTreeDropTarget(self)
        self.SetDropTarget(dtree_drop_target)

    def set_file_list(self, file_list):
        self.file_list = file_list

    def init_dir_name(self, parent_dir, parent_dir_ele):
        for child_ele in list(parent_dir_ele):
            qv_pos = int(child_ele.get('quick_visit'))
            if child_ele.tag == 'dir':
                child_dir = self.AppendItem(parent_dir, child_ele.get('name'))
                self.SetItemImage(child_dir, self.folder_idx, 
                                  wx.TreeItemIcon_Normal)
                self.SetItemImage(child_dir, self.folder_open_idx, 
                                  wx.TreeItemIcon_Expanded)
                self.SetPyData(child_dir, child_ele)
                # the dir is in qv bar
                if qv_pos > 0:
                    self.quickvisit.append(('d', child_dir, qv_pos))
                self.init_dir_name(child_dir, child_ele)
            else:# child_ele is a file
                if qv_pos > 0:
                    self.quickvisit.append(('f', (child_ele, parent_dir), 
                                            qv_pos))
    def on_sel_changed(self, event):
        item = event.GetItem()
        if item.IsOk():
            dir_ele = self.GetPyData(item)
            self.file_list.DeleteAllItems()
            self.file_list.show_files(dir_ele.findall('file'), [item])

    def on_right_down(self, event):
        point = event.GetPosition()
        item, flags = self.HitTest(point)
        if item.IsOk():
            self.SelectItem(item)
            self.right_down_menu(item)

    def right_down_menu(self, item):
        menu = wx.Menu()
        menu_new = menu.Append(-1, "New Sub Category")
        menu_rename = menu.Append(1, "Rename")
        menu_delete = menu.Append(2, "Delete")
        menu_move = menu.Append(3, 'Move to ...')
        self.Bind(wx.EVT_MENU, self.on_new_dir, menu_new)
        self.Bind(wx.EVT_MENU, lambda event:self.EditLabel(self.GetSelection()),
                  menu_rename)
        self.Bind(wx.EVT_MENU, self.on_delete, menu_delete)
        self.Bind(wx.EVT_MENU, lambda event:DirTreeFrame(self, -1, (600, 500), 
                                                         'Move to', self),
                  menu_move)
        if item == self.GetRootItem() or item == self.uncategorized:
            menu.Enable(1, False)
            menu.Enable(2, False)
            menu.Enable(3, False)
        self.PopupMenu(menu)
        menu.Destroy()

    def on_new_dir(self, event):
        new_dir_ele = ET.Element('dir', name='New Category', quick_visit='0')
        current_dir = self.GetSelection()
        self.GetPyData(current_dir).append(new_dir_ele)
        new_dir = self.AppendItem(current_dir, 'New Category')
        self.SetItemImage(new_dir, self.folder_idx, wx.TreeItemIcon_Normal)
        self.SetItemImage(new_dir, self.folder_open_idx, 
                          wx.TreeItemIcon_Expanded)
        self.SetPyData(new_dir, new_dir_ele)
        self.Expand(current_dir)
        self.SelectItem(new_dir)
        self.EditLabel(new_dir)

    #def on_rename_dir(self, event):
        #self.EditLabel(self.GetSelection())

    def on_delete(self, event):
        current_dir = self.GetSelection()
        if current_dir.IsOk() and current_dir != self.GetRootItem()\
                              and current_dir != self.uncategorized:
            parent_dir = self.GetItemParent(current_dir) 
            parent_dir_ele = self.GetPyData(parent_dir)
            current_dir_ele = self.GetPyData(current_dir)
            self.del_dir_and_qv(current_dir, current_dir_ele)
            self.traverse(current_dir, self.del_dir_and_qv)
            parent_dir_ele.remove(current_dir_ele)
            self.Delete(current_dir)

    def del_dir_and_qv(self, current_dir, info=None):
        #check if the dir is in qv_bar
        current_dir_ele = self.GetPyData(current_dir)
        if int(current_dir_ele.get('quick_visit')) > 0:
            data, index = self.main_win.find_qv_by(lambda d:d[1], 
                                                   current_dir, 'd')
            self.main_win.quickvisit_bar.DeleteTool(data[2])
            del self.main_win.qv_bar_data[index]
        #check if the file under dir is in qv_bar
        for file_ele in current_dir_ele.findall('file'):
            if int(file_ele.get('quick_visit')) > 0:
                data, index = self.main_win.find_qv_by(lambda d:d[1], 
                                                       file_ele, 'f')
                self.main_win.quickvisit_bar.DeleteTool(data[2])
                del self.main_win.qv_bar_data[index]
        return (None, False)

    def on_end_edit(self, event):
        if not event.IsEditCancelled():
            new_name = event.GetLabel()
            current_dir = self.GetSelection()
            current_dir_ele = self.GetPyData(current_dir)
            current_dir_ele.set('name', new_name)

###### setlabel not work?? ######
###### have to delete and insert a new tool in order to update label ######
            if int(current_dir_ele.get('quick_visit')) > 0:
                data, index = self.main_win.find_qv_by(lambda d:d[1], 
                                                       current_dir, 'd')
                wxid = wx.NewId()
                self.main_win.quickvisit_bar.DeleteTool(data[2])
                tool = self.main_win.quickvisit_bar.InsertLabelTool(
                           index, wxid, new_name, 
                           wx.ArtProvider_GetBitmap(wx.ART_FOLDER, size=(16,16)),
                           longHelp=self.get_full_path(
                                        self.GetItemParent(current_dir))+
                                    '/'+new_name)
                self.main_win.Bind(wx.EVT_TOOL, self.main_win.on_quick_visit,
                                   tool)
                self.main_win.Bind(wx.EVT_TOOL_RCLICKED, 
                                   self.main_win.on_bar_right_down, tool)
                data[2] = wxid
                self.main_win.quickvisit_bar.Realize()
################################################

    #def on_move(self, event):
        #DirTreeFrame(self, -1, (600, 500), 'Move to', self)

    def move_to(self, target_dir):
        current_dir = self.GetSelection()
        current_dir_ele = self.GetPyData(current_dir)
        target_dir_ele = self.GetPyData(target_dir)

        #check if the target is child of the current dir
        target_is_child = False
        for ele in current_dir_ele.iter('dir'):
            if target_dir_ele is ele:
                target_is_child = True
                break

        if not target_is_child:
            new_root_dir, stop = self.update_dir_and_qv(current_dir, target_dir)
            self.traverse(current_dir, self.update_dir_and_qv, new_root_dir)

            parent_dir_ele = self.GetPyData(self.GetItemParent(current_dir))
            parent_dir_ele.remove(current_dir_ele)
            target_dir_ele.append(current_dir_ele)

            self.Delete(current_dir)
            self.SelectItem(new_root_dir)

    def update_dir_and_qv(self, child_dir, new_root_dir):
    # when moving dir, check if it's in qv_bar; 
    # if so, assign the new addr of dir to the qv tool
        child_dir_ele = self.GetPyData(child_dir)
        new_child_dir = self.AppendItem(new_root_dir, child_dir_ele.get('name'))
        self.SetItemImage(new_child_dir, self.folder_idx, 
                          wx.TreeItemIcon_Normal)
        self.SetItemImage(new_child_dir, self.folder_open_idx, 
                          wx.TreeItemIcon_Expanded)
        self.SetPyData(new_child_dir, child_dir_ele)

        # if the dir is in qv bar, set it's reference to the new dir, 
        # and update the tool longhelp
        if int(child_dir_ele.get('quick_visit')) > 0:
            data, index = self.main_win.find_qv_by(lambda d:d[1], 
                                                   child_dir, 'd')
            data[1] = new_child_dir
            self.main_win.quickvisit_bar.SetToolLongHelp(
                data[2], self.get_full_path(new_child_dir))

        # if any file in the dir is in qv bar, update its longhelp
        for file_ele in child_dir_ele.findall('file'):
            if int(file_ele.get('quick_visit')) > 0:
                data, index = self.main_win.find_qv_by(lambda d:d[1], 
                                                       file_ele, 'f')
                self.main_win.quickvisit_bar.SetToolLongHelp(
                    data[2], 
                    self.get_full_path(new_child_dir)+
                    '/'+file_ele.get('title'))
        return (new_child_dir, False)

    def search_file_inodes(self, file_inodes, file_names, file_paths, root_dir):
        self.traverse(root_dir, self.search_inodes, 
                      (file_inodes, file_names, file_paths))

    def search_title_author(self, text, root_dir, file_eles, dirs):
        self.traverse(root_dir, self.search_text, (text, file_eles, dirs))

    def search_file_inode(self, inode, root_dir):
        info = (inode, [None, None])
        self.traverse(root_dir, self.search_inode, info)
        return info

    def adv_search(self, title, author, ignore_case, reg, choice, 
                   time, root_dir, file_eles, dirs):
        self.traverse(
            root_dir, self.search, 
            (title, author, ignore_case, reg, choice, time, file_eles, dirs))

    def search_inode(self, current_dir, info):
        # info[0] is inode, info[1] is [current_dir, file_ele]
        #i = 0
        current_dir_ele = self.GetPyData(current_dir)
        for file_ele in current_dir_ele.findall('file'):
            if file_ele.get('inode') == info[0]:
                info[1][0] = current_dir
                info[1][1] = file_ele
                #info[1][1] = i
                return (info, True)
            #i += 1
        return (info, False)

    def search_inodes(self, current_dir, info):
    # info[0] is file_inodes, info[1] is file_names, info[2] is file_paths
        current_dir_ele = self.GetPyData(current_dir)
        for file_ele in current_dir_ele.findall('file'):
            n_inodes = len(info[0])
            inode = file_ele.get('inode')
            for index in xrange(n_inodes):
                if inode == info[0][index]:
                    del info[0][index]
                    del info[1][index]
                    del info[2][index]
                    if len(info[0]) == 0:
                        return (info, True)
                    break
        return (info, False)

    def search_text(self, current_dir, info):
        # info[0] is the text, 
        # info[1] is the list to save found file_eles,
        # info[2] is the list to save their dirs
        current_dir_ele = self.GetPyData(current_dir)
        for file_ele in current_dir_ele.findall('file'):
            if file_ele.get('title').find(info[0]) != -1 or\
               file_ele.get('author').find(info[0]) != -1:
                info[1].append(file_ele)
                info[2].append(current_dir)
        return (info, False)

    def search(self, current_dir, info):
        current_dir_ele = self.GetPyData(current_dir)
        for file_ele in current_dir_ele.findall('file'):
            title = info[0]
            author = info[1]
            ignore_case = info[2]
            reg = info[3]
            choice = info[4]
            time = info[5]
            if reg is True: #use regex
                if title != '': #title not blank
                    if title.search(file_ele.get('title')) is None:
                        continue
                if author != '': #author not blank
                    if author.search(file_ele.get('author')) is None:
                        continue
            else:#no regex
                if title != '': #title not blank
                    if ignore_case is True: #ignore case
                        if file_ele.get('title').lower().find(title) == -1:
                            continue
                    else:#do not ignore_case
                        if file_ele.get('title').find(title) == -1:
                            continue
                if author != '': #author not blank
                    if ignore_case is True:
                        if file_ele.get('author').lower().find(author) == -1:
                            continue
                    else:#not ignore_case
                        if file_ele.get('author').find(author) == -1:
                            continue
                if choice != '': #choice about time
                    f_time = wx.DateTime()
                    f_time.ParseTime(file_ele.get('create_time'))
                    if choice == 'before':
                        if f_time.IsEarlierThan(time):
                            continue
                    if choice == 'after':
                        if time.IsEarlierThan(f_time):
                            continue
            info[6].append(file_ele)
            info[7].append(current_dir)
        return (info, False)

    def get_full_path(self, category):
        if category == self.GetRootItem():
            return '/'
        else:
            path = ''#self.GetItemText(dir)
            while category != self.GetRootItem():
                path = '/' + self.GetItemText(category) + path
                category = self.GetItemParent(category)
            return path

    def on_key_down(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_DELETE:
            self.on_delete(None)
        elif keycode == wx.WXK_MENU:
            if self.GetSelection().IsOk():
                self.right_down_menu(self.GetSelection())
        else:
            event.Skip()

    def on_begin_drag(self, event):
        current_dir = self.GetSelection()
        if current_dir.IsOk():
            if current_dir != self.GetRootItem() and\
               current_dir != self.uncategorized:
                data = wx.CustomDataObject(wx.CustomDataFormat('DnD'))
                data.SetData('d')

                drop_source = wx.DropSource(self)
                drop_source.SetData(data)
                drop_source.DoDragDrop()
        else:
            event.Veto()
