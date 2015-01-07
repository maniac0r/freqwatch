#!/usr/bin/env python2
import os
import sys
from setuptools import setup, find_packages


setup(
    name = 'freqwatch',
    version = '0.2',
    packages = find_packages(),
    scripts = ['freqwatch.py'],
    description='Keep track of the airwaves with RTL-SDR',
    url='https://github.com/covertcodes/freqwatch',
    install_requires=['MySQL-python', 'pyrtlsdr', 'iniparse >= 0.4']
)

