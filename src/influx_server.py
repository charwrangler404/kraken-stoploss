#!/usr/bin/env python

import asyncio
import websockets
import json
from datetime import datetime
import os
from influxdb_client_3 import InfluxDBClient3, InfluxDBError, WriteOptions
from influxdb_client_3 import write_client_options, Point
from influxdb_client_3
import pandas as pd
from IPython.display import display, HTML
from collections import deque


#TZ=timezone(offset=tzinfo.utcoffset())

BATCH_SIZE = 100
FLUSH_INTERVAL = 10_000
JITTER_INTERVAL = 2_000
RETRY_INTERVAL = 5_000
MAX_RETRIES = 5
MAX_RETRY_DELAY = 30_000
EXPONENTIAL_BASE = 2
WRITE_OPTIONS = {
    "batch_size" = BATCH_SIZE,
    "flush_interval" = FLUSH_INTERVAL,
    "jitter_interval" = JITTER_INTERVAL,
    "retry_interval" = RETRY_INTERVAL,
    "max_retries" = MAX_RETRIES
}
TOKEN = os.environ('INFLUXDB3_AUTH_TOKEN')
HOST = os.environ('INFLUXDB3_TICKER_HOST')
ORG = os.environ('INFLUXDB3_TICKER_ORG')
DATABASE = os.environ('INFLUXDB3_TICKER_DATABASE')
PAIRS = os.environ('INFLUXDB3_CURRENCY_PAIRS').split(',')

request_body = {
    "method": "",
    "params": {
    }
}

class BatchingCallback(object):
    """BatchingCallback - callback class for batching"""

    def success(self, conf, data: str):
        print(f"Written batch: {conf}")

    def error(self, conf, data: str, exception: InfluxDBError):
        print(f"Cannot write batch: {conf}, data: {data} due: {exception}")

    def retry(self, conf, data:str, exception: InfluxDBError):
        print(f"Retryable error occurs for batch: {conf}, data: {data} retry: {exception}")


class InfluxDBWriter:
    """
    Manages buffering and batch writing data points to InfluxDB.
    """
    def __init__(self, host, token, org, database, enable_gzip, write_options):
            # Initialize Callback
        self.callback = BatchingCallback()

        # initialize write options
        # 10_000 = 10ms
        self.write_options = WriteOptions(batch_size=BATCH_SIZE,
                                     flush_interval=FLUSH_INTERVAL,
                                     jitter_interval=JITTER_INTERVAL,
                                     retry_interval=RETRY_INTERVAL,
                                     max_retries=MAX_RETRIES,
                                     max_retry_delay=MAX_RETRY_DELAY,
                                     exponetial_base=EXPONENTIAL_BASE
                                     )

        # write_client_options sets our client options for retries
        # and passes the WriteOptions object
        self.wco = write_client_options(success_callback=callback.success,
                                   error_callback=self.callback.error,
                                   retry_callback=self.callback.retry,
                                   WriteOptions=self.write_options
                                   )

        # Initialize the influx client
        self.client = InfluxDBClient3(
                token=token,
                host=host,
                org=org,
                database=database,
                enable_gzip=enable_gzip,
                write_client_options=self.wco
        )
        # Use SYNCHRONOUS write option for explicit control over flushing
        # For higher throughput, consider ASYNCHRONOUS or BATCHING options provided by InfluxDB client.
        # Here, we implement our own batching logic on top of SYNCHRONOUS.
        self.buffer = deque()
        self.batch_size = BATCH_SIZE
        self.flush_interval = FLUSH_INTERVAL
        self.last_flush_time = datetime.now()
        self._flusher_task = None
        print(f"InfluxDBWriter initialized for bucket: {self.bucket}")

    async def write_point(self, point: Point):
        """Adds a single InfluxDB Point to the buffer and triggers flush if needed."""
        self.buffer.append(point)
        if len(self.buffer) >= self.batch_size:
            print(f"Buffer size {len(self.buffer)} >= {self.batch_size}. Triggering immediate flush.")
            await self._flush_buffer()

    async def _flush_buffer(self):
        """Flushes the current buffer to InfluxDB."""
        if not self.buffer:
            return

        points_to_write = list(self.buffer)
        self.buffer.clear()
        self.last_flush_time = datetime.now()

        try:
            print(f"Flushing {len(points_to_write)} points to InfluxDB...")
            # The write_api.write method is blocking, so run it in a thread pool executor
            # to avoid blocking the asyncio event loop.
            await asyncio.to_thread(self.write_api.write, bucket=self.bucket, record=points_to_write)
            print(f"Successfully flushed {len(points_to_write)} points.")
        except Exception as e:
            print(f"Error writing to InfluxDB: {e}")
            # Optionally, re-add points to buffer or log for retry
            for p in points_to_write:
                self.buffer.appendleft(p) # Add back to front for retry
            print(f"Re-added {len(points_to_write)} points to buffer due to error.")

    async def _periodic_flusher(self):
        """Periodically flushes the buffer based on the flush interval."""
        while True:
            await asyncio.sleep(self.flush_interval)
            if self.buffer and (datetime.now() - self.last_flush_time >= timedelta(seconds=self.flush_interval)):
                print(f"Periodic flush triggered. Buffer size: {len(self.buffer)}")
                await self._flush_buffer()

    def start_flusher(self):
        """Starts the background periodic flusher task."""
        if not self._flusher_task:
            self._flusher_task = asyncio.create_task(self._periodic_flusher())
            print("InfluxDB periodic flusher started.")

    async def stop_flusher(self):
        """Stops the background periodic flusher task and flushes any remaining data."""
        if self._flusher_task:
            self._flusher_task.cancel()
            try:
                await self._flusher_task
            except asyncio.CancelledError:
                print("InfluxDB periodic flusher stopped.")
        print("Flushing remaining points before shutdown...")
        await self._flush_buffer()
        self.client.close()
        print("InfluxDB client closed.")


