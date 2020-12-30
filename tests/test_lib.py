import pytest
import requests
from datetime import datetime

import alfalfa_client.lib as acl


class TestStartOne:

    @pytest.mark.parametrize('args, error', [
        ({}, 'url'),
        ({'url': 'http://localhost'}, 'site_id'),
        ({'url': 'http://localhost', 'site_id': 'abc'}, 'kwargs'),
    ])
    def test_required_args_raise_key_errors(self, args, error):
        try:
            acl.start_one(args)
        except KeyError as e:
            assert e.args[0] == error

    @pytest.mark.parametrize('parameter, value', [
        ('timescale', 1),
        ('realtime', True),
        ('realtime', False),
        ('external_clock', True),
        ('external_clock', False),
        ('start_datetime', datetime(2020, 1, 1, 0, 0, 0)),
        ('end_datetime', datetime(2020, 1, 1, 0, 0, 0)),
        ('start_datetime', "2020-01-01T00:00:00"),
        ('end_datetime', "2020-01-01T00:00:00")
    ])
    def test_kwargs_of_correct_type_dont_raise_type_error(self, start_one_default_args, parameter, value):
        # Make sure no Alfalfa server is running
        args = start_one_default_args
        args['kwargs'] = {parameter: value}
        try:
            acl.start_one(args)

            # -- Should not get here
            assert False
        except requests.exceptions.ConnectionError:
            # -- Should get here
            assert True

    @pytest.mark.parametrize('parameter, value, expected', [
        ('timescale', "<class 'str'>", '(int, float)'),
        ('realtime', "<class 'str'>", 'bool'),
        ('external_clock', "<class 'str'>", 'bool'),
    ])
    def test_kwargs_of_incorrect_type_raise_type_error(self, start_one_default_args, parameter, value, expected):
        # Make sure no Alfalfa server is running
        args = start_one_default_args
        args['kwargs'] = {parameter: value}
        try:
            acl.start_one(args)

            # -- Should not get here
            assert False
        except TypeError as e:
            assert e.args[0] == f"Expected '{parameter}' of type: {expected}, got {value}"

    @pytest.mark.parametrize('parameter, value, error_type', [
        ('start_datetime', "2020-01-01 00:00:00", ValueError),
        ('end_datetime', "2020-01-01 00:00:00", ValueError),
        ('end_datetime', 1, TypeError)
    ])
    def test_datetime_kwargs_of_incorrect_type_raise_error(self, start_one_default_args, parameter, value, error_type):
        # Make sure no Alfalfa server is running
        args = start_one_default_args
        args['kwargs'] = {parameter: value}
        try:
            acl.start_one(args)

            # -- Should not get here
            assert False
        except error_type:
            # -- Should get here
            assert True
