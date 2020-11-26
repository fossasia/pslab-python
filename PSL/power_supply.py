# -*- coding: utf-8 -*-
# Sub Library of Communication Library for  Pocket Science Lab from FOSSASIA
# related to current and voltage sources PV1,PV2,PV3,PCS
# License : GNU GPL

from __future__ import print_function

import time
from typing import Tuple, Union

import numpy as np

import PSL.commands_proto as CP
from PSL.Peripherals import DACCHAN, MCP4728
from PSL.packet_handler import Handler
from PSL import packet_handler


class PowerSupply:

    
    def connect(**kwargs):
    '''
        If hardware is found, returns an instance of 'ScienceLab', else returns None.
    '''

    obj = ScienceLab(**kwargs)
    if obj.H.fd is not None:
        return obj
    else:
        print('Err')
        raise RuntimeError('Could Not Connect')

    def __init__(self, timeout=1.0, **kwargs):

		self._device = packet_handler.Handler() if device is None else device
        self.DAC = MCP4728(self.H, 3.3, 0)
        self.errmsg = ''

    def set_pv1(self, val):
        """
		Set the voltage on PV1
		12-bit DAC...  -5V to 5V

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		val             Output voltage on PV1. -5V to 5V
		==============  ============================================================================================

		"""
        return self.DAC.setVoltage('PV1', val)

    def set_pv2(self, val):
        """
		Set the voltage on PV2.
		12-bit DAC...  0-3.3V

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		val             Output voltage on PV2. 0-3.3V
		==============  ============================================================================================

		:return: Actual value set on pv2
		"""
        return self.DAC.setVoltage('PV2', val)

    def set_pv3(self, val):
        """
		Set the voltage on PV3

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		val             Output voltage on PV3. 0V to 3.3V
		==============  ============================================================================================

		:return: Actual value set on pv3
		"""
        return self.DAC.setVoltage('PV3', val)

    def set_pcs(self, val):
        """
		Set programmable current source

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		val             Output current on PCS. 0 to 3.3mA. Subject to load resistance. Read voltage on PCS to check.
		==============  ============================================================================================

		:return: value attempted to set on pcs
		"""
        return self.DAC.setCurrent(val)

    def get_pv1(self):
        """
		get the last set voltage on PV1
		12-bit DAC...  -5V to 5V
		"""
        return self.DAC.getVoltage('PV1')

    def get_pv2(self):
        return self.DAC.getVoltage('PV2')

    def get_pv3(self):
        return self.DAC.getVoltage('PV3')

    def get_pcs(self):
        return self.DAC.getVoltage('PCS')
