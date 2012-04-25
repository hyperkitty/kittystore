# -*- coding: utf-8 -*-

import datetime
from kittystore.kittysastore import KittySAStore

if __name__ == '__main__':
    URL = 'postgres://mm3:mm3@localhost/mm3'
    #create(URL)
    STORE = KittySAStore(URL)#, debug=True)
    print STORE.get_email('devel',
        'Pine.LNX.4.55.0307210822320.19648@verdande.oobleck.net')
    START = datetime.datetime(2012, 3, 1)
    END = datetime.datetime(2012, 3, 30)
    print len(STORE.get_archives('devel', START, END))
    print STORE.get_thread_length('devel',
        '4FCWUV6BCP3A5PASNFX6L5JOAE4GJ7F2')
    print STORE.get_thread_participants('devel',
        '4FCWUV6BCP3A5PASNFX6L5JOAE4GJ7F2')
    print STORE.get_archives_length('devel')
    print 'Subject', len(STORE.search_subject('devel', 'rawhid'))
    print 'Content', len(STORE.search_content('devel', 'rawhid'))
    print 'Content-Subject', len(
        STORE.search_content_subject('devel', 'rawhid'))
    print 'Sender', len(STORE.search_sender('devel', 'pingou'))
    print STORE.get_list_size('devel')

