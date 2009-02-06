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


import obnamlib


class Component(object):

    """A piece of data inside an obnamlib.Object.

    Instances of this class store data inside obnamlib.Object objects.
    An Object is a list of Components, and a Component is either a string
    or a list of Components. The distinction between Object and Component
    makes it easier to encode and decode things for on-disk storage:
    Object needs more meta data than Component, for example every Object
    has a unique id, but a Component does not.

    A component has a kind, and the kind determines whether it contains
    a single octet string or other components (never both).

    """

    def __init__(self, kind, string=None, children=None):
        self.kind = kind
        if string is not None:
            self.assert_is_string_valued()
        self._string = string or ""
        if children is not None:
            self.assert_is_composite()
        self._children = children or []

    def assert_is_string_valued(self):
        if (not obnamlib.cmp_kinds.is_plain(self.kind) and
            not obnamlib.cmp_kinds.is_ref(self.kind)):
            raise obnamlib.Exception("Using string value of "
                                     "non-plain component.")

    def get_string(self):
        self.assert_is_string_valued()
        return self._string

    def set_string(self, string):
        self.assert_is_string_valued()
        if type(string) != str:
            raise obnamlib.Exception("Cannot set string value to type %s" %
                                     type(string))
        self._string = string

    string = property(fget=get_string, fset=set_string, 
                      doc="String value of plain component.")

    def assert_is_composite(self):
        if not obnamlib.cmp_kinds.is_composite(self.kind):
            raise obnamlib.Exception("Using children of non-composite "
                                     "Component.")
    
    def get_children(self):
        self.assert_is_composite()
        return self._children

    def set_children(self, children):
        self.assert_is_composite()
        self._children = children

    children = property(fget=get_children, fset=set_children,
                        doc="Children of composite component.")

    def find(self, kind=None):
        """Find subcomponents of a given kind."""
        return [c for c in self.children if c.kind == kind]

    def find_strings(self, **kwargs):
        """Like find, but return string values of matches."""
        return [c.string for c in self.find(**kwargs)]

    def first(self, **kwargs):
        """Like find, but return first matching sub-component, or None."""
        list = self.find(**kwargs)
        if list:
            return list[0]
        else:
            return None

    def first_string(self, **kwargs):
        """Like first, but return string value if found."""
        c = self.first(**kwargs)
        if c:
            return c.string
        else:
            return None

    def extract(self, **kwargs):
        """Like find, but remove the matches, as well as returning them."""
        list = self.find(**kwargs)
        for cmp in list:
            self.children.remove(cmp)
        return list


class StringComponent(Component):

    """Base class for components that only contain a string."""
    
    def __init__(self, string):
        Component.__init__(self, kind=self.string_kind, string=string)
