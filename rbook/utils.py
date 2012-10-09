#!/usr/bin/env python
#-*- coding: utf8 -*-
#
# Copyright (C) 2012 Ruikai Liu <lrk700@gmail.com>
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

from datetime import datetime
import xml.etree.cElementTree as ET
import os

import wx

class ConfigFrame(wx.Frame):
    def __init__(self, parent, wxid, title, size):
        space = 10
        wx.Frame.__init__(self, parent, wxid, title, size=size)
        self.parent = parent

        self.cb1 = wx.CheckBox(self, -1, 'When deleting, '\
                                         'also delete the original file')
        self.cb1.SetValue(int(self.parent.lines[0].strip()))
        key2 = wx.StaticText(self, -1, 'Set directory to be monitored:')
        self.entry2 = wx.TextCtrl(self, -1, size=(250, -1))
        #if not self.parent.lines[1].strip() == '':
        self.entry2.SetValue(self.parent.lines[1].strip())
        self.cb2 = wx.CheckBox(self, -1, 'Automatically sync at start')
        self.cb2.SetValue(int(self.parent.lines[2].strip()))

        button_select = wx.Button(self, wx.ID_OPEN)
        button_cancel = wx.Button(self, wx.ID_CANCEL)
        button_ok = wx.Button(self, wx.ID_OK)
        button_ok.SetDefault()
        self.Bind(wx.EVT_BUTTON, self.on_select, button_select)
        self.Bind(wx.EVT_BUTTON, self.on_cancel, button_cancel)
        self.Bind(wx.EVT_BUTTON, self.on_ok, button_ok)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(button_cancel, 0, wx.RIGHT, 10)
        hbox.Add(button_ok, 0)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(self.entry2, 1, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 20)
        hbox1.Add(button_select, 0, wx.TOP | wx.RIGHT, 20)
        
        border = wx.BoxSizer(wx.VERTICAL)
        border.Add(self.cb1, 0, wx.ALL, 20)
        border.Add(key2, 0, wx.TOP | wx.LEFT | wx.RIGHT, 20)
        border.Add(hbox1, 0, wx.EXPAND)
        border.Add(self.cb2, 0, wx.TOP | wx.LEFT | wx.RIGHT, 20)
        border.Add(hbox, 0, wx.ALIGN_RIGHT | wx.ALL, 20)
        self.SetSizer(border)
        self.SetAutoLayout(True)

        self.Show()

    def on_select(self, event):
        dialog = wx.DirDialog(self, 'Choose a directory') 
        if dialog.ShowModal() == wx.ID_OK:
            dirpath = dialog.GetPath()
            self.entry2.SetValue(dirpath)
    

    def on_cancel(self, event):
        self.Destroy()

    def on_ok(self, event):
        delete_origin = int(self.cb1.GetValue())
        self.parent.lines[0] = str(delete_origin)+'\n'
        dirpath = self.entry2.GetValue()
        self.parent.lines[1] = dirpath+'\n'
        auto_sync = int(self.cb2.GetValue())
        self.parent.lines[2] = str(auto_sync)+'\n'

        if (not dirpath == '') or auto_sync:
            if not os.path.exists(dirpath):
                dialog = wx.MessageDialog(self, 
                                          "'%s' is not a valid directory" % dirpath,
                                          'Error',
                                          wx.OK | wx.ICON_EXCLAMATION)
                dialog.ShowModal()
                dialog.Destroy()
            else:
                self.Destroy()
        else:
            self.Destroy()



def get_newfile(path, time):
    newfile = []
    if os.path.exists(path):
        for dirpaths, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpaths, filename)
                file_suf = filename[-3:].lower()
                if (file_suf == 'pdf' or file_suf == 'cbz' or file_suf == 'xps') and \
                   os.path.getctime(filepath) > time:
                    file_ele = ET.Element('file', title=filename[0:-4], author='', 
                                          current_page='0', path=filepath, 
                                          create_time=datetime.now().
                                          strftime('%b %d %Y %H:%M:%S'), 
                                          inode=str(os.stat(filepath).st_ino), 
                                          quick_visit='0')
                    newfile.append(file_ele)

    return newfile


