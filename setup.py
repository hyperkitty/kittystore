#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages

setup(
    name="KittyStore",
    version="0.1",
    description="A storage engine for GNU Mailman v3 archives",
    long_description=open('README.rst').read(),
    url="https://fedorahosted.org/hyperkitty/",
    packages=find_packages(exclude=["*.test", "test", "*.test.*"]),
    include_package_data=True,
    install_requires=[
        'mailman',
        'zope.interface',
        'SQLAlchemy==0.7.8',
        'python-dateutil < 2.0' # 2.0+ is for Python 3
        'mock',
        ],
    )
