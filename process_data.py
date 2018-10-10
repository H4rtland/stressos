"""
Processes several CSV data files.

Those CSV files should have the .yaml deployment file used to generate that stress test data
copied next to it with the same file name but keeping the .yaml extension.

i.e data_2018_09_10_15_50_12.csv should have an associated data_2018_09_10_15_50_12.yaml
"""

import os
import os.path as op
import sys
from operator import itemgetter
import datetime

import yaml
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

if len(sys.argv) < 2:
    print("python process_data.py [DATA_FILENAME_1] [DATA_FILENAME_2] [...]")
    sys.exit(0)

if not op.isdir("plots"):
    os.mkdir("plots")


data_files = sys.argv[1:]

for data_file in data_files:
    if not op.isfile(data_file):
        print("File does not exist: {}".format(data_file))
        sys.exit(0)

data = {}
data_metadata = {}

just_filename = op.basename(data_files[0])
just_name = op.splitext(just_filename)[0]
plot_output_prefix = op.join("plots", just_name)


for data_file in data_files:
    basename = op.basename(data_file)
    name, ext = op.splitext(basename)
    directory = op.split(data_file)[0]

    metadata_file = op.join(directory, name+".yaml")
    with open(metadata_file, "r") as meta:
        metadata = yaml.load(meta)

    hostname = ""
    yaml_env = metadata["spec"]["template"]["spec"]["containers"][0]["env"]
    pods = metadata["spec"]["replicas"]
    threads = 0
    for env_var in yaml_env:
        if env_var["name"] == "ENDPOINT_HOSTNAME":
            hostname = env_var["value"]
        if env_var["name"] == "NUM_THREADS":
            threads = env_var["value"]

    data_metadata[hostname] = {"pods": pods, "threads": threads}

    csv_data = pd.read_csv(data_file, index_col=False, header=0)
    csv_data.columns = ["hostname", "timestamp", "endpoint", "bucket", "size", "duration", "error"]

    print("Errors in {} ({}): {}".format(basename, hostname, sum(csv_data["size"] < 0)))
    data[hostname] = csv_data

def plot_durations():
    ax_max = 5
    for hostname, csv_data in data.items():
        if "mwt" in hostname: continue
        ax_max = max(ax_max, int(max(csv_data["duration"])+2))
    fig, ax = plt.subplots()
    ax.grid(True)
    bins = 100
    xaxis_range = (0, ax_max)

    for hostname, csv_data in data.items():
        csv_data = csv_data[csv_data["size"] >= 0]
        ax.hist(csv_data["duration"], bins=bins, range=xaxis_range, histtype="step", linewidth=2, fill=False, log=True, label="{} {}p*{}t".format(hostname, data_metadata[hostname]["pods"], data_metadata[hostname]["threads"]))
        

    ax.set_xlabel("Transfer duration for successes (seconds)")
    ax.set_ylabel("Number of transfers")
    ax.set_xlim(xaxis_range)
    ax.legend()
    fig.tight_layout()
    plt.savefig("{}_durhist.png".format(plot_output_prefix))



def plot_separated_durations():
    ax_max = 5
    for hostname, csv_data in data.items():
        ax_max = max(ax_max, int(max(csv_data["duration"])+2))
    fig, ax = plt.subplots()
    ax.grid(True)
    bins = 40
    xaxis_range = (0, ax_max)

    precision = 90
    hists = {}
    for hostname, csv_data in data.items():
        start_time = int(csv_data["timestamp"].min())
        end_time = int(csv_data["timestamp"].max())
        hists[hostname] = {}
        for t in range(0, end_time-start_time, precision):
            d = csv_data[csv_data["timestamp"].between(start_time+t, start_time+t+precision)]
            hists[hostname][(t, t+precision)] = d

    for hostname, times in hists.items():
        for (t_s, t_e), d in reversed(list(times.items())):
        #for (t_s, t_e), d in times.items():
            if len(d) == 0: continue
            ax.hist(d["duration"], bins=bins, range=xaxis_range, histtype="barstacked", stacked=True, log=True, label="{}-{}s {} {}p*{}t".format(t_s, t_e, hostname, data_metadata[hostname]["pods"], data_metadata[hostname]["threads"]))
    #for hostname, csv_data in data.items():
    #    ax.hist(csv_data["duration"], bins=bins, range=xaxis_range, histtype="step", linewidth=2, fill=False, log=True, label="{} {}p*{}t".format(hostname, data_metadata[hostname]["pods"], data_metadata[hostname]["threads"]))
        

    ax.set_xlabel("Transfer duration (seconds)")
    ax.set_ylabel("Number of transfers")
    ax.set_xlim(xaxis_range)
    ax.legend()
    fig.tight_layout()
    plt.savefig("{}_sep_durhist.png".format(plot_output_prefix))


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
    fig, ax = plt.subplots()

    for hostname, csv_data in data.items():
        start_time = csv_data["timestamp"].min()
        end_time = csv_data["timestamp"].max()
        precision = 10 # seconds
        reqsps = []

        for t in range(int(start_time), int(end_time), precision):
            time_into_test = t-int(start_time)
            filtered_data = csv_data[csv_data["timestamp"].between(t, t+precision)]
            total_requests = len(filtered_data)
            reqs_per_s = total_requests/precision
            reqsps.append((time_into_test, reqs_per_s))
        
        ax.plot(*zip(*reqsps), label="{} {}p*{}t".format(hostname, data_metadata[hostname]["pods"], data_metadata[hostname]["threads"]))

    ax.set_xlabel("Time into stress test (seconds)")
    ax.set_ylabel("Requests handled per second")
    ax.grid(True)
    ax.set_ylim(bottom=0)
    ax.legend()
    fig.tight_layout()    
    plt.savefig("{}_reqsps.png".format(plot_output_prefix))


