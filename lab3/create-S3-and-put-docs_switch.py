import os
import argparse
from openstack import connection
from openstack.config import OpenStackConfig
import configparser

def list_container(conn):
    containers = list(conn.object_store.containers())
    if not containers:
        print("No containers.")
        return

    print("Containers available :")
    for c in containers:
        print(f"- {c.name} , container_read: {c.metadata}")
        for obj in conn.object_store.objects(c.name):
            size = getattr(obj, "size", getattr(obj, "content_length", "unknown"))
            print(f"Found object in container: {obj.name}, size={size} bytes")

def get_container_public_url(conn, container_name):
    # Récupérer l'endpoint public du service object-store (Swift)
    endpoint = conn.session.get_endpoint(service_type='object-store', interface='public')

    # Construire l'URL complète du container
    # L'account/project ID est généralement le current_project_id du token
    account = f"AUTH_{conn.current_project_id}"
    public_url = f"{endpoint}/{account}/{container_name}"
    return public_url

def upload_pdfs(conn, container_name, pdf_path):
    # Upload PDF file
    if os.path.isfile(pdf_path):
        files = [pdf_path]
    elif os.path.isdir(pdf_path):
        files = [os.path.join(pdf_path, f) for f in os.listdir(pdf_path) if f.endswith(".pdf")]
    else:
        print(f"Error: {pdf_path} is neither a file nor a directory")
        return

    for file_path in files:
        filename = os.path.basename(file_path)
        print(f"Uploading {filename} to container {container_name}...")
        with open(file_path, 'rb') as f:
            conn.object_store.upload_object(container=container_name, name=filename, data=f)
        print(f"{filename} uploaded successfully.")


def download_pdfs(conn, container_name, download_dir):
    # create dir if not exists
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    try:
        objects = conn.object_store.objects(container_name)
        for obj in objects:
            if obj.name.endswith(".pdf"):
                local_path = os.path.join(download_dir, obj.name)
                print(f"Download {obj.name} in {local_path}...")

                with open(local_path, 'wb') as f:
                    conn.object_store.download_object(
                        container=container_name,
                        obj=obj.name,
                        output=f
                    )
                print(f"{obj.name} downloaded successfully.")
    except Exception as e:
        print(f"error during pdf download : {e}")

def create_container(conn, container_name):
    print(f"Creating container '{container_name}'...")
    conn.object_store.create_container(name=container_name)
    # setting the container to public doesn’t seem to work...
    conn.object_store.set_container_metadata(container_name, metadata={"x-container-read": "*"})
    public_url = get_container_public_url(conn, container_name)
    print(f"Container '{container_name}' created. Available at '{public_url}'")

def delete_container(conn, container_name):
    try:
        # Check if container exists
        containers = [c for c in conn.object_store.containers() if c.name == container_name]
        if not containers:
            print(f"Container '{container_name}' not found.")
            return
        container = containers[0]

        # Delete container content
        objects = list(conn.object_store.objects(container.name))
        for obj in objects:
            conn.object_store.delete_object(container=container.name, obj=obj.name)
            print(f"Deleted object: {obj.name}")

        # Delete container
        conn.object_store.delete_container(container.name)
        print(f"Container '{container_name}' deleted successfully.")

    except Exception as e:
        print(f"Error deleting container '{container_name}': {e}")


def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config


config = load_config()

S3_CONTAINER_NAME = config.get('switch', 's3_container_name')

def main(pdf_path):
    # Load speciif config
    config = OpenStackConfig(config_files=["./switch/clouds.yaml"])
    cloud = config.get_one("engines")

    # Create connection
    conn = connection.Connection(config=cloud)

    # Create container
    create_container(conn, S3_CONTAINER_NAME)

    # Just for check, list containers
    list_container(conn)

    # Upload PDF file
    upload_pdfs(conn, S3_CONTAINER_NAME, pdf_path)

    # Download PDF
    download_pdfs(conn, S3_CONTAINER_NAME, "./mydir")

    # Delete container
    delete_container(conn, S3_CONTAINER_NAME) 


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload PDF files to an OpenStack Swift container")
    parser.add_argument("--pdf_path", help="Path to a PDF file or directory of PDF files")
    args = parser.parse_args()
    main(args.pdf_path)