class RootNoFileDialog(wx.MessageDialog):
    def __init__(self, parent):
        self.parent = parent
        wx.MessageDialog.__init__(
                self, parent, 'Root category should not contain any file!', 
                'Warning', wx.OK | wx.ICON_EXCLAMATION)
        self.ShowModal()
        self.Destroy()


class DirTree(wx.TreeCtrl):
    def __init__(self, parent, wxid, style):
        wx.TreeCtrl.__init__(self, parent, wxid, style=style)
        self.imglist = wx.ImageList(16, 16)
        self.folder_idx = self.imglist.Add(wx.ArtProvider_GetBitmap(
                                                wx.ART_FOLDER, size=(16,16)))
        self.folder_open_idx = self.imglist.Add(wx.ArtProvider_GetBitmap(
                                                    wx.ART_FILE_OPEN, 
                                                    size=(16,16)))
        self.SetImageList(self.imglist)

        self.root_dir = self.AddRoot('/')
        self.SetItemImage(self.root_dir, self.folder_idx, 
                          wx.TreeItemIcon_Normal)
        self.SetItemImage(self.root_dir, self.folder_open_idx, 
                          wx.TreeItemIcon_Expanded)

        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_sel_changed)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.on_end_edit)

    def on_sel_changed(self, event):
        pass

    def on_end_edit(self, event):
        pass

    def traverse(self, parent_dir, func, info=None):
        child_dir, cookie = self.GetFirstChild(parent_dir)
        while child_dir.IsOk():
            new_info, stop = func(child_dir, info)
            if stop:
                return True
            if self.ItemHasChildren(child_dir):
                if self.traverse(child_dir, func, new_info):
                    return True
            child_dir, cookie = self.GetNextChild(parent_dir, cookie)
        return False


class OtherDirTree(DirTree):
    def __init__(self, parent, wxid, style, dir_tree):
        DirTree.__init__(self, parent, wxid, style)
        self.main_dir_tree = dir_tree
        self.main_new_dir = None

        self.SetPyData(self.root_dir, dir_tree.GetRootItem())
        dir_tree.traverse(dir_tree.GetRootItem(), 
                          self.copy_dir_tree, self.root_dir)
        self.Expand(self.root_dir)

    def copy_dir_tree(self, child_dir, new_root_dir):
        new_child_dir = self.AppendItem(new_root_dir, 
                                        self.main_dir_tree.
                                        GetPyData(child_dir).get('name'))
        self.SetItemImage(new_child_dir, self.folder_idx, 
                          wx.TreeItemIcon_Normal)
        self.SetItemImage(new_child_dir, self.folder_open_idx, 
                          wx.TreeItemIcon_Expanded)
        self.SetPyData(new_child_dir, child_dir)
        return (new_child_dir, False)

    def on_end_edit(self, event):
        if not event.IsEditCancelled():
            text = event.GetLabel()
            self.main_dir_tree.SetItemText(self.main_new_dir, text)
            self.main_dir_tree.GetPyData(self.main_new_dir).set('name', text)

    def new_dir(self):
        #main dir tree part:
        main_target_dir = self.GetPyData(self.GetSelection())
        new_dir_ele = ET.Element('dir', name='New Category', quick_visit='0')
        self.main_dir_tree.GetPyData(main_target_dir).append(new_dir_ele)
        self.main_new_dir = self.main_dir_tree.AppendItem(
                                main_target_dir, 'New Category')
        self.main_dir_tree.SetItemImage(
            self.main_new_dir, self.main_dir_tree.folder_idx, 
            wx.TreeItemIcon_Normal)
        self.main_dir_tree.SetItemImage(
            self.main_new_dir, self.main_dir_tree.folder_open_idx, 
            wx.TreeItemIcon_Expanded)
        self.main_dir_tree.SetPyData(self.main_new_dir, new_dir_ele)

        #own part:
        new_dir = self.AppendItem(self.GetSelection(), 'New Category')
        self.SetItemImage(new_dir, self.folder_idx, wx.TreeItemIcon_Normal)
        self.SetItemImage(new_dir, self.folder_open_idx, 
                          wx.TreeItemIcon_Expanded)
        self.SetPyData(new_dir, self.main_new_dir)
        self.Expand(self.GetSelection())
        self.SelectItem(new_dir)
        self.EditLabel(new_dir)


