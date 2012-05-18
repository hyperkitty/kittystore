# -*- coding: utf-8 -*-

import datetime
import time
from kittystore.kittysastore import KittySAStore
from kittystore.mongostore import KittyMGStore

# Define global constant

TABLE = 'devel'
REP = 1
URL = 'postgres://mm3:mm3@localhost/mm3'
DB_STORE = KittySAStore(URL)
MG_STORE = KittyMGStore(host='localhost', port=27017)

START = datetime.datetime(2012, 3, 1)
END = datetime.datetime(2012, 3, 30)

def output(name, post, mongo):
    stream = open(name, 'w')
    stream.write('postgresql\tMongodb')
    for i in range(0, len(post)):
        stream.write(str(post[i]) + '\t' + str(mongo[i]))
    stream.close()

def get_email(rep):
    print 'get_email'
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        res_pg = DB_STORE.get_email(TABLE, '3D97B04F.7090405@terra.com.br')
        post.append(time.time() - t0)
    for i in range(0,rep):
        t0 = time.time()
        res_mg = MG_STORE.get_email(TABLE, '3D97B04F.7090405@terra.com.br')
        mongo.append(time.time() - t0)
    output('get_email', post, mongo)
    if res_mg['Subject'] != res_pg.subject and res_mg['Date'] != res_pg.date:
        print '** Results differs'
        print 'MG: %s' % res_mg
        print 'PG: %s\n' % res_pg

def get_archives_range(rep):
    print 'get_archives_range'
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        res_pg = len(DB_STORE.get_archives(TABLE, START, END))
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        res_mg = len(MG_STORE.get_archives(TABLE, START, END))
        mongo.append(time.time() - t0)
    output('get_thread_length', post, mongo)
    if res_mg != res_pg:
        print '** Results differs'
        print 'MG: %s' % res_mg
        print 'PG: %s\n' % res_pg

def first_email_in_archives_range(rep):
    print 'first_email_in_archives_range'
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        res_pg = DB_STORE.get_archives(TABLE, START, END)[0]
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        res_mg = MG_STORE.get_archives(TABLE, START, END)[0]
        mongo.append(time.time() - t0)
    output('first_email_in_archives_range', post, mongo)
    if res_mg['Subject'] != res_pg.subject and res_mg['Date'] != res_pg.date:
        print '** Results differs'
        print 'MG: %s' % res_mg
        print 'PG: %s\n' % res_pg

def get_thread_length(rep):
    print 'get_thread_length'
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        res_pg = DB_STORE.get_thread_length(TABLE,
            '4FCWUV6BCP3A5PASNFX6L5JOAE4GJ7F2')
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        res_mg = MG_STORE.get_thread_length(TABLE,
            '4FCWUV6BCP3A5PASNFX6L5JOAE4GJ7F2')
        mongo.append(time.time() - t0)
    output('get_thread_length', post, mongo)
    if res_mg != res_pg:
        print '** Results differs'
        print 'MG: %s' % res_mg
        print 'PG: %s\n' % res_pg

def get_thread_participants(rep):
    print 'get_thread_participants'
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        res_pg = len(DB_STORE.get_thread_participants(TABLE,
            '4FCWUV6BCP3A5PASNFX6L5JOAE4GJ7F2'))
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        res_mg = len(MG_STORE.get_thread_participants(TABLE,
            '4FCWUV6BCP3A5PASNFX6L5JOAE4GJ7F2'))
        mongo.append(time.time() - t0)
    output('get_thread_participants', post, mongo)
    if res_mg != res_pg:
        print '** Results differs'
        print 'MG: %s' % res_mg
        print 'PG: %s\n' % res_pg

def get_archives_length(rep):
    print 'get_archives_length'
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        res_pg = DB_STORE.get_archives_length(TABLE)
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        res_mg = MG_STORE.get_archives_length(TABLE)
        mongo.append(time.time() - t0)
    output('get_archives_length', post, mongo)
    if res_mg != res_pg:
        print '** Results differs'
        print 'MG: %s' % res_mg
        print 'PG: %s\n' % res_pg

def search_subject(rep):
    print 'search_subject'
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        res_pg = len(DB_STORE.search_subject(TABLE, 'rawhid'))
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        res_mg = len(MG_STORE.search_subject(TABLE, 'rawhid'))
        mongo.append(time.time() - t0)
    output('search_subject', post, mongo)
    if res_mg != res_pg:
        print '** Results differs'
        print 'MG: %s' % res_mg
        print 'PG: %s\n' % res_pg

def search_content(rep):
    print 'search_content'
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        res_pg = len(DB_STORE.search_content(TABLE, 'rawhid'))
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        res_mg = len(MG_STORE.search_content(TABLE, 'rawhid'))
        mongo.append(time.time() - t0)
    output('search_content', post, mongo)
    if res_mg != res_pg:
        print '** Results differs'
        print 'MG: %s' % res_mg
        print 'PG: %s\n' % res_pg

def search_content_subject(rep):
    print 'search_content_subject'
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        res_pg = len( DB_STORE.search_content_subject(TABLE, 'rawhid'))
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        res_mg = len( MG_STORE.search_content_subject(TABLE, 'rawhid'))
        mongo.append(time.time() - t0)
    output('search_content_subject', post, mongo)
    if res_mg != res_pg:
        print '** Results differs'
        print 'MG: %s' % res_mg
        print 'PG: %s\n' % res_pg

def search_sender(rep):
    print 'search_sender'
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        res_pg = len(DB_STORE.search_sender(TABLE, 'pingou'))
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        res_mg = len(MG_STORE.search_sender(TABLE, 'pingou'))
        mongo.append(time.time() - t0)
    output('search_sender', post, mongo)
    if res_mg != res_pg:
        print '** Results differs'
        print 'MG: %s' % res_mg
        print 'PG: %s\n' % res_pg

def get_list_size(rep):
    print 'get_list_size'
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        res_pg = res_pg = DB_STORE.get_list_size(TABLE)
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        res_mg = MG_STORE.get_list_size(TABLE)
        mongo.append(time.time() - t0)
    output('get_list_size', post, mongo)
    if res_mg != res_pg:
        print '** Results differs'
        print 'MG: %s' % res_mg
        print 'PG: %s\n' % res_pg


if __name__ == '__main__':
    t_start = time.time()
    get_email(REP)
    get_archives_range(REP)
    first_email_in_archives_range(REP)
    get_thread_length(REP)
    get_thread_participants(REP)
    get_archives_length(REP)

    search_subject(REP)
    search_content(REP)
    search_content_subject(REP)
    
    get_list_size(REP)
    print "Ran for %s seconds" % (time.time() - t_start)




