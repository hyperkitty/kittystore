# -*- coding: utf-8 -*-

"""
mmstore - an object mapper and interface to the mongo database
           representation of emails for mailman 3.

Copyright (C) 2012 Pierre-Yves Chibon
Author: Pierre-Yves Chibon <pingou@pingoured.fr>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.
See http://www.gnu.org/copyleft/gpl.html  for the full text of the
license.
"""

from ming import Session, Document, Field, schema
from ming.datastore import DataStore

from datetime import datetime

host = 'localhost'
port = '27017'
database = 'test'
bind = DataStore('mongodb://%s:%s/' %(host, port),
            database=database)
session = Session(bind)


class MMStore(Document):
    """ Object representation of the information stored for every email
    in the mongo database.

    This class is the interface used to read and write to the database
    any email it contains.
    """

    class __mongometa__:
        """ Meta information required for the class """
        name = 'mails'
        session = session
        custom_indexes = [
            dict(fields=('MessageID',), unique=True, sparse=False),
            dict(fields=('Date',), unique=False, sparse=True)
        ]

    # Unique identifier, specific to mongodb
    _id = Field(schema.ObjectId)
    # Name of the sender
    From = Field(str)
    # Email address of the sender
    Email = Field(str)
    # Email body
    Content = Field(str)
    # Date when the email was sent
    Date = Field(datetime)
    # Unique identifier of the message as present in the header
    MessageID = Field(str)
    # Helper to keep links consistent with pipermail
    #LegacyID = Field(int)
    # Assign a category to the email -- HK specific
    #Category = Field(str)
    # Full email (headers and body included)
    Full = Field(str)


if __name__ == '__main__':
    #store = MMStore(dict(From = 'test@test', Content = 'test'))
    #store.m.save()
    mail = MMStore.m.find({'MessageID':'jfc06g$ci3$1@dough.gmane.org'}).one()
    print mail, mail.keys()
    print dir(MMStore.__mongometa__.session.db.name)
    print MMStore.__mongometa__.session.db.name
