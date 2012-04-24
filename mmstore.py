# -*- coding: utf-8 -*-

"""
mm_store - an object mapper and interface to the mongo database
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





class MMStore(Document):
    """ Object representation of the information stored for every email
    in the mongo database.

    This class is the interface used to read and write to the database
    any email it contains.
    """

    class __mongometa__:
        """ Meta information required for the class """
        session = session
        name = 'mailman_email'

    _id = Field(schema.ObjectId)
    From = Field(str)
    Content = Field(str)
    Date = Field(datetime)

    def __init__(self, database, host='localhost', port='27017'):
        self.bind = DataStore('mongodb://%s:%s/' %(host, port),
            database=database)
        self.session = Session(bind)

if __name__ == '__main__':
    store = MMStore('devel')
    print store

