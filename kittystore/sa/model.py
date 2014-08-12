# -*- coding: utf-8 -*-

"""
Copyright (C) 2012 Aurelien Bompard <abompard@fedoraproject.org>
Author: Aurelien Bompard <abompard@fedoraproject.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.
See http://www.gnu.org/copyleft/gpl.html  for the full text of the
license.
"""

from __future__ import absolute_import, print_function, unicode_literals

import datetime
from collections import namedtuple

from zope.interface import implements
from mailman.interfaces.archiver import ArchivePolicy
from mailman.interfaces.messages import IMessage

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy import and_, desc
from sqlalchemy import Column, ForeignKey, Integer, Unicode, DateTime, UnicodeText, LargeBinary, Enum
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship, backref, object_session
from sqlalchemy.sql import expression
from sqlalchemy.schema import ForeignKeyConstraint, Index
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import event as sa_event

from kittystore import events
from kittystore.utils import get_message_id_hash
from .utils import get_participants_count_between, get_threads_between

Base = declarative_base()



class IntegerEnum(TypeDecorator):
    """
    Stores an integer-based Enum as an integer in the database, and converts it
    on-the-fly.
    """

    impl = Integer

    def __init__(self, *args, **kw):
        self.enum = kw.pop("enum")
        TypeDecorator.__init__(self, *args, **kw)

    def process_bind_param(self, value, dialect):
        if not isinstance(value, self.enum):
            raise ValueError("{} must be a value of the {} enum".format(
                             self.value, self.enum.__name__))
        return value.value


    def process_result_value(self, value, dialect):
        return self.enum(value)



class List(Base):
    """
    An archived mailing-list.
    """
    # When updating this model, remember to update the fake version
    # in test/__init__.py

    __tablename__ = "list"

    # The following properties are mirrored from Mailman's MailingList instance
    mailman_props = ("display_name", "description", "subject_prefix",
                     "archive_policy", "created_at")

    name = Column(Unicode(255), primary_key=True, nullable=False)
    display_name = Column(UnicodeText)
    description = Column(UnicodeText)
    subject_prefix = Column(UnicodeText)
    archive_policy = Column(IntegerEnum(enum=ArchivePolicy))
    created_at = Column(DateTime)
    emails = relationship("Email", backref="mlist")
    threads = relationship("Thread", backref="mlist", cascade="all, delete-orphan")

    #def __repr__(self):
    #    return "<List('{}')>".format(self.name)

    def get_recent_dates(self):
        today = datetime.datetime.utcnow()
        #today -= datetime.timedelta(days=400) #debug
        # the upper boundary is excluded in the search, add one day
        end_date = today + datetime.timedelta(days=1)
        begin_date = end_date - datetime.timedelta(days=32)
        return begin_date, end_date

    @property
    def recent_participants_count(self):
        begin_date, end_date = self.get_recent_dates()
        session = object_session(self)
        return session.cache.get_or_create(
            str("list:%s:recent_participants_count" % self.name),
            lambda: get_participants_count_between(session, self.name,
                                                   begin_date, end_date),
            86400)

    @property
    def recent_threads_count(self):
        begin_date, end_date = self.get_recent_dates()
        session = object_session(self)
        return session.cache.get_or_create(
            str("list:%s:recent_threads_count" % self.name),
            lambda: get_threads_between(session, self.name,
                                        begin_date, end_date).count(),
            86400)

    def get_month_activity(self, year, month):
        session = object_session(self)
        begin_date = datetime.datetime(year, month, 1)
        end_date = begin_date + datetime.timedelta(days=32)
        end_date = end_date.replace(day=1)
        participants_count = session.cache.get_or_create(
            str("list:%s:participants_count:%s:%s" % (self.name, year, month)),
            lambda: get_participants_count_between(session, self.name,
                                                   begin_date, end_date),
            )
        threads_count = session.cache.get_or_create(
            str("list:%s:threads_count:%s:%s" % (self.name, year, month)),
            lambda: get_threads_between(session, self.name,
                                        begin_date, end_date).count(),
            )
        Activity = namedtuple('Activity',
                ['year', 'month', 'participants_count', 'threads_count'])
        return Activity(year, month, participants_count, threads_count)

    @events.subscribe_to(events.NewMessage)
    def on_new_message(event): # will be called unbound (no self as 1st argument)
        cache = event.store.db.cache
        l = event.store.get_list(event.mlist.fqdn_listname)
        # recent activity
        begin_date = l.get_recent_dates()[0]
        if event.message.date >= begin_date:
            cache.delete(str("list:%s:recent_participants_count" % l.name))
            l.recent_participants_count
            cache.delete(str("list:%s:recent_threads_count" % l.name))
            l.recent_threads_count
        # month activity
        year, month = event.message.date.year, event.message.date.month
        cache.delete(str("list:%s:participants_count:%s:%s"
                         % (l.name, year, month)))
        l.get_month_activity(year, month)



