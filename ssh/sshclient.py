import paramiko.client
from paramiko import SSHClient


class SSH(object):

    def __init__(self, host, username, password, ssl_key=None):
        self.host = host
        self.username = username
        self.password = password
        self.ssl_key = ssl_key

        self.sshclient = SSHClient()
        self.sshclient.set_missing_host_key_policy(paramiko.client.AutoAddPolicy)
        self.sshclient.connect(self.host, username=self.username, password=self.password)


    def run_command(self, cmd):
        stdin, stdout, stderr = self.sshclient.exec_command(cmd)
        out = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        return out, error

    def get_file(self, remote_path, local_path):
        sftp = self.sshclient.open_sftp()
        return sftp.get(remote_path, local_path)


    def put_file(self, remote_path, local_path):
        sftp = self.sshclient.open_sftp()
        return sftp.put(local_path, remote_path)

    def get_transport_channel(self):
        return self.sshclient.get_transport().open_session()

    def close(self):
        self.sshclient.close()

