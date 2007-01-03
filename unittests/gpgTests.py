# Copyright (C) 2006  Lars Wirzenius <liw@iki.fi>
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


"""Unit tests for obnam.gpg."""


import os
import shutil
import tempfile
import unittest


import obnam


class GpgTests(unittest.TestCase):

    def test(self):
        block = "pink"
        config = obnam.config.default_config()
        config.set("backup", "gpg-home", "sample-gpg-home")
        config.set("backup", "gpg-encrypt-to", "490C9ED1")
        config.set("backup", "gpg-sign-with", "490C9ED1")
        
        encrypted = obnam.gpg.encrypt(config, block)
        self.failIf(block in encrypted)
        
        decrypted = obnam.gpg.decrypt(config, encrypted)
        self.failUnlessEqual(block, decrypted)