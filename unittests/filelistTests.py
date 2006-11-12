import os
import unittest


import obnam


class FileComponentTests(unittest.TestCase):

    def testCreate(self):
        c = obnam.filelist.create_file_component(".", "pink")
        self.check(c)

    def testCreateFromStatResult(self):
        st = os.lstat(".")
        c = obnam.filelist.create_file_component_from_stat(".", st, "pink")
        self.check(c)
        
    def check(self, c):
        self.failIfEqual(c, None)
        subs = obnam.cmp.get_subcomponents(c)
        self.failUnlessEqual(
          obnam.cmp.first_string_by_kind(subs, obnam.cmp.CMP_FILENAME),
          ".")

        st = os.lstat(".")
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.CMP_ST_MODE),
          st.st_mode)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.CMP_ST_INO),
          st.st_ino)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.CMP_ST_DEV),
          st.st_dev)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.CMP_ST_NLINK),
          st.st_nlink)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.CMP_ST_UID),
          st.st_uid)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.CMP_ST_GID),
          st.st_gid)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.CMP_ST_SIZE),
          st.st_size)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.CMP_ST_ATIME),
          st.st_atime)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.CMP_ST_MTIME),
          st.st_mtime)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.CMP_ST_CTIME),
          st.st_ctime)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.CMP_ST_BLOCKS),
          st.st_blocks)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, 
            obnam.cmp.CMP_ST_BLKSIZE),
          st.st_blksize)

        self.failUnlessEqual(
            obnam.cmp.first_string_by_kind(subs, obnam.cmp.CMP_CONTREF),
            "pink")


class FilelistTests(unittest.TestCase):

    def testCreate(self):
        fl = obnam.filelist.create()
        self.failUnlessEqual(obnam.filelist.num_files(fl), 0)

    def testAddFind(self):
        fl = obnam.filelist.create()
        obnam.filelist.add(fl, ".", "pink")
        self.failUnlessEqual(obnam.filelist.num_files(fl), 1)
        c = obnam.filelist.find(fl, ".")
        self.failUnlessEqual(obnam.cmp.get_kind(c), obnam.cmp.CMP_FILE)

    def testAddFileComponent(self):
        fl = obnam.filelist.create()
        fc = obnam.filelist.create_file_component(".", "pink")
        obnam.filelist.add_file_component(fl, ".", fc)
        self.failUnlessEqual(obnam.filelist.num_files(fl), 1)
        c = obnam.filelist.find(fl, ".")
        self.failUnlessEqual(obnam.cmp.get_kind(c), obnam.cmp.CMP_FILE)

    def testToFromObject(self):
        fl = obnam.filelist.create()
        obnam.filelist.add(fl, ".", "pretty")
        o = obnam.filelist.to_object(fl, "pink")
        self.failUnlessEqual(obnam.obj.get_kind(o), 
                             obnam.obj.OBJ_FILELIST)
        self.failUnlessEqual(obnam.obj.get_id(o), "pink")
        
        fl2 = obnam.filelist.from_object(o)
        self.failIfEqual(fl2, None)
        self.failUnlessEqual(type(fl), type(fl2))
        self.failUnlessEqual(obnam.filelist.num_files(fl2), 1)

        c = obnam.filelist.find(fl2, ".")
        self.failIfEqual(c, None)
        self.failUnlessEqual(obnam.cmp.get_kind(c), obnam.cmp.CMP_FILE)


class FindTests(unittest.TestCase):

    def testFindInodeSuccessful(self):
        pathname = "Makefile"
        fl = obnam.filelist.create()
        obnam.filelist.add(fl, pathname, "pink")
        st = os.lstat(pathname)
        c = obnam.filelist.find_matching_inode(fl, pathname, st)
        subs = obnam.cmp.get_subcomponents(c)
        self.failUnlessEqual(
          obnam.cmp.first_varint_by_kind(subs, obnam.cmp.CMP_ST_MTIME),
          st.st_mtime)

    def testFindInodeUnsuccessful(self):
        pathname = "Makefile"
        fl = obnam.filelist.create()
        obnam.filelist.add(fl, pathname, "pink")
        st = os.lstat(".")
        c = obnam.filelist.find_matching_inode(fl, pathname, st)
        self.failUnlessEqual(c, None)
