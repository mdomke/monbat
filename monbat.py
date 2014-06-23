#!/usr/bin/env python
# encoding: utf-8

"""
Monitor battery capacity of a portable Mac computer.

Usage:
    monbat run
    monbat stats
"""

from __future__ import print_function

import sys
import subprocess as sub
import shlex
import re
import time
from tempfile import mktemp
from datetime import datetime
from collections import OrderedDict
from docopt import docopt


PROPERTIES = OrderedDict([
    ("CurrentCapacity", {"type": int, "unit": "mAh"}),
    ("MaxCapacity", {"type": int, "unit": "mAh"}),
    ("DesignCapacity", {"type": int, "unit": "mAh"}),
    ("CycleCount", {"type": int, "unit": "cycles"}),
    ("DesignCycleCount", {"type": int, "unit": "cycles"}),
    ("TimeRemaining", {"type": int, "unit": "min"}),
    ("Voltage", {"type": int, "unit": "mV"})
])


def _battery_status():
    status = sub.check_output(shlex.split("ioreg -c AppleSmartBattery -r"))
    return {key: _parse_value(key, status, PROPERTIES[key]["type"])
            for key in PROPERTIES}


def _parse_value(key, data, _type=int):
    if _type == int:
        value_expr = "\d+"
    return _type(re.search('"{}[^"]*"\s*=\s*({})'.format(
        key, value_expr), data).group(1))


def _format_key(key):
    return re.sub('([A-Z])', r' \1', key).strip()


class BatteryMonitor(object):

    def __init__(self):
        self.current = dict.fromkeys(PROPERTIES, "")
        self.history = {"time": [], "capacity": [], "level": []}

    def update(self):
        self.current.update(_battery_status())

    def print_statistics(self):
        self.update()
        for key, meta in PROPERTIES.items():
            self._print_stat(key, meta["unit"])

    def _print_stat(self, key, unit=None):
        unit = (unit or "")
        print("{0:.<30}{1:.>10} {2}".format(
            _format_key(key), self.current[key], unit))

    def print_status(self):
        print("\r{:.1f} mAh => {:.1f}%".format(
            self.history["capacity"][-1],
            self.history["level"][-1]), end='')
        sys.stdout.flush()

    def _step(self):
        self.update()
        current_capacity = self.current["CurrentCapacity"]
        max_capacity = self.current["MaxCapacity"]
        self.history["time"].append(datetime.isoformat(datetime.now()))
        self.history["capacity"].append(float(current_capacity))
        self.history["level"].append(
            float(current_capacity) / float(max_capacity) * 100)
        self.print_status()

    def run(self):
        while True:
            try:
                self._step()
                time.sleep(1)
            except KeyboardInterrupt:
                break
        self.plot()

    def plot(self):
        import numpy as np
        from bokeh.plotting import (
            figure, line, curplot, show, hold, output_file)
        from bokeh.objects import Range1d
        output_file(mktemp())
        hold()
        figure(y_range=Range1d(start=0, end=100), x_axis_type="datetime")
        time_values = np.array(self.history["time"], "M64")
        level_values = np.array(self.history["level"])
        line(time_values, level_values)
        curplot().title = "Battery cacpacity"
        show()


if __name__ == '__main__':
    args = docopt(__doc__)
    monitor = BatteryMonitor()
    if args["stats"]:
        monitor.print_statistics()
    elif args["run"]:
        monitor.run()