class User(Base):
    """
    A user with a definition similar to Mailman's (it may have multiple email
    adresses)
    """

    __tablename__ = "user"

    id = Column(Unicode(255), primary_key=True, nullable=False)
    senders = relationship("Sender", backref="user", cascade="all, delete-orphan")
    votes = relationship("Vote", backref="user", cascade="all, delete-orphan")
    addresses = association_proxy('senders', 'email')

    @property
    def messages(self):
        # TODO: rename messages to emails
        return object_session(self).query(Email).join(Sender
                    ).with_parent(self).order_by(Email.date).all()

    def get_votes_in_list(self, list_name):
        session = object_session(self)
        def getvotes():
            req = session.query(Vote).filter(Vote.list_name == list_name)
            likes = req.filter(Vote.value == 1).count()
            dislikes = req.filter(Vote.value == -1).count()
            return likes, dislikes # TODO: optimize with a Union statement?
        cache_key = str("user:%s:list:%s:votes" % (self.id, list_name))
        return session.cache.get_or_create(cache_key, getvotes)



class Sender(Base):
    """
    Link between an email address and a User object
    """

    __tablename__ = "sender"

    # TODO: rename "email" to "address"
    email = Column(Unicode(255), primary_key=True, nullable=False)
    name = Column(Unicode(255))
    user_id = Column(Unicode(255), ForeignKey("user.id"), index=True)
    emails = relationship("Email", backref="sender", cascade="all, delete-orphan")



