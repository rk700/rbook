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

from datetime import datetime
import os
import re
import xml.etree.cElementTree as ET
import time

import wx

from utils import *
from dirtree import MainDirTree
from filelist import FileList
from viewer import DocViewer


def add_help_file():
    xml_file = '<dir name="/" quick_visit="0">'\
                '<dir name="Uncategorized" quick_visit="1">'
    help_file = '/usr/share/rbook/viewer.pdf'
    if not os.path.exists(help_file):
        xml_file += '</dir> </dir>'
    else:
        inode = str(os.stat(help_file).st_ino)
        xml_file += '<file title="Viewer Shortcuts" '\
                    'author="Ruikai Liu" inode="' + inode +\
                    '" current_page="0" quick_visit="2" ' +\
                    'path="' + help_file +'" create_time="' +\
                    datetime.now().strftime('%b %d %Y %H:%M:%S')+\
                    '"/></dir> </dir>'
    return xml_file


def create_xml_file(rbook_dir, xmlfile):
    if not os.path.exists(rbook_dir):
        os.makedirs(rbook_dir, 0755)
        fout = open(xmlfile, 'w')
        fout.write(add_help_file())
        fout.close()
    if not os.path.exists(xmlfile):
        fout = open(xmlfile, 'w')
        fout.write(add_help_file())
        fout.close()


def on_about(event):
    about = wx.AboutDialogInfo()
    about.Name = 'rbook'
    about.Version = '0.1.0'
    about.Copyright = 'Copyright (C) 2012 Ruikai Liu' 
    about.Description = 'rbook is a simple PDF document manager.'
    about.WebSite = 'http://code.google.com/p/rbook'
    about.Developers = ['Ruikai Liu <lrk700@gmail.com>']
    about.License = \
        'rbook is free software: you can redistribute it and/or modify '\
        'it\nunder the terms of the GNU General Public License as '\
        'published by\nthe Free Software Foundation, either version 3 '\
        'of the License, or\n(at your option) any later version.\n\n'\
        'rbook is distributed in the hope that it will be useful, but\n'\
        'WITHOUT ANY WARRANTY; without even the implied warranty of\n'\
        'MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.\n'\
        'See the GNU General Public License for more details.\n\n'\
        'You should have received a copy of the GNU General Public '\
        'License\nalong with rbook.  If not, see '\
        '<http://www.gnu.org/licenses/>.'

    wx.AboutBox(about)


