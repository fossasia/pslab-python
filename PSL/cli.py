"""Functions related to CLI for PSLab.

Example
-------
>>> from PSL import cli
>>> parser, subparser = cli.get_parser()
>>> cli.add_collect_args(subparser)
>>> cli.add_wave_gen_args(subparser)
>>> parser.parse_args(["collect","-i","logic_analyzer"])
Namespace(channels=1, duration=1, file_path=None, function='collect',
instrument='logic_analyzer', json=False, port=None)
"""

import argparse
import csv
import json
import sys
import time
from itertools import zip_longest
from typing import List, Tuple

import numpy as np

import PSL.commands_proto as CP
from PSL.logic_analyzer import LogicAnalyzer
from PSL.oscilloscope import Oscilloscope
from PSL.packet_handler import Handler
from PSL.waveform_generator import WaveformGenerator, PWMGenerator


def logic_analyzer(
    device: Handler, channels: int, duration: float
) -> Tuple[List[str], List[np.ndarray]]:
    """Capture logic events on up to four channels simultaneously.

    Parameters
    ----------
    device : :class:`Handler`
        Serial interface for communicating with the PSLab device.
    channels : {1, 2, 3, 4}
        Number of channels to capture events on. Events will be captured on LA1,
        LA2, LA3, and LA4, in that order.
    duration : float
        Duration in seconds up to which events will be captured.

    Returns
    -------
    list of str
        Name of active channels.
    list of numpy.ndarray
        List of numpy.ndarrays holding timestamps in microseconds when logic events
        were detected. The length of the list is equal to the number of channels
        that were used to capture events, and each list element corresponds to a
        channel.

    Warnings
    --------
        This cannot be used at the same time as the oscilloscope.
    """
    la = LogicAnalyzer(device)
    la.capture(channels, block=False)
    time.sleep(duration)
    la.stop()
    timestamps = la.fetch_data()
    channels_name = [la._channel_one_map, la._channel_two_map, "LA3", "LA4"]

    return channels_name[:channels], timestamps


def oscilloscope(
    device: Handler, channels: int, duration: float
) -> Tuple[List[str], List[np.ndarray]]:
    """Capture varying voltage signals on up to four channels simultaneously.

    Parameters
    ----------
    device : :class:`Handler`
        Serial interface for communicating with the PSLab device.
    channels : {1, 2, 4}
        Number of channels to sample from simultaneously. By default, samples are
        captured from CH1, CH2, CH3 and MIC.
    duration : float
        Duration in seconds up to which samples will be captured.

    Returns
    -------
    list of str
        "Timestamp", Name of active channels.
    list of numpy.ndarray
        List of numpy.ndarrays with timestamps in the first index and corresponding
        voltages in the following index. The length of the list is equal to one
        additional to the number of channels that were used to capture samples.
    """
    scope = Oscilloscope(device)
    max_samples = CP.MAX_SAMPLES // channels
    min_timegap = scope._lookup_mininum_timegap(channels)
    max_duration = max_samples * min_timegap * 1e-6
    active_channels = ([scope._channel_one_map] + scope._CH234)[:channels]
    xy = [np.array([]) for _ in range(1 + channels)]

    while duration > 0:
        if duration >= max_duration:
            samples = max_samples
        else:
            samples = (duration * 1e6) // min_timegap

        np.append(xy, scope.capture(channels, samples, min_timegap), axis=1)
        duration -= max_duration

    return ["Timestamp"] + active_channels, xy


INSTRUMENTS = {
    "logic_analyzer": logic_analyzer,
    "oscilloscope": oscilloscope,
}


def collect(handler: Handler, args: argparse.Namespace):
    """Collect data from instruments, and write it in file or stdout.

    Parameters
    ----------
    handler : :class:`Handler`
        Serial interface for communicating with the PSLab device.
    args : :class:`argparse.Namespace`
        Parsed arguments.

    Raises
    ------
    LookupError
        If the given instrument not available.
    """
    instrument = INSTRUMENTS.get(args.instrument)

    if instrument is None:
        raise LookupError(args.instrument + " not available")

    output = instrument(handler, args.channels, args.duration)

    if args.file_path is not None:
        file = open(args.file_path, "w")
    else:
        file = sys.stdout

    if not args.json:
        csv_file = csv.writer(file)
        csv_file.writerow(output[0])
        for row in zip_longest(*output[1]):
            csv_file.writerow(row)
    else:
        output_dict = dict()
        for key, val in zip_longest(*output):
            output_dict[key] = val.tolist()
        json.dump(output_dict, file)

    if args.file_path is not None:
        file.close()


