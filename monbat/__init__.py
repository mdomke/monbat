#!/usr/bin/env python
# encoding: utf-8

"""
Monitor battery capacity of a portable Mac computer.

Usage:
    monbat run [--plot]
    monbat stats

Options:
    --plot          Create a graph of the charging data
"""
from __future__ import print_function

import re
import shlex
import subprocess as sub
import time
from progressbar import ProgressBar, Bar, Counter, Percentage
from collections import OrderedDict
from datetime import datetime
from tempfile import mktemp

from docopt import docopt


PROPERTIES = OrderedDict([
    ("IsCharging", {"type": bool, "unit": None, "show": False}),
    ("ExternalConnected", {"type": bool, "unit": None, "show": False}),
    ("CurrentCapacity", {"type": int, "unit": "mAh", "show": True}),
    ("MaxCapacity", {"type": int, "unit": "mAh", "show": True}),
    ("DesignCapacity", {"type": int, "unit": "mAh", "show": True}),
    ("CycleCount", {"type": int, "unit": "cycles", "show": True}),
    ("DesignCycleCount", {"type": int, "unit": "cycles", "show": True}),
    ("TimeRemaining", {"type": int, "unit": "min", "show": True}),
    ("Voltage", {"type": int, "unit": "mV", "show": True})
])


def _battery_status():
    status = sub.check_output(shlex.split("ioreg -c AppleSmartBattery -r"))
    return {key: _parse_value(key, status, PROPERTIES[key]["type"])
            for key in PROPERTIES}


def _parse_value(key, data, _type=int):
    converter = lambda x: x
    if _type is int:
        value_expr = "\d+"
    elif _type is bool:
        value_expr = "(Yes|No)"
        converter = lambda x: x == "Yes"
    return _type(converter(re.search('"{}[^"]*"\s*=\s*({})'.format(
        key, value_expr), data).group(1)))


def _format_key(key):
    return re.sub('([A-Z])', r' \1', key).strip()


class ChargingDisplay(ProgressBar):

    def _need_update(self):
        return True


class BatteryMonitor(object):

    def __init__(self):
        self.progress = Bar()
        self.display = ChargingDisplay(
            widgets=[Counter(), " mAh ", Percentage(), " ", self.progress])
        self.current = dict.fromkeys(PROPERTIES, "")
        self.history = {
            "time": [], "capacity": [], "level": [], "charging": []}
        self.started = False

    def update(self):
        self.current.update(_battery_status())

    def print_stats(self):
        self.update()
        for key, meta in PROPERTIES.items():
            if meta["show"]:
                self._print_stat_value(key, meta["unit"])

    def _print_stat_value(self, key, unit=None):
        unit = (unit or "")
        print("{0:.<30}{1!s:.>10} {2}".format(
            _format_key(key), self.current[key], unit))

    def print_status(self):
        if not self.started:
            self.display.maxval = self.current["MaxCapacity"]
            self.display.start()
            self.started = True
        if self.current["ExternalConnected"]:
            self.progress.marker = ">" if self.current["IsCharging"] else "#"
        else:
            self.progress.marker = "<"
        self.display.update(self.current["CurrentCapacity"])

    def _step(self):
        self.update()
        current_capacity = self.current["CurrentCapacity"]
        max_capacity = self.current["MaxCapacity"]
        self.history["charging"].append(self.current["IsCharging"])
        self.history["time"].append(datetime.isoformat(datetime.now()))
        self.history["capacity"].append(float(current_capacity))
        self.history["level"].append(
            float(current_capacity) / float(max_capacity) * 100)
        self.print_status()

    def run(self, plot=False):
        while True:
            try:
                self._step()
                time.sleep(1)
            except KeyboardInterrupt:
                break
        if plot:
            self.plot()

    def plot(self):
        try:
            import numpy as np
            from bokeh.plotting import (
                figure, line, curplot, show, hold, output_file)
            from bokeh.objects import Range1d
        except ImportError:
            return
        output_file(mktemp())
        hold()
        figure(y_range=Range1d(start=0, end=100), x_axis_type="datetime")
        time_values = np.array(self.history["time"], "M64")
        level_values = np.array(self.history["level"])
        line(time_values, level_values)
        curplot().title = "Battery cacpacity"
        show()


def run():
    args = docopt(__doc__)
    monitor = BatteryMonitor()
    if args["stats"]:
        monitor.print_stats()
    elif args["run"]:
        monitor.run(args["--plot"])


if __name__ == '__main__':
    run()
