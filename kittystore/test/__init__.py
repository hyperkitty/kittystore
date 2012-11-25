# -*- coding: utf-8 -*-

import os


def get_test_file(*fileparts):
    return os.path.join(os.path.dirname(__file__), "testdata", *fileparts)
get_test_file.__test__ = False


class FakeList(object):
    # pylint: disable=R0903
    # (Too few public methods)
    def __init__(self, name):
        self.fqdn_listname = name
        self.display_name = None


