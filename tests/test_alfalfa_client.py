import alfalfa_client.alfalfa_client as ac
import alfalfa_client.historian as ah


class TestAlfalfaClient:
    def test_instantiation(self):
        client = ac.AlfalfaClient
        assert client is not None


class TestHistorian:
    def test_historian_instantiation(self):
        hist = ah.Historian
        assert hist is not None
