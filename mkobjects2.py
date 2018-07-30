import argparse
import random
import logging
import os
import csv
import socket
import time
import platform
import sys
import threading
import uuid

from datetime import datetime

import boto
from boto.s3.connection import S3Connection
from boto.s3.key import Key

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y/%m/%d %H:%M:%S", level=logging.INFO)

# hostname of machine, which is the container rather than the kubernetes node
NODE = platform.node()
LOG_SERVER_ADDR = "py-dev.lancs.ac.uk"
LOG_SERVER_PORT = 5050

ENDPOINT_HOSTNAME = os.environ.get("ENDPOINT_HOSTNAME")
ENDPOINT_PORT = os.environ.get("ENDPOINT_PORT")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
NUM_THREADS = os.environ.get("NUM_THREADS")

OBJ_MEAN_KB = os.environ.get("OBJ_MEAN_KB")
OBJ_STDDEV_KB = os.environ.get("OBJ_STDDEV_KB")

missing_var = False

if ENDPOINT_HOSTNAME is None:
    logging.critical("Missing environment variable ENDPOINT_HOSTNAME")
    missing_var = True

if ENDPOINT_PORT is None:
    logging.critical("Missing environment variable ENDPOINT_PORT")
    missing_var = True
elif not ENDPOINT_PORT.isdigit():
    logging.critical("ENDPOINT_PORT is not an integer value")
    missing_var = True
else:
    ENDPOINT_PORT = int(ENDPOINT_PORT)

if BUCKET_NAME is None:
    logging.critical("Missing environment variable BUCKET_NAME")
    missing_var = True

if NUM_THREADS is None:
    logging.critical("Missing environment variable NUM_THREADS")
    missing_var = True
elif not NUM_THREADS.isdigit():
    logging.critical("NUM_THREADS is not an integer value")
    missing_var = True
else:
    NUM_THREADS = int(NUM_THREADS)

if OBJ_MEAN_KB is None:
    logging.critical("Missing environment variable OBJ_MEAN_KB")
    missing_var = True
elif not OBJ_MEAN_KB.isdigit():
    logging.critical("OBJ_MEAN_KB is not an integer value")
    missing_var = True
else:
    OBJ_MEAN_KB = int(OBJ_MEAN_KB)

if OBJ_STDDEV_KB is None:
    logging.critical("Missing environment variable OBJ_STDDEV_KB")
    missing_var = True
elif not OBJ_STDDEV_KB.isdigit():
    logging.critical("OBJ_STDDEV_KB is not an integer value")
    missing_var = True
else:
    OBJ_STDDEV_KB = int(OBJ_STDDEV_KB)


if missing_var:
    logging.critical("Exiting early")
    sys.exit(1)



def run_stress_test(thread_num):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    s3conn = S3Connection(host=ENDPOINT_HOSTNAME,
                          port=ENDPOINT_PORT,
                          calling_format=boto.s3.connection.OrdinaryCallingFormat())

    bucket = s3conn.create_bucket(BUCKET_NAME)
    bucket.set_acl("public-read")

    while True:
        obj_name = uuid.uuid4().hex
        size_in_kb = int(random.normalvariate(OBJ_MEAN_KB, OBJ_STDDEV_KB))

        object_contents = os.urandom(1024)*size_in_kb

        key = Key(bucket, obj_name)

        try:
            start_time = datetime.now()
            key.set_contents_from_string(object_contents)
            end_time = datetime.now()
            elapsed = (end_time-start_time).total_seconds()

            msg = [NODE,
                   datetime.timestamp(start_time),
                   ENDPOINT_HOSTNAME,
                   BUCKET_NAME,
                   size_in_kb*1024,
                   elapsed]

            csv_data = ",".join(map(str, msg))

            logging.info("Thread %d: %s", thread_num, csv_data)

            sock.sendto(csv_data.encode("utf-8"), (LOG_SERVER_ADDR, LOG_SERVER_PORT))

        except Exception as e:
            logging.error("Thread %d: %s", thread_num, str(e))





def main():
    threads = [threading.Thread(target=run_stress_test, args=(t,)) for t in range(0, NUM_THREADS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
