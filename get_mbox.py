#! /bin/python

import itertools
import urlgrabber
import gzip
import sys
from multiprocessing import Pool

years = [2010, 2011, 2012, 2009, 2008, 2007, 2006, 2005, 2004, 2003, 2002]
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
    'August', 'September', 'October', 'November', 'December']


def archive_downloader(i):
    """ Retrieve the archive for all the year and month defined. """
    print i
    list_name = i[0]
    year = i[1]
    month = i[2]
    if not list_name or not year or not month:
        return
    basename = "{0}-{1}.txt.gz".format(year, month)
    filename = "http://lists.fedoraproject.org/pipermail/{0}/{1}".format(
        list_name, basename)
    try:
        urlgrabber.urlgrab(filename)
        pos = str(months.index(month) + 1)
        if len(pos) == 1:
            pos = '0{0}'.format(pos)
        newname = '{0}-{1}-{2}-{3}.txt'.format(list_name, year, pos, month)
        with open(newname, "w") as f:
           f.write(gzip.open(basename).read())
        print "== {0} downloaded ==".format(filename)
    except urlgrabber.grabber.URLGrabError:
        pass


if __name__ == "__main__":
    if len(sys.argv) < 1 or '-h' in sys.argv or '--help' in sys.argv:
        print '''USAGE:
python get_mbox.py list_name'''
    else:
        list_name = sys.argv[1:]
        p = Pool(5)
        p.map(archive_downloader, itertools.product(list_name, years,
            months))
