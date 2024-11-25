from io import BytesIO, StringIO
import socket
from unittest import TestCase

import paramiko
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
        "test.com": {"Outbound": {"file.txt": "some text"}},
        "otherdomain.com": {"Outbound": {"another.TXT": "another text"}}
    })
    def test_fake_server_port_set_correctly(self):
        '''
        Tests if Connection was mocked to include the hostname -> port attribute (_fake_server_port)
        '''
        # Import needs to happen here because we want to use mocked Transport
        from paramiko import Transport

        assert hasattr(
            Transport, "_fake_server_port"), "Transport class should have mocked _fake_server_port attribute"

        assert isinstance(Transport._fake_server_port, dict)

        assert "test.com" in Transport._fake_server_port, "Transport should have 'test.com' as _fake_server_port key"
        assert "otherdomain.com" in Transport._fake_server_port, "Transport should have 'otherdomain.com' as _fake_server_port key"

        assert Transport._fake_server_port["test.com"] is not None, "Transport should have a port for 'test.com'"
        assert Transport._fake_server_port["otherdomain.com"] is not None, "Transport should have a port for 'otherdomain.com'"

        assert Transport._fake_server_port["test.com"] != Transport._fake_server_port[
            "otherdomain.com"], "Transport should have different ports for different hosts"

    @with_sftpmock({
        "test.com": {"a_folder": {"file.txt": "some text"}},
    })
    def test_getfo_operation(self):
        '''
        Test if SFTPClient.getfo works as expected 
        '''
        # Import needs to happen here because we need to use mocked Transport
        from paramiko import Transport

        with Transport(("test.com", 22)) as transport:
            transport.connect(None, "user", "pass")
            client = paramiko.SFTPClient.from_transport(transport)

            outfile = BytesIO()
            client.getfo("/a_folder/file.txt", outfile)
            assert outfile.getvalue().decode('utf-8') == "some text"

    @with_sftpmock({
        "test.com": {"a_folder": {"file.txt": "some text"}},
    })
    def test_putfo_operation(self):
        '''
        Test if Connection.putfo works as expected 
        '''
        # Import needs to happen here because we need to use mocked Transport
        from paramiko import Transport

        with Transport(("test.com", 22)) as transport:
            transport.connect(None, "user", "pass")
            client = paramiko.SFTPClient.from_transport(transport)

            client.putfo(StringIO("texto aleatorio"),
                         "/a_folder/outro_arquivo")

            outfile = BytesIO()
            client.getfo("/a_folder/outro_arquivo", outfile)
            assert outfile.getvalue().decode('utf-8') == "texto aleatorio"

    @with_sftpmock({
        "test.com": {"a_folder": {"file.txt": "some text"}, "other_folder": {}},
    })
    def test_listdir_operation(self):
        '''
        Test if Connection.putfo works as expected 
        '''
        # Import needs to happen here because we need to use mocked Transport
        from paramiko import Transport

        with Transport(("test.com", 22)) as transport:
            transport.connect(None, "user", "pass")
            client = paramiko.SFTPClient.from_transport(transport)

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
        "test.com": {"a_folder": {"coisa.txt": "some text"}},
        "otherdomain.com": {"a_folder": {"another.txt": "another text"}}
    })
    def test_both_connections_work_independently(self):
        '''
        Test if nested connections work correctly as two separate servers 
        '''
        # Import needs to happen here because we need to use mocked Transport
        from paramiko import Transport

        with Transport(("test.com", 22)) as transport:
            transport.connect(None, "user", "pass")
            client = paramiko.SFTPClient.from_transport(transport)

            records = client.listdir("/a_folder")
            assert records == ["coisa.txt"], \
                f"Expected '[coisa.txt]', found {records}"

            with Transport(("otherdomain.com", 22)) as transport:
                transport.connect(None, "user", "pass")
                other_client = paramiko.SFTPClient.from_transport(transport)

                records = other_client.listdir("/a_folder")
                assert records == ["another.txt"], \
                    f"Expected '[another.txt]', found {records}"

    def test_servers_are_shutdown_normally(self):
        '''
        Test if servers are shutdown when execution ends normally.

        We test MockSFTPServers directly because we need to check its variables
        '''
        servers_context = MockSFTPServers({
            "test.com": {"Outbound": {"EDI_020_20210704_023428_0017_004524526_000739.TXT": "some text"}},
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
            "test.com": {"Outbound": {"EDI_020_20210704_023428_0017_004524526_000739.TXT": "some text"}},
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

    @with_sftpmock({
        "test.com": {},
    })
    def test_init_with_string(self):
        '''
        Test if Transport can be initialized with a string as sock argument
        '''
        # Import needs to happen here because we need to use mocked Transport
        from paramiko import Transport

        with Transport("test.com:22") as transport:
            assert transport.hostname == "localhost"

    @with_sftpmock({
        "test.com": {},
    })
    def test_init_with_tuple(self):
        '''
        Test if Transport can be initialized with a tuple as sock argument
        '''
        # Import needs to happen here because we need to use mocked Transport
        from paramiko import Transport

        with Transport(("test.com", 22)) as transport:
            assert transport.hostname == "localhost"

    @with_sftpmock({
        "test.com": {},
    },
        mock_socket_bind=True)
    def test_init_with_socket(self):
        '''
        Test if Transport can be initialized with a socket as sock argument
        '''
        # Import needs to happen here because we need to use mocked Transport
        from paramiko import Transport

        # TODO fix this behavior, maybe have a flag to make sure socket bind works?

        serversocket = socket.socket()

        serversocket.bind(("test.com", 22))

        with Transport(serversocket) as transport:
            assert transport.hostname == "localhost"

    @with_sftpmock({
        "test.com": {},
    })
    def _test_init_client_directly(self):
        '''
        Test if using SFTPClient.__init__ works as expected
        '''
        # TODO maybe this test does not make sense
        # Also can't figure out how to make Channel work

        # Import needs to happen here because we need to use mocked Transport
        from paramiko import SFTPClient

        channel = paramiko.Channel(1)

        print(channel.getpeername())

        # channel.co

        # with SFTPClient(channel) as client:
        #     assert client.transport.hostname == "localhost"

    # TODO add tests to check so other forms of using paramiko client like:
    #   - Not creating client without transport
    #       - Cant figure out to to use paramiko.Channel. Maybe this test is unecessary
    #   - Using SSHClient instead of SFTPClient
    #   - Connecting socket before using Transport (if that even is possible)