def get_ticker(symbol, request_body):
    """Get Kraken websocket initialization"""

    request_body.update({"params": {
        "channel": "ticker",
        "symbol": symbol
    }})
    request_body.update({"method":"subscribe"})

    return json.dumps(request_body)

async def ws_client(client):
    """
    Ticker websocket client
    """

    print("WebSocket Client Initialization started")
    url = "wss://ws.kraken.com/v2"

    async with websockets.connect(url) as ws:

        await ws.send(get_ticker(["BTC/USD"], request_body))
        
        while True:
            msg = await ws.recv()
            # upon receiving json message,
            # parse out data that we want, then
            # write to the database
            data = json.loads(msg)

            for datum in data["data"]:
                new_data = {
                    symbol = datum["symbol"],
                    bid = datum["bid"],
                    bid_qty = datum["bid_qty"],
                    ask = datum["ask"], 
                    ask_qty = datum["ask_qty"],
                    daily_high = datum["high"],
                    daily_low = datum["low"],
                    change = datum["change"],
                    change_pct = datum["change_pct"],
                }
                # add data to buffer
                
            
            # asynchronously commit data to database

            print(f"{datetime.now()} - {msg}")

async def write_data(client, data):
    try:
        # try to write the data
        client.write(data, data_frame_measurement_name=None,
                     data_frame_tag_columns=None)
    except Exception as e:
        print(f"Error writing data point: {e}")

    # non-blocking sleep to wait for data to be written
    await asyncio.sleep(2)


# --- Websocket Consumer Function ---
async def websocket_consumer(uri: str, data_queue: asyncio.Queue):
    """
    Connects to a websocket, receives messages, and puts them into a queue.
    Includes basic reconnection logic.
    """
    while True:
        try:
            print(f"Connecting to WebSocket: {uri}...")
            async with websockets.connect(uri) as websocket:
                print("WebSocket connected.")
                while True:
                    try:
                        message = await websocket.recv()
                        # print(f"Received message: {message[:100]}...") # Print first 100 chars
                        try:
                            # Assuming messages are JSON, parse them and extract relevant data
                            data = json.loads(message)
                            # Example: If data has 'price' and 'symbol'
                            if 'data' in data and 's' in data['data'] and 'p' in data['data']:
                                symbol = data['data']['s']
                                price = float(data['data']['p'])
                                timestamp = datetime.fromtimestamp(data['data']['T'] / 1000) # Convert ms to seconds
                                await data_queue.put({'symbol': symbol, 'price': price, 'timestamp': timestamp})
                            else:
                                # Handle other message formats or log ignored messages
                                pass
                        except json.JSONDecodeError:
                            print(f"Received non-JSON message: {message}")
                        except KeyError as e:
                            print(f"Missing expected key in message: {e} in {message}")

                    except websockets.exceptions.ConnectionClosedOK:
                        print("WebSocket connection closed gracefully.")
                        break
                    except websockets.exceptions.ConnectionClosed as e:
                        print(f"WebSocket connection closed unexpectedly: {e}")
                        break
                    except Exception as e:
                        print(f"Error receiving message: {e}")
                        break # Break to attempt reconnection

        except websockets.exceptions.InvalidURI as e:
            print(f"Invalid WebSocket URI: {e}. Please check WEBSOCKET_URL.")
            return # Exit if URI is invalid
        except ConnectionRefusedError:
            print(f"Connection refused to {uri}. Retrying in 5 seconds...")
        except Exception as e:
            print(f"General WebSocket error: {e}. Retrying in 5 seconds...")

        await asyncio.sleep(5) # Wait before attempting to reconnect

