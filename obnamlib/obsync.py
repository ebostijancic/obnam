# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
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


import hashlib
import obnamlib
import zlib


class RsyncLookupTable(object):

    def __init__(self, compute_weak, compute_strong, checksums):
        self.compute_weak = compute_weak
        self.compute_strong = compute_strong
        self.dict = {}
        for block_number, c in enumerate(checksums):
            weak = c.first_string(kind=obnamlib.ADLER32)
            strong = c.first_string(kind=obnamlib.MD5)
            if weak not in self.dict:
                self.dict[weak] = dict()
            self.dict[weak][strong] = block_number

    def __getitem__(self, block_data):
        weak = str(self.compute_weak(block_data))
        subdict = self.dict.get(weak)
        if subdict:
            strong = str(self.compute_strong(block_data))
            return subdict.get(strong)
        return None


class Obsync(object):

    """A pure-Python implementation of the rsync algorithm.

    See http://www.samba.org/rsync/tech_report/ for an explanation of the
    rsync algorithm.

    This is not at all compatible with rsync the program, or rdiff,
    or librsync, or any other implementation of the rsync algorithm. It
    does not even implement the algorithm as described in the original
    paper. This is mostly because a) Python sucks as bit twiddling kinds
    of things, so we have chosen approaches that are fast in Python, and
    b) this is meant to be part of Obnam, a backup program, which changes
    the requirements of generic rsync a little bit.

    """
    
    def weak_checksum(self, data):
        """Compute weak checksum for data.
        
        Return obnamlib.Adler32 component.
        
        """
        
        return obnamlib.Adler32(str(zlib.adler32(data)))

    def strong_checksum(self, data):
        """Compute weak checksum for data.
        
        Return obnamlib.Md5 component.
        
        """

        return obnamlib.Md5(hashlib.md5(data).digest())

    def block_signature(self, block_data):
        """Compute rsync signature for a given block of data.
        
        Return an obnamlib.Checksums component.
        
        Assume the block is of whatever size the signatures should be
        computed for. It is the caller's responsibility to make sure
        all blocks in a signature file are of the same size.
        
        """
        
        weak = self.weak_checksum(block_data)
        strong = self.strong_checksum(block_data)
        return obnamlib.Checksums([weak, strong])
        
    def file_signature(self, f, block_size):
        """Compute signatures for a file.
        
        Return a list of obnamlib.SyncSignature objects.
        
        """
        
        sigs = []
        while True:
            block = f.read(block_size)
            if not block:
                break
            sigs.append(self.block_signature(block))

        return sigs

    def make_signature(self, obj_id, f, block_size):
        """Create an rsync signature for a file."""
        
        checksums = self.file_signature(f, block_size)
        return obnamlib.RsyncSig(obj_id, block_size=block_size, 
                                 checksums=checksums)

    def file_delta(self, rsyncsig, new_file):
        """Compute delta from RsyncSig to new_file.
        
        Return list of obnamlib.FileChunk and obnamlib.OldFileSubString
        objects.
        
        """

        block_size = rsyncsig.block_size
        lookup_table = RsyncLookupTable(self.weak_checksum,
                                        self.strong_checksum,
                                        rsyncsig.checksums)
        output = []
        
        block_data = new_file.read(block_size)
        while block_data:
            block_number = lookup_table[block_data]
            if block_number is None:
                literal = obnamlib.FileChunk(block_data[0])
                output.append(literal)
                block_data = block_data[1:]
                byte = new_file.read(1)
                if byte:
                    block_data += byte
            else:
                offset = block_number * block_size
                ofss = obnamlib.OldFileSubString(offset, block_size)
                output.append(ofss)
                block_data = new_file.read(block_size)

        return output

