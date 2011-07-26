# Copyright (C) 2009, 2011  Lars Wirzenius
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import cliapp
import logging
import os
import socket
import tracing
import sys

import obnamlib


class App(cliapp.Application):

    '''Main program for backup program.'''
    
    def add_settings(self):
        self.settings.string(['repository', 'r'], 'name of backup repository')

        self.settings.string(['client-name'], 'name of client (%default)',
                           default=self.deduce_client_name())

        self.settings.boolean(['pretend', 'dry-run', 'no-act'],
                           'do not write or remove anything, just '
                                'pretend to do that')

        self.settings.bytesize(['node-size'],
                             'size of B-tree nodes on disk '
                                 '(default: %default)',
                              default=obnamlib.DEFAULT_NODE_SIZE)

        self.settings.bytesize(['chunk-size'],
                            'size of chunks of file data backed up '
                                 '(default: %default)',
                             default=obnamlib.DEFAULT_CHUNK_SIZE)

        self.settings.bytesize(['upload-queue-size'],
                            'length of upload queue for B-tree nodes '
                                 '(default: %default)',
                            default=obnamlib.DEFAULT_UPLOAD_QUEUE_SIZE)

        self.settings.bytesize(['lru-size'],
                             'size of LRU cache for B-tree nodes '
                                 '(default: %default)',
                             default=obnamlib.DEFAULT_LRU_SIZE)

        self.settings.choice(['dump-memory-profile'],
                           ['simple', 'none', 'meliae', 'heapy'],
                           'make memory profiling dumps '
                                'after each checkpoint and at end? '
                                'set to none, simple, meliae, or heapy '
                                '(default: %default)')

        self.settings.string_list(['trace'],
                                'add to filename patters for which trace '
                                'debugging logging happens')

        
        self.settings.integer(['idpath-depth'],
                              'depth of chunk id mapping',
                              default=obnamlib.IDPATH_DEPTH)
        self.settings.integer(['idpath-bits'],
                              'chunk id level size',
                              default=obnamlib.IDPATH_BITS)
        self.settings.integer(['idpath-skip'],
                              'chunk id mapping lowest bits skip',
                              default=obnamlib.IDPATH_SKIP)

        # The following needs to be done here, because it needs
        # to be done before option processing. This is a bit ugly,
        # but the best we can do with the current cliapp structure.
        # Possibly cliapp will provide a better hook for us to use
        # later on, but this is reality now.

        self.pm = obnamlib.PluginManager()
        self.pm.locations = [self.plugins_dir()]
        self.pm.plugin_arguments = (self,)
        
        self.setup_hooks()

        self.fsf = obnamlib.VfsFactory()

        self.pm.load_plugins()
        self.pm.enable_plugins()
        self.hooks.call('plugins-loaded')

    def deduce_client_name(self):
        return socket.gethostname()

    def setup_hooks(self):
        self.hooks = obnamlib.HookManager()
        self.hooks.new('plugins-loaded')
        self.hooks.new('config-loaded')
        self.hooks.new('shutdown')

        # The Repository class defines some hooks, but the class
        # won't be instantiated until much after plugins are enabled,
        # and since all hooks must be defined when plugins are enabled,
        # we create one instance here, which will immediately be destroyed.
        # FIXME: This is fugly.
        obnamlib.Repository(None, 1000, 1000, 100, self.hooks, 10, 10, 10)

    def plugins_dir(self):
        return os.path.join(os.path.dirname(obnamlib.__file__), 'plugins')

    def process_args(self, args):
        for pattern in self.settings['trace']:
            tracing.trace_add_pattern(pattern)
        self.hooks.call('config-loaded')
        logging.info('Obnam %s starts' % obnamlib.__version__)
        cliapp.Application.process_args(self, args)
        self.hooks.call('shutdown')
        logging.info('Obnam ends')

    def open_repository(self, create=False): # pragma: no cover
        logging.debug('opening repository (create=%s)' % create)
        repopath = self.settings['repository']
        repofs = self.fsf.new(repopath, create=create)
        repofs.connect()
        return obnamlib.Repository(repofs, 
                                    self.settings['node-size'],
                                    self.settings['upload-queue-size'],
                                    self.settings['lru-size'],
                                    self.hooks,
                                    self.settings['idpath-depth'],
                                    self.settings['idpath-bits'],
                                    self.settings['idpath-skip'])

    def require(self, setting):
        '''Make sure the named option is set.'''
        
        if not self.settings[setting]:
            raise obnamlib.Error('you must use option --%s' % setting)

