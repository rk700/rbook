#!/usr/bin/env python

from distutils.core import setup

setup(name = 'rbook',
      version = '0.1.3',
      description = 'A Vim style document viewer',
      classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.7',
        'Topic :: Utilities',
      ],
      url = 'https://github.com/rk700/rbook',
      author = 'Ruikai Liu',
      author_email = 'lrk700@gmail.com',
      license = 'GPLv3+',
      packages = ['rbook'],
      scripts = ['bin/rbook'],
      data_files = [('/usr/share/rbook', ['manual.pdf'])]
     )
