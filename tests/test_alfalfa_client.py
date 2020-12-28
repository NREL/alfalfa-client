from alfalfa_client import __version__
import alfalfa_client.alfalfa_client as ac
import alfalfa_client.historian as ah


def test_version():
    assert __version__ == '0.1.0.dev5'


class TestAlfalfaClient:
    def test_instantiation(self):
        client = ac.AlfalfaClient
        assert client is not None


class TestHistorian:
    def test_historian_instantiation(self):
        hist = ah.Historian
        assert hist is not None
