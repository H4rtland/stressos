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

from multiprocessing.pool import ThreadPool
from datetime import datetime

import boto
from boto.s3.connection import S3Connection
from boto.s3.key import Key

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y/%m/%d %H:%M:%S", level=logging.INFO)

# hostname of machine, which is the container rather than the kubernetes node
NODE = platform.node()
LOG_SERVER_ADDR = "py-dev.lancs.ac.uk"
LOG_SERVER_PORT = 5050

bad_env_var = False

def getenv(name, is_int=False):
    global bad_env_var
    value = os.environ.get(name)
    if value is None:
        logging.critical("Missing environment variable {}".format(name))
        bad_env_var = True
    elif is_int:
        if not value.isdigit():
            logging.critical("{} is not an integer value")
            bad_env_var = True
        else:
            value = int(value)
    return value
    

ENDPOINT_HOSTNAME = getenv("ENDPOINT_HOSTNAME")
ENDPOINT_PORT = getenv("ENDPOINT_PORT", is_int=True)
BUCKET_NAME = getenv("BUCKET_NAME")
NUM_THREADS = getenv("NUM_THREADS", is_int=True)

OBJ_MEAN_KB = getenv("OBJ_MEAN_KB", is_int=True)
OBJ_STDDEV_KB = getenv("OBJ_STDDEV_KB", is_int=True)


if bad_env_var:
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
        st = datetime.now()
        obj_name = uuid.uuid4().hex
        size_in_kb = int(random.normalvariate(OBJ_MEAN_KB, OBJ_STDDEV_KB))
        object_contents = os.urandom(1024)*size_in_kb
        obj_create_time = (datetime.now()-st).total_seconds()

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

            logging.info("Thread %d: %s obj_create:%s", thread_num, csv_data, str(obj_create_time))

            sock.sendto(csv_data.encode("utf-8"), (LOG_SERVER_ADDR, LOG_SERVER_PORT))

        except Exception as e:
            logging.error("Thread %d: %s", thread_num, str(e))





def main():
    pool = ThreadPool(processes=NUM_THREADS)
    pool.map(run_stress_test, range(0, NUM_THREADS))

if __name__ == "__main__":
    main()
