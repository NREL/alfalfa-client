import json

import hszinc
import pytest

import alfalfa_client.alfalfa_client as ac
import alfalfa_client.historian as ah


class TestAlfalfaClient:
    def test_instantiation(self):
        client = ac.AlfalfaClient()
        assert client is not None
        assert client.url == 'http://localhost'

    @pytest.mark.parametrize('pre_typed', [
        True,
        False
    ])
    def test_construct_point_write_grid(self, pre_typed):
        point_id = 'bfc28235-826e-4af0-8645-f93bd53cbb3b'
        value = 2
        level = 1
        who = 'me'
        if pre_typed:
            new_point_id = hszinc.Ref(point_id)
            new_value = hszinc.Quantity(value)
            new_level = hszinc.Quantity(level)
        else:
            new_point_id = point_id
            new_value = value
            new_level = level
        g = ac.AlfalfaClient.construct_point_write_grid(new_point_id, new_value, new_level, who)
        expected = {
            'meta': {'ver': '2.0'},
            'cols': [
                {'name': 'id'},
                {'name': 'val'},
                {'name': 'level'},
                {'name': 'who'},
            ],
            'rows': [{
                'id': f"r:{point_id}",
                'val': f"n:2.000000",
                'level': f"n:1.000000",
                'who': f"s:me"
            }]
        }
        assert hszinc.dump(g, hszinc.MODE_JSON) == json.dumps(expected)

    @pytest.mark.parametrize('pre_typed', [
        True,
        False
    ])
    def test_construct_point_write_read_val_grid(self, pre_typed):
        point_id = 'bfc28235-826e-4af0-8645-f93bd53cbb3b'
        if pre_typed:
            new_point_id = hszinc.Ref(point_id)
        else:
            new_point_id = point_id

        expected = {
            'meta': {'ver': '2.0'},
            'cols': [
                {'name': 'id'}
            ],
            'rows': [{
                'id': f"r:{point_id}"
            }]
        }
        g = ac.AlfalfaClient.construct_point_write_read_val_grid(new_point_id)
        assert hszinc.dump(g, hszinc.MODE_JSON) == json.dumps(expected)

    def test_construct_advance_mutation(self):
        site_ids = ['abc', 'def']
        mutation = ac.AlfalfaClient.construct_advance_mutation(site_ids)
        assert mutation == 'mutation { advance(siteRefs: ["abc", "def"]) }'


class TestHistorian:
    def test_historian_instantiation(self):
        hist = ah.Historian()
        assert hist is not None
        assert hist.time_step == 1
