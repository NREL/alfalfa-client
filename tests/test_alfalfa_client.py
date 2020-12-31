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

    def test_get_highest_priority_value(self):
        data = {"meta": {"ver": "2.0"},
                "cols": [{"name": "level"}, {"name": "levelDis"}, {"name": "val"}, {"name": "who"}],
                "rows": [
            {"level": "n:1", "levelDis": "s:1"},
            {"level": "n:2", "levelDis": "s:2", "val": "n:0", "who": "s:alfalfa-client"},
            {"level": "n:3", "levelDis": "s:3"},
            {"level": "n:4", "levelDis": "s:4"},
            {"level": "n:5", "levelDis": "s:5"},
            {"level": "n:6", "levelDis": "s:6"},
            {"level": "n:7", "levelDis": "s:7"},
            {"level": "n:8", "levelDis": "s:8"},
            {"level": "n:9", "levelDis": "s:9"},
            {"level": "n:10", "levelDis": "s:10"},
            {"level": "n:11", "levelDis": "s:11"},
            {"level": "n:12", "levelDis": "s:12"},
            {"level": "n:13", "levelDis": "s:13"},
            {"level": "n:14", "levelDis": "s:14"},
            {"level": "n:15", "levelDis": "s:15"},
            {"level": "n:16", "levelDis": "s:16"},
            {"level": "n:17", "levelDis": "s:17"}
        ]}
        grid = hszinc.parse(data, hszinc.MODE_JSON)
        highest_value = ac.AlfalfaClient.get_highest_priority_value(grid)
        assert highest_value == 0


class TestHistorian:
    def test_historian_instantiation(self):
        hist = ah.Historian()
        assert hist is not None
        assert hist.time_step == 1
