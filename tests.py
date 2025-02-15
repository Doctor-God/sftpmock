from io import BytesIO, StringIO
import socket
from unittest import TestCase

import paramiko

from sftpmock import SFTMock, with_sftpmock
from unittest import mock


class SFTPMockerTest(TestCase):
    '''
    This tests core functionality of the "with_sftpmock" decorator
    '''

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

        We test SFTMock directly because we need to check its variables
        '''
        servers_context = SFTMock({
            "test.com": {"Outbound": {"file.TXT": "some text"}},
            "otherdomain.com": {"Outbound": {"another.TXT": "another text"}}
        })

        assert not servers_context.host_servers, "Servers should not be started yet"

        with servers_context:
            assert all(server.port for server in servers_context.host_servers.values(
            )), "Servers should be started"

        assert all(not server.is_alive() for server in servers_context.host_servers.values()), \
            "Servers should be stopped"

        assert all(server.socket._closed for server in servers_context.host_servers.values()), \
            "All sockets should be closed"

    def test_servers_are_shutdown_exception(self):
        '''
        Test if servers are shutdown when an exception is raised

        We test SFTMock directly because we need to check its variables
        '''
        servers_context = SFTMock({
            "test.com": {"Outbound": {"file.TXT": "some text"}},
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

        assert all(server.socket._closed for server in servers_context.host_servers.values()), \
            "All sockets should be closed"

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
    })
    @mock.patch('socket.socket', spec=socket.socket)
    def test_init_with_socket(self, mock_socket):
        '''
        Test if Transport can be initialized with a socket as sock argument
        '''
        # Import needs to happen here because we need to use mocked Transport
        from paramiko import Transport

        mock_socket.return_value.getsockname.return_value = ("test.com", 22)

        serversocket = socket.socket()

        serversocket.connect(("test.com", 22))

        with Transport(serversocket) as transport:
            assert transport.hostname == "localhost"

    @with_sftpmock({
        "test.com": {},
    })
    def test_other_connections(self):
        '''
        Test if a non-mocked server is unnafected by the decorator
        '''
        # NOTE this test does an actual connection and tests if it fails, which it should
        # This also means this test is slighly slower, due to timeout not being changeable in this case

        # Import needs to happen here because we need to use mocked Transport
        from paramiko import Transport

        with mock.patch('socket.getaddrinfo') as mock_getaddrinfo:
            try:
                with Transport("example.com:22") as transport:
                    pass
            except:
                # This raises and exception because of the mocked getaddrinfo,
                # but we only want to know if the connection was attempted, meaning it was not mocked
                pass
            mock_getaddrinfo.assert_called_once_with(
                "example.com", 22, socket.AF_UNSPEC, socket.SOCK_STREAM)
