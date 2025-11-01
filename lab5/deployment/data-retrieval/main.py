import boto3
import pandas as pd
import redis
from io import StringIO
import numpy
import csv
import logging
import os 

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def check_redis_connection():
    try:
        # Create a Redis client
        redis_client = redis.Redis(host=os.environ['REDIS_HOST'], port=6379, decode_responses=True)
        
        # Perform a simple operation to check the connection
        redis_client.set('test_key', 'test_value')
        value = redis_client.get('test_key')
        
        if value == 'test_value':
            logger.info("Successfully connected to Redis and performed a test operation.")
        else:
            logger.info("Connected to Redis, but test operation failed.")
            
    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")



def read_partial_csv(bucket_name, object_name, n_col=11):
    """Reads a CSV from S3, yielding rows with the specified number of columns."""

    logger.info(f"Reading CSV from S3 bucket: {bucket_name}")
    response = s3_client.get_object(Bucket=bucket_name, Key=object_name)

    # Use a generator to read lines without loading the whole file
    csv_string_generator = (line.decode('utf-8') for line in response['Body'].iter_lines())
    csv_reader = csv.reader(csv_string_generator, delimiter=';')  # Replace with your delimiter
    for row in csv_reader:
        yield row[:n_col]  # Yield only the first num_columns


def write_dataset_to_redis_timeseries(redis_client, df):
    """Writes a DataFrame with timestamps as index and device values as columns to RedisTimeSeries."""
    logger.info("Writing dataset to RedisTimeSeries")

    # Set first row as column name
    df.set_index(0, inplace=True)
    df = df.transpose()
    df.set_index("DATETIME", inplace=True)

    # Iterate over each device
    pipe = redis_client.pipeline()  # Create a Redis pipeline
    for index, row in df.iterrows():
        device_id = index
        key = f"ts:{device_id}"

        logger.info(f"Writing data for device: {key}")
        # Prepare data for RedisTimeSeries
        data = [[int(pd.to_datetime(ts).timestamp() * 1000), value] for ts, value in row[1:].items() if pd.notna(value)]

        # Use pipeline to add data points for the device
        pipe.execute_command("TS.CREATE", f"{key}_real", "LABELS", "device_id", device_id)
        if data:
            data_insert = [[f"{key}_real"] + sublist for sublist in data]    
            pipe.execute_command("TS.MADD", *sum(data_insert, []))  # Flatten data into list
            pipe.execute_command("LPUSH", "device_queue", key)

        # Execute all the commands in the pipeline
        pipe.execute() 
   
    logger.info("Finished writing dataset to RedisTimeSeries")


if __name__ == "__main__":
    try:
        redis_client = redis.Redis(host=os.environ['REDIS_HOST'], port=6379, decode_responses=True)
        logger.info(f"Connected to Redis: {os.environ['REDIS_HOST']}")
        check_redis_connection()

        # Initialize boto3 session with specified AWS credentials
        session = boto3.Session(
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name='us-east-1'
        )

        # S3 client from the session
        s3_client = session.client('s3')

        bucket_name = 'k8s-class-2024'
        object_name = 'GroupeE_data.csv'

        # Read the CSV file
        df = pd.DataFrame(read_partial_csv(bucket_name, object_name))
        # Get only the first 10 columns for demonstration purposes

        logger.info("Data read from CSV successfully.")
        logger.info(f"Number of columns = {len(df.columns)}")

        write_dataset_to_redis_timeseries(redis_client, df)
    except:
        logger.error("Failed to connect to Redis.")
        exit(1)

