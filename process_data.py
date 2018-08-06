import os
import os.path as op
import sys
from operator import itemgetter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

if len(sys.argv) < 2:
    print("python process_data.py [DATA_FILENAME]")
    sys.exit(0)

data_file = sys.argv[1]

if not op.isfile(data_file):
    print("File does not exist")
    sys.exit(0)


just_filename = op.basename(data_file)
just_name = op.splitext(just_filename)[0]
output_prefix = op.join("plots", just_name)
data = pd.read_csv(data_file, index_col=False, header=0)
data.columns = ["hostname", "timestamp", "endpoint", "bucket", "size", "duration"]

def plot_durations():
    fig, ax = plt.subplots()
    bins = 100
    xaxis_range = (0, 10)
    ax.hist(data["duration"], bins=bins, range=xaxis_range)
    ax.set_xlabel("Transfer duration (seconds)")
    ax.set_ylabel("Number of transfers")
    ax.set_xlim(xaxis_range)
    ax.grid(True)
    fig.tight_layout()
    plt.savefig("{}_durhist.png".format(output_prefix))


def plot_rate():
    fig, ax = plt.subplots()
    bins = 100
    xaxis_range = (0, 10)
    ax.hist(data["duration"]/(data["size"]/(2**20)), bins=bins, range=xaxis_range)
    ax.set_xlabel("Transfer duration per MB (seconds)")
    ax.set_ylabel("Number of transfers")
    ax.set_xlim(xaxis_range)
    ax.grid(True)
    fig.tight_layout()
    plt.savefig("{}_ratehist.png".format(output_prefix))


def plot_separate_durations():
    fig, ax = plt.subplots()
    bins = 40
    xaxis_range = (0, 0.4)
    datas = []
    for pod_name in set(data["hostname"]):
        filtered_data = data[data.hostname == pod_name]
        ax.hist(filtered_data["duration"], bins=bins, range=xaxis_range, label=pod_name, alpha=0.4)
        #datas.append(filtered_data)

    #ax.hist(datas, bins=bins, range=xaxis_range, stacked=True)


    ax.set_xlabel("Transfer duration (seconds)")
    ax.set_ylabel("Number of transfers")
    ax.set_xlim(xaxis_range)
    ax.grid(True)
    #ax.legend()
    fig.tight_layout()
    plt.savefig("{}_poddurhist.png".format(output_prefix))


def speed_over_time():
    start_time = data["timestamp"].min()
    end_time = data["timestamp"].max()
    precision = 10 # seconds
    transfer_speeds = []

    for t in range(int(start_time), int(end_time), precision):
        time_into_test = t-int(start_time)
        filtered_data = data[data["timestamp"].between(t, t+precision)]
        total_bytes = filtered_data["size"].sum()
        total_mb = total_bytes / 2**20
        mb_per_s = total_mb/precision
        transfer_speeds.append((time_into_test, mb_per_s))

    fig, ax = plt.subplots()
    ax.plot(*zip(*transfer_speeds))
    ax.set_xlabel("Time into stress test (seconds)")
    ax.set_ylabel("Overall transfer speed (MB/s)")
    ax.grid(True)
    ax.set_ylim(bottom=0)
    fig.tight_layout()    
    plt.savefig("{}_speeds.png".format(output_prefix))


def transfer_speed_per_pod():
    start_time = data["timestamp"].min()
    end_time = data["timestamp"].max()
    precision = 10 # seconds
    transfer_speeds = []
    for t in range(int(start_time), int(end_time), precision):
        time_into_test = t-int(start_time)
        filtered_data = data[data["timestamp"].between(t, t+precision)]
        total_bytes = filtered_data["size"].sum()
        total_mb = total_bytes / 2**20
        mb_per_s = total_mb/precision

        #data_up_to_now = data[data["timestamp"] < t+precision]
        #unique_pods = len(set(data_up_to_now["hostname"]))
        unique_pods = len(set(filtered_data["hostname"]))
        unique_pods = max(unique_pods, 1)
        mb_per_s_per_pod = mb_per_s/unique_pods
        transfer_speeds.append((time_into_test, mb_per_s_per_pod))

    fig, ax = plt.subplots()
    ax.plot(*zip(*transfer_speeds))
    ax.set_xlabel("Time into stress test (seconds)")
    ax.set_ylabel("Overall transfer speed per pod (MB/s)")
    ax.grid(True)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    plt.savefig("{}_speeds_per_pod.png".format(output_prefix))



def requests_per_second():
    start_time = data["timestamp"].min()
    end_time = data["timestamp"].max()
    precision = 10 # seconds
    reqsps = []

    for t in range(int(start_time), int(end_time), precision):
        time_into_test = t-int(start_time)
        filtered_data = data[data["timestamp"].between(t, t+precision)]
        total_requests = len(filtered_data)
        reqs_per_s = total_requests/precision
        reqsps.append((time_into_test, reqs_per_s))

    fig, ax = plt.subplots()
    ax.plot(*zip(*reqsps))
    ax.set_xlabel("Time into stress test (seconds)")
    ax.set_ylabel("Requests handled per second")
    ax.grid(True)
    ax.set_ylim(bottom=0)
    fig.tight_layout()    
    plt.savefig("{}_reqsps.png".format(output_prefix))


plot_durations()
#plot_rate()
#plot_separate_durations()
speed_over_time()
transfer_speed_per_pod()
requests_per_second()
