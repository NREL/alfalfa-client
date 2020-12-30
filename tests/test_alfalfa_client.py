import json

import hszinc

import alfalfa_client.alfalfa_client as ac
import alfalfa_client.historian as ah


class TestAlfalfaClient:
    def test_instantiation(self):
        client = ac.AlfalfaClient()
        assert client is not None
        assert client.url == 'http://localhost'

    def test_construct_point_write_grid(self):
        string_id = 'bfc28235-826e-4af0-8645-f93bd53cbb3b'
        point_id = hszinc.Ref(string_id)
        value = hszinc.Quantity(2)
        level = hszinc.Quantity(1)
        who = 'me'
        g = ac.AlfalfaClient.construct_point_write_grid(point_id, value, level, who)
        expected = {
            'meta': {'ver': '2.0'},
            'cols': [
                {'name': 'id'},
                {'name': 'value'},
                {'name': 'level'},
                {'name': 'who'},
            ],
            'rows': [{
                'id': f"r:{string_id}",
                'value': f"n:2.000000",
                'level': f"n:1.000000",
                'who': f"s:me"
            }]
        }
        assert hszinc.dump(g, hszinc.MODE_JSON) == json.dumps(expected)


class TestHistorian:
    def test_historian_instantiation(self):
        hist = ah.Historian()
        assert hist is not None
        assert hist.time_step == 1
