from io import BytesIO, StringIO
from unittest import TestCase

from pysftp import CnOpts  # TODO switch out pysftp for paramiko

from sftpmock import MockSFTPServers, with_sftpmock


class SFTPMockerTest(TestCase):
    '''
    This tests core functionality of the "with_sftpmock" decorator
    '''

    def setUp(self):
        self.cnopts = CnOpts()
        self.cnopts.hostkeys = None

    @with_sftpmock({
        "test.com.br": {"Outbound": {"file.txt": "some text"}},
        "otherdomain.com": {"Outbound": {"another.TXT": "another text"}}
    })
    def test_fake_server_port_set_correctly(self):
        '''
        Tests if Connection was mocked to include the hostname -> port attribute (_fake_server_port)
        '''
        # Import needs to happen here because we want to use mocked Connection
        from paramiko import Transport

        assert hasattr(
            Transport, "_fake_server_port"), "Transport class should have mocked _fake_server_port attribute"

        assert isinstance(Transport._fake_server_port, dict)

        assert "test.com.br" in Transport._fake_server_port, "Transport should have 'test.com.br' as _fake_server_port key"
        assert "otherdomain.com" in Transport._fake_server_port, "Transport should have 'otherdomain.com' as _fake_server_port key"

        assert Transport._fake_server_port["test.com.br"] is not None, "Transport should have a port for 'test.com.br'"
        assert Transport._fake_server_port["otherdomain.com"] is not None, "Transport should have a port for 'otherdomain.com'"

        assert Transport._fake_server_port["test.com.br"] != Transport._fake_server_port[
            "otherdomain.com"], "Transport should have different ports for different hosts"

    @with_sftpmock({
        "test.com.br": {"a_folder": {"file.txt": "some text"}},
    })
    def test_getfo_operation(self):
        '''
        Test if Connection.getfo works as expected 
        '''
        # Import needs to happen here because we need to use mocked Connection
        from pysftp import Connection

        with Connection("test.com.br", port=22, username="user", password="pass", cnopts=self.cnopts) as client:
            outfile = BytesIO()
            client.getfo("/a_folder/file.txt", outfile)
            assert outfile.getvalue().decode('utf-8') == "some text"

    @with_sftpmock({
        "test.com.br": {"a_folder": {"file.txt": "some text"}},
    })
    def test_putfo_operation(self):
        '''
        Test if Connection.putfo works as expected 
        '''
        # Import needs to happen here because we need to use mocked Connection
        from pysftp import Connection

        with Connection("test.com.br", port=22, username="user", password="pass", cnopts=self.cnopts) as client:
            client.putfo(StringIO("texto aleatorio"),
                         "/a_folder/outro_arquivo")

            outfile = BytesIO()
            client.getfo("/a_folder/outro_arquivo", outfile)
            assert outfile.getvalue().decode('utf-8') == "texto aleatorio"

    @with_sftpmock({
        "test.com.br": {"a_folder": {"file.txt": "some text"}, "other_folder": {}},
    })
    def test_listdir_operation(self):
        '''
        Test if Connection.putfo works as expected 
        '''
        # Import needs to happen here because we need to use mocked Connection
        from pysftp import Connection

        with Connection("test.com.br", port=22, username="user", password="pass", cnopts=self.cnopts) as client:
            records = client.listdir()
            assert records == ["a_folder", "other_folder"], \
                f"Expected '[a_folder, other_folder]', found {records}"

            records = client.listdir("/")
            assert records == ["a_folder", "other_folder"], \
                f"Expected '[a_folder, other_folder]', found {records}"

            records = client.listdir("/a_folder")
            assert records == ["file.txt"], \
                f"Expected '[file.txt]', found {records}"

            records = client.listdir("/other_folder")
            assert records == [], \
                f"Expected '[]', found {records}"

    @with_sftpmock({
        "test.com.br": {"a_folder": {"coisa.txt": "some text"}},
        "otherdomain.com": {"a_folder": {"another.txt": "another text"}}
    })
    def test_both_connections_work_independently(self):
        '''
        Test if nested connections work correctly as two separate servers 
        '''
        # Import needs to happen here because we need to use mocked Connection
        from pysftp import Connection

        with Connection("test.com.br", port=22, username="user", password="pass", cnopts=self.cnopts) as client:
            records = client.listdir("/a_folder")
            assert records == ["coisa.txt"], \
                f"Expected '[coisa.txt]', found {records}"

            with Connection("otherdomain.com", port=22, username="user", password="pass", cnopts=self.cnopts) as outro_client:
                records = outro_client.listdir("/a_folder")
                assert records == ["another.txt"], \
                    f"Expected '[another.txt]', found {records}"

    def test_servers_are_shutdown_normally(self):
        '''
        Test if servers are shutdown when execution ends normally.

        We test MockSFTPServers directly because we need to check its variables
        '''
        servers_context = MockSFTPServers({
            "test.com.br": {"Outbound": {"EDI_020_20210704_023428_0017_004524526_000739.TXT": "some text"}},
            "otherdomain.com": {"Outbound": {"another.TXT": "another text"}}
        })

        assert not servers_context.host_servers, "Servers should not be started yet"

        with servers_context:
            assert all(server.port for server in servers_context.host_servers.values(
            )), "Servers should be started"

        assert all(not server.is_alive() for server in servers_context.host_servers.values()), \
            "Servers should be stopped"

    def test_servers_are_shutdown_exception(self):
        '''
        Test if servers are shutdown when an exception is raised

        We test MockSFTPServers directly because we need to check its variables
        '''
        servers_context = MockSFTPServers({
            "test.com.br": {"Outbound": {"EDI_020_20210704_023428_0017_004524526_000739.TXT": "some text"}},
            "otherdomain.com": {"Outbound": {"another.TXT": "another text"}}
        })

        assert not servers_context.host_servers, "Servers should not be started yet"

        try:
            with servers_context:
                assert all(server.port for server in servers_context.host_servers.values(
                )), "Servers should be started"
                raise Exception("Some error")
        except Exception as e:
            pass

        assert all(not server.is_alive() for server in servers_context.host_servers.values()), \
            "Servers should be stopped"
