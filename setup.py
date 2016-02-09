from distutils.core import setup

files = [
    'LICENSE',
    'ui/*.py', 'ui/*.glade', 'ui/*.png',
    'ui/dialogs/*.py', 'ui/view_models/*.py', 'ui/listview_models/*.py',
    'src/*.py'
]

description = 'A GTK+ tool to create, delete and monitor CouchDB, AvanceDB, PouchDB and Cloudant replication jobs'

long_description = \
    'Replicate data between your CouchDB instances easily, for example:\n' \
    '* replicate a single database to multiple targets, remote or local\n' \
    '* replicate multiple databases to multiple targets\n' \
    '* drag and drop a database to replicate it\n' \
    '* drop the target database before replication\n' \
    '* continuous replication\n' \
    '* stored credentials and server details'

classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: X11 Applications :: Gnome',
    'Environment :: X11 Applications :: GTK',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved :: MIT License',
    'Natural Language :: English',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 3 :: Only',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Topic :: Database :: Front-Ends',
    'Topic :: Utilities'
]

setup(name='replication-monitor',
      version='0.1.0',
      author='Craig Minihan, Ripcord Software',
      author_email='craig@ripcordsoftware.com',
      url='https://github.com/RipcordSoftware/avancedb-replication-monitor',
      description=description,
      long_description=long_description,
      classifiers=classifiers,
      keywords=['couchdb', 'pouchdb', 'avancedb', 'cloudant' 'replication'],
      license='MIT',
      packages=['replication_monitor'],
      package_dir={'replication_monitor': '.'},
      package_data={'replication_monitor': files},
      scripts=['scripts/replication-monitor'],
      install_requires=['keyring >= 0.8.3', 'keyrings.alt >= 1.1']
      )
