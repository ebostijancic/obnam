# Copyright (C) 2008  Lars Wirzenius <liw@iki.fi>
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


"""Unit tests for abstraction for storing backup data, for Obnam."""


import os
import shutil
import socket
import tempfile
import unittest

import obnam


class StoreTests(unittest.TestCase):

    def setUp(self):
        context = obnam.context.Context()
        context.cache = obnam.cache.Cache(context.config)
        context.be = obnam.backend.init(context.config, context.cache)
        self.store = obnam.Store(context)

    def tearDown(self):
        shutil.rmtree(self.store._context.config.get("backup", "store"),
                      ignore_errors=True)
        shutil.rmtree(self.store._context.config.get("backup", "cache"),
                      ignore_errors=True)

    def testReturnsNoneWhenNoHostBlockExists(self):
        self.failUnlessEqual(self.store.get_host_block(), None)

    def testReturnsAnActualHostBlockAfterFetch(self):
        self.store.fetch_host_block()
        host = self.store.get_host_block()
        self.failUnless(isinstance(host, obnam.obj.HostBlockObject))

    def testReturnsActualHostBlockWhenOneExists(self):
        self.store.fetch_host_block()
        self.store.commit_host_block([])
        
        context = obnam.context.Context()
        context.be = obnam.backend.init(context.config, context.cache)
        store = obnam.Store(context)
        store.fetch_host_block()
        host = store.get_host_block()
        self.failUnless(isinstance(host, obnam.obj.HostBlockObject))

    def testReplacesHostObjectInMemory(self):
        self.store.fetch_host_block()
        host = self.store.get_host_block()
        self.store.commit_host_block([])
        self.failIfEqual(self.store.get_host_block(), host)

    def testCreatesNewHostBlockWhenNoneExists(self):
        self.store.fetch_host_block()
        host = self.store.get_host_block()
        self.failUnlessEqual(host.get_id(), socket.gethostname())
        self.failUnlessEqual(host.get_generation_ids(), [])
        self.failUnlessEqual(host.get_map_block_ids(), [])
        self.failUnlessEqual(host.get_contmap_block_ids(), [])

    def testLoadsActualHostBlockWhenOneExists(self):
        context = obnam.context.Context()
        cache = obnam.cache.Cache(context.config)
        context.be = obnam.backend.init(context.config, context.cache)
        host_id = context.config.get("backup", "host-id")
        temp = obnam.obj.HostBlockObject(host_id=host_id,
                                         gen_ids=["pink", "pretty"])
        obnam.io.upload_host_block(context, temp.encode())
        
        self.store.fetch_host_block()
        host = self.store.get_host_block()
        self.failUnlessEqual(host.get_generation_ids(), ["pink", "pretty"])

    def testGettingNonExistentObjectRaisesException(self):
        self.failUnlessRaises(obnam.exception.ObnamException,
                              self.store.get_object, "pink")

    def testAddsObjectToStore(self):
        o = obnam.obj.GenerationObject(id="pink")
        self.store.fetch_host_block()
        self.store.queue_object(o)
        self.store.commit_host_block([])
        
        context2 = obnam.context.Context()
        context2.cache = obnam.cache.Cache(context2.config)
        context2.be = obnam.backend.init(context2.config, context2.cache)
        store2 = obnam.Store(context2)
        store2.fetch_host_block()
        store2.load_maps()
        self.failUnless(store2.get_object(o.get_id()))

    def mock_queue_object(self, object):
        self.queued_objects.append(object)
        
    def testAddsSeveralObjectsToStore(self):
        objs = [None, True, False]
        self.queued_objects = []
        self.store.queue_object = self.mock_queue_object
        self.store.queue_objects(objs)
        self.failUnlessEqual(objs, self.queued_objects)


class StoreMapTests(unittest.TestCase):

    def setUp(self):
        # First, set up two mappings.

        context = obnam.context.Context()
        context.cache = obnam.cache.Cache(context.config)
        context.be = obnam.backend.init(context.config, context.cache)

        obnam.map.add(context.map, "pink", "pretty")
        obnam.map.add(context.contmap, "black", "beautiful")

        map_id = context.be.generate_block_id()
        map_block = obnam.map.encode_new_to_block(context.map, map_id)
        context.be.upload_block(map_id, map_block, True)

        contmap_id = context.be.generate_block_id()
        contmap_block = obnam.map.encode_new_to_block(context.contmap, 
                                                      contmap_id)
        context.be.upload_block(contmap_id, contmap_block, True)

        host_id = context.config.get("backup", "host-id")
        host = obnam.obj.HostBlockObject(host_id=host_id,
                                         map_block_ids=[map_id],
                                         contmap_block_ids=[contmap_id])
        obnam.io.upload_host_block(context, host.encode())

        # Then set up the real context and app.

        self.context = obnam.context.Context()
        self.context.cache = obnam.cache.Cache(self.context.config)
        self.context.be = obnam.backend.init(self.context.config, 
                                             self.context.cache)
        self.store = obnam.Store(self.context)
        self.store.fetch_host_block()

    def tearDown(self):
        shutil.rmtree(self.store._context.config.get("backup", "store"),
                      ignore_errors=True)
        shutil.rmtree(self.store._context.config.get("backup", "cache"),
                      ignore_errors=True)

    def testHasNoMapsLoadedByDefault(self):
        self.failUnlessEqual(obnam.map.count(self.context.map), 0)

    def testHasNoContentMapsLoadedByDefault(self):
        self.failUnlessEqual(obnam.map.count(self.context.contmap), 0)

    def testLoadsMapsWhenRequested(self):
        self.store.load_maps()
        self.failUnlessEqual(obnam.map.count(self.context.map), 1)

    def testLoadsContentMapsWhenRequested(self):
        self.store.load_content_maps()
        self.failUnlessEqual(obnam.map.count(self.context.contmap), 1)

    def testAddsNoNewMapsWhenNothingHasChanged(self):
        self.store.update_maps()
        self.failUnlessEqual(obnam.map.count(self.context.map), 0)

    def testAddsANewMapsWhenSomethingHasChanged(self):
        obnam.map.add(self.context.map, "pink", "pretty")
        self.store.update_maps()
        self.failUnlessEqual(obnam.map.count(self.context.map), 1)

    def testAddsNoNewContentMapsWhenNothingHasChanged(self):
        self.store.update_content_maps()
        self.failUnlessEqual(obnam.map.count(self.context.contmap), 0)

    def testAddsANewContentMapsWhenSomethingHasChanged(self):
        obnam.map.add(self.context.contmap, "pink", "pretty")
        self.store.update_content_maps()
        self.failUnlessEqual(obnam.map.count(self.context.contmap), 1)


class StorePathnameParserTests(unittest.TestCase):

    def setUp(self):
        context = obnam.context.Context()
        self.store = obnam.Store(context)

    def testReturnsRootForRoot(self):
        self.failUnlessEqual(self.store.parse_pathname("/"), ["/"])

    def testReturnsDotForDot(self):
        self.failUnlessEqual(self.store.parse_pathname("."), ["."])

    def testReturnsItselfForSingleElement(self):
        self.failUnlessEqual(self.store.parse_pathname("foo"), ["foo"])

    def testReturnsListOfPartsForMultipleElements(self):
        self.failUnlessEqual(self.store.parse_pathname("foo/bar"), 
                             ["foo", "bar"])

    def testReturnsListOfPartsFromRootForAbsolutePathname(self):
        self.failUnlessEqual(self.store.parse_pathname("/foo/bar"), 
                             ["/", "foo", "bar"])

    def testIgnoredTrailingSlashIfNotRoot(self):
        self.failUnlessEqual(self.store.parse_pathname("foo/bar/"), 
                             ["foo", "bar"])


class StoreLookupTests(unittest.TestCase):

    def create_data_dir(self):
        dirname = tempfile.mkdtemp()
        file(os.path.join(dirname, "file"), "w").close()
        os.mkdir(os.path.join(dirname, "dir1"))
        os.mkdir(os.path.join(dirname, "dir1", "dir2"))
        file(os.path.join(dirname, "dir1", "dir2", "file"), "w").close()
        return dirname

    def create_context(self):
        context = obnam.context.Context()
        context.cache = obnam.cache.Cache(context.config)
        context.be = obnam.backend.init(context.config, context.cache)
        return context

    def setUp(self):
        self.datadir = self.create_data_dir()
        self.dirbasename = os.path.basename(self.datadir)

        app = obnam.Application(self.create_context())
        app.load_host()
        gen = app.backup([self.datadir])
        app.get_store().commit_host_block([gen])
        
        self.store = obnam.Store(self.create_context())
        self.store.fetch_host_block()
        self.store.load_maps()
        gen_ids = self.store.get_host_block().get_generation_ids()
        self.gen = self.store.get_object(gen_ids[0])

    def tearDown(self):
        shutil.rmtree(self.datadir)
        shutil.rmtree(self.store._context.config.get("backup", "store"))

    def testFindsBackupRoot(self):
        dir = self.store.lookup_dir(self.gen, self.dirbasename)
        self.failUnless(dir.get_name(), self.dirbasename)

    def testFindsFirstSubdir(self):
        pathname = os.path.join(self.dirbasename, "dir1")
        dir = self.store.lookup_dir(self.gen, pathname)
        self.failUnless(dir.get_name(), "dir1")

    def testFindsSecondSubdir(self):
        pathname = os.path.join(self.dirbasename, "dir1", "dir2")
        dir = self.store.lookup_dir(self.gen, pathname)
        self.failUnless(dir.get_name(), "dir2")

    def testDoesNotFindNonExistentDir(self):
        self.failUnlessEqual(self.store.lookup_dir(self.gen, "notexist"),
                             None)

    def testDoesNotFindNonExistentFile(self):
        self.failUnlessEqual(self.store.lookup_file(self.gen, "notexist"),
                             None)