def plot_errors():
    for hostname in data:
        fig, ax = plt.subplots()
        csv_data = data[hostname]
        csv_data = csv_data.replace(np.nan, "Success", regex=True)
        #if len(csv_data[csv_data["size"] < 0]) == 0:
        #    print("Skipping {}, no errors".format(hostname))
        #    continue

        start_time = csv_data["timestamp"].min()
        end_time = csv_data["timestamp"].max()
        precision = 10

        print(hostname, set(csv_data["error"]))
        errs = list(set(csv_data["error"]))
        errs = sorted(errs, key=lambda x: (x!="Success", x))
        for errtype in errs:
            errsps = []
            csv_err = csv_data[csv_data["error"] == errtype]

            for t in range(int(start_time), int(end_time), precision):
                time_into_test = t-int(start_time)
                filtered_data = csv_err[csv_err["timestamp"].between(t, t+precision)]
                #filtered_data = filtered_data[filtered_data["size"] < 0]
                total_errs = len(filtered_data)
                errs_per_s = total_errs/precision
                errsps.append((time_into_test, errs_per_s))

            ax.plot(*zip(*errsps), label="{} {}p*{}t {}".format(hostname, data_metadata[hostname]["pods"], data_metadata[hostname]["threads"], errtype))

        ax.set_xlabel("Time into stress test (seconds)")
        ax.set_ylabel("Requests per second")
        ax.grid(True)
        ax.set_ylim(bottom=0)
        ax.legend()
        ax.text(0, 1.01, "{} - {} (UTC)".format(datetime.datetime.utcfromtimestamp(start_time), datetime.datetime.utcfromtimestamp(end_time)), transform=ax.transAxes)
        fig.tight_layout()
        plt.savefig("{}_{}_errsps.png".format(plot_output_prefix, hostname.replace(".", "_")))


def plot_error_durations():
    ax_max = 5
    for hostname, csv_data in data.items():
        if len(csv_data[csv_data["size"] < 0]) == 0:
            continue
        fil = csv_data[csv_data["size"] < 0]
        ax_max = max(ax_max, int(max(fil["duration"])+2))
    fig, ax = plt.subplots()
    ax.grid(True)
    bins = 100
    xaxis_range = (0, ax_max)

    for hostname, csv_data in data.items():
        filtered_data = csv_data[csv_data["size"] < 0]
        ax.hist(filtered_data["duration"], bins=bins, range=xaxis_range, histtype="step", linewidth=2, fill=False, log=True, label="{} {}p*{}t".format(hostname, data_metadata[hostname]["pods"], data_metadata[hostname]["threads"]))
        

    ax.set_xlabel("Transfer duration for errors (seconds)")
    ax.set_ylabel("Number of error transfers")
    ax.set_xlim(xaxis_range)
    ax.legend()
    fig.tight_layout()
    plt.savefig("{}_errdurhist.png".format(plot_output_prefix))

plot_durations()
#plot_rate()
#plot_separate_durations()
#speed_over_time()
#transfer_speed_per_pod()
requests_per_second()
plot_separated_durations()
plot_errors()
plot_error_durations()
