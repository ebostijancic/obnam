# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import unittest
import mox

import obnamlib


class DummyObject(object):

    """Dummy object for aiding in some unit tests."""

    def __init__(self, id):
        self.id = id


class BackupCommandTests(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()
        self.cmd = obnamlib.BackupCommand()
        self.cmd.store = self.mox.CreateMock(obnamlib.Store)
        self.cmd.fs = self.mox.CreateMock(obnamlib.VirtualFileSystem)

    def test_backs_up_new_file_correctly(self):
        f = self.mox.CreateMock(file)
        fc = self.mox.CreateMock(obnamlib.FileContents)
        fc.id = "contentsid"
        part = self.mox.CreateMock(obnamlib.FilePart)
        part.id = "partid"

        self.cmd.store.new_object(kind=obnamlib.FILECONTENTS).AndReturn(fc)
        self.cmd.fs.open("foo", "r").AndReturn(f)
        f.read(self.cmd.PART_SIZE).AndReturn("data")
        self.cmd.store.new_object(kind=obnamlib.FILEPART).AndReturn(part)
        self.cmd.store.put_object(part)
        fc.add(part.id)
        f.read(self.cmd.PART_SIZE).AndReturn(None)
        f.close()
        self.cmd.store.put_object(fc)

        self.mox.ReplayAll()
        new_file = self.cmd.backup_new_file("foo")
        self.mox.VerifyAll()
        self.assertEqual(new_file, fc)

    def test_backs_up_filegroup_correctly(self):
        self.cmd.backup_new_file = lambda relative_path: DummyObject("id")

        fg = self.mox.CreateMock(obnamlib.FileGroup)
        fg.components = self.mox.CreateMock(list)

        self.cmd.store.new_object(kind=obnamlib.FILEGROUP).AndReturn(fg)
        fg.components.append(mox.IsA(obnamlib.Component))
        fg.components.append(mox.IsA(obnamlib.Component))
        self.cmd.store.put_object(fg)

        self.mox.ReplayAll()
        ret = self.cmd.backup_new_files_as_group(["foo", "bar"])
        self.mox.VerifyAll()
        self.assertEqual(ret, fg)

    def test_backs_up_directory_correctly(self):
        dir = self.mox.CreateMock(obnamlib.Dir)
        self.cmd.backup_new_files_as_group = lambda: DummyObject("fg")
        subdirs = [DummyObject(id) for id in ["dir1", "dir2"]]

        self.cmd.store.new_object(obnamlib.DIR).AndReturn(dir)
        self.cmd.store.put_object(dir)

        self.mox.ReplayAll()
        ret = self.cmd.backup_dir("foo", subdirs, ["file1", "file2"])
        self.mox.VerifyAll()
        self.assertEqual(ret, dir)
        self.assertEqual(ret.name, "foo")
        self.assertEqual(ret.dirrefs, ["dir1", "dir2"])
        self.assertEqual(ret.fgrefs, ["fg"])

    def test_backs_up_empty_directory_correctly(self):
        self.cmd.backup_new_files_as_group = lambda: None

        ret = self.cmd.backup_dir("foo", [], [])
        self.assertEqual(ret.dirrefs, [])
        self.assertEqual(ret.fgrefs, [])
