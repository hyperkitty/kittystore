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

from __future__ import absolute_import

import importlib
import sys
import logging
from optparse import OptionParser

from kittystore import get_store, create_store, SchemaUpgradeNeeded

from kittystore.caching import sync_mailman


#
# Helpers
#
class StoreFromOptionsError(Exception): pass

def get_settings_from_options(opts):
    """
    Returns a settings object from an options object. Known options are;
    - "settings": the Django settings module
    - "pythonpath": an additional Python path to import the Django settings
    """
    settings = None
    if opts.pythonpath is not None:
        sys.path.append(opts.pythonpath)
    try:
        settings = importlib.import_module(opts.settings)
    except ImportError as e:
        raise StoreFromOptionsError(
                "could not import settings '%s' (Is it on "
                "sys.path?): %s" % (opts.settings, e))
    return settings

def get_store_from_options(opts):
    """
    Returns a Store instance from an options object. Known options are;
    - "settings": the Django settings module
    - "pythonpath": an additional Python path to import the Django settings
    """
    settings = get_settings_from_options(opts)
    return get_store(settings, debug=opts.debug)


#
# Manual database update
#

def updatedb():
    parser = OptionParser(usage="%prog -s settings_module")
    parser.add_option("-s", "--settings", default="settings",
                      help="the Python path to a Django-like settings module")
    parser.add_option("-p", "--pythonpath",
                      help="a directory to add to the Python path")
    parser.add_option("-d", "--debug", action="store_true",
                      help="show SQL queries")
    opts, args = parser.parse_args()
    if args:
        parser.error("no arguments allowed.")
    if opts.debug:
        debuglevel = logging.DEBUG
    else:
        debuglevel = logging.INFO
    logging.basicConfig(format='%(message)s', level=debuglevel)
    print 'Upgrading the database schema and populating ' \
          'the search index if necessary...'
    try:
        settings = get_settings_from_options(opts)
    except (StoreFromOptionsError, AttributeError), e:
        parser.error(e.args[0])
    try:
        store = get_store(settings, debug=opts.debug)
    except SchemaUpgradeNeeded:
        print "Upgrading the schema..."
        store = create_store(settings, debug=opts.debug)
        version = list(store.db.execute(
                    "SELECT patch.version FROM patch "
                    "ORDER BY version DESC LIMIT 1"
                    ))[0][0]
        print "Done, the current schema version is %d." % version
        print "Synchonizing data from Mailman, this can take some time..."
        sync_mailman(store)
        store.commit()
        print "  ...done!"
    else:
        print "No schema upgrade needed."



#
# Manual Mailman sync
#

def sync_mailman_cmd():
    parser = OptionParser(usage="%prog -s settings_module [-f]")
    parser.add_option("-s", "--settings", default="settings",
                      help="the Python path to a Django-like settings module")
    parser.add_option("-p", "--pythonpath",
                      help="a directory to add to the Python path")
    parser.add_option("-d", "--debug", action="store_true",
                      help="show SQL queries")
    opts, args = parser.parse_args()
    if args:
        parser.error("no arguments allowed.")
    if opts.debug:
        debuglevel = logging.DEBUG
    else:
        debuglevel = logging.INFO
    logging.basicConfig(format='%(message)s', level=debuglevel)
    print 'Synchronizing data from Mailman...'
    try:
        store = get_store_from_options(opts)
    except (StoreFromOptionsError, AttributeError), e:
        parser.error(e.args[0])
    except SchemaUpgradeNeeded:
        print >>sys.stderr, ("The database schema needs to be upgraded, "
                             "please run kittystore-updatedb first")
        sys.exit(1)
    sync_mailman(store)
    store.commit()
    print "  ...done!"



#
# Mailman 2 archives downloader
#

import os
import urllib2
import gzip
import itertools
from multiprocessing import Pool
from datetime import date

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']

def dl_archives():
    parser = OptionParser(usage="%prog -u URL -l LIST_NAME [-d destdir]")
    parser.add_option("-u", "--url", help="URL to the mailman installation")
    parser.add_option("-l", "--list-name", help="mailing-list name")
    parser.add_option("-d", "--destination", default=os.getcwd(),
                      help="directory to download the archives to. Defaults "
                           "to the current directory (%default)")
    parser.add_option("-s", "--start", default="2002",
                      help="first year to start looking for archives")
    parser.add_option("-v", "--verbose", action="store_true",
                      help="show more information")
    opts, args = parser.parse_args()
    if not opts.url:
        parser.error("an URL must be provided")
    if not opts.list_name:
        parser.error("a list name must be provided")
    if "@" in opts.list_name:
        opts.list_name = opts.list_name[:opts.list_name.index("@")]
    years = range(int(opts.start), date.today().year + 1)
    p = Pool(5)
    p.map(_archive_downloader, itertools.product([opts], years, MONTHS))

def _archive_downloader(args):
    opts, year, month = args
    if not year or not month:
        return
    basename = "{0}-{1}.txt.gz".format(year, month)
    filepath = os.path.join(opts.destination, basename)
    if os.path.exists(filepath):
        if opts.verbose:
            print "{0} already downloaded, skipping".format(basename)
        return
    url = "{0}/pipermail/{1}/{2}".format(
            opts.url, opts.list_name, basename)
    if opts.verbose:
        print "Downloading from {0}".format(url)
    try:
        request = urllib2.urlopen(url)
        with open(filepath, "w") as f:
            f.write(request.read())
    except urllib2.URLError, e:
        if isinstance(e, urllib2.HTTPError) and e.code == 404:
            print ("This archive hasn't been created on the server yet: "
                   + basename)
        else:
            print "Error: %s" % e.reason
        return
    pos = str(MONTHS.index(month) + 1).rjust(2, "0")
    newname = '{0}-{1}-{2}-{3}.txt'.format(opts.list_name, year, pos, month)
    with open(os.path.join(opts.destination, newname), "w") as f:
        f.write(gzip.open(filepath).read())
    print "Downloaded archive for {0} {1} from {2}".format(month, year, url)
