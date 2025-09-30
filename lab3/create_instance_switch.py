from openstack import connection
from openstack.config import OpenStackConfig

IMAGE_NAME = "Ubuntu Jammy 22.04 (SWITCHengines)"
FLAVOR_NAME = "m1.small"
NETWORK_NAME = "private"
SERVER_NAME = "groupd-labo1"
KEYPAIR_NAME = "switchengine-tsm-cloudsys"
PRIVATE_KEYPAIR_FILE = "./switchengine-tsm-cloudsys.pem"

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

    ip = None
    for net, addresses in server.addresses.items():
        ip = addresses[0]["addr"]
        break

    print(f"ssh -i {PRIVATE_KEYPAIR_FILE} ubuntu@{ip}")

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

# --- Programme principal ---
if __name__ == "__main__":
    # Load speciif config
    config = OpenStackConfig(config_files=["./switch/clouds.yaml"])
    cloud = config.get_one("engines")

    # Create connection
    conn = connection.Connection(config=cloud)

    #list_images_dispo(conn)
    create_server(conn)
    list_servers(conn)
    #delete_server(conn, "1c5cccd0-6f48-432b-b359-7d8186f39832")
