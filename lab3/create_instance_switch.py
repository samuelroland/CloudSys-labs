import argparse
import os.path
from openstack import connection
from openstack.config import OpenStackConfig

# A very hacky way to copy file to a remote server
# with a shell command containing their content in the command directly
#
# If the file is config.ini, the bash command is this
# cat <<EOT > config.ini
# <config.ini content is given here>
# EOT
def gen_bash_copy_files(files):
    commands = ""
    for file in files:
        with open(file, 'r') as file:
            content = file.read()
        commands += f"""
printf '%s' '{content}
' > {file.name}
"""
    return commands


IMAGE_NAME = "Ubuntu Jammy 22.04 (SWITCHengines)"
FLAVOR_NAME = "m1.small"
NETWORK_NAME = "private"
SERVER_NAME = "groupd-labo1"
KEYPAIR_NAME = "switchengine-tsm-cloudsys"
PRIVATE_KEYPAIR_FILE = f"./switch/{KEYPAIR_NAME}.pem"
CLOUDS_YAML = "./switch/clouds.yaml"
CONFIG_INI_CONTENT = ''
FILES_TO_UPLOAD = ["init.sh", "config.ini", CLOUDS_YAML, PRIVATE_KEYPAIR_FILE, "azure-db-key.txt", "vertexai-service-account-key.json"]
FILES_COPY_CMDS = gen_bash_copy_files(FILES_TO_UPLOAD)
# The script that runs when the VM has been created, which serves as a way to install dependencies and deploy our app
# Most of the content is written in init.sh for ease of editing
VM_SETUP_SCRIPT = "#!/bin/bash\ncurl -d 'starting script' ntfy.sh/superchatbot && cd $HOME && mkdir deploy && cd deploy && mkdir switch\nbash init.sh\n{0}\nPATH=$PATH:$HOME/.local/bin streamlit run chatbot.py".format(FILES_COPY_CMDS)

def list_images_dispo(conn):
    print("Available Server:")
    for img in conn.compute.images():
        print(img.name)
        break

def create_server(conn):
    print("Create Server:")
    image = conn.compute.find_image(IMAGE_NAME)
    flavor = conn.compute.find_flavor(FLAVOR_NAME)
    network = conn.network.find_network(NETWORK_NAME)
    keypair = conn.compute.find_keypair(KEYPAIR_NAME)
    if keypair is None:
        keypair = conn.compute.create_keypair(name=KEYPAIR_NAME)
        with open(PRIVATE_KEYPAIR_FILE, "w") as f:
            f.write(keypair.private_key)

    # Make sure all FILES_TO_UPLOAD do exist
    for file in FILES_TO_UPLOAD:
        if not os.path.isfile(file):
            print(f"Error: file {file} should have been manually created to be uploaded !")
            return

    # Finally create the server and run the VM_SETUP_SCRIPT
    server = conn.compute.create_server(
        name=SERVER_NAME,
        image_id=image.id,
        flavor_id=flavor.id,
        networks=[{"uuid": network.id}],
        key_name=keypair.name,
        userdata=VM_SETUP_SCRIPT
    )
    server = conn.compute.wait_for_server(server)
    print(f"VM '{SERVER_NAME}' created.")

    # find public network
    public_net = None
    for net in conn.network.networks():
        if "public" in net.name.lower():
            public_net = net
            break
    if public_net is None:
        raise Exception("Unable to find public network for Floating IP.")

    floating_ip = conn.network.create_ip(floating_network_id=public_net.id)

    # Get VM port
    ports = list(conn.network.ports(device_id=server.id))
    if not ports:
        raise Exception("Unable to find the VM network port")
    port_id = ports[0].id

    # Link Floating IP
    conn.network.update_ip(floating_ip, port_id=port_id)

    print(f"ssh -i {PRIVATE_KEYPAIR_FILE} ubuntu@{floating_ip.floating_ip_address}")

def list_servers(conn):
    print("List Servers:")
    for server in conn.compute.servers():
        print(f"{server.name} - {server.status} - {server.id}")

def delete_server(conn, server_name):
    server = conn.compute.find_server(server_name)
    if server is None:
        print(f"Server '{server_name}' not found")
        return
    conn.compute.delete_server(server.id)
    print(f"Server '{server_name}' deleted")
    # release floating ip
    ports = list(conn.network.ports(device_id=server.id))
    for fip in conn.network.ips():
        if fip.port_id and fip.port_id in [p.id for p in ports]:
            conn.network.delete_ip(fip)
            print(f"Floating IP {fip.floating_ip_address} released")


if __name__ == "__main__":
    # parse arg
    parser = argparse.ArgumentParser(description="Manage switch engine VM")
    parser.add_argument("--delete-vm", type=str, help="VM id to delete")
    args = parser.parse_args()
    # Load specific config
    config = OpenStackConfig(config_files=[CLOUDS_YAML])
    cloud = config.get_one("engines")

    # Create connection
    conn = connection.Connection(config=cloud)

    list_servers(conn)
    # list_images_dispo(conn)

    if args.delete_vm:
        delete_server(conn, args.delete_vm)
    else:
        create_server(conn)