class Email(Base):
    """
    An archived email, from a mailing-list. It is identified by both the list
    name and the message id.
    """

    implements(IMessage)
    __tablename__ = "email"

    list_name = Column(Unicode(255), ForeignKey("list.name", ondelete="CASCADE"), primary_key=True, nullable=False, index=True)
    message_id = Column(Unicode(255), primary_key=True, nullable=False)
    # TODO: rename to sender_address
    sender_email = Column(Unicode(255), ForeignKey("sender.email"), nullable=False, index=True)
    subject = Column(UnicodeText, nullable=False, index=True)
    content = Column(UnicodeText, nullable=False)
    date = Column(DateTime, index=True, nullable=False)
    timezone = Column(Integer, nullable=False)
    in_reply_to = Column(Unicode(255)) # no foreign key to handle replies from an email not in the archives. But should we have the list-id too, for replies from another list?
    message_id_hash = Column(Unicode(255), nullable=False)
    thread_id = Column(Unicode(255), nullable=False, index=True)
    archived_date = Column(DateTime, nullable=False, server_default=expression.text("CURRENT_TIMESTAMP"), index=True)
    thread_depth = Column(Integer, default=0, nullable=False) # TODO: index this?
    thread_order = Column(Integer, default=0, nullable=False, index=True)
    # path is required by IMessage, but it makes no sense here
    path = None
    # References
    attachments = relationship("Attachment", order_by="Attachment.counter", backref="email", cascade="all, delete-orphan")
    full_email = relationship("EmailFull", uselist=False, backref="email", cascade="all, delete-orphan")
    # TODO: rename to "email"
    votes = relationship("Vote", backref="message", cascade="all, delete-orphan")

    def __init__(self, *args, **kw):
        Base.__init__(self, *args, **kw)
        if "message_id_hash" not in kw:
            self.message_id_hash = unicode(get_message_id_hash(self.message_id))

    @hybrid_property
    def full(self):
        return self.full_email.full
    @hybrid_property
    def sender_name(self):
        return self.sender.name
    @hybrid_property
    def user_id(self):
        return self.sender.user_id

    def _get_votes_query(self):
        session = object_session(self)
        return session.query(Vote).filter(
                    Vote.list_name == self.list_name).filter(
                    Vote.message_id == self.message_id)

    @property
    def likes(self):
        session = object_session(self)
        return session.cache.get_or_create(
            str("list:%s:email:%s:likes" % (self.list_name, self.message_id)),
            lambda: self._get_votes_query.filter(Vote.value == 1).count()
            )

    @property
    def dislikes(self):
        session = object_session(self)
        return session.cache.get_or_create(
            str("list:%s:email:%s:dislikes" % (self.list_name, self.message_id)),
            lambda: self._get_votes_query.filter(Vote.value == -1).count()
            )

    @property
    def likestatus(self):
        likes, dislikes = self.likes, self.dislikes
        # TODO: use an Enum?
        if likes - dislikes >= 10:
            return "likealot"
        if likes - dislikes > 0:
            return "like"
        return "neutral"

    def vote(self, value, user_id):
        session = object_session(self)
        # Checks if the user has already voted for this message.
        existing = self._get_votes_query().filter(Vote.user_id == user_id).first()
        # TODO: make sure this is covered by unit tests
        if existing is not None and existing.value == value:
            return # Vote already recorded (should I raise an exception?)
        if value not in (0, 1, -1):
            raise ValueError("A vote can only be +1 or -1 (or 0 to cancel)")
        # The vote can be added, changed or cancelled. Keep it simple and
        # delete likes and dislikes cached values.
        session.cache.delete_multi((
            # this message's (dis)likes count
            str("list:%s:email:%s:likes" % (self.list_name, self.message_id)),
            str("list:%s:email:%s:dislikes" % (self.list_name, self.message_id)),
            # this thread (dis)likes count
            str("list:%s:thread:%s:likes" % (self.list_name, self.thread_id)),
            str("list:%s:thread:%s:dislikes" % (self.list_name, self.thread_id)),
            # the user's vote count on this list
            str("user:%s:list:%s:votes" % (user_id, self.list_name)),
            ))
        if existing is not None:
            # vote changed or cancelled
            if value == 0:
                session.delete(existing)
            else:
                existing.value = value
        else:
            # new vote
            if session.query(User).get(user_id) is None:
                session.add(User(user_id=user_id))
            session.add(Vote(list_name=self.list_name,
                             message_id=self.message_id,
                             user_id=user_id, value=value))

    def get_vote_by_user_id(self, user_id):
        if user_id is None:
            return None
        return self._get_votes_query.filter(Vote.user_id == user_id).first()

# composite foreign key, no other way to declare it
Email.__table__.append_constraint(
    ForeignKeyConstraint(
        ["list_name", "thread_id"],
        ["thread.list_name", "thread.thread_id"],
        ondelete="CASCADE"
    ))
# composite indexes
Index("ix_email_list_name_message_id_hash",
      Email.__table__.c.list_name, Email.__table__.c.message_id_hash,
      unique=True)
Index("ix_email_list_name_thread_id",
      Email.__table__.c.list_name, Email.__table__.c.thread_id)



class EmailFull(Base):
    """
    The full contents of an archived email, for storage and post-processing
    reasons.
    """
    __tablename__ = "email_full"

    list_name = Column(Unicode(255), nullable=False, primary_key=True)
    message_id = Column(Unicode(255), nullable=False, primary_key=True)
    full = Column(LargeBinary, nullable=False)

