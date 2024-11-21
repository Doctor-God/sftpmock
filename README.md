# sftpmock


## Known Issues / Limitations
- Trying to test transport.sock hostname and ports may result in errors, as they are replaced by localhost and a random local port
- SSHClient may be replaced by a local server, as it also uses paramiko.Transport (need to test this still)