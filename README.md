# sftpmock
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Tests](https://github.com/Doctor-God/sftpmock/actions/workflows/test.yml/badge.svg?branch=main) 

## Known Issues / Limitations
- Trying to test transport.sock hostname and ports may result in errors, as they are replaced by localhost and a random local port
- SSHClient may be replaced by a local server, as it also uses paramiko.Transport (need to test this still)
- If you are using sockets to init a Transport, you may need to mock them first
- If the SFTP servers being tested are actually localhost, this won't work

## Future improvements
- Not depend on pytest-sftpserver package
- Allow for server port differentiation
- Avoid affecting SSHClient with our mock
- Test for initializing SFTPClient directly (not using "with_transport" method)