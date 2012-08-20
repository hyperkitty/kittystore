# -*- coding: utf-8 -*-

"""
KittySAModel - an object mapper to a SQL database representation of
                emails for mailman 3.

Copyright (C) 2012 Pierre-Yves Chibon
Author: Pierre-Yves Chibon <pingou@pingoured.fr>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.
See http://www.gnu.org/copyleft/gpl.html  for the full text of the
license.
"""

from sqlalchemy import (
    Table,
    Column,
    Integer,
    DateTime,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import mapper


def get_table(table, metadata, create=False):
    """ For a given string, create the table with the corresponding name,
    and following the defined structure and returns the Table object of
    the said table.

    :arg table, the name of the table in the database.
    :arg metadata, MetaData object containing the information relative
    to the connection to the database.
    :kwarg create, a boolean stipulating whether the table should be
    created if it does not already exist in the database.
    """
    # TODO:
    # - add an insertion timestamp to be able to calculate the "legacy id
    #   number" which was used to identify the email in pipermail, and
    #   eventually setup a proper redirection.
    # - use the msg_hash_id and the list_id as a primary key
    # - add a content-type (html or text) (and an encoding field maybe? or store everything as UTF-8?)
    table = Table( table, metadata,
        Column('id', Integer, primary_key=True),
        Column('sender', String(100), nullable=False),
        Column('email', String(75), nullable=False),
        Column('subject', Text, nullable=False, index=True),
        Column('content', Text, nullable=False),
        Column('date', DateTime, index=True),
        Column('message_id', String(150), index=True, unique=True,
            nullable=False),
        Column('stable_url_id', String(250), index=True, unique=True,
            nullable=False),
        Column('thread_id', String(150), nullable=False, index=True),
        Column('references', Text),
        Column('full', LargeBinary),
        useexisting=True)
    if create:
        metadata.create_all()
    return table


def get_class_object(table, entity_name, metadata, create=False, **kw):
    """ For a given table name, returns the object mapping the said
    table.

    :arg table, the name of the table in the database.
    :arg metadata, MetaData object containing the information relative
    to the connection to the database.
    :kwarg create, a boolean stipulating whether the table should be
    created if it does not already exist in the database.
    """
    newcls = type(entity_name, (Email, ), {})
    mapper(newcls, get_table(table, metadata, create), **kw)
    return newcls


class Email(object):
    """ Email table.

    Define the fields of the table and their types.
    """

    def __init__(self, sender, email, subject, content, date, message_id,
        stable_url_id, thread_id, references, full):
        """ Constructor instanciating the defaults values. """
        self.sender = sender
        self.email = email
        self.subject = subject
        self.content = content
        self.date = date
        self.message_id = message_id
        self.stable_url_id = stable_url_id
        self.thread_id = thread_id
        self.references = references
        self.full = full

    def __repr__(self):
        """ Representation of the Email object when printed. """
        return "<Email('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')>" \
                % (self.sender, self.email, self.date, self.subject,
                   self.message_id, self.stable_url_id, self.thread_id,
                   self.references)

    def save(self, session):
        """ Save the object into the database. """
        session.add(self)
