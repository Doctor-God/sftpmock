from pytest_sftpserver.sftp.content_provider import ContentProvider
from pytest_sftpserver.sftp.server import SFTPServer


class FixedContentProvider(ContentProvider):  # fixes default content_object
    '''
    This fixes broken behavior on the default ContentProvider.

    Obtained from https://github.com/ulope/pytest-sftpserver/issues/29
    '''

    def __init__(self, content_object=None):
        self.content_object = content_object or {}

    def is_dir(self, path):  # fixes wrong mode attr on binary uploads
        return not isinstance(self.get(path), (bytes, str, int))

    def _find_object_for_path(self, path):  # fixes adding to empty storage
        if path == '':
            return self.content_object
        else:
            return super()._find_object_for_path(path)
