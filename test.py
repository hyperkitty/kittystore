# -*- coding: utf-8 -*-

import datetime
from kittystore.kittysastore import KittySAStore

if __name__ == '__main__':
    URL = 'postgres://mm3:mm3@localhost/mm3'
    TABLE = 'email'
    STORE = KittySAStore(URL)#, debug=True)
    #create(URL)
    print STORE.get_email(TABLE,
        '3D97B04F.7090405@terra.com.br')
        #'Pine.LNX.4.55.0307210822320.19648@verdande.oobleck.net')
    START = datetime.datetime(2012, 3, 1)
    END = datetime.datetime(2012, 3, 30)
    print len(STORE.get_archives(TABLE, START, END))
    print STORE.get_thread_length(TABLE,
        '4FCWUV6BCP3A5PASNFX6L5JOAE4GJ7F2')
    print STORE.get_thread_participants(TABLE,
        '4FCWUV6BCP3A5PASNFX6L5JOAE4GJ7F2')
    print STORE.get_archives_length(TABLE)
    print 'Subject', len(STORE.search_subject(TABLE, 'rawhid'))
    print 'Content', len(STORE.search_content(TABLE, 'rawhid'))
    print 'Content-Subject', len(
        STORE.search_content_subject(TABLE, 'rawhid'))
    print 'Sender', len(STORE.search_sender(TABLE, 'pingou'))
    print STORE.get_list_size(TABLE)

