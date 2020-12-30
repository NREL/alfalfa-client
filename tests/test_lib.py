import pytest
from datetime import datetime

import alfalfa_client.lib as acl


class TestCreateRunSiteMutation:

    @pytest.mark.parametrize('args, error', [
        ({}, 'url'),
        ({'url': 'http://localhost'}, 'site_id'),
        ({'url': 'http://localhost', 'site_id': 'abc'}, 'kwargs'),
    ])
    def test_required_args_raise_key_errors(self, args, error):
        try:
            acl.create_run_site_mutation(args)
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
    def test_kwargs_of_correct_type_dont_raise_type_error(self, create_run_site_mutation_default_args, parameter,
                                                          value):
        # -- Setup
        args = create_run_site_mutation_default_args
        args['kwargs'] = {parameter: value}
        _, _, mutation = acl.create_run_site_mutation(args)

        # -- Assert should get here
        assert True

    @pytest.mark.parametrize('parameter, value, expected', [
        ('timescale', "<class 'str'>", '(int, float)'),
        ('realtime', "<class 'str'>", 'bool'),
        ('external_clock', "<class 'str'>", 'bool'),
    ])
    def test_kwargs_of_incorrect_type_raise_type_error(self, create_run_site_mutation_default_args, parameter, value,
                                                       expected):
        # -- Setup
        args = create_run_site_mutation_default_args
        args['kwargs'] = {parameter: value}
        try:
            acl.create_run_site_mutation(args)

            # -- Should not get here
            assert False
        except TypeError as e:
            assert e.args[0] == f"Expected '{parameter}' of type: {expected}, got {value}"

    @pytest.mark.parametrize('parameter, value, error_type', [
        ('start_datetime', "2020-01-01 00:00:00", ValueError),
        ('end_datetime', "2020-01-01 00:00:00", ValueError),
        ('end_datetime', 1, TypeError)
    ])
    def test_datetime_kwargs_of_incorrect_type_raise_error(self, create_run_site_mutation_default_args, parameter,
                                                           value, error_type):
        # -- Setup
        args = create_run_site_mutation_default_args
        args['kwargs'] = {parameter: value}
        try:
            acl.create_run_site_mutation(args)

            # -- Should not get here
            assert False
        except error_type:
            # -- Should get here
            assert True

    @pytest.mark.parametrize('parameter, value', [
        ('realtime', True),
        ('realtime', False),
    ])
    def test_boolean_mutation_as_expected(self, create_run_site_mutation_default_args, parameter, value):
        # -- Setup
        args = create_run_site_mutation_default_args
        args['kwargs'] = {parameter: value}
        _, site_id, mutation = acl.create_run_site_mutation(args)

        # -- Define expectations
        expected_val = 'true' if value else 'false'
        # Double brackets escape brackets in f-string
        expected_mutation = f"mutation {{ runSite(siteRef: \"{site_id}\", {parameter}: {expected_val}) }}"

        # -- Assert
        assert mutation == expected_mutation
