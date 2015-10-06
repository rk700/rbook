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
import shutil
import zipfile

import wx
import fitz

import r_pdf
import utils


class DocViewer(wx.SplitterWindow):
    def __init__(self, parent, docfile, ext, show_outline):
        wx.SplitterWindow.__init__(self, parent, -1, style=wx.SP_LIVE_UPDATE)
        self.min_scale = 0.25
        self.max_scale = 4.0
        self.main_frame = parent.GetParent()

        if self.main_frame.settings['storepages']:
            try:
                self.inode = os.stat(docfile).st_ino
                info = self.main_frame.pages[self.inode]
                self.current_page_idx = info[1]
                self.scale = info[2]
                self.init_pos = info[3]
                self.show_outline = info[4]
            except KeyError:
                self.current_page_idx = 0
                self.scale = 0
                self.init_pos = (0, 0)
                self.show_outline = show_outline
            except OSError:
                self.Destroy()
                raise IOError('cannot open file %s' % docfile)


        self.filepath = docfile
        self.outline_tree = wx.TreeCtrl(self, -1, 
                                        style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT)

        if ext == '.DJVU':
            self.ext = ext
            self.djvu_init_doc()
        elif ext == '.PDF' or ext == '.CBZ' or ext == '.XPS':
            self.ext = '.PDF'
            self.pdf_init_doc()
        elif ext == '.EPUB':
            self.ext = ext
            self.epub_init_doc()
            self.set_outline()
        else:
            self.Destroy()
            raise IOError('%s file is not supported' % ext[1:])

        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_sel_changed, self.outline_tree)
        self.SetMinimumPaneSize(180)
        self.SplitVertically(self.outline_tree, self.doc_scroll, 200)
        if not self.show_outline > 0:
            self.Unsplit(self.outline_tree)

        self.scale = self.doc_scroll.scale
        self.main_frame.update_statusbar(self)
        self.view_start = (0,0)
            
        self.init()

    def __del__(self):
        if self.ext == '.EPUB':
            try: 
                shutil.rmtree(os.path.join(os.path.expanduser('~/.rbook/cache/'),
                                    str(os.stat(self.filepath).st_ino)))
            except:
                pass
            finally:
                self.book.close()
        if self.main_frame.settings['storepages']:
            self.save_page()

    def djvu_init_doc(self):
        try:
            import djvu.decode
        except ImportError:
            self.Destroy()
            raise IOError('Install python-djvulibre for DJVU files')
        else:
            import r_djvu

            self.ctx = djvu.decode.Context()
            try:
                self.document = self.ctx.new_document(djvu.decode.FileURI(self.filepath))
                self.document.decoding_job.wait()
                self.n_pages = len(self.document.pages)
            except djvu.decode.JobFailed:
                self.Destroy()
                raise IOError('cannot open file %s' % docfile)
            self.set_outline()
            if not self.current_page_idx < self.n_pages:
                self.current_page_idx = self.n_pages - 1
            self.doc_scroll = r_djvu.DocScroll(self, self.current_page_idx);

    def pdf_init_doc(self):
        #self.ctx = fitz.Context(fitz.FZ_STORE_DEFAULT)
        try:
            self.document = fitz.Document(self.filepath)
            self.n_pages = self.document.pageCount
        except IOError:
            self.Destroy()
            raise IOError('cannot open file %s' % docfile)
        self.set_outline()
        if not self.current_page_idx < self.n_pages:
            self.current_page_idx = self.n_pages - 1
        self.doc_scroll = r_pdf.DocScroll(self, self.current_page_idx);

    def epub_init_doc(self):
        try:
            import epub
        except ImportError:
            self.Destroy()
            raise IOError('Install python-epub for EPUB files')
        else:
            import r_epub

            extract_path = os.path.join(os.path.expanduser('~/.rbook/cache/'),
                                        str(os.stat(self.filepath).st_ino))
            zipfile.ZipFile(self.filepath, 'r').extractall(extract_path)
            self.book = epub.open_epub(self.filepath)
            self.extract_path = os.path.join(extract_path, 
                                             os.path.dirname(self.book.opf_path))
            chaps = self.book.opf.spine.itemrefs
            self.items = [self.book.opf.manifest[chap[0]].href for chap in chaps]
            self.n_pages = len(self.items)
            if not self.current_page_idx < self.n_pages:
                self.current_page_idx = self.n_pages - 1
            os.chdir(self.extract_path)                                       
            self.doc_scroll = r_epub.DocScroll(self, self.current_page_idx)

    def epub_set_outline(self):
        nav_point = self.book.toc.nav_map.nav_point
        page_target = self.book.toc.page_list.page_target
        nav_lists = self.book.toc.nav_lists
        root = self.outline_tree.AddRoot('/')
        #nav_map
        if len(page_target) == 0 and len(nav_lists) == 0:                
               content = root
        else:
           content = self.outline_tree.AppendItem(root, 'Content')
           self.outline_tree.SetItemData(content, None)
        self.epub_init_outline_tree(nav_point, content)
        #page_list
        if len(page_target) > 0:
           pagelist = self.outline_tree.AppendItem(root, 'PageList')
           self.outline_tree.SetItemData(pagelist, None)
           for target in page_target:
               child = self.outline_tree.AppendItem(pagelist, target.value)
               self.outline_tree.SetItemData(child, 
                                             wx.TreeItemData(
                                                 self.epub_find_page_idx(target.src)))
        #nav_lists
        if len(nav_lists) > 0:
            navlists = self.outline_tree.AppendItem(root, 'NavLists')
            self.outline_tree.SetItemData(navlists, None)
            for navlist in nav_lists:
                for target in navlist.navtarget:
                    child = self.outline_tree.AppendItem(navlists, target.value)
                    self.outline_tree.SetItemData(child, 
                                             wx.TreeItemData(
                                                 self.epub_find_page_idx(target.src)))

    def epub_find_page_idx(self, src):
        addr = src.split('#')
        html = addr[0]
        try:
            idx = self.items.index(html)
        except ValueError:
            return None
        else:
            if len(addr) > 1:
                return (idx, addr[1])
            else:
                return (idx, None)

    def epub_init_outline_tree(self, nav_points, parent):
        for point in nav_points:
            child = self.outline_tree.AppendItem(parent, point.labels[0][0])
            self.outline_tree.SetItemData(child, 
                                     wx.TreeItemData(
                                         self.epub_find_page_idx(point.src)))
            self.epub_init_outline_tree(point.nav_point, child)

    def set_outline(self):
        if self.ext == '.DJVU':
            item = iter(self.document.outline.sexpr)
            try:
                if item.next().as_string() == 'bookmarks':
                    root = self.outline_tree.AddRoot('/')
                    try:
                        self.djvu_init_outline_tree(item, root)
                    except StopIteration:
                        pass
                self.show_outline = 1
            except StopIteration:
                self.show_outline = 0
        elif self.ext == '.PDF':
            outline = self.document.outline
            if not outline is None:
                root = self.outline_tree.AddRoot('/')
                self.pdf_init_outline_tree(outline, root)
                self.show_outline *= 1
            else:
                self.show_outline *= 0
        else:
            self.show_outline *= 1
            self.epub_set_outline()

    def on_sel_changed(self, event):
        item = event.GetItem()
        if item.IsOk():
            data = self.outline_tree.GetItemData(item).GetData()
            if self.ext == '.EPUB' and data:
                self.set_current_page(data[0], data[1])
            elif self.ext == '.DJVU':
                self.set_current_page(data)
            elif self.ext == '.PDF':
                self.set_current_page(data[0])
                if data[1] & fitz.fz_link_flag_t_valid:
                    pos = self.doc_scroll.trans.transform_point(data[2])
                    self.doc_scroll.Scroll(-1, (self.doc_scroll.height-pos.y)/self.doc_scroll.scroll_unit)

    def djvu_init_outline_tree(self, item, parent):
        ii = iter(item.next())
        try:
            child = self.outline_tree.AppendItem(parent, ii.next().value)
            page_num = ii.next().value
            try:
                if page_num[0] == '#':
                    num = int(page_num[1:]) - 1
            except IndexError:
                num = -1

            self.outline_tree.SetItemData(child, wx.TreeItemData(num))
            self.djvu_init_outline_tree(ii, child)
        except StopIteration:
            self.djvu_init_outline_tree(item, parent)

    def pdf_init_outline_tree(self, outline_item, parent):
        child = self.outline_tree.AppendItem(parent, outline_item.title)
        self.outline_tree.SetItemData(child, 
                                      wx.TreeItemData(
                                         (outline_item.dest.page,
                                          outline_item.dest.flags,
                                          outline_item.dest.lt)))
        downitem = outline_item.down
        if not downitem is None:
            self.pdf_init_outline_tree(downitem, child)
        nextitem = outline_item.next
        if not nextitem is None:
            self.pdf_init_outline_tree(nextitem, parent)

    def on_refresh(self):
        if self.ext == '.EPUB':
            return

        self.doc_scroll.on_refresh()

        self.outline_tree.DeleteAllItems()
        self.set_outline()

        if self.n_pages > self.current_page_idx:
            current_page_idx = self.current_page_idx
        else:
            current_page_idx = self.n_pages - 1
        
        self.init()
        pos = self.doc_scroll.GetViewStart()
        self.set_current_page(current_page_idx)
        self.doc_scroll.Scroll(pos[0], pos[1])
        self.main_frame.update_statusbar(self)

    def init(self):
        self.marks = {}
        self.page_back = []
        self.page_fwd = []
        self.prev_cmd = ''
        self.search_text = ''
        self.hit = -1
        self.ori = 1

    def search(self, ori):
        self.hit = self.doc_scroll.search_in_page(self.current_page_idx, 
                                                  self.search_text, 
                                                  ori)

    def search_next(self, ori):
        if self.search_text == '':
            pass
        elif self.hit < 0:
            self.main_frame.statusbar.SetStatusText('!Error: "%s" not found' % 
                                                    self.search_text)
        else:
            if self.ori > 0:
                self.main_frame.statusbar.SetStatusText('%s%s' % ('/',
                                                        self.search_text))
            else:
                self.main_frame.statusbar.SetStatusText('%s%s' % ('?',
                                                        self.search_text))
            self.hit = self.doc_scroll.search_next(self.current_page_idx, 
                                            self.search_text, 
                                            ori*self.ori)
        
    def set_current_page(self, current_page_idx, scroll=None, scale=None):
        self.doc_scroll.set_current_page(current_page_idx, scroll=scroll, scale=scale)
        self.current_page_idx = current_page_idx
        self.main_frame.update_statusbar(self)

    def on_page_back(self):
        if len(self.page_back) > 0:
            self.page_fwd.append(self.current_page_idx)
            self.set_current_page(self.page_back.pop())

    def on_page_fwd(self):
        if len(self.page_fwd) > 0:
            self.page_back.append(self.current_page_idx)
            self.set_current_page(self.page_fwd.pop())

    def on_fit_width(self):
        if self.ext == '.EPUB':
            return
        self.scale = self.fit_width_scale()
        self.main_frame.update_statusbar(self)

    def on_zoom_in(self):
        try:
            self.set_scale(self.scale+0.2)
        except ValueError:
            raise ValueError('cannot zoom in anymore')
            
    def on_zoom_out(self):
        try:
            self.set_scale(self.scale-0.2)
        except ValueError:
            raise ValueError('cannot zoom out anymore')

    def set_scale(self, scale):
        if scale > self.min_scale and scale < self.max_scale:
            self.scale = scale
            self.doc_scroll.set_scale(scale)
            self.main_frame.update_statusbar(self)
        else:
            raise ValueError('%s is either too large or too small' % str(scale))

    def on_prev_page(self):
        try:
            self.change_page(self.current_page_idx-1)
        except ValueError:
            raise ValueError('already the first page')

    def on_next_page(self):
        try:
            self.change_page(self.current_page_idx+1)
        except ValueError:
            raise ValueError('already the last page')

    def retrive_mark(self, code):
        if code in self.marks:
            mark = (self.current_page_idx, self.scale, self.doc_scroll.GetViewStart())
            page_idx, scale, point = self.marks[code]
            self.scale = scale
            if mark[0] != page_idx:
                self.page_back.append(self.current_page_idx)
                self.page_fwd = []
                self.set_current_page(page_idx, point, scale=scale)
            else:
                self.doc_scroll.set_scale(scale, scroll=point)
            self.main_frame.update_statusbar(self)
            self.marks[96] = mark

    def change_page(self, page_idx):
        if page_idx > -1 and page_idx < self.n_pages:
            self.page_back.append(self.current_page_idx)
            self.page_fwd = []
            self.set_current_page(page_idx)
        else:
            raise ValueError('%s is not a valid page number' % str(page_idx+1))
    
    def repeat_cmd(self):
        if len(self.prev_cmd) > 0:
            eval(self.prev_cmd)

    def save_page(self):
        self.main_frame.pages[self.inode] = (self.filepath, 
                                             self.current_page_idx, 
                                             self.scale, 
                                             self.view_start, 
                                             self.show_outline)

    def fit_width_scale(self):
        width = self.doc_scroll.orig_width

        if not self.show_outline == 1:
            w_width, w_height = self.main_frame.GetSize()
        else:
            w_width, w_height = self.GetWindow2().GetSize()
        scale = round((w_width-self.doc_scroll.vscroll_wid)/width-0.005, 2)
        if scale < self.min_scale or scale > self.max_scale:
            scale = 1.0
        self.doc_scroll.set_scale(scale)
        return scale

    def horizontal_scroll(self, move):
        x = self.doc_scroll.GetViewStart()[0] + move
        self.doc_scroll.Scroll(x, -1)

    def vertical_scroll(self, move):
        bottom = int(round((self.doc_scroll.GetVirtualSize()[1] - 
                            self.doc_scroll.GetClientSize()[1])/self.doc_scroll.scroll_unit))
        y = self.doc_scroll.GetViewStart()[1] + move
        try:
            if y < 0:
                if self.doc_scroll.GetViewStart()[1] > 0:
                    self.doc_scroll.Scroll(-1, 0)
                else:
                    if self.current_page_idx == 0:
                        pass
                    else:
                        self.on_prev_page()
                        self.doc_scroll.Scroll(0, self.doc_scroll.GetScrollRange(wx.VERTICAL))
            elif y > bottom:
                if self.doc_scroll.GetViewStart()[1] < bottom:
                    self.doc_scroll.Scroll(-1, self.doc_scroll.GetScrollRange(wx.VERTICAL)) 
                else:
                    self.on_next_page()
            else:
                self.doc_scroll.Scroll(-1, y)
        except ValueError:
            pass
