# -*- coding: utf-8 -*-

# Copyright (C) 2013-2014 by the Free Software Foundation, Inc.
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
Events dispatched throughout the application, and functions to subscribe and
emit them.

Author: Aurelien Bompard <abompard@fedoraproject.org>
"""

from collections import defaultdict, namedtuple


subscribers = defaultdict(list)


def subscribe(target, eventclass):
    subscribers[eventclass].append(target)

def notify(event):
    for sub in subscribers[event.__class__]:
        sub(event)

def subscribe_to(eventclass):
    def wrapper(f):
        subscribe(f, eventclass)
        return f
    return wrapper

NewMessage = namedtuple("NewMessage", ["store", "mlist", "message"])
NewThread = namedtuple("NewThread", ["store", "mlist", "thread"])
