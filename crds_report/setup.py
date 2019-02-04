#!/usr/bin/env python
import os.path
import glob 

from distutils.core import setup


import setuptools

setup_pars = {
    "packages" : [
        'crds_report',
        ],
    "package_dir" : {
        'crds_report' : 'crds_report',
        },
    "package_data" : {
        'crds_report': [
            '*.html',
            '*.css',
            ],
        },
    "scripts" : glob.glob("scripts/*"),
    }

setup(name="crds_report",
      provides=["crds_report"],
      version = '7.3.1',
      description="Calibration Reference Data System,  automated weekly and monthly status report",
      long_description=open('README.rst').read(),
      author="Todd Miller",
      author_email="jmiller@stsci.edu",
      license="BSD",
      zip_safe=False,
      classifiers=[
          'License :: OSI Approved :: BSD License',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python :: 3',
      ],
      **setup_pars
)

