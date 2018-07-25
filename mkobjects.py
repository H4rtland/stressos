import argparse
import traceback
import random
import logging
import sys
import string
import boto
import datetime
import csv
import socket
import time
import io

from boto.s3.connection import S3Connection
from boto.s3.key import Key

# from google.cloud import pubsub_v1

#publisher = pubsub_v1.PublisherClient()
#topic_path = publisher.topic_path('palove-198915', 'podtopic')
#print(topic_path)

"""
Populate a bucket with objects following a specified size distribution

Authors:
  w.frost@lancaster.ac.uk
  p.love@lancaster.ac.uk
"""

def getargs():
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--bucket', help='name of target bucket')
    parser.add_argument('-m', '--mean', type=int,  help='mean size of file in bytes')
    parser.add_argument('-s', '--stddev', type=int,  help='stddev of file in bytes')
    parser.add_argument('-n', '--num', help='number of files',type=int)
    parser.add_argument('-t', '--duration', help='duration of test',type=int)
    parser.add_argument('--seed', dest='seed', help='optional seed for the random number generator')
    parser.add_argument('-k', '--key', dest='access_key', help='access key')
    parser.add_argument('-e', '--secret', dest='secret_key', help='access secret')
    parser.add_argument('-d', '--hostname', dest='hostname', default='localhost', help='hostname of endpoint')
    parser.add_argument("--profile", dest="profile", default='default', help="profile name")
    parser.add_argument('-p', '--port', dest='port', type=int, default=443, help='port number')
    parser.add_argument("-c", "--insecure", dest="is_secure", default=True, action="store_false", help="use http")
    parser.add_argument("-f", "--filename", dest="filename", help='[csv file name].csv')
    return parser.parse_args()

def main():
    args = getargs()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    now = datetime.datetime.now()
    filenamedata = [now.hour, now.minute, now.day, now.month, now.year, args.num, args.mean, args.stddev]

    """for i in range(0, len(filenamedata)):
        filenamedata[i] = str(filenamedata[i])
        if len(filenamedata[i])==1:
            filenamedata[i]='0' + filenamedata[i]"""
    filenamedata = list(map(str, filenamedata))

    outputwriter = csv.writer(sys.stdout)
    outputwriter.writerow(['Time_Stamp','Dest_Host', 'Dest_Bucket', 'File_Size','Duration'])

    # If --seed not given value is None - defaults to using system time
    random.seed(args.seed)

    conn = S3Connection(aws_access_key_id = args.access_key,
                        aws_secret_access_key = args.secret_key,
                        host = args.hostname,
                        port = args.port,
                        is_secure = args.is_secure,
                        calling_format = boto.s3.connection.OrdinaryCallingFormat(),
                        profile_name = args.profile)

    bucket = conn.create_bucket(args.bucket)
    bucket.set_acl('public-read')

    for i in range(args.num):
        output = io.StringIO()
        stringwriter = csv.writer(output)

        size = int(random.normalvariate(args.mean, args.stddev))
        randname = ''.join(random.choice(string.ascii_lowercase) for _ in range(20))
        randfile = ''.join(random.choice(string.ascii_lowercase) for _ in range(size))

        starttime = datetime.datetime.now()

        key = Key(bucket, randname)

        try:
            key.set_contents_from_string(randfile)
            #key.set_acl('public-read')

            elapsed = datetime.datetime.now() - starttime
            elapsed_time = float(elapsed.seconds)+float(elapsed.microseconds)/1000000.
            timestamp = datetime.datetime.timestamp(starttime)

            outputwriter = csv.writer(sys.stdout)
            msg = [timestamp, args.hostname, args.bucket, size, elapsed_time]
            outputwriter.writerow(msg)
            stringwriter.writerow(msg)

            data = output.getvalue().strip('\r\n').encode('utf-8')
            sock.sendto(data, ('py-dev.lancs.ac.uk', 5050))
            # publisher.publish(topic_path, data=data)
            output.close()
        except Exception as ex:
            print(ex)    
        sys.stdout.flush()
    
    print('Done')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        return

if __name__ == '__main__':
    main()
