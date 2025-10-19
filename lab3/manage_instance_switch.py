import argparse
from openstack import connection
from openstack.config import OpenStackConfig
import configparser

def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config


config = load_config()

IMAGE_NAME = config.get('switch', 'image_name')
FLAVOR_NAME = config.get('switch', 'flavor_name')
NETWORK_NAME = config.get('switch', 'network_name')
SERVER_NAME = config.get('switch', 'server_name')
KEYPAIR_NAME = config.get('switch', 'keypair_name')
PRIVATE_KEYPAIR_FILE = config.get('switch', 'private_keypair_file')
CLOUDS_YAML = config.get('switch', 'clouds_yaml')

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

    # Finally create the server and run the VM_SETUP_SCRIPT
    server = conn.compute.create_server(
        name=SERVER_NAME,
        image_id=image.id,
        flavor_id=flavor.id,
        networks=[{"uuid": network.id}],
        key_name=keypair.name,
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

    print(f"You can login with SSH in a minute with\nssh -i {PRIVATE_KEYPAIR_FILE} ubuntu@{floating_ip.floating_ip_address}")

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
# todo make sure it released them all


if __name__ == "__main__":
    # parse arg
    parser = argparse.ArgumentParser(description="Manage switch engine VM")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all VMs")
    group.add_argument("--create", action="store_true", help="Create a new VM")
    group.add_argument("--delete-vm", type=str, metavar="VM_NAME", help="Delete the VM by id or name")
    args = parser.parse_args()

    # Load specific config
    config = OpenStackConfig(config_files=[CLOUDS_YAML])
    cloud = config.get_one("engines")

    # Create connection
    conn = connection.Connection(config=cloud)

    # list_images_dispo(conn)

    # Execute based on argument
    if args.list:
        list_servers(conn)
    elif args.create:
        create_server(conn)
    elif args.delete_vm:
        delete_server(conn, args.delete_vm)