def wave_gen(handler: Handler, args: argparse.Namespace):
    """Generate wave.

    Parameters
    ----------
    handler : :class:`Handler`
        Serial interface for communicating with the PSLab device.
    args : :class:`argparse.Namespace`
        Parsed arguments.
    """
    waveform_generator = WaveformGenerator(handler)

    if args.wave_function == "gen":
        waveform_generator.generate(
            channel= args.channel,
            frequency= args.frequency,
            phase=args.phase,
        )
    elif args.wave_function == "load":
        if args.table is not None:
            table = args.table
        elif args.table_file is not None:
            with open(args.table_file) as table_file:
                table = json.load(table_file)

        x = np.arange(0, len(table), len(table)/512)
        y = [table[int(i)] for i in x]
        waveform_generator.load_table(channel=args.channel, points=y)


def pwn_gen(handler: Handler, args: argparse.Namespace):
    """PWN wave.

    Parameters
    ----------
    handler : :class:`Handler`
        Serial interface for communicating with the PSLab device.
    args : :class:`argparse.Namespace`
        Parsed arguments.
    """
    pass  # TODO


def main(args: argparse.Namespace):
    """Perform the given function on PSLab.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Parsed arguments.
    """
    handler = Handler(port=args.port)

    if args.function == "collect":
        collect(handler, args)
    elif args.function == "wave":
        wave_gen(handler, args)


def get_parser() -> Tuple[argparse.ArgumentParser, argparse._SubParsersAction]:
    """Parser for CLI.

    Returns
    -------
    parser : :class:`argparse.ArgumentParser`
        Arqument parser for CLI.
    functions : :class:`argparse._SubParsersAction`
        SubParser to add other arguments related to different function.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--port",
        type=str,
        default=None,
        required=False,
        help="The name of the port to which the PSLab is connected",
    )
    functions = parser.add_subparsers(
        title="Functions", dest="function", description="Functions to perform on PSLab."
    )

    return parser, functions


def add_collect_args(subparser: argparse._SubParsersAction):
    """Add arguments for collect function to ArgumentParser.

    Parameters
    ----------
    subparser : :class:`argparse._SubParsersAction`
        SubParser to add other arguments related to collect function.
    """
    description = "Available Instruments: " + ", ".join(INSTRUMENTS) + "."
    collect = subparser.add_parser("collect", description=description)
    collect.add_argument(
        "instrument",
        type=str,
        help="The name of the instrument to use",
    )
    collect.add_argument(
        "-c",
        "--channels",
        type=int,
        default=1,
        required=False,
        help="Number of channels to capture"
    )
    collect.add_argument(
        "-d",
        "--duration",
        type=int,
        default=1,
        required=False,
        help="Duration for capturing (in seconds)",
    )
    collect.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        required=False,
        dest="file_path",
        help="File name to write data, otherwise in stdout",
    )
    collect.add_argument(
        "-j",
        "--json",
        action="store_true",
        default=False,
        help="Enable it to write data in json format",
    )


def add_wave_gen_args(subparser: argparse._SubParsersAction):
    """Add arguments for wave_gen function to ArgumentParser.

    Parameters
    ----------
    subparser : :class:`argparse._SubParsersAction`
        SubParser to add other arguments related to wave_gen function.
    """
    wave = subparser.add_parser("wave")
    wave_functions = wave.add_subparsers(
        title="Wave Functions", dest="wave_function",
    )
    wave_gen = wave_functions.add_parser("gen")
    wave_gen.add_argument(
        "channel",
        nargs="+",
        choices=['SI1', 'SI2'],
        help="Pin(s) on which to generate a waveform",
    )
    wave_gen.add_argument(
        "-f",
        "--frequency",
        nargs="+",
        type=float,
        required=True,
        help="Frequency in Hz",
    )
    wave_gen.add_argument(
        "-p",
        "--phase",
        type=float,
        default=0,
        required=False,
        help="Phase between waveforms in degrees",
    )
    load = wave_functions.add_parser("load")
    load.add_argument(
        "channel",
        choices=['SI1', 'SI2'],
        help="Pin(s) on which to load a table",
    )
    load_table = load.add_mutually_exclusive_group(required=True)
    load_table.add_argument(
        "--table",
        type=json.loads,
        default=None,
        help="Table to load in pin SI1 as json",
    )
    load_table.add_argument(
        "--table-file",
        nargs="?",
        type=str,
        const=0,
        default=None,
        help="Table to load in pin SI1 as json file. Default is stdin",
    )


def add_pwn_gen_args(subparser: argparse._SubParsersAction):
    """Add arguments for pwn_gen function to ArgumentParser.

    Parameters
    ----------
    subparser : :class:`argparse._SubParsersAction`
        SubParser to add other arguments related to pwn_gen function.
    """
    # pwn_gen = subparser.add_parser("pwngen")
    pass  # TODO

