from functools import wraps
from inspect import getcallargs
from typing import Dict

import pysftp  # TODO switch out to use paramiko directly
from pytest_sftpserver.sftp.server import SFTPServer
import paramiko
from socket import socket
from server import FixedContentProvider


class MockSFTPServers(object):
    '''
    Act as a context to make local SFTP servers run for its duration

    Inspired by httmock's implementation
    '''

    # TODO have ways to test authentication errors by saving provided fake credentials

    def __init__(self, host_contents: dict):
        '''
        host_contents should be in the format:
        {
            "hostname": {
                "path": "content",
                "path2": "content2",
            }
        }
        '''

        self.host_contents = host_contents
        # set when servers start on __enter__
        self.host_servers: Dict[str, SFTPServer] = {}

    def __enter__(self):
        # We ignore original port, but there is a small likelyhoood of having two FTPs on the same hostname
        for host, content in self.host_contents.items():
            # NOTE this opens a server on a Thread, in the future we might want to
            # mock server further to make it more like HTTMock and use only python objects and functions internally
            server = SFTPServer(
                content, content_provider_class=FixedContentProvider)
            server.start()
            self.host_servers[host] = server

        self._real_SFTPClient__init__ = paramiko.SFTPClient.__init__

        def _fake_SFTPClient__init__(*args, **kwargs):
            '''
            This is meat to replace SFTPClient.__init__ to always connect to localhost
            on the fake servers we created
            '''
            # Transform all arguments into kwargs, to allow us to replace some of them
            kwargs = getcallargs(
                self._real_SFTPClient__init__, *args, **kwargs)
            sftpclient_self = kwargs.get("self")
            sock = kwargs.pop("sock")

            real_host = None
            real_port = None
            if isinstance(sock, socket):
                real_host = sock.getsockname()[0]
                real_port = sock.getsockname()[1]
            elif isinstance(sock, tuple):
                real_host, real_port = sock  # remove host and port that were passed
            elif isinstance(sock, str):
                real_host, real_port = sock.split(":")
            else:
                raise ValueError(
                    "sock argument must be a socket, a tuple or a string")

            print(real_host, '  ', real_port)

            # NOTE this prevents paramiko usage on pytest_sftpserver from breaking
            if real_host not in ("localhost", "127.0.0.1"):
                self._real_SFTPClient__init__(
                    sock=("localhost", sftpclient_self._fake_server_port[real_host]), **kwargs)
            else:
                self._real_SFTPClient__init__(sock=sock, **kwargs)

        # Make paramiko.SFTPClient use our fake functions
        paramiko.SFTPClient.__init__ = _fake_SFTPClient__init__
        paramiko.SFTPClient._fake_server_port = {
            host: server.port for host, server in self.host_servers.items()}

    def __exit__(self, type, value, traceback):
        # Stop servers
        for server in self.host_servers.values():
            server.shutdown()
            server.join()

        # Restore SFTPClient to its original state
        paramiko.SFTPClient.__init__ = self._real_SFTPClient__init__
        del paramiko.SFTPClient._fake_server_port


def with_sftpmock(host_contents: dict = {}):
    '''
    Decorator to makes the specified SFTP connections use a local, fake server

    This ONLY works on the pysftp library, any other library will still try to connect to the real server

    host_contents should be in the format:
        {
            "hostname": {
                "path": "content",
                "path2": "content2",
            }
        }
    '''

    # Create a local, fake server
    servers_context = MockSFTPServers(host_contents)

    def decorator(func):
        @ wraps(func)
        def inner(*inner_args, **kwargs):
            # Create a local server and replace Connection.__init__ to force connection to that server
            with servers_context:
                return func(*inner_args, **kwargs)
        return inner
    return decorator
