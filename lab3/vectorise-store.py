# Based on the app of Abir Chebbi (abir.chebbi@hesge.ch)
# Modified for the Switch Engine+Azure Cosmos DB+Google Vertex AI
# Helped by ChatGPT
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import argparse
import uuid
import configparser
from azure.cosmos import CosmosClient, PartitionKey, exceptions

from google.genai import Client
# The account name is an arbitrary name defined during cosmo db creation


def get_cosmos_client(account_name):
    cosmos_url = "https://{0}.documents.azure.com:443/".format(account_name)
    with open('azure-db-key.txt', 'r') as file:
        key = file.read().rstrip()
    return CosmosClient(cosmos_url, credential=key)


def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config


config = load_config()

# Google Vertex AI Client
vertexai_region = config.get('vertexai', 'region')
project_id = config.get('vertexai', 'project_id')
ai_model_embeddings = config.get('vertexai', 'ai_model_embeddings')
ai_model_final_prompt = config.get('vertexai', 'ai_model_final_prompt')

ai_vectors_dimensions = 768  # kinda arbitrary value

# This implementation is based on https://docs.azure.cn/en-us/cosmos-db/nosql/how-to-python-vector-index-query#enable-the-feature
def create_cosmos_db_container(container_name, account_name):
    # Define that the JSON field vector_field need to be indexed as the embeddings
    vector_embedding_policy = {
        "vectorEmbeddings": [
            {
                "path": "/vector_field",
                "dataType": "float32",
                "distanceFunction": "dotproduct",
                "dimensions": ai_vectors_dimensions
            },
        ]
    }
    # Index everything except the embedding field
    indexing_policy = {
        "includedPaths": [
            {
                "path": "/*"
            }
        ],
        "excludedPaths": [
            {
                "path": "/vector_field/*",
            }
        ],
        "vectorIndexes": [{"path": "/vector_field", "type": "quantizedFlat"}]
    }

    try:
        client = get_cosmos_client(account_name)
        db = client.create_database_if_not_exists(id=account_name)

        print('\nDatabase with id \'{0}\' exists or is created'.format(db.id))
        container = db.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path='/id'),
            indexing_policy=indexing_policy,
            vector_embedding_policy=vector_embedding_policy)
        print('\nContainer with id \'{0}\' exists or is created\n'.format(
            container.id))

    except exceptions.CosmosHttpResponseError:
        raise


# Load docs from S3
# TODO: convert to download from switch engine bucket !
# and enable again in main()
#
# def download_documents(bucket_name, local_dir):
#     response = s3_client.list_objects_v2(Bucket=bucket_name)
#     for item in response['Contents']:
#         key = item['Key']
#         if key.endswith('.pdf'):
#             local_filename = os.path.join(local_dir, key)
#             s3_client.download_file(
#                 Bucket=bucket_name, Key=key, Filename=local_filename)


# Split pages/text into chunks
def split_text(docs, chunk_size, chunk_overlap):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = text_splitter.split_documents(docs)

    return chunks


# Generate embedding with Google Vertex AI from given chunks of the PDF
def generate_embeddings(chunks):
    chunks_list = [chunk.page_content for chunk in chunks]

    # Batch embeddings (Vertex AI supports batching up to 100 texts per request)
    embeddings = []
    batch_size = 100
    client = Client(
        vertexai=True, project=project_id, location=vertexai_region)

    for i in range(0, len(chunks_list), batch_size):
        batch = chunks_list[i:i+batch_size]
        batch_embeddings = client.models.embed_content(
            model=ai_model_embeddings,
            contents=batch,
            # config=EmbedContentConfig(
            #     task_type="RETRIEVAL_DOCUMENT",  # Optional
            #     output_dimensionality=1000,  # Optional
            #     title="Driver's License",  # Optional
            # ),
        )
        print(batch_embeddings)
        # Convert to list of floats
        embeddings.extend([e.values for e in batch_embeddings.embeddings])

    # Debug: Print actual embedding dimensions
    if embeddings:
        actual_dimension = len(embeddings[0])
        print(f"Actual embedding dimension: {actual_dimension}")
        if actual_dimension != 768:
            print(f"WARNING: Embedding dimension ({
                  actual_dimension}) doesn't match index dimension (768)")

    return embeddings


# Store generated embeddings into a Cosmos DB
def store_embeddings_cosmos(embeddings, texts, meta_data_list, account_name, database_name, container_name):
    client = get_cosmos_client(account_name)
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)

    documents = []
    for i, (embedding, text, metadata) in enumerate(zip(embeddings, texts, meta_data_list)):
        doc = {
            "id": str(uuid.uuid4()),
            "vector_field": embedding,
            "text": text,
            **metadata  # merge metadata keys directly into the doc
        }
        documents.append(doc)

    for doc in documents:
        container.upsert_item(doc)

    return f"{len(documents)} documents upserted into Cosmos DB"


# main
def main(bucket_name, account_name, local_path, container_name):

    # TODO enable that again
    # download_documents(bucket_name, local_path)
    loader = PyPDFDirectoryLoader(local_path)
    docs = loader.load()
    print('Start chunking')
    chunks = split_text(docs, 1000, 100)
    print(chunks[1])
    create_cosmos_db_container(container_name, account_name)
    print('Start vectorising')
    embeddings = generate_embeddings(chunks)
    print(embeddings[1])
    texts = [chunk.page_content for chunk in chunks]
    # Prepare metadata for each chunk
    meta_data = [{'source': chunk.metadata['source'],
                  'page': chunk.metadata['page'] + 1} for chunk in chunks]
    print('Start storing')
    print(f"Storing {len(embeddings)} embeddings in batches...")

    try:
        store_embeddings_cosmos(
            embeddings,
            texts,
            meta_data,
            account_name,
            database_name=account_name,
            container_name=container_name,
        )
        print('End storing - Success!')
    except Exception as e:
        print(f"Error storing embeddings: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process PDF documents and store their embeddings.")
    parser.add_argument(
        "--bucket_name", help="The S3 bucket name where documents are stored")
    parser.add_argument(
        "--account_name", help="The account_name of Azure Cosmos Database")
    parser.add_argument(
        "--container_name", help="The name of the container to create inside the Azure Cosmos Database")
    parser.add_argument("--local_path", help="local path")
    args = parser.parse_args()
    main(args.bucket_name, args.account_name,
         args.local_path, args.container_name)
