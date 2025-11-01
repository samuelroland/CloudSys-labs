import redis
import pandas as pd
import numpy as np
import time
from datetime import datetime
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

MODEL_FILE = "lstm_model.keras"  # Store the model for reuse
DEVICE_QUEUE = "device_queue"

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

def get_data_from_redis(redis_client, key):
    """Fetches data from RedisTimeSeries."""
    logger.info(f"Fetching data for key: {key}")
    data = redis_client.ts().range(f"{key}_real", "-", "+")
    return pd.DataFrame(data, columns=["timestamp", "value"]).set_index("timestamp")

def prepare_data(df, n_steps):
    """Prepares time-series data for LSTM input."""
    logger.info(f"Preparing data with {n_steps} steps")

    X, y = [], []
    for i in range(len(df) - n_steps):
        X.append(df["value"].iloc[i : i + n_steps].values)
        y.append(df["value"].iloc[i + n_steps])
    return np.array(X).reshape(-1, n_steps, 1), np.array(y)

def train_or_load_model(X_train, y_train, n_steps):
    """Trains the LSTM model or loads an existing one if available."""
    try:
        model = load_model(MODEL_FILE)
        logger.info("Loaded existing model")
    except ValueError:  # Model file doesn't exist
        logger.info("Training new model")
        logger.info(f"X_train shape: {X_train.shape}, y_train shape: {y_train.shape}")
        logger.info(f"n_steps: {n_steps}")
        model = Sequential()
        model.add(LSTM(50, activation='relu', input_shape=(n_steps, 1)))
        model.add(Dense(1))
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
        model.fit(X_train, y_train, epochs=1, batch_size=32, validation_split=0.2, callbacks=[EarlyStopping(patience=10)])
        model.save(MODEL_FILE)  # Save the trained model
        logger.info("Trained and saved new model")
    return model

def forecast(model, data, input_seq, n_steps):
    """Generates forecasts for the next day."""
    logger.info("Generating forecasts for the next day")

    forecasts = []
    # for _ in range(96):
    next_value = model.predict(input_seq, verbose=0)[0][0]
    forecasts.append(next_value)

    return forecasts

def write_forecasts_to_redis(redis_client, key, index, forecasts):
    """Writes forecasts to RedisTimeSeries."""

    pipe = redis_client.pipeline()  # Create a Redis pipeline

    logger.info(f"Writing forecasts for device: {key}")
    # Gets the last timestamp, and adds 15 minutes to it

    all_timestamps = redis_client.ts().range(f"{key}_real", "-", "+")
    curr_timestamp = all_timestamps[index][0] if all_timestamps else int(datetime.now().timestamp() * 1000)
    logger.info(f"Current timestamp: {curr_timestamp}")
    logger.info(f"Index: {index}")

    # last_timestamp = all_timestamps[-1][0] if all_timestamps else int(datetime.now().timestamp() * 1000)
    # first_timestamp = all_timestamps[0][0] if all_timestamps else int(datetime.now().timestamp() * 1000)
    # Add 15 minutes to the last timestamp

    data = [[curr_timestamp + i * 15 * 60 * 1000, float(value)] for i, value in enumerate(forecasts)]
    data_insert = [[f"{key}_forecasted"] + sublist for sublist in data]
    logger.info(f"Data to insert: {data_insert}")
    pipe.execute_command("TS.MADD", *sum(data_insert, []))
    pipe.execute()

    return index + 1

def main():
    redis_client = redis.Redis(host=os.environ["REDIS_HOST"], port=6379, decode_responses=True)
    key = redis_client.rpoplpush(DEVICE_QUEUE, DEVICE_QUEUE)
    pipe = redis_client.pipeline()
    index = 4
    data = get_data_from_redis(redis_client, key)
    X, y = prepare_data(data, n_steps=24) 

    try:
        pipe.execute_command("TS.CREATE", f"{key}_forecasted", "LABELS", "device_id", key)
        pipe.execute()
    except:
        logger.info(f"Time series {key}_forecasted already exists")
        pass # We don't care that the key already exists, we just want to make sure it does.

    while True:
        if not key:
            logger.info("No keys in device queue, waiting...")
            time.sleep(10)  # Wait if the queue is empty
            continue

        model = train_or_load_model(X, y, n_steps=4)
        logger.info(f"Model trained for device: {key}")

        # Input sequence should be the last 4 values from the current index
        input_seq = data["value"].iloc[index-4:index].values.reshape(1, -1, 1)
        logger.info(f"Input sequence: {input_seq}")

        forecasts = forecast(model, data, input_seq, n_steps=1)
        logger.info(f"Forecasts generated for device: {key}")

        index = write_forecasts_to_redis(redis_client, key, index, forecasts)
        logger.info(f"Forecasts written to Redis for device: {key}")
        
        logger.info("Waiting for next forecast...")
        time.sleep(10)


if __name__ == "__main__":
    # try: 
    redis_client = redis.Redis(host=os.environ['REDIS_HOST'], port=6379, decode_responses=True)
    logger.info(f"Connected to Redis: {os.environ['REDIS_HOST']}")
    check_redis_connection()
    logger.info("Starting forecast service")
    logger.info(f"Model file: {MODEL_FILE}") 
    logger.info(f"Device queue: {DEVICE_QUEUE}")
    logger.info("Storing forecasts as RedisTimeSeries in Redis database")
    main()
    # except:
    #     logger.error("An error occurred in the forecast service.")
    #     exit(1)