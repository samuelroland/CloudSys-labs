import argparse
import time
from openstack import connection
from openstack.config import OpenStackConfig
from openstack.exceptions import NotFoundException

IMAGE_NAME = "Ubuntu Jammy 22.04 (SWITCHengines)"
FLAVOR_NAME = "m1.small"
NETWORK_NAME = "private"
SERVER_NAME = "groupd-labo1"
KEYPAIR_NAME = "switchengine-tsm-cloudsys"
PRIVATE_KEYPAIR_FILE = "./switch/switchengine-tsm-cloudsys.pem"

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

    server = conn.compute.create_server(
        name=SERVER_NAME,
        image_id=image.id,
        flavor_id=flavor.id,
        networks=[{"uuid": network.id}],
        key_name=keypair.name
    )
    server = conn.compute.wait_for_server(server)
    print(f"VM '{SERVER_NAME}' créée avec succès.")

    # find public network
    public_net = None
    for net in conn.network.networks():
        if "public" in net.name.lower():
            public_net = net
            break
    if public_net is None:
        raise Exception("Impossible de trouver le réseau public pour la Floating IP.")

    floating_ip = conn.network.create_ip(floating_network_id=public_net.id)
    
    # Get VM port
    ports = list(conn.network.ports(device_id=server.id))
    if not ports:
        raise Exception("Impossible de trouver le port réseau de la VM")
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
        print(f"Serveur '{server_name}' introuvable")
        return
    conn.compute.delete_server(server.id)
    print(f"Serveur '{server_name}' supprimé")
    # release floating ip
    ports = list(conn.network.ports(device_id=server.id))
    for fip in conn.network.ips():
        if fip.port_id and fip.port_id in [p.id for p in ports]:
            conn.network.delete_ip(fip)
            print(f"Floating IP {fip.floating_ip_address} released")


# --- Programme principal ---
if __name__ == "__main__":
    # parse arg
    parser = argparse.ArgumentParser(description="Manage switch engine VM")
    parser.add_argument("--delete-vm", type=str, help="VM id to delete")
    args = parser.parse_args()
    # Load speciif config
    config = OpenStackConfig(config_files=["./switch/clouds.yaml"])
    cloud = config.get_one("engines")

    # Create connection
    conn = connection.Connection(config=cloud)


    list_servers(conn)
    #list_images_dispo(conn)
    
    if args.delete_vm:
        delete_server(conn, args.delete_vm)
    else:
         create_server(conn)
   