# --- Data Processor Function ---
async def data_processor(data_queue: asyncio.Queue, influx_writer: InfluxDBWriter):
    """
    Pulls data from the queue, converts it to InfluxDB Line Protocol, and passes to the writer.
    """
    print("Data processor started.")
    while True:
        try:
            data = await data_queue.get()
            # Convert the received data into InfluxDB Line Protocol string
            # Format: measurement,tag_key=tag_value field_key=field_value timestamp_in_nanoseconds
            # Example: market_data,symbol=TESTSYM price=100.0 1678886400000000000
            # Timestamps for Line Protocol should be in nanoseconds since epoch
            timestamp_ns = int(data['timestamp'].timestamp() * 1_000_000_000)
            line_protocol = f"market_data,symbol={data['symbol']} price={data['price']} {timestamp_ns}"

            await influx_writer.write_point(line_protocol)
            data_queue.task_done()
        except asyncio.CancelledError:
            print("Data processor cancelled.")
            break
        except Exception as e:
            print(f"Error processing data from queue: {e}")
            data_queue.task_done() # Mark as done even on error to prevent blocking

# --- Main Application Logic ---
async def main():
    """Main function to run the asyncio application."""
    data_queue = asyncio.Queue()
    influx_writer = InfluxDBWriter(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG,
        database=INFLUXDB_DATABASE,
        batch_size=BATCH_SIZE,
        flush_interval=FLUSH_INTERVAL_SECONDS
    )

    # Start the periodic flusher for InfluxDB
    influx_writer.start_flusher()

    # Create and run tasks for websocket consumer and data processor
    consumer_task = asyncio.create_task(websocket_consumer(WEBSOCKET_URL, data_queue))
    processor_task = asyncio.create_task(data_processor(data_queue, influx_writer))

    print("Application started. Press Ctrl+C to exit.")

    try:
        # Keep the main loop running until tasks are done or cancelled
        await asyncio.gather(consumer_task, processor_task)
    except asyncio.CancelledError:
        print("Main application tasks cancelled.")
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Shutting down...")
    finally:
        # Graceful shutdown
        print("Initiating graceful shutdown...")
        consumer_task.cancel()
        processor_task.cancel()

        # Wait for tasks to finish or be cancelled
        await asyncio.gather(consumer_task, processor_task, return_exceptions=True)

        # Wait for any remaining items in the queue to be processed
        if not data_queue.empty():
            print(f"Waiting for {data_queue.qsize()} items in queue to be processed...")
            await data_queue.join()

        await influx_writer.stop_flusher()
        print("Shutdown complete.")

if __name__ == "__main__":
    # Ensure you have the necessary libraries installed:
    # pip install websockets influxdb-client-3

    # Before running, make sure:
    # 1. An InfluxDB 3.0 instance is running and accessible at INFLUXDB_URL.
    # 2. You have created an organization (INFLUXDB_ORG), a database (INFLUXDB_DATABASE),
    #    and a token (INFLUXDB_TOKEN) with write permissions for that database.
    # 3. A WebSocket server is running at WEBSOCKET_URL that sends JSON messages.
    #    (For testing, you can use a simple test WebSocket server or a public one like Binance's)

    # Example of a simple test WebSocket server (you can run this in a separate terminal):
    # import asyncio
    # import websockets
    # import json
    # import time
    # async def echo(websocket, path):
    #     i = 0
    #     while True:
    #         await websocket.send(json.dumps({"data": {"s": "TESTSYM", "p": str(100.0 + i), "T": int(time.time() * 1000)}}))
    #         i += 1
    #         await asyncio.sleep(1) # Send data every second
    # start_server = websockets.serve(echo, "localhost", 8765)
    # asyncio.get_event_loop().run_until_complete(start_server)
    # asyncio.get_event_loop().run_forever()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Application terminated by user.")
    except Exception as e:
        print(f"An unhandled error occurred: {e}")



while __name__ == "__main__":
    
    # Initialize Callback
    callback = BatchingCallback()

    # initialize write options
    # 10_000 = 10ms
    write_options = WriteOptions(batch_size=100,
                                 flush_interval=10_000,
                                 jitter_interval=2_000,
                                 retry_interval=5_000,
                                 max_retries=5,
                                 max_retry_delay=30_000,
                                 exponetial_base=2
                                 )

    # write_client_options sets our client options for retries
    # and passes the WriteOptions object
    wco = write_client_options(success_callback=callback.success,
                               error_callback=callback.error,
                               retry_callback=callback.retry,
                               WriteOptions=write_options
                               )

    # Initialize the influx client
    client = InfluxDBClient3(
            token=token,
            host=host,
            org=org,
            database=database,
            enable_gzip=True,
            write_client_options=wco
    )

    now = pd.Timestamp.now(tz="UTC").floor("ms")

    asyncio.run(ws_client(client))

    
