# -*- coding: utf-8 -*-

import os

from mailman.interfaces.archiver import ArchivePolicy


def get_test_file(*fileparts):
    return os.path.join(os.path.dirname(__file__), "testdata", *fileparts)
get_test_file.__test__ = False


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

    def __init__(self, name):
        self.fqdn_listname = unicode(name)


class SettingsModule:
    KITTYSTORE_URL = "sqlite:"
    KITTYSTORE_SEARCH_INDEX = None
    MAILMAN_REST_SERVER = "http://localhost:8001"
    MAILMAN_API_USER = "testrestuser"
    MAILMAN_API_PASS = "testrestpass"
