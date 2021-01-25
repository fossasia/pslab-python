"""Functions related to CLI for PSLab.

Example
-------
>>> from PSL import cli
>>> parser, subparser = cli.get_parser()
>>> cli.add_collect_args(subparser)
>>> cli.add_wave_args(subparser)
>>> cli.add_pwm_args(subparser)
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

import pslab.protocol as CP
from pslab.instrument.logic_analyzer import LogicAnalyzer
from pslab.instrument.oscilloscope import Oscilloscope
from pslab.instrument.waveform_generator import WaveformGenerator, PWMGenerator
from pslab.serial_handler import SerialHandler


def logic_analyzer(
    device: SerialHandler, channels: int, duration: float
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
    device: SerialHandler, channels: int, duration: float
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
            samples = round((duration * 1e6) / min_timegap)

        st = time.time()
        xy = np.append(xy, scope.capture(channels, samples, min_timegap), axis=1)
        duration -= time.time() - st

    return ["Timestamp"] + active_channels, xy


INSTRUMENTS = {
    "logic_analyzer": logic_analyzer,
    "oscilloscope": oscilloscope,
}


def collect(handler: SerialHandler, args: argparse.Namespace):
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


def wave(handler: SerialHandler, args: argparse.Namespace):
    """Generate or load wave.

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
            channels=args.channel,
            frequency=args.frequency,
            phase=args.phase,
        )
    elif args.wave_function == "load":
        if args.table is not None:
            table = args.table
        elif args.table_file is not None:
            with open(args.table_file) as table_file:
                table = json.load(table_file)

        x = np.arange(0, len(table), len(table) / 512)
        y = [table[int(i)] for i in x]
        waveform_generator.load_table(channel=args.channel, points=y)


def pwm(handler: SerialHandler, args: argparse.Namespace):
    """Generate PWM.

    Parameters
    ----------
    handler : :class:`Handler`
        Serial interface for communicating with the PSLab device.
    args : :class:`argparse.Namespace`
        Parsed arguments.
    """
    pwm_generator = PWMGenerator(handler)

    if args.pwm_function == "gen":
        pwm_generator.generate(
            channels=args.channel,
            frequency=args.frequency,
            duty_cycles=args.duty_cycles,
            phases=args.phases,
        )
    elif args.pwm_function == "map":
        pwm_generator.map_reference_clock(
            channels=args.channel,
            prescaler=args.prescaler,
        )


def main(args: argparse.Namespace):
    """Perform the given function on PSLab.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Parsed arguments.
    """
    handler = SerialHandler(port=args.port)

    if args.function == "collect":
        collect(handler, args)
    elif args.function == "wave":
        wave(handler, args)
    elif args.function == "pwm":
        pwm(handler, args)


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
        help="Number of channels to capture",
    )
    collect.add_argument(
        "-d",
        "--duration",
        type=float,
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


def add_wave_args(subparser: argparse._SubParsersAction):
    """Add arguments for wave {gen,load} function to ArgumentParser.

    Parameters
    ----------
    subparser : :class:`argparse._SubParsersAction`
        SubParser to add other arguments related to wave_gen function.
    """
    wave = subparser.add_parser("wave")
    wave_functions = wave.add_subparsers(
        title="Wave Functions",
        dest="wave_function",
    )
    wave_gen = wave_functions.add_parser("gen")
    wave_gen.add_argument(
        "channel",
        nargs="+",
        choices=["SI1", "SI2"],
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
    description = """
        TABLE:
            JSON array of voltage values which make up the waveform. Array length
            must be 512. If the array length less than 512, then the array will be
            expanded in length of 512. Values outside the range -3.3 V to 3.3 V
            will be clipped.

            examples:
                [1,0] or [1,...,0,...],
                [0,1,0,-1,0,1,0,-1,...],
                [0,.025,.05,.075,.1,.125,.15,...]
    """
    load = wave_functions.add_parser("load", description=description)
    load.add_argument(
        "channel",
        choices=["SI1", "SI2"],
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


def add_pwm_args(subparser: argparse._SubParsersAction):
    """Add arguments for pwm {gen,map,set} function to ArgumentParser.

    Parameters
    ----------
    subparser : :class:`argparse._SubParsersAction`
        SubParser to add other arguments related to pwm_gen function.
    """
    pwm = subparser.add_parser("pwm")
    pwm_functions = pwm.add_subparsers(
        title="PWM Functions",
        dest="pwm_function",
    )
    pwm_gen = pwm_functions.add_parser("gen")
    pwm_gen.add_argument(
        "channel",
        nargs="+",
        choices=["SQ1", "SQ2", "SQ3", "SQ4"],
        help="Pin(s) on which to generate a PWM signals",
    )
    pwm_gen.add_argument(
        "-f",
        "--frequency",
        type=float,
        required=True,
        help="Frequency in Hz. Shared by all outputs",
    )
    pwm_gen.add_argument(
        "-d",
        "--duty-cycles",
        nargs="+",
        type=float,
        required=True,
        help="Duty cycle between 0 and 1",
    )
    pwm_gen.add_argument(
        "-p",
        "--phases",
        nargs="+",
        type=float,
        default=0,
        required=False,
        help="Phase between 0 and 1",
    )
    map_ = pwm_functions.add_parser("map")
    map_.add_argument(
        "channel",
        nargs="+",
        choices=["SQ1", "SQ2", "SQ3", "SQ4"],
        help="Digital output pin(s) to which to map the internal oscillator",
    )
    map_.add_argument(
        "-p",
        "--prescaler",
        type=int,
        required=True,
        help="Prescaler value in interval [0, 15]."
        + "The output frequency is 128 / (1 << prescaler) MHz",
    )


def cmdline(args: List[str] = None):
    """Command line for pslab.

    Parameters
    ----------
    args : list of strings.
        Arguments to parse.
    """
    if args is None:
        args = sys.argv[1:]

    parser, subparser = get_parser()
    add_collect_args(subparser)
    add_wave_args(subparser)
    add_pwm_args(subparser)
    main(parser.parse_args(args))
