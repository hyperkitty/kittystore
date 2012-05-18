# -*- coding: utf-8 -*-

import datetime
import time
from kittystore.kittysastore import KittySAStore
from kittystore.mongostore import KittyMGStore

# Define global constant

TABLE = 'devel'
REP = 30
URL = 'postgres://mm3:mm3@localhost/mm3'
DB_STORE = KittySAStore(URL)
MG_STORE = KittyMGStore(host='localhost', port=27017)

START = datetime.datetime(2012, 3, 1)
END = datetime.datetime(2012, 3, 30)

def output(name, post, mongo):
    print name
    print 'postgresql\tMongodb'
    for i in range(0, len(post)):
        print post[i],'\t', mongo[i]


def get_email(rep):
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        DB_STORE.get_email(TABLE, '3D97B04F.7090405@terra.com.br')
        post.append(time.time() - t0)
    for i in range(0,rep):
        t0 = time.time()
        MG_STORE.get_email(TABLE, '3D97B04F.7090405@terra.com.br')
        mongo.append(time.time() - t0)
    output('get_email', post, mongo)

def get_archives_range(rep):
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        len(DB_STORE.get_archives(TABLE, START, END))
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        len(MG_STORE.get_archives(TABLE, START, END))
        mongo.append(time.time() - t0)
    output('get_thread_length', post, mongo)

def first_email_in_archives_range(rep):
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        DB_STORE.get_archives(TABLE, START, END)[0]
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        MG_STORE.get_archives(TABLE, START, END)[0]
        mongo.append(time.time() - t0)
    output('first_email_in_archives_range', post, mongo)

def get_thread_length(rep):
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        DB_STORE.get_thread_length(TABLE,
            '4FCWUV6BCP3A5PASNFX6L5JOAE4GJ7F2')
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        MG_STORE.get_thread_participants(TABLE,
            '4FCWUV6BCP3A5PASNFX6L5JOAE4GJ7F2')
        mongo.append(time.time() - t0)
    output('get_thread_length', post, mongo)

def get_archives_length(rep):
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        DB_STORE.get_archives_length(TABLE)
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        MG_STORE.get_archives_length(TABLE)
        mongo.append(time.time() - t0)
    output('get_archives_length', post, mongo)

def search_subject(rep):
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        len(DB_STORE.search_subject(TABLE, 'rawhid'))
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        len(MG_STORE.search_subject(TABLE, 'rawhid'))
        mongo.append(time.time() - t0)
    output('search_subject', post, mongo)

def search_content(rep):
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        len(DB_STORE.search_content(TABLE, 'rawhid'))
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        len(MG_STORE.search_content(TABLE, 'rawhid'))
        mongo.append(time.time() - t0)
    output('search_content', post, mongo)

def search_content_subject(rep):
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        len( DB_STORE.search_content_subject(TABLE, 'rawhid'))
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        len( MG_STORE.search_content_subject(TABLE, 'rawhid'))
        mongo.append(time.time() - t0)
    output('search_content_subject', post, mongo)

def search_sender(rep):
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        len(DB_STORE.search_sender(TABLE, 'pingou'))
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        len(MG_STORE.search_sender(TABLE, 'pingou'))
        mongo.append(time.time() - t0)
    output('search_sender', post, mongo)

def get_list_size(rep):
    post = []
    mongo = []
    for i in range(0, rep):
        t0 = time.time()
        DB_STORE.get_list_size(TABLE)
        post.append(time.time() - t0)
    for i in range(0, rep):
        t0 = time.time()
        MG_STORE.get_list_size(TABLE)
        mongo.append(time.time() - t0)
    output('get_list_size', post, mongo)


if __name__ == '__main__':
    t_start = time.time()
    get_email(REP)
    get_archives_range(REP)
    first_email_in_archives_range(REP)
    get_thread_length(REP)
    get_archives_length(REP)

    search_subject(REP)
    search_content(REP)
    search_content_subject(REP)
    
    get_list_size(REP)
    print "Ran for %s seconds" % (time.time() - t_start)




