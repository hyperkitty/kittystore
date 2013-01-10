==========
KittyStore
==========

KittyStore is the archiving library for `HyperKitty`_, the Mailman 3 archiver.
It provides an interface to different storage systems. Currently only the
`Storm ORM`_ system is supported.

.. _HyperKitty: https://fedorahosted.org/hyperkitty
.. _Storm ORM: http://storm.canonical.com

The code is available from: https://github.com/hyperkitty/kittystore


Populating the database
=======================

- Retrieve the archives by calling ``kittystore-download21``,
- Load the archives by calling ``kittystore-import``.

This might be memory intensive, so you may want to do 2 or 3 years per run and
split the runs.

Alternatively, to load the data you may want to do something like::

    for i in lists/devel-*; do kittystore-import -l devel@fp.o $i; done;


License
=======

The authors are listed in the ``AUTHORS.txt`` file.

Copyright (C) 2012 by the Free Software Foundation, Inc.

``KittyStore`` is licensed under the `GPL v3.0`_

.. _GPL v3.0: http://www.gnu.org/licenses/gpl-3.0.html