class MainFrame(wx.Frame):
    def __init__(self, parent, wxid, title, size): 
        wx.Frame.__init__(self, parent, wxid, title=title, size=size)
        
        self.qv_bar_data = []

        rbook_dir = os.path.expanduser('~/.rbook')
        self.xmlfile = os.path.expanduser('~/.rbook/books.xml')
        create_xml_file(rbook_dir, self.xmlfile)

        self.configfile = os.path.expanduser('~/.rbook/config')
        if os.path.exists(self.configfile):
            f = open(self.configfile)
            self.lines = f.readlines()
            f.close()
        else:
            self.lines = ['0\n', '\n', '0\n', str(time.time())]


        self.CreateStatusBar()

        # some bmp used in menus and toolbar
        bmp_add = wx.ArtProvider.GetBitmap('filenew', size=(16, 16))
        bmp_quickadd = wx.ArtProvider.GetBitmap('emblem-documents',
                                                size=(16, 16))
        bmp_open = wx.ArtProvider.GetBitmap('fileopen', size=(16, 16))

        # create menus
        menubar = wx.MenuBar()

        file_menu = wx.Menu()
        menu_add = wx.MenuItem(file_menu, -1, 'Add',
                               help='Add a file to some category')
        menu_add.SetBitmap(bmp_add)
        menu_quickadd = wx.MenuItem(file_menu, -1, 'Quick add',
                                    help='Add multiple files ' \
                                         'to the current category')
        menu_quickadd.SetBitmap(bmp_quickadd)
        menu_open = wx.MenuItem(file_menu, -1, "Open",
                                help='Open a file and add it ' \
                                     'to "Uncategorized" if not added yet')
        menu_open.SetBitmap(bmp_open)

        file_menu.AppendItem(menu_add)
        file_menu.AppendItem(menu_quickadd)
        file_menu.AppendItem(menu_open)
        menu_exit = file_menu.Append(wx.ID_EXIT, "Exit", help='Exit rbook')

        edit_menu = wx.Menu()
        menu_search = edit_menu.Append(wx.ID_FIND, 
                                       help='Search file in all the categories')
        menu_config = edit_menu.Append(wx.ID_PREFERENCES)

        about_menu = wx.Menu()
        menu_about = about_menu.Append(wx.ID_ABOUT, "About rbook")
        
        menubar.Append(file_menu, "File")
        menubar.Append(edit_menu, "Edit")
        menubar.Append(about_menu, "About")
        
        self.SetMenuBar(menubar)
        #self.SetMinSize(wx.Size(400, 300))

        toolbar = self.CreateToolBar(wx.TB_HORIZONTAL | 
                                     wx.NO_BORDER | 
                                     wx.TB_FLAT)
        tool_add = toolbar.AddLabelTool(
                       -1, 'Add', bmp_add, shortHelp='Add',
                       longHelp='Add a file to some category')
        tool_quickadd = toolbar.AddLabelTool(
                            -1, 'QuickAdd', bmp_quickadd, shortHelp='Quick add',
                            longHelp='Add multiple files ' \
                                     'to the current category')
        tool_open = toolbar.AddLabelTool(
                        -1, 'Open', bmp_open, shortHelp='Open',
                        longHelp='Open a file and add it ' \
                                 'to "Uncategorized" if not added yet')
        tool_newdir = toolbar.AddLabelTool(
                          -1, 'New Subcategory', 
                          wx.ArtProvider.GetBitmap('folder_new', size=(16, 16)),
                          shortHelp='New subcategory',
                          longHelp='Create new subcategory')
        tool_refresh = toolbar.AddLabelTool(
                          -1, 'Sync',
                          wx.ArtProvider.GetBitmap('gtk-refresh', size=(16, 16)),
                          shortHelp='Sync',
                          longHelp='Sync with the directory minitored')
        self.search = wx.SearchCtrl(toolbar, size=(300, -1),
                                    style=wx.TE_PROCESS_ENTER)
        self.search.ShowCancelButton(True)
        self.search.SetDescriptiveText('title or author')
        toolbar.AddControl(self.search)

        split_win = wx.SplitterWindow(self, -1, 
                                      style=wx.SP_LIVE_UPDATE)

        self.dir_tree = MainDirTree(split_win, -1, 
                                    wx.TR_DEFAULT_STYLE | wx.NO_BORDER, 
                                    ET.parse(self.xmlfile))
        self.file_list = FileList(split_win, -1, self.dir_tree)
        self.dir_tree.set_file_list(self.file_list)

        if int(self.lines[2].strip()):
            newfile = get_newfile(self.lines[1].strip(), float(self.lines[3].strip()))
            for newfile_ele in newfile:
                self.dir_tree.GetPyData(self.dir_tree.uncategorized).append(newfile_ele)


        split_win.SetMinimumPaneSize(180)
        split_win.SplitVertically(self.dir_tree, self.file_list, 200)

        self.quickvisit_bar = wx.ToolBar(self, -1, size=(-1, 36), 
                                         style=wx.TB_HORIZONTAL | wx.NO_BORDER |
                                               wx.TB_FLAT | wx.TB_HORZ_TEXT)
        self.quickvisit_bar.SetDropTarget(BarDropTarget(self, self.dir_tree, self.file_list))
        self.init_qv_bar()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.quickvisit_bar, 0, wx.EXPAND)
        vbox.Add(split_win, 1, wx.EXPAND)
        self.SetSizer(vbox)
        self.SetAutoLayout(True) 

        self.Bind(wx.EVT_TOOL, self.on_add, tool_add)
        self.Bind(wx.EVT_TOOL, self.on_quick_add, tool_quickadd)
        self.Bind(wx.EVT_TOOL, self.on_open, tool_open)
        self.Bind(wx.EVT_TOOL, self.dir_tree.on_new_dir, tool_newdir)
        self.Bind(wx.EVT_TOOL, self.on_sync, tool_refresh)
        self.Bind(wx.EVT_MENU, self.on_add, menu_add)
        self.Bind(wx.EVT_MENU, self.on_quick_add, menu_quickadd)
        self.Bind(wx.EVT_MENU, self.on_open, menu_open)
        self.Bind(wx.EVT_MENU, self.on_exit, menu_exit)
        self.Bind(wx.EVT_MENU, lambda event:SearchDialog(self, -1, 'Find', (385, 230)), menu_search)
        self.Bind(wx.EVT_MENU, self.on_config, menu_config)
        self.Bind(wx.EVT_MENU, on_about, menu_about)
        self.search.Bind(wx.EVT_TEXT_ENTER, self.on_search_title_author)
        self.search.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, 
                         self.on_search_title_author)
        #self.search.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self.on_search_cancel)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
    def on_config(self, event):
        dialog = ConfigFrame(self, -1, 'Preference', (400, 260))
        dialog.Show()
        

    def on_close(self, event):
        # store page idx for those unclosed viewers
        for doc in self.file_list.doc_list:
            doc.on_close(None)

        # store pos of quick visit items
        i = 1
        for data in self.qv_bar_data:
            # data = self.quickvisit_bar.GetToolClientData(id)
            # it's a dir
            if data[0] == 'd':
                self.dir_tree.GetPyData(data[1]).set('quick_visit', str(i))
            else:
                data[1].set('quick_visit', str(i))
            i += 1

        self.write_xml()

        self.lines[3] = str(time.time())
        f = open(self.configfile, 'w')
        f.writelines(self.lines)
        
        self.Destroy()

    def write_xml(self):
        self.dir_tree.element_tree.write(self.xmlfile, encoding='UTF-8')

    def on_exit(self, event):
        self.on_close(None)

    def on_sync(self, event):
        newfiles = get_newfile(self.lines[1].strip(), float(self.lines[3].strip()))
        for newfile in newfiles:
            if self.dir_tree.GetSelection() == self.dir_tree.uncategorized:
                self.file_list.append_file_ele(newfile, self.dir_tree.uncategorized)
            self.dir_tree.GetPyData(self.dir_tree.uncategorized).append(newfile)
        self.lines[3] = str(time.time())

    def on_open(self, event):
        dlg = wx.FileDialog(self, "Open file", "", "", "PDF files (*.pdf)|*.pdf|CBZ files (*.cbz)|*.cbz|XPS files (*.xps)|*.xps|Djvu files (*.djvu)|*.djvu", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            file_name = os.path.splitext(dlg.GetFilename())[0]
            file_path = dlg.GetPath()
            file_inode = str(os.stat(file_path).st_ino)
            info = self.dir_tree.search_file_inode(file_inode, 
                                                 self.dir_tree.GetRootItem())
            if info[1][0] is None:
                file_ele = ET.Element(
                                'file', title=file_name, author='', 
                                current_page='0', path=file_path, 
                                create_time=datetime.now().
                                            strftime('%b %d %Y %H:%M:%S'),
                                inode=file_inode, quick_visit='0')
                self.dir_tree.SelectItem(self.dir_tree.uncategorized)
                self.file_list.unselect_all()
                self.file_list.append_file_ele(file_ele, 
                                             self.dir_tree.uncategorized)
                doc = DocViewer(self.file_list, file_ele)
                self.file_list.doc_list.append(doc)
                dir_ele = self.dir_tree.GetPyData(self.dir_tree.uncategorized)
                dir_ele.append(file_ele)
            else:
                if not info[1][0] == self.dir_tree.GetSelection():
                    self.dir_tree.SelectItem(info[1][0])
                self.file_list.open_file_ele(info[1][1])
                self.file_list.select_item(self.file_list.search_inode(file_inode))
                #self.file_list.select_item(info[1][1])
                #self.file_list.on_open(None)
        dlg.Destroy()

    def on_quick_add(self, event):
        if self.dir_tree.GetSelection() == self.dir_tree.GetRootItem():
            RootNoFileDialog(self)
        else:
            dlg = wx.FileDialog(self, 'Quick add', "", "", "PDF files (*.pdf)|*.pdf|CBZ files (*.cbz)|*.cbz|XPS files (*.xps)|*.xps|Djvu files (*.djvu)|*.djvu", wx.OPEN | wx.MULTIPLE)
            if dlg.ShowModal() == wx.ID_OK:
                file_names = [name[0:-4] for name in dlg.GetFilenames()]
                file_paths = dlg.GetPaths()
                file_inodes = [str(os.stat(file_path).st_ino) 
                               for file_path in file_paths]
                self.dir_tree.search_file_inodes(file_inodes, file_names, 
                                               file_paths, 
                                               self.dir_tree.GetRootItem())
                count = len(file_inodes)
                current_dir = self.dir_tree.GetSelection()
                current_dir_ele = self.dir_tree.GetPyData(current_dir)
                self.file_list.unselect_all()
                for i in xrange(count): 
                    file_ele = ET.Element(
                                   'file', title=file_names[i], author='', 
                                   current_page='0', path=file_paths[i], 
                                   create_time=datetime.now().
                                   strftime('%b %d %Y %H:%M:%S'), 
                                   inode=file_inodes[i], quick_visit='0')
                    self.file_list.append_file_ele(file_ele, current_dir)
                    current_dir_ele.append(file_ele)
            dlg.Destroy()

    def on_add(self, event):
        dlg = wx.FileDialog(self, 'Add', "", "", "PDF files (*.pdf)|*.pdf|CBZ files (*.cbz)|*.cbz|XPS files (*.xps)|*.xps|Djvu files (*.djvu)|*.djvu", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            file_name = os.path.splitext(dlg.GetFilename())[0]
            file_path = dlg.GetPath()
            file_inode = str(os.stat(file_path).st_ino)
            info = self.dir_tree.search_file_inode(file_inode, 
                                                 self.dir_tree.GetRootItem())
            if info[1][0] is None:
                info = InfoInit(self, -1, (600, 500), 'File info', 
                                self.dir_tree, file_name, file_path, file_inode)
            else:
                msg = 'File "'+file_name+'" has already been added to '+\
                      self.dir_tree.get_full_path(info[1][0])
                msg_dlg = wx.MessageDialog(self, msg, 
                                           'File already added', wx.OK)
                msg_dlg.ShowModal()
                msg_dlg.Destroy()
        dlg.Destroy()

    def on_search_title_author(self, event):
        text = event.GetString()
        if text != '':
            self.dir_tree.SelectItem(self.dir_tree.GetSelection(), False)
            self.file_list.DeleteAllItems()
            file_eles = []
            dirs = []
            self.dir_tree.search_title_author(text, self.dir_tree.GetRootItem(),
                                            file_eles, dirs)
            self.file_list.show_files(file_eles, dirs)
            self.file_list.SetFocus()

    def adv_search(self, title, author, ignore_case, reg, choice, time):
        self.dir_tree.SelectItem(self.dir_tree.GetSelection(), False)
        self.file_list.DeleteAllItems()
        file_eles = []
        dirs = []
        if reg is False:
            if ignore_case is True:
                title = title.lower()
                author = author.lower()
        else:
            if ignore_case is True:
                if title != '':
                    title = re.compile(title, re.I)
                if author != '':
                    author = re.compile(author, re.I)
            else:
                if title != '':
                    title = re.compile(title)
                if author != '':
                    author = re.compile(author)
        self.dir_tree.adv_search(title, author, ignore_case, reg, choice, time, 
                                self.dir_tree.GetRootItem(), file_eles, dirs)
        self.file_list.show_files(file_eles, dirs)
        self.file_list.SetFocus()

    def on_quick_visit(self, event):
        data, index = self.find_qv_by(lambda data:data[2], event.GetId())
        # it's a dir
        if data[0] == 'd':
            self.dir_tree.SelectItem(data[1])
            self.dir_tree.SetFocus()
        # it's a file
        else:
            doc = DocViewer(self.file_list, data[1])
            self.file_list.doc_list.append(doc)

    def on_bar_right_down(self, event):
        self.remove_id = event.GetId()
        menu = wx.Menu()
        menu_remove = menu.Append(wx.ID_REMOVE, 'remove')
        self.quickvisit_bar.Bind(wx.EVT_MENU, self.remove_bar_item, menu_remove)
        self.quickvisit_bar.PopupMenu(menu)
        menu.Destroy()

    def remove_bar_item(self, event):
        # it's a dir
        data, index = self.find_qv_by(lambda data:data[2], self.remove_id)
        if data[0] == 'd':
            self.dir_tree.GetPyData(data[1]).set('quick_visit', '0')
        else:
            data[1].set('quick_visit', '0')
        del self.qv_bar_data[index]
        self.quickvisit_bar.DeleteTool(self.remove_id)

    def init_qv_bar(self):
        qv_pos = sorted(self.dir_tree.quickvisit, key=lambda i:i[2])
        for qv_tool in qv_pos:
            self.add_quick_visit(qv_tool[0], qv_tool[1])

    def add_quick_visit(self, data_type, data):
        wxid = wx.NewId()
        if data_type == 'd':
            tool = self.quickvisit_bar.AddLabelTool(
                       wxid, self.dir_tree.GetItemText(data), 
                       wx.ArtProvider_GetBitmap(wx.ART_FOLDER, size=(16, 16)),
                       longHelp=self.dir_tree.get_full_path(data))
            self.qv_bar_data.append([data_type, data, wxid])
        else:# it's a file, data[0] is file_ele, data[1] is containing dir
            tool = self.quickvisit_bar.AddLabelTool(
                       wxid, data[0].get('title'), 
                       wx.ArtProvider_GetBitmap('document', size=(16, 16)),
                       longHelp=self.dir_tree.get_full_path(data[1])+'/'+\
                                data[0].get('title'))
            self.qv_bar_data.append([data_type, data[0], wxid])
        self.Bind(wx.EVT_TOOL, self.on_quick_visit, tool)
        self.Bind(wx.EVT_TOOL_RCLICKED, self.on_bar_right_down, tool)

    def find_qv_by(self, func, item, data_type=None):
        i = 0
        for data in self.qv_bar_data:
            if data_type is None:
                if func(data) == item:
                    return (data, i)
            else:
                if data_type == data[0] and func(data) == item:
                    return (data, i)
            i += 1

class Run:
    def __init__(self):
        app = wx.App(False)
        frame = MainFrame(None, -1, "rbook", (800, 600))
        frame.Show()
        app.MainLoop()
