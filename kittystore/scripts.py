# -*- coding: utf-8 -*-

# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""
Various utility scripts.

Author: Aurelien Bompard <abompard@fedoraproject.org>
"""


from optparse import OptionParser

from kittystore import get_store


def updatedb():
    parser = OptionParser(usage="%prog -s store_url")
    parser.add_option("-s", "--store", help="the URL to the store database")
    parser.add_option("-d", "--debug", action="store_true",
            help="show SQL queries")
    opts, args = parser.parse_args()
    if opts.store is None:
        parser.error("the store URL is missing (eg: "
                     "sqlite:///kittystore.sqlite).")
    if args:
        parser.error("no arguments allowed.")
    print 'Upgrading the database schema if necessary...'
    store = get_store(opts.store, debug=opts.debug)
    version = list(store.db.execute(
                "SELECT patch.version FROM patch "
                "ORDER BY version DESC LIMIT 1"
                ))[0][0]
    print "Done, the current schema version is %d." % version