# composite foreign key, no other way to declare it
EmailFull.__table__.append_constraint(
    ForeignKeyConstraint(
        ["list_name", "message_id"],
        ["email.list_name", "email.message_id"],
        ondelete="CASCADE"
    ))



class Attachment(Base):

    __tablename__ = "attachment"

    list_name = Column(Unicode(255), nullable=False, primary_key=True)
    message_id = Column(Unicode(255), nullable=False, primary_key=True)
    counter = Column(Integer, nullable=False, primary_key=True)
    name = Column(Unicode(255))
    content_type = Column(Unicode(255), nullable=False)
    encoding = Column(Unicode(50))
    size = Column(Integer, nullable=False)
    content = Column(LargeBinary, nullable=False)

# composite foreign key, no other way to declare it
Attachment.__table__.append_constraint(
    ForeignKeyConstraint(
        ["list_name", "message_id"],
        ["email.list_name", "email.message_id"],
        ondelete="CASCADE"
    ))
# composite indexes
Index("ix_attachment_list_name_message_id",
      Attachment.__table__.c.list_name, Attachment.__table__.c.message_id)



class Thread(Base):
    """
    A thread of archived email, from a mailing-list. It is identified by both
    the list name and the thread id.
    """

    __tablename__ = "thread"

    list_name = Column(Unicode(255), ForeignKey("list.name", ondelete="CASCADE"), primary_key=True, nullable=False, index=True)
    thread_id = Column(Unicode(255), primary_key=True, nullable=False)
    date_active = Column(DateTime, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("category.id"))
    emails = relationship("Email", order_by="Email.date", backref="thread", cascade="all, delete-orphan")
    category_obj = relationship("Category", backref="threads")
    _starting_email = None

    @property
    def starting_email(self):
        """Return (and cache) the email starting this thread"""
        session = object_session(self)
        message_id = session.cache.get_or_create(
            str("list:%s:thread:%s:starting_email_id" % (self.list_name, self.thread_id)),
            lambda: session.query(Email.message_id).with_parent(self).order_by(
                        Email.in_reply_to != None, Email.date).limit(1).scalar(),
            should_cache_fn=lambda val: val is not None
            )
        if message_id is not None:
            return session.query(Email).get((self.list_name, message_id))

    @property
    def last_email(self):
        return object_session(self).query(Email).with_parent(self
                    ).order_by(desc(Email.date)).first()

    def _get_participants(self):
        """Email senders in this thread"""
        session = object_session(self)
        return session.query(Sender).join(Email).filter(and_(
                    Email.list_name == self.list_name,
                    Email.thread_id == self.thread_id,
                )).distinct()

    @property
    def participants(self):
        """Set of email senders in this thread"""
        return self._get_participants().all()

    @property
    def participants_count(self):
        session = object_session(self)
        return session.cache.get_or_create(
            str("list:%s:thread:%s:participants_count"
                % (self.list_name, self.thread_id)),
            lambda: self._get_participants().count())

    @property
    def emails_by_reply(self):
        return object_session(self).query(Email).with_parent(self)\
                    .order_by(Email.thread_order).all()

    @property
    def email_ids(self):
        return object_session(self).query(Email.message_id
                    ).with_parent(self).all()
        #session = object_session(self)
        #return session.query(Email.message_id).filter(and_(
        #            Email.list_name == list_name,
        #            Email.thread_id == thread_id)
        #       ).all()

    @property
    def email_id_hashes(self):
        return object_session(self).query(Email.message_id_hash
                    ).with_parent(self).all()
        #session = object_session(self)
        #return session.query(Email.message_id_hash).filter(and_(
        #            Email.list_name == list_name,
        #            Email.thread_id == thread_id)
        #       ).all()

    def replies_after(self, date):
        return object_session(self).query(Email).filter(
                    Email.date > date).all()
        #session = object_session(self)
        #return session.query(Email).filter(and_(
        #                Email.list_name == list_name,
        #                Email.thread_id == thread_id)
        #            ).filter(Email.date > date).all()

    def _get_category(self):
        if not self.category_id:
            return None
        return self.category_obj.name
    def _set_category(self, name):
        if not name:
            self.category_id = None
            return
        session = object_session(self)
        try:
            category = session.query(Category).filter_by(name=name).one()
        except NoResultFound:
            category = Category(name=name)
            session.add(category)
        self.category_id = category.id
    category = property(_get_category, _set_category)

    def __len__(self):
        return self.emails_count

    @property
    def emails_count(self):
        session = object_session(self)
        return session.cache.get_or_create(
            str("list:%s:thread:%s:emails_count"
                % (self.list_name, self.thread_id)),
            lambda: session.query(Email).with_parent(self).count())

    @property
    def subject(self):
        session = object_session(self)
        return session.cache.get_or_create(
            str("list:%s:thread:%s:subject"
                % (self.list_name, self.thread_id)),
            lambda: self.starting_email.subject)

    def _getvotes(self):
        return object_session(self).query(Vote).join(Email).filter(and_(
                    Email.list_name == self.list_name,
                    Email.thread_id == self.thread_id,
                ))

    @property
    def likes(self):
        session = object_session(self)
        return session.cache.get_or_create(
            str("list:%s:thread:%s:likes" % (self.list_name, self.thread_id)),
            lambda: self._getvotes().filter(Vote.value == 1).count()
            )

    @property
    def dislikes(self):
        session = object_session(self)
        return session.cache.get_or_create(
            str("list:%s:thread:%s:dislikes" % (self.list_name, self.thread_id)),
            lambda: self._getvotes().filter(Vote.value == -1).count()
            )

    @property
    def likestatus(self):
        # TODO: deduplicate with the equivalent function in the Email class
        likes, dislikes = self.likes, self.dislikes
        # XXX: use an Enum?
        if likes - dislikes >= 10:
            return "likealot"
        if likes - dislikes > 0:
            return "like"
        return "neutral"

    @events.subscribe_to(events.NewMessage)
    def on_new_message(event): # will be called unbound (no self as 1st argument)
        cache = event.store.db.cache
        cache.delete(str("list:%s:thread:%s:emails_count"
                         % (event.message.list_name, event.message.thread_id)))
        event.message.thread.emails_count
        cache.delete(str("list:%s:thread:%s:participants_count"
                         % (event.message.list_name, event.message.thread_id)))
        event.message.thread.participants_count

    @events.subscribe_to(events.NewThread)
    def on_new_thread(event): # will be called unbound (no self as 1st argument)
        event.store.db.cache.set(
                str("list:%s:thread:%s:subject"
                    % (event.thread.list_name, event.thread.thread_id)),
                event.thread.starting_email.subject)

