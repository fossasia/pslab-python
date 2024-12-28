"""Pocket Science Lab by FOSSASIA."""
from pslab.instrument.logic_analyzer import LogicAnalyzer
from pslab.instrument.multimeter import Multimeter
from pslab.instrument.oscilloscope import Oscilloscope
from pslab.instrument.power_supply import PowerSupply
from pslab.instrument.waveform_generator import PWMGenerator, WaveformGenerator
from pslab.sciencelab import ScienceLab

__all__ = (
    "LogicAnalyzer",
    "Multimeter",
    "Oscilloscope",
    "PowerSupply",
    "PWMGenerator",
    "WaveformGenerator",
    "ScienceLab",
)

__version__ = "3.1.0"
