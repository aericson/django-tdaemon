## django-tdaemon

[![Build Status](https://travis-ci.org/aericson/django-tdaemon.svg?branch=master)](https://travis-ci.org/aericson/django-tdaemon)
[![Coverage Status](https://coveralls.io/repos/aericson/django-tdaemon/badge.png)](https://coveralls.io/r/aericson/django-tdaemon)

Test daemon for Django. Based on https://github.com/brunobord/tdaemon

Will try to find the app where changes were made and run test only for the app.
If cannot find it or changes that affects the whole project all tests will be run.

It won't notice that tests from other apps use an app that changed.
i.e: changes in app accounts but tests from bank app uses accounts.
Only accounts tests will be run.

### Installation

git clone this repository and then:

    pip install -e .

from an activated virtualenv.

### Usage

    Usage: Usage: %[prog] [options] [<path>]

Options:

    -h, --help            show this help message and exit
    -s SETTINGS, --settings=SETTINGS
                        Django settings module ie: proj_name.settings. The
                        default will try to guess from the path passed or by
                        using the currrent directory.