class DirTreeDropTarget(wx.PyDropTarget):
    def __init__(self, dir_tree):
        wx.PyDropTarget.__init__(self)
        self.dir_tree = dir_tree
        self.data = wx.CustomDataObject(wx.CustomDataFormat('DnD'))
        self.SetDataObject(self.data)

    def OnDrop(self, x, y):
        target_dir, flags = self.dir_tree.HitTest((x, y))
        if target_dir.IsOk(): return True
        else:
            return False

    def OnData(self, x, y, d):
        if self.GetData():
            target_dir, flags = self.dir_tree.HitTest((x, y))
            if self.data.GetData() == 'd':
                self.dir_tree.move_to(target_dir)
            elif self.data.GetData() == 'f':
                if target_dir == self.dir_tree.GetRootItem():
                    RootNoFileDialog(None)
                else:
                    self.dir_tree.file_list.move_to(target_dir)
        return d


class BarDropTarget(wx.PyDropTarget):
    def __init__(self, parent, dir_tree, file_list):
        wx.PyDropTarget.__init__(self)
        self.parent = parent
        self.dir_tree = dir_tree
        self.file_list = file_list
        self.data = wx.CustomDataObject(wx.CustomDataFormat('DnD'))
        self.SetDataObject(self.data)

    def add_file_to_qv_bar(self, idx):
        #get the file_ele and its containing dir
        file_and_dir = self.file_list.GetItemPyData(idx)
        #set the file qv bigger than 0
        file_and_dir[0].set('quick_visit', '1')
        self.parent.add_quick_visit('f', file_and_dir)
        return idx

    def OnData(self, x, y, d):
        if self.GetData():
            if self.data.GetData() == 'd':
                current_dir = self.dir_tree.GetSelection()
                self.parent.add_quick_visit('d', current_dir )
                self.dir_tree.GetPyData(current_dir).set('quick_visit', '1')
            else:
                self.file_list.traverse_selected(self.add_file_to_qv_bar)
        return d


