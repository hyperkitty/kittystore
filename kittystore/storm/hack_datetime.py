# -*- coding: utf-8 -*-
#
# hack around a bug in storm: support for timezones is missing
# https://bugs.launchpad.net/storm/+bug/280708
#
# pylint: disable=C,W,R

import datetime
import re
from storm.locals import *
from storm.variables import _parse_date, _parse_time


RE_TIME = re.compile(r"""^
                          (?P<year>\d{4})\-(?P<month>\d{2})\-(?P<day>\d{2})        # pattern matching date
                          T                                                        # seperator
                          (?P<hour>\d{2})\:(?P<minutes>\d{2})\:(?P<seconds>\d{2})  # pattern matching time
                          (\.(?P<microseconds>\d{6}))?                             # pattern matching optional microseconds
                          (?P<tz_offset>[\-\+]\d{2}\:\d{2})?                       # pattern matching optional timezone offset
                         $""", re.VERBOSE)

def parse_time(time_str):
    x = RE_TIME.match(time_str)
    if not x:
        raise ValueError
    d = datetime.datetime(int(x.group("year")), int(x.group("month")),
        int(x.group("day")), int(x.group("hour")), int(x.group("minutes")),
        int(x.group("seconds")))
    if x.group("microseconds"):
        d = d.replace(microsecond=int(x.group("microseconds")))
    if x.group("tz_offset"):
        d = d.replace(tzinfo=TimeZone(x.group("tz_offset")))
    return d

class DateTimeVariableHack(DateTime.variable_class):

    def parse_set(self, value, from_db):
        if from_db:
            if isinstance(value, datetime.datetime):
                pass
            elif isinstance(value, (str, unicode)):
                if value.count(":") == 3: #additional timezone info
                    value = value.replace(" ", "T")
                    value = parse_time(value)
                else:
                    if " " not in value:
                        raise ValueError("Unknown date/time format: %r" % value)
                    date_str, time_str = value.split(" ")
                    value = datetime.datetime(*(_parse_date(date_str) +
                                       _parse_time(time_str)))
            else:
                raise TypeError("Expected datetime, found %s" % repr(value))
            if self._tzinfo is not None:
                if value.tzinfo is None:
                    value = value.replace(tzinfo=self._tzinfo)
                else:
                    value = value.astimezone(self._tzinfo)
        else:
            if type(value) in (int, long, float):
                value = datetime.datetime.utcfromtimestamp(value)
            elif not isinstance(value, datetime.datetime):
                raise TypeError("Expected datetime, found %s" % repr(value))
            if self._tzinfo is not None:
                value = value.astimezone(self._tzinfo)
        return value



class DateTime(DateTime):
    # Overwrite DateTime in Storm's locals
    # pylint: disable-msg=E0102
    variable_class = DateTimeVariableHack



class TimeZone(datetime.tzinfo):

    def __init__(self, tz_string):
        hours, minutes = tz_string.lstrip("-+").split(":")
        self.stdoffset = datetime.timedelta(hours=int(hours), minutes=int(minutes))
        if tz_string.startswith("-"):
            self.stdoffset *= -1

    def __repr__(self):
        return "TimeZone(%s)" %(self.stdoffset.days*24*60*60 + self.stdoffset.seconds)

    def utcoffset(self, dt):
        return self.stdoffset

    def dst(self, dt):
        return datetime.timedelta(0)
