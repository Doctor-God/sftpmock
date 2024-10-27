from functools import wraps
from inspect import getcallargs
from typing import Dict

import pysftp  # TODO switch out to use paramiko directly
from pytest_sftpserver.sftp.server import SFTPServer
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

        self._real_Connection__init__ = pysftp.Connection.__init__

        def _fake_connection_init(*args, **kwargs):
            '''
            This is meat to replace Connection.__init__ to always connect to localhost
            on the fake servers we created
            '''
            # Transform all arguments into kwargs, to allow us to replace some of them
            kwargs = getcallargs(
                self._real_Connection__init__, *args, **kwargs)
            connection_self = kwargs.get("self")
            real_port = kwargs.pop("port")  # remove port that was passed
            real_host = kwargs.pop("host")  # remove host that was passed
            self._real_Connection__init__(
                host="localhost", port=connection_self._fake_server_port[real_host], **kwargs)

        # Make pysftp.Connection use our fake functions
        pysftp.Connection.__init__ = _fake_connection_init
        pysftp.Connection._fake_server_port = {
            host: server.port for host, server in self.host_servers.items()}

    def __exit__(self, type, value, traceback):
        # Stop servers
        for server in self.host_servers.values():
            server.shutdown()
            server.join()

        # Restore Connection to its original state
        pysftp.Connection.__init__ = self._real_Connection__init__
        del pysftp.Connection._fake_server_port


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
