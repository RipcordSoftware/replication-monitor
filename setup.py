from distutils.core import setup
from codecs import open

files = [
    'LICENSE', 'README.rst',
    'ui/*.py', 'ui/*.glade', 'ui/*.png',
    'ui/dialogs/*.py', 'ui/view_models/*.py', 'ui/listview_models/*.py',
    'src/*.py'
]

description = 'Replication Monitor - a GTK+ tool for AvanceDB, CouchDB, PouchDB and Cloudant'

with open('README.rst', 'r', 'utf-8') as f:
    readme = f.read()

long_description = readme + '\n'

classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: X11 Applications :: Gnome',
    'Environment :: X11 Applications :: GTK',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved :: MIT License',
    'Natural Language :: English',
    'Operating System :: POSIX :: Linux',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: MacOS :: MacOS X',
    'Programming Language :: Python :: 3 :: Only',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Topic :: Database :: Front-Ends',
    'Topic :: Utilities'
]

setup(name='replication-monitor',
      version='0.1.8',
      author='Craig Minihan, Ripcord Software',
      author_email='craig@ripcordsoftware.com',
      url='https://github.com/RipcordSoftware/replication-monitor',
      description=description,
      long_description=long_description,
      classifiers=classifiers,
      keywords=['couchdb', 'pouchdb', 'avancedb', 'cloudant', 'replication'],
      license='MIT',
      packages=['replication_monitor'],
      package_dir={'replication_monitor': '.'},
      package_data={'replication_monitor': files},
      scripts=['scripts/replication-monitor', 'scripts/replication-monitor.bat'],
      install_requires=['keyring >= 0.8.3', 'keyrings.alt >= 1.1', 'requests >= 2.4', 'bunch >= 1.0.1']
      )