class SearchDialog(wx.Frame):
    def __init__(self, parent, wxid, title, size):
        space = 10
        wx.Frame.__init__(self, parent, wxid, title, size=size)
        self.parent = parent
        key1 = wx.StaticText(self, -1, 'Title:')
        self.entry1 = wx.TextCtrl(self, -1, size=(200, -1))
        key2 = wx.StaticText(self, -1, 'Author:')
        self.entry2 = wx.TextCtrl(self, -1, size=(200, -1)) 

        self.cb1 = wx.CheckBox(self, -1, 'ignore case')
        self.cb2 = wx.CheckBox(self, -1, 'regular expression')

        key3 = wx.StaticText(self, -1, 'Create Time:')
        self.choice = wx.Choice(self, -1, (100, 50), choices=['', 'before', 'after'])
        self.dpc = wx.DatePickerCtrl(self, -1, size=(150, -1), 
                                     style=wx.DP_DROPDOWN | wx.DP_SHOWCENTURY)
       
        self.timechoice = ''
        self.searchtime = None

        button_cancel = wx.Button(self, wx.ID_CANCEL)
        button_ok = wx.Button(self, wx.ID_OK)
        button_ok.SetDefault()

        self.Bind(wx.EVT_BUTTON, self.on_cancel, button_cancel)
        self.Bind(wx.EVT_BUTTON, self.on_ok, button_ok)
        self.Bind(wx.EVT_CHOICE, self.on_choice, self.choice)
        self.Bind(wx.EVT_DATE_CHANGED, self.on_date_changed, self.dpc)

        sizer = wx.FlexGridSizer(0, cols=2, hgap=space, vgap=space)
        sizer.AddGrowableCol(1)
        
        sizer.Add(key1, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.entry1, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(key2, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.entry2, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.cb1, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.cb2, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)


        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(self.choice, 0, wx.RIGHT, 10)
        hbox1.Add(self.dpc)
        sizer.Add(key3, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(hbox1, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(button_cancel, 0, wx.RIGHT, 10)
        hbox2.Add(button_ok, 0)

        border = wx.BoxSizer(wx.VERTICAL)
        border.Add(sizer, 1, wx.EXPAND | wx.ALL, 15)
        border.Add(hbox2, 0, 
                   wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 
                   15)
        
        self.SetSizer(border)
        self.SetAutoLayout(True)

        self.Show()

    def on_cancel(self, event):
        self.Show(False)

    def on_ok(self, event):
        title = self.entry1.GetValue()
        author = self.entry2.GetValue()
        ignore_case = self.cb1.GetValue()
        reg = self.cb2.GetValue()
        if title != '' or author != '' or self.timechoice != '':
            self.parent.adv_search(title, author, ignore_case, reg, 
                                   self.timechoice, self.searchtime)
        self.Destroy()

    def on_choice(self, event):
        self.timechoice = event.GetString()
        if self.timechoice != '':
            self.searchtime = self.dpc.GetValue()

    def on_date_changed(self, event):
        self.searchtime = self.dpc.GetValue()


class InfoFrame(wx.Frame):
    def __init__(self, parent, wxid, title, size, file_and_dir):
        space = 10
        wx.Frame.__init__(self, parent, wxid, title, size=size)
        self.file_ele = file_and_dir[0]
        self.parent = parent

        key1 = wx.StaticText(self, -1, 'Title:')
        self.entry1 = wx.TextCtrl(self, -1, self.file_ele.get('title'),
                                  size=(200, -1))

        key2 = wx.StaticText(self, -1, 'Author:')
        author = self.file_ele.get('author')
        self.entry2 = wx.TextCtrl(self, -1, size=(200, -1)) 
        if not author == '':
            self.entry2.SetValue(author)

        key3 = wx.StaticText(self, -1, 'Path:')
        entry3 = wx.StaticText(self, -1, self.file_ele.get('path'))
        
        key4 = wx.StaticText(self, -1, 'Category:')
        self.entry4 = wx.StaticText(
                        self, -1, 
                        self.parent.dir_tree.get_full_path(file_and_dir[1]))

        key5 = wx.StaticText(self, -1, 'Create Time:')
        entry5 = wx.StaticText(self, -1, self.file_ele.get('create_time'))

        button_cancel = wx.Button(self, wx.ID_CANCEL)
        button_ok = wx.Button(self, wx.ID_OK)
        button_ok.SetDefault()
        self.Bind(wx.EVT_BUTTON, self.on_cancel, button_cancel)
        self.Bind(wx.EVT_BUTTON, self.on_ok, button_ok)

        sizer = wx.FlexGridSizer(0, cols=2, hgap=space, vgap=space)
        sizer.AddGrowableCol(1)
        
        sizer.Add(key1, 0, 
                  wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        sizer.Add(self.entry1, 0, 
                  wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        sizer.Add(key2, 0, 
                  wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        sizer.Add(self.entry2, 0, 
                  wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        sizer.Add(key3, 0, wx.ALIGN_LEFT | wx.LEFT, 10)
        sizer.Add(entry3, 0, 
                  wx.EXPAND | wx.ALIGN_CENTER_VERTICAL| wx.RIGHT, 10)
        sizer.Add(key4, 0, wx.ALIGN_LEFT | wx.LEFT, 10)
        sizer.Add(self.entry4, 0, 
                  wx.EXPAND | wx.ALIGN_CENTER_VERTICAL| wx.RIGHT, 10)
        sizer.Add(key5, 0, wx.ALIGN_LEFT | wx.LEFT, 10)
        sizer.Add(entry5, 0, 
                  wx.EXPAND | wx.ALIGN_CENTER_VERTICAL| wx.RIGHT, 10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(button_cancel, 0, wx.RIGHT, 10)
        hbox.Add(button_ok, 0)

        border = wx.BoxSizer(wx.VERTICAL)
        border.Add(sizer, 1, wx.EXPAND | wx.ALL, 10)
        border.Add(hbox, 0, wx.ALIGN_RIGHT | wx.ALL, 20)
        self.SetSizer(border)
        self.SetAutoLayout(True)

        self.Show()

    def on_cancel(self, event):
        self.Destroy()

    def on_ok(self, event):
        if self.entry1.IsModified():
            new_title = self.entry1.GetValue()
            self.file_ele.set('title', new_title)
            self.parent.SetItemText(self.parent.GetFirstSelected(), new_title)
            # if the file is in qv bar, 
            # we need to change the tool's label and longhelp
            if int(self.file_ele.get('quick_visit')) > 0:
                data, index = self.parent.main_win.find_qv_by(
                                lambda d:d[1], self.file_ele, 'f')
                wxid = wx.NewId()
                self.parent.main_win.quickvisit_bar.DeleteTool(data[2])
                tool = self.parent.main_win.quickvisit_bar.InsertLabelTool(
                            index, wxid, new_title, 
                            wx.ArtProvider_GetBitmap('document', size=(16,16)))
                self.parent.main_win.Bind(
                            wx.EVT_TOOL, 
                            self.parent.main_win.on_quick_visit, tool)
                self.parent.main_win.Bind(
                            wx.EVT_TOOL_RCLICKED, 
                            self.parent.main_win.on_bar_right_down, tool)
                data[2] = wxid
                self.parent.main_win.quickvisit_bar.SetToolLongHelp(
                            wxid, self.entry4.GetLabelText()+'/'+new_title)
            for doc in self.parent.doc_list:
                if doc.file_ele is self.file_ele:
                    doc.SetTitle(new_title)
        if self.entry2.IsModified():
            new_author = self.entry2.GetValue()
            self.file_ele.set('author', new_author)
            self.parent.set_author(new_author)
        self.Destroy()


class DirTreeFrame(wx.Frame):
    def __init__(self, parent, wxid, size, title, dir_tree):
        wx.Frame.__init__(self, parent, wxid, title=title, size=size)
        self.parent = parent
        self.main_dir_tree = dir_tree

        self.dir_tree = OtherDirTree(self, -1, wx.TR_DEFAULT_STYLE, dir_tree)
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.dir_tree, 1, wx.EXPAND)

        button_cancel = wx.Button(self, wx.ID_CANCEL)
        button_ok = wx.Button(self, wx.ID_OK)
        button_newdir = wx.Button(self, wx.ID_ADD)
        button_ok.SetDefault()

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(button_cancel, 0, wx.RIGHT, 8)
        hbox.Add(button_ok, 0)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(button_newdir, 0)
        hbox1.Add((0, 0), 1, wx.EXPAND)
        hbox1.Add(hbox, 0)

        border = wx.BoxSizer(wx.VERTICAL)
        border.Add(vbox, 1, wx.ALL | wx.EXPAND, 10)
        border.Add(hbox1, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(border)
        self.SetAutoLayout(True)

        self.Bind(wx.EVT_BUTTON, self.on_cancel, button_cancel)
        self.Bind(wx.EVT_BUTTON, self.on_ok, button_ok)
        self.Bind(wx.EVT_BUTTON, self.on_new_dir, button_newdir)
        self.Show()

    def on_cancel(self, event):
        self.Destroy()

    def on_ok(self, event):
        target_dir = self.dir_tree.GetPyData(self.dir_tree.GetSelection())
        # moving files to the root category
        if target_dir == self.main_dir_tree.GetRootItem() and\
           self.parent != self.main_dir_tree:
            RootNoFileDialog(self)
        else:
            self.parent.move_to(target_dir)
            self.Destroy()

    def on_new_dir(self, event):
        self.dir_tree.new_dir()


class InfoInit(wx.Frame):
    def __init__(self, parent, wxid, size, title, dir_tree, 
                 file_name, file_path, file_inode):
        wx.Frame.__init__(self, parent, wxid, size=size, title=title)
        space = 10

        self.parent = parent
        self.file_name = file_name
        self.file_path = file_path
        self.file_inode = file_inode
        self.dir_tree = OtherDirTree(self, -1, wx.TR_DEFAULT_STYLE, dir_tree)
        self.old_dir_tree = dir_tree

        key1 = wx.StaticText(self, -1, 'Title:')
        key2 = wx.StaticText(self, -1, 'Author:')
        key3 = wx.StaticText(self, -1, 'Add to:')
        self.entry1 = wx.TextCtrl(self, -1, file_name, size=(200, -1))
        self.entry2 = wx.TextCtrl(self, -1, size=(200, -1))

        sizer = wx.FlexGridSizer(0, cols=2, hgap=space, vgap=space)
        sizer.AddGrowableCol(1)
        sizer.Add(key1, 0, 
                  wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        sizer.Add(self.entry1, 0, 
                  wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        sizer.Add(key2, 0, 
                  wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        sizer.Add(self.entry2, 0, 
                  wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
 
        vbox1 = wx.BoxSizer(wx.VERTICAL)
        vbox1.Add(key3, 0, wx.ALIGN_LEFT | wx.LEFT, 10)
        vbox1.Add(self.dir_tree, 1, wx.EXPAND | wx.TOP, 5)

        button_cancel = wx.Button(self, wx.ID_CANCEL)
        button_ok = wx.Button(self, wx.ID_OK)
        button_newdir = wx.Button(self, wx.ID_ADD)
        button_ok.SetDefault()

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(button_cancel, 0, wx.RIGHT, 8)
        hbox.Add(button_ok, 0)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(button_newdir, 0)
        hbox1.Add((0, 0), 1, wx.EXPAND)
        hbox1.Add(hbox, 0)

        self.Bind(wx.EVT_BUTTON, self.on_cancel, button_cancel)
        self.Bind(wx.EVT_BUTTON, self.on_ok, button_ok)
        self.Bind(wx.EVT_BUTTON, self.on_new_dir, button_newdir)

        border = wx.BoxSizer(wx.VERTICAL)
        border.Add(sizer, 0, wx.EXPAND | wx.ALL, 10)
        border.Add(vbox1, 1, wx.EXPAND | wx.ALL, 10)
        border.Add(hbox1, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(border)
        self.SetAutoLayout(True)
        self.Show()

    def on_cancel(self, event):
        self.Destroy()

    def on_ok(self, event):
        title = self.entry1.GetValue()
        author = self.entry2.GetValue()
        target_dir = self.dir_tree.GetPyData(self.dir_tree.GetSelection())
        if target_dir == self.old_dir_tree.GetRootItem():
            RootNoFileDialog(self)
        else:
            time = datetime.now()
            file_ele = ET.Element(
                        'file', title=title, author=author, current_page='0',
                        path=self.file_path, 
                        create_time=time.strftime('%b %d %Y %H:%M:%S'), 
                        inode=self.file_inode, quick_visit='0')
            if target_dir != self.old_dir_tree.GetSelection():
                self.old_dir_tree.SelectItem(target_dir)
            self.parent.file_list.unselect_all()
            self.parent.file_list.append_file_ele(file_ele, target_dir)
            self.old_dir_tree.GetPyData(target_dir).append(file_ele)
            self.Destroy()

    def on_new_dir(self, event):
        self.dir_tree.new_dir()
