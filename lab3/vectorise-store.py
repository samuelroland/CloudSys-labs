# Based on the app of Abir Chebbi (abir.chebbi@hesge.ch)
# Modified for the Switch Engine+Azure Cosmos DB+Google Vertex AI
# Helped by ChatGPT
import boto3
import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from langchain_community.vectorstores import OpenSearchVectorSearch
import argparse
import uuid
from azure.cosmos import CosmosClient, PartitionKey, exceptions, DatabaseProxy
from azure.identity import DefaultAzureCredential
from vertexai.preview.language_models import TextEmbeddingModel
import vertexai


# The account name is an arbitrary name defined during cosmo db creation
def get_cosmos_client(account_name):
    credential = DefaultAzureCredential()
    cosmos_url = "https://{0}.documents.azure.com:443/".format(
        account_name)
    return CosmosClient(cosmos_url, credential=credential)


# Google Vertex AI Client
region = 'europe-west12'
project_id = "chatbot-475420"
ai_model = "textembedding-gecko@latest"
# https://cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/use-embedding-models#use-vertexai-text-embedding-models
ai_vectors_dimensions = 768
vertexai.init(project=project_id, location=region)


# This implementation is based on https://docs.azure.cn/en-us/cosmos-db/nosql/how-to-python-vector-index-query#enable-the-feature
def create_cosmos_db_container(container_name, account_name):
    # Define that the JSON field vector_field need to be indexed as the embeddings
    vector_embedding_policy = {
        "vectorEmbeddings": [
            {
                "path": "/vector_field",
                # TODO: check with what we did in google vertex AI
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

        db = get_cosmos_client(account_name).get_database_client(account_name)

        container = db.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path='/id'),
            indexing_policy=indexing_policy,
            vector_embedding_policy=vector_embedding_policy)
        print('Container with id \'{0}\' created'.format(container.id))

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
    # Use Vertex AI's embedding model
    # https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/textembedding-gecko
    model = TextEmbeddingModel.from_pretrained(ai_model)

    chunks_list = [chunk.page_content for chunk in chunks]

    # Batch embeddings (Vertex AI supports batching up to 100 texts per request)
    embeddings = []
    batch_size = 100
    for i in range(0, len(chunks_list), batch_size):
        batch = chunks_list[i:i+batch_size]
        batch_embeddings = model.get_embeddings(batch)
        # Convert to list of floats
        embeddings.extend([e.values for e in batch_embeddings])

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
# TODO: continue to refactor logic with cosmos db
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
    # TODO: remove this probably useless arg as equal to the account_name
    # parser.add_argument(
    #     "--database_name", help="The name of the existing Azure Cosmos Database")
    parser.add_argument(
        "--container_name", help="The name of the container to create inside the Azure Cosmos Database")
    parser.add_argument("--local_path", help="local path")
    args = parser.parse_args()
    main(args.bucket_name, args.account_name,
         args.local_path, args.container_name)
