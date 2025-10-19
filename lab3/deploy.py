# This script is used to deploy the local files of the current folder into the VM
# and execute the final commands in deploy.sh
import argparse
from scp import SCPClient
from paramiko import SSHClient, AutoAddPolicy
import os.path

import configparser

def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config


config = load_config()

PRIVATE_KEYPAIR_FILE = config.get('switch', 'private_keypair_file')
CLOUDS_YAML = config.get('switch', 'clouds_yaml')
FILES_TO_UPLOAD = ["deploy.sh", "config.ini", CLOUDS_YAML, PRIVATE_KEYPAIR_FILE, "azure-db-key.txt", "vertexai-service-account-key.json"]
DEPLOY_ROOT_FOLDER = '/home/ubuntu'

def deploy(username, host):
    # Make sure all FILES_TO_UPLOAD do exist
    for file in FILES_TO_UPLOAD:
        if not os.path.isfile(file):
            print(f"Error: file {file} should exist for the deployment !")
            return

    ssh = SSHClient()

    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(host, 22, username, key_filename=PRIVATE_KEYPAIR_FILE)

    scp = SCPClient(ssh.get_transport())

    # Last safety measure to avoid uploading files from the wrong directory...
    if not os.path.isfile("chatbot.py"):
        print("Chatbot not found, probably incorrect folder")
        return

    print("Uploading current folder into the VM")
    scp.put('./', recursive=True, remote_path=DEPLOY_ROOT_FOLDER)

    scp.close()

    print("Starting deploy.sh on the VM")

    # Execute and capture output
    stdin, stdout, stderr = ssh.exec_command(f"cd {DEPLOY_ROOT_FOLDER} && bash deploy.sh")

    # Print output in real-time
    while True:
        line = stdout.readline()
        if not line:
            break
        print(line, end='')

    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        for line in stderr.readlines():
            print(f"ERROR: {line}", end='')
        print(f"\nDeployment failed with exit status {exit_status}")
        return

    print(f"\n\nCHATBOT HAS BEEN DEPLOYED...\nPlease open http://{host}:8501 in your Web browser !")


if __name__ == "__main__":
    # parse arg
    parser = argparse.ArgumentParser(description="Give the VM hostname")
    parser.add_argument("--host", type=str, help="hostname")
    args = parser.parse_args()

    deploy("ubuntu", args.host)
