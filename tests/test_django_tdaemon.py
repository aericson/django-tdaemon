# -*- coding:utf-8 -*-
import os
import sys
import time
import shutil
from unittest import TestCase
from subprocess import call as sub_call
from mock import patch, call
from django_tdaemon.tdaemon import run_for_all_apps, run_for_apps, Watcher

from importlib import import_module

import django_tdaemon


def create_tmp_dir(folder='test_tmp'):
    try:
        os.mkdir(folder)
    except OSError as err:
        if err.errno != 17:
            raise err
    return os.path.join(os.getcwd(), folder)


def tmp_dir_cleanup(folder):
    shutil.rmtree(folder)


class TestDjangoTDaemon(TestCase):

    @classmethod
    def _create_test_file(cls, app_path, n):
        filename = os.path.join(app_path, 'tests.py')
        with open(filename, "w")as test_file:
            test_file.write("from django.test import TestCase\n\n")
            test_file.write("class GeneratedTestCase(TestCase):\n\n")
            for i in range(n):
                test_file.write((' ' * 4) + "def test_%i(self):\n" % i)
                test_file.write((' ' * 8) + "self.assertTrue(True)\n\n")

    @classmethod
    def _create_app(cls, app, number_of_tests):
        app_path = os.path.join(cls.dir, app)
        os.mkdir(app_path)
        sub_call(
            ['django-admin', 'startapp', app, app_path]
        )
        cls._create_test_file(app_path, number_of_tests)

        with open(os.path.join(cls.proj_path, 'settings.py'), 'a') as f:
            f.write("INSTALLED_APPS += ('%s',)\n" % app)

    @classmethod
    def setUpClass(cls):
        cls.patcher = patch('django_tdaemon.tdaemon.TEST', new=True)
        cls.patcher.start()

        cls.dir = create_tmp_dir()
        sub_call(
            ['django-admin', 'startproject', 'test_proj',
             cls.dir])
        cls.proj_path = os.path.join(cls.dir, 'test_proj')
        sys.path.append(cls.dir)

        cls._create_app('app1', 1)

        cls._create_app('app2', 2)

    def setUp(self):
        self.settings = import_module('test_proj.settings')

    def test_run_all_tests(self):
        output = run_for_all_apps(self.dir)
        self.assertIn("Ran 3 tests", str(output))

    def test_run_for_app(self):
        output = run_for_apps(self.dir, ['app1'])
        self.assertIn("Ran 1 test", str(output))
        output = run_for_apps(self.dir, ['app2'])
        self.assertIn("Ran 2 test", str(output))

    def test_run_for_apps(self):
        output = run_for_apps(self.dir, ['app1', 'app2'])
        self.assertIn("Ran 3 test", str(output))

    def touch(self, filename):
        with open(filename, 'a'):
            os.utime(filename, None)

    @patch('django_tdaemon.tdaemon.run_for_all_apps')
    @patch('django_tdaemon.tdaemon.run_for_apps')
    def test_watcher_all(self, apps_mock, all_mock):
        watcher = Watcher(self.dir, self.settings)
        watcher.start()
        # import pdb; pdb.set_trace()
        self.touch(os.path.join(self.proj_path, 'settings.py'))
        time.sleep(1)
        watcher.stop()
        all_mock.assert_called_once_with(self.dir)
        self.assertFalse(apps_mock.called)

    @patch('django_tdaemon.tdaemon.run_for_all_apps')
    @patch('django_tdaemon.tdaemon.run_for_apps')
    def test_watcher_lonly(self, apps_mock, all_mock):
        watcher = Watcher(self.dir, self.settings)
        watcher.start()
        self.touch(os.path.join(self.dir, 'app1', 'admin.py'))
        time.sleep(1)
        watcher.stop()
        self.assertFalse(all_mock.called)
        apps_mock.assert_called_once_with(self.dir, ['app1'])

    @patch('django_tdaemon.tdaemon.run_for_all_apps')
    @patch('django_tdaemon.tdaemon.run_for_apps')
    def test_watcher_with_more_apps(self, apps_mock, all_mock):
        watcher = Watcher(self.dir, self.settings)
        watcher.start()
        watcher.pause()
        self.touch(os.path.join(self.dir, 'app1', 'admin.py'))
        self.touch(os.path.join(self.dir, 'app2', 'admin.py'))
        watcher.pause()
        time.sleep(1)
        watcher.stop()
        self.assertFalse(all_mock.called)
        self.assertTrue(apps_mock.called)
        app_list = ['app1', 'app2']
        a1 = call(self.dir, app_list) == apps_mock.call_args
        a2 = call(self.dir, app_list[::-1]) == apps_mock.call_args
        self.assertTrue(a1 or a2)

    @patch.object(django_tdaemon.tdaemon.Consumer, 'test')
    def test_event_on_create_py(self, test_mock):
        watcher = Watcher(self.dir, self.settings)
        watcher.start()
        self.touch(os.path.join(self.dir, 'app1', 'admin.py'))
        time.sleep(1)
        watcher.stop()

        test_mock.assert_called_with(
            [os.path.join(self.dir, 'app1', 'admin.py')]
        )

        self.assertTrue(test_mock.called)

    @patch.object(django_tdaemon.tdaemon.Consumer, 'test')
    def test_event_on_create_pyc(self, test_mock):
        watcher = Watcher(self.dir, self.settings)
        watcher.start()
        self.touch(os.path.join(self.dir, 'app1', 'admin.pyc'))
        time.sleep(1)
        watcher.stop()
        self.assertFalse(test_mock.called)

    @patch.object(django_tdaemon.tdaemon.Consumer, 'test')
    def test_event_on_create_tmp(self, test_mock):
        watcher = Watcher(self.dir, self.settings)
        watcher.start()
        self.touch(os.path.join(self.dir, 'app1', 'admin.tmp'))
        time.sleep(1)
        watcher.stop()
        self.assertFalse(test_mock.called)

    @patch.object(django_tdaemon.tdaemon.Consumer, 'test')
    def test_event_on_mv_tmp(self, test_mock):
        watcher = Watcher(self.dir, self.settings)
        watcher.start()
        self.touch(os.path.join(self.dir, 'app1', 'module.tmp'))
        os.rename(os.path.join(self.dir, 'app1', 'module.tmp'),
                  os.path.join(self.dir, 'app1', 'module.py'))
        time.sleep(1)
        watcher.stop()
        test_mock.assert_called_with(
            [os.path.join(self.dir, 'app1', 'module.py')]
        )

    @patch.object(django_tdaemon.tdaemon.Consumer, 'test')
    def test_create_and_mv_folder(self, test_mock):
        watcher = Watcher(self.dir, self.settings)
        watcher.start()
        os.mkdir(os.path.join(self.dir, 'app1', 'a_folder'))
        time.sleep(1)
        self.assertFalse(test_mock.called)
        open(os.path.join(self.dir, 'app1', 'a_folder', 'file.py'),
             "w").close()
        time.sleep(1)
        test_mock.assert_called_with(
            [os.path.join(self.dir, 'app1', 'a_folder', 'file.py')]
        )
        os.rename(os.path.join(self.dir, 'app1', 'a_folder'),
                  os.path.join(self.dir, 'app1', 'a_folder1'))
        time.sleep(2)
        test_mock.assert_called_with(
            [os.path.join(self.dir, 'app1', 'a_folder', 'file.py'),
             os.path.join(self.dir, 'app1', 'a_folder1', 'file.py')
             ]
        )
        watcher.stop()

    @classmethod
    def tearDownClass(cls):
        tmp_dir_cleanup(cls.dir)
        cls.patcher.stop()