@sa_event.listens_for(Thread, 'before_insert')
def Thread_before_insert(mapper, connection, target):
    """Auto-set the active date from the last email in thread"""
    if target.date_active is not None:
        return
    session = object_session(target)
    last_email_date = session.query(Email.date).order_by(desc(Email.date)).limit(1).scalar()
    if last_email_date:
        target.date_active = last_email_date
    else:
        target.date_active = datetime.datetime.now()



class Category(Base):
    """
    A thread category
    """

    __tablename__ = "category"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(Unicode(255), nullable=False, unique=True)



class Vote(Base):
    """
    A User's vote on a message
    """

    __tablename__ = "vote"

    list_name = Column(Unicode(255), ForeignKey("list.name", ondelete="CASCADE"), nullable=False, primary_key=True)
    message_id = Column(Unicode(255), nullable=False, primary_key=True)
    user_id = Column(Unicode(255), ForeignKey("user.id"), nullable=False, primary_key=True, index=True)
    value = Column(Integer, nullable=False, index=True)
    mlist = relationship("List")

# composite foreign key, no other way to declare it
Vote.__table__.append_constraint(
    ForeignKeyConstraint(
        ["list_name", "message_id"],
        ["email.list_name", "email.message_id"],
        ondelete="CASCADE"
    ))
# composite indexes
Index("ix_vote_list_name_message_id",
      Vote.__table__.c.list_name, Vote.__table__.c.message_id)
