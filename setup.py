# -*- coding:utf-8 -*-
from distutils.core import setup

setup(
    name='django-tdaemon',
    license='MIT',
    version='0.1',
    description='Django test daemon',
    author='André Ericson',
    author_email='de.ericson@gmail.com',
    url='https://github.com/aericson/django-tdaemon',
    packages=['django_tdaemon'],
    scripts=['bin/django-tdaemon'],
    long_description="A test daemon to run django tests when file changes",
    install_requires=[
        'watchdog>=0.8.1',
    ],
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
    ])
