|replmon| Replication Monitor
=============================
A GTK+ desktop app which can create, monitor and delete AvanceDB, CouchDB, PouchDB or IBM Cloudant replication jobs.
Runs on Linux/Gnome but can be persuaded to run on `Windows <https://github.com/RipcordSoftware/replication-monitor/wiki/Platform:-Windows>`_ or `OSX <https://github.com/RipcordSoftware/replication-monitor/wiki/Platform:-OSX>`_.

Features:
---------
- Create new replications: single, multiple, to/from remote, drag and drop replication
- View active replication tasks
- Create and delete databases
- Compact databases
- Set database revisions
- Browse to selected databases
- Backup and restore databases

Requirements:
-------------
- Python 3
- GTK+ (pygobject)
- Keyring
- Requests

Installation
------------
Install the latest release on ``pypi`` with ``pip``:

.. code-block:: bash

    $ pip3 install replication-monitor

Alternately pull the latest code from our ``github`` repository:

.. code-block:: bash

    $ git clone https://github.com/RipcordSoftware/replication-monitor.git
    $ cd replication-monitor
    $ ./replication_monitor.py

If you clone from ``git`` make sure you satisfy the ``requirements.txt`` file.

.. |replmon| image:: https://raw.githubusercontent.com/RipcordSoftware/replication-monitor/master/ui/replication-monitor-small.png