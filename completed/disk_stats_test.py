#!/usr/bin/env python3

import sys
import os
import time

# Simple script to gather some data about a disk to verify it's seen by the OS
# and is properly represented. Defaults to sda if not passed a disk at run time.

DISK = "sda"
STATUS = 0


def check_return_code(return_code, error_message, *output):
    if return_code != 0:
        print(f"ERROR: retval {return_code}: {error_message}", file=sys.stderr)
        global STATUS
        if STATUS == 0:
            STATUS = return_code
        if output:
            for item in output:
                print("output:", item, file=sys.stderr)


if len(sys.argv) > 1:
    DISK = sys.argv[1]

if "pmem" in DISK:
    print(f"Disk {DISK} appears to be an NVDIMM, skipping")
    sys.exit(STATUS)

# Check /proc/partitions, exit with fail if disk isn't found
with open("/proc/partitions", "r") as f:
    if f.read().find(f" {DISK}\n") == -1:
        check_return_code(1, f"Disk {DISK} not found in /proc/partitions")

# Next, check /proc/diskstats
with open("/proc/diskstats", "r") as f:
    if f.read().find(f" {DISK} ") == -1:
        check_return_code(1, f"Disk {DISK} not found in /proc/diskstats")

# Verify the disk shows up in /sys/block/
if not os.path.exists(f"/sys/block/{DISK}"):
    check_return_code(1, f"Disk {DISK} not found in /sys/block/")

# Verify there are stats in /sys/block/$DISK/stat
if os.path.getsize(f"/sys/block/{DISK}/stat") == 0:
    check_return_code(1, f"stat is either empty or nonexistant in /sys/block/{DISK}/")

# Get some baseline stats for use later
with open("/proc/diskstats", "r") as f:
    PROC_STAT_BEGIN = f.readlines()[0].strip()

with open(f"/sys/block/{DISK}/stat", "r") as f:
    SYS_STAT_BEGIN = f.read().strip()

# Generate some disk activity using hdparm -t
os.system(f"hdparm -t /dev/{DISK} > /dev/null 2>&1")

# Sleep 5 to let the stats files catch up
time.sleep(5)

# Make sure the stats have changed
with open("/proc/diskstats", "r") as f:
    PROC_STAT_END = f.readlines()[0].strip()

with open(f"/sys/block/{DISK}/stat", "r") as f:
    SYS_STAT_END = f.read().strip()

if PROC_STAT_BEGIN == PROC_STAT_END:
    check_return_code(1, "Stats in /proc/diskstats did not change", PROC_STAT_BEGIN, PROC_STAT_END)

if SYS_STAT_BEGIN == SYS_STAT_END:
    check_return_code(1, f"Stats in /sys/block/{DISK}/stat did not change", SYS_STAT_BEGIN, SYS_STAT_END)

if STATUS == 0:
    print(f"PASS: Finished testing stats for {DISK}")

sys.exit(STATUS)
