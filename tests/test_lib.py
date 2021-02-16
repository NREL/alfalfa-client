"""
****************************************************************************************************
:copyright (c) 2008-2021 URBANopt, Alliance for Sustainable Energy, LLC, and other contributors.

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted
provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions
and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this list of conditions
and the following disclaimer in the documentation and/or other materials provided with the
distribution.

Neither the name of the copyright holder nor the names of its contributors may be used to endorse
or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
****************************************************************************************************
"""

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

    @pytest.mark.parametrize('parameter, mutated_param, value', [
        ('realtime', 'realtime', True),
        ('timescale', 'timescale', False),
        ('external_clock', 'externalClock', False),
    ])
    def test_boolean_mutation_as_expected(self, create_run_site_mutation_default_args, parameter, mutated_param, value):
        # -- Setup
        args = create_run_site_mutation_default_args
        args['kwargs'] = {parameter: value}
        _, site_id, mutation = acl.create_run_site_mutation(args)

        # -- Define expectations
        expected_val = 'true' if value else 'false'

        # Double brackets escape brackets in f-string
        expected_mutation = f"mutation {{ runSite(siteRef: \"{site_id}\", {mutated_param}: {expected_val}) }}"

        # -- Assert
        assert mutation == expected_mutation
