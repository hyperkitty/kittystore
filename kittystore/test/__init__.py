# -*- coding: utf-8 -*-

import os
import datetime

from mailman.interfaces.archiver import ArchivePolicy


def get_test_file(*fileparts):
    return os.path.join(os.path.dirname(__file__), "testdata", *fileparts)
get_test_file.__test__ = False


#def drop_all_tables(db):
#    # http://stackoverflow.com/questions/525512/drop-all-tables-command
#    db.rollback()
#    db.execute("PRAGMA writable_schema = 1")
#    db.execute("DELETE FROM sqlite_master WHERE type = 'table' OR type = 'index'")
#    db.execute("PRAGMA writable_schema = 0")

class FakeList(object):
    """
    This is a fake Mailman list (implementing the IMailingList interface).
    It is not the same as the kittystore model list.
    """
    # pylint: disable=R0903
    # (Too few public methods)
    display_name = None
    description = None
    subject_prefix = None
    archive_policy = ArchivePolicy.public
    created_at = datetime.datetime.utcnow()

    def __init__(self, name):
        self.fqdn_listname = unicode(name)


class SettingsModule:
    KITTYSTORE_URL = "sqlite:"
    KITTYSTORE_SEARCH_INDEX = None
    MAILMAN_REST_SERVER = "http://localhost:8001"
    MAILMAN_API_USER = "testrestuser"
    MAILMAN_API_PASS = "testrestpass"
