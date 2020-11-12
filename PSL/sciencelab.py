# -*- coding: utf-8 -*-
# Communication Library for  Pocket Science Lab from FOSSASIA
#
# License : GNU GPL

from __future__ import print_function

import time

import numpy as np

import PSL.commands_proto as CP
import PSL.packet_handler as packet_handler
from PSL.multimeter import Multimeter
from PSL.logic_analyzer import LogicAnalyzer
from PSL.oscilloscope import Oscilloscope
from PSL.waveform_generator import PWMGenerator, WaveformGenerator


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


class ScienceLab():
    """
	**Communications library.**

	This class contains methods that can be used to interact with the FOSSASIA PSLab

	Initialization does the following

	* connects to tty device

	.. tabularcolumns:: |p{3cm}|p{11cm}|

	+----------+-----------------------------------------------------------------+
	|Arguments |Description                                                      |
	+==========+=================================================================+
	|timeout   | serial port read timeout. default = 1s                          |
	+----------+-----------------------------------------------------------------+

	>>> from PSL import sciencelab
	>>> I = sciencelab.connect()
	>>> self.__print__(I)
	<sciencelab.ScienceLab instance at 0xb6c0cac>


	Once you have initiated this class,  its various methods will allow access to all the features built
	into the device.



	"""

    BAUD = 1000000
    WType = {'SI1': 'sine', 'SI2': 'sine'}

    def __init__(self, timeout=1.0, **kwargs):
        self.verbose = kwargs.get('verbose', False)
        self.initialArgs = kwargs
        self.generic_name = 'PSLab'
        self.DDS_CLOCK = 0
        self.timebase = 40
        self.MAX_SAMPLES = CP.MAX_SAMPLES
        self.samples = self.MAX_SAMPLES
        self.triggerLevel = 550
        self.triggerChannel = 0
        self.error_count = 0
        self.channels_in_buffer = 0
        self.digital_channels_in_buffer = 0
        self.currents = [0.55e-3, 0.55e-6, 0.55e-5, 0.55e-4]
        self.currentScalers = [1.0, 1.0, 1.0, 1.0]

        self.sine1freq = None
        self.sine2freq = None
        self.sqrfreq = {'SQR1': None, 'SQR2': None, 'SQR3': None, 'SQR4': None}
        self.aboutArray = []
        self.errmsg = ''
        # --------------------------Initialize communication handler, and subclasses-----------------
        self.H = packet_handler.Handler(**kwargs)
        self.logic_analyzer = LogicAnalyzer(device=self.H)
        self.oscilloscope = Oscilloscope(device=self.H)
        self.waveform_generator = WaveformGenerator(device=self.H)
        self.pwm_generator = PWMGenerator(device=self.H)
        self.multimeter = Multimeter(device=self.H)
        self.__runInitSequence__(**kwargs)

    def __runInitSequence__(self, **kwargs):
        self.aboutArray = []
        from PSL.Peripherals import I2C, SPI, NRF24L01, MCP4728
        self.connected = self.H.connected
        if not self.H.connected:
            self.__print__('Check hardware connections. Not connected')

        self.streaming = False
        self.buff = np.zeros(10000)

        self.I2C = I2C(self.H)
        # self.I2C.pullSCLLow(5000)
        self.SPI = SPI(self.H)
        self.hexid = ''
        if self.H.connected:
            for a in ['SI1', 'SI2']:
                self.waveform_generator.load_equation(a, 'sine')
            self.SPI.set_parameters(1, 7, 1, 0)
            self.hexid = hex(self.device_id())

        self.NRF = NRF24L01(self.H)

        self.aboutArray.append(['Radio Transceiver is :', 'Installed' if self.NRF.ready else 'Not Installed'])

        self.DAC = MCP4728(self.H, 3.3, 0)

    def __print__(self, *args):
        if self.verbose:
            for a in args:
                print(a, end="")
            print()

    def get_version(self):
        """
		Returns the version string of the device
		format: LTS-......
		"""
        return self.H.get_version()

    def getRadioLinks(self):
        return self.NRF.get_nodelist()

    def newRadioLink(self, **args):
        '''

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		============== ==============================================================================
		**Arguments**  Description
		============== ==============================================================================
		\*\*Kwargs     Keyword Arguments
		address        Address of the node. a 24 bit number. Printed on the nodes.\n
					   can also be retrieved using :py:meth:`~NRF24L01_class.NRF24L01.get_nodelist`
		============== ==============================================================================


		:return: :py:meth:`~NRF_NODE.RadioLink`


		'''
        from PSL.Peripherals import RadioLink
        return RadioLink(self.NRF, **args)

    # -------------------------------------------------------------------------------------------------------------------#

    # |================================================ANALOG SECTION====================================================|
    # |This section has commands related to analog measurement and control. These include the oscilloscope routines,     |
    # |voltmeters, ammeters, and Programmable voltage sources.                                                           |
    # -------------------------------------------------------------------------------------------------------------------#

    def reconnect(self, **kwargs):
        '''
		Attempts to reconnect to the device in case of a commmunication error or accidental disconnect.
		'''
        self.H.reconnect(**kwargs)
        self.__runInitSequence__(**kwargs)

    def fetch_buffer(self, starting_position=0, total_points=100):
        """
		fetches a section of the ADC hardware buffer
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.RETRIEVE_BUFFER)
        self.H.__sendInt__(starting_position)
        self.H.__sendInt__(total_points)
        for a in range(int(total_points)): self.buff[a] = self.H.__getInt__()
        self.H.__get_ack__()

    def clear_buffer(self, starting_position, total_points):
        """
		clears a section of the ADC hardware buffer
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.CLEAR_BUFFER)
        self.H.__sendInt__(starting_position)
        self.H.__sendInt__(total_points)
        self.H.__get_ack__()

    def fill_buffer(self, starting_position, point_array):
        """
		fill a section of the ADC hardware buffer with data
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.FILL_BUFFER)
        self.H.__sendInt__(starting_position)
        self.H.__sendInt__(len(point_array))
        for a in point_array:
            self.H.__sendInt__(int(a))
        self.H.__get_ack__()

    def start_streaming(self, tg, channel='CH1'):
        """
		Instruct the ADC to start streaming 8-bit data.  use stop_streaming to stop.

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		tg              timegap. 250KHz clock
		channel         channel 'CH1'... 'CH9','IN1','RES'
		==============  ============================================================================================

		"""
        chosa = self.oscilloscope.channels[channel].chosa
        if (self.streaming): self.stop_streaming()
        self.H.__sendByte__(CP.ADC)
        self.H.__sendByte__(CP.START_ADC_STREAMING)
        self.H.__sendByte__(chosa)
        self.H.__sendInt__(tg)  # Timegap between samples.  8MHz timer clock
        self.streaming = True

    def stop_streaming(self):
        """
		Instruct the ADC to stop streaming data
		"""
        if (self.streaming):
            self.H.__sendByte__(CP.STOP_STREAMING)
            self.H.fd.read(20000)
            self.H.fd.flush()
        else:
            self.__print__('not streaming')
        self.streaming = False

    # -------------------------------------------------------------------------------------------------------------------#

    # |===============================================DIGITAL SECTION====================================================|
    # |This section has commands related to digital measurement and control. These include the Logic Analyzer, frequency |
    # |measurement calls, timing routines, digital outputs etc                               |
    # -------------------------------------------------------------------------------------------------------------------#

    def get_temperature(self):
        """
		return the processor's temperature

		:return: Chip Temperature in degree Celcius
		"""
        cs = 3
        V = self.get_ctmu_voltage(0b11110, cs, 0)

        if cs == 1:
            return (646 - V * 1000) / 1.92  # current source = 1
        elif cs == 2:
            return (701.5 - V * 1000) / 1.74  # current source = 2
        elif cs == 3:
            return (760 - V * 1000) / 1.56  # current source = 3

    def get_ctmu_voltage(self, channel, Crange, tgen=1):
        """
		get_ctmu_voltage(5,2)  will activate a constant current source of 5.5uA on IN1 and then measure the voltage at the output.
		If a diode is used to connect IN1 to ground, the forward voltage drop of the diode will be returned. e.g. .6V for a 4148diode.

		If a resistor is connected, ohm's law will be followed within reasonable limits

		channel=5 for IN1

		CRange=0   implies 550uA
		CRange=1   implies 0.55uA
		CRange=2   implies 5.5uA
		CRange=3   implies 55uA

		:return: Voltage
		"""
        if channel == 'CAP': channel = 5

        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.GET_CTMU_VOLTAGE)
        self.H.__sendByte__((channel) | (Crange << 5) | (tgen << 7))

        v = self.H.__getInt__()  # 16*voltage across the current source

        self.H.__get_ack__()
        V = 3.3 * v / 16 / 4095.
        return V

    def __start_ctmu__(self, Crange, trim, tgen=1):
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.START_CTMU)
        self.H.__sendByte__((Crange) | (tgen << 7))
        self.H.__sendByte__(trim)
        self.H.__get_ack__()

    def __stop_ctmu__(self):
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.STOP_CTMU)
        self.H.__get_ack__()

    def resetHardware(self):
        """
		Resets the device, and standalone mode will be enabled if an OLED is connected to the I2C port
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.RESTORE_STANDALONE)

    def read_flash(self, page, location):
        """
		Reads 16 BYTES from the specified location

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		================    ============================================================================================
		**Arguments**
		================    ============================================================================================
		page                page number. 20 pages with 2KBytes each
		location            The flash location(0 to 63) to read from .
		================    ============================================================================================

		:return: a string of 16 characters read from the location
		"""
        self.H.__sendByte__(CP.FLASH)
        self.H.__sendByte__(CP.READ_FLASH)
        self.H.__sendByte__(page)  # send the page number. 20 pages with 2K bytes each
        self.H.__sendByte__(location)  # send the location
        ss = self.H.fd.read(16)
        self.H.__get_ack__()
        return ss

    def read_bulk_flash(self, page, numbytes):
        """
		Reads BYTES from the specified location

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		================    ============================================================================================
		**Arguments**
		================    ============================================================================================
		page                Block number. 0-20. each block is 2kB.
		numbytes               Total bytes to read
		================    ============================================================================================

		:return: a string of 16 characters read from the location
		"""
        self.H.__sendByte__(CP.FLASH)
        self.H.__sendByte__(CP.READ_BULK_FLASH)
        bytes_to_read = numbytes
        if numbytes % 2: bytes_to_read += 1  # bytes+1 . stuff is stored as integers (byte+byte) in the hardware
        self.H.__sendInt__(bytes_to_read)
        self.H.__sendByte__(page)
        ss = self.H.fd.read(int(bytes_to_read))
        self.H.__get_ack__()
        if numbytes % 2: return ss[:-1]  # Kill the extra character we read. Don't surprise the user with extra data
        return ss

    def write_flash(self, page, location, string_to_write):
        """
		write a 16 BYTE string to the selected location (0-63)

		DO NOT USE THIS UNLESS YOU'RE ABSOLUTELY SURE KNOW THIS!
		YOU MAY END UP OVERWRITING THE CALIBRATION DATA, AND WILL HAVE
		TO GO THROUGH THE TROUBLE OF GETTING IT FROM THE MANUFACTURER AND
		REFLASHING IT.

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		================    ============================================================================================
		**Arguments**
		================    ============================================================================================
		page                page number. 20 pages with 2KBytes each
		location            The flash location(0 to 63) to write to.
		string_to_write     a string of 16 characters can be written to each location
		================    ============================================================================================

		"""
        while (len(string_to_write) < 16): string_to_write += '.'
        self.H.__sendByte__(CP.FLASH)
        self.H.__sendByte__(CP.WRITE_FLASH)  # indicate a flash write coming through
        self.H.__sendByte__(page)  # send the page number. 20 pages with 2K bytes each
        self.H.__sendByte__(location)  # send the location
        self.H.fd.write(string_to_write)
        time.sleep(0.1)
        self.H.__get_ack__()

    def write_bulk_flash(self, location, data):
        """
		write a byte array to the entire flash page. Erases any other data

		DO NOT USE THIS UNLESS YOU'RE ABSOLUTELY SURE YOU KNOW THIS!
		YOU MAY END UP OVERWRITING THE CALIBRATION DATA, AND WILL HAVE
		TO GO THROUGH THE TROUBLE OF GETTING IT FROM THE MANUFACTURER AND
		REFLASHING IT.

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		================    ============================================================================================
		**Arguments**
		================    ============================================================================================
		location            Block number. 0-20. each block is 2kB.
		bytearray           Array to dump onto flash. Max size 2048 bytes
		================    ============================================================================================

		"""
        if (type(data) == str): data = [ord(a) for a in data]
        if len(data) % 2 == 1: data.append(0)

        self.H.__sendByte__(CP.FLASH)
        self.H.__sendByte__(CP.WRITE_BULK_FLASH)  # indicate a flash write coming through
        self.H.__sendInt__(len(data))  # send the length
        self.H.__sendByte__(location)
        for n in range(len(data)):
            self.H.__sendByte__(data[n])
        self.H.__get_ack__()

        # verification by readback
        tmp = [ord(a) for a in self.read_bulk_flash(location, len(data))]
        print('Verification done', tmp == data)
        if tmp != data: raise Exception('Verification by readback failed')

    # -------------------------------------------------------------------------------------------------------------------#

    # |===============================================ANALOG OUTPUTS ====================================================|
    # |This section has commands related to current and voltage sources PV1,PV2,PV3,PCS					            |
    # -------------------------------------------------------------------------------------------------------------------#

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

    def WS2812B(self, cols, output='CS1'):
        """
		set shade of WS2182 LED on SQR1

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		cols                2Darray [[R,G,B],[R2,G2,B2],[R3,G3,B3]...]
							brightness of R,G,B ( 0-255  )
		==============  ============================================================================================

		example::

			>>> I.WS2812B([[10,0,0],[0,10,10],[10,0,10]])
			#sets red, cyan, magenta to three daisy chained LEDs

		see :ref:`rgb_video`


		"""
        if output == 'CS1':
            pin = CP.SET_RGB1
        elif output == 'CS2':
            pin = CP.SET_RGB2
        elif output == 'SQR1':
            pin = CP.SET_RGB3
        else:
            print('invalid output')
            return

        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(pin)
        self.H.__sendByte__(len(cols) * 3)
        for col in cols:
            R = col[0]
            G = col[1]
            B = col[2]
            self.H.__sendByte__(G)
            self.H.__sendByte__(R)
            self.H.__sendByte__(B)
        self.H.__get_ack__()

    # -------------------------------------------------------------------------------------------------------------------#

    # |======================================READ PROGRAM AND DATA ADDRESSES=============================================|
    # |Direct access to RAM and FLASH		     																		|
    # -------------------------------------------------------------------------------------------------------------------#

    def read_program_address(self, address):
        """
		Reads and returns the value stored at the specified address in program memory

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		address         Address to read from. Refer to PIC24EP64GP204 programming manual
		==============  ============================================================================================
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.READ_PROGRAM_ADDRESS)
        self.H.__sendInt__(address & 0xFFFF)
        self.H.__sendInt__((address >> 16) & 0xFFFF)
        v = self.H.__getInt__()
        self.H.__get_ack__()
        return v

    def device_id(self):
        a = self.read_program_address(0x800FF8)
        b = self.read_program_address(0x800FFa)
        c = self.read_program_address(0x800FFc)
        d = self.read_program_address(0x800FFe)
        val = d | (c << 16) | (b << 32) | (a << 48)
        self.__print__(a, b, c, d, hex(val))
        return val

    def __write_program_address__(self, address, value):
        """
		Writes a value to the specified address in program memory. Disabled in firmware.

		.. tabularcolumns:: |p{3cm}|p{11cm}|
		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		address         Address to write to. Refer to PIC24EP64GP204 programming manual
						Do Not Screw around with this. It won't work anyway.
		==============  ============================================================================================
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.WRITE_PROGRAM_ADDRESS)
        self.H.__sendInt__(address & 0xFFFF)
        self.H.__sendInt__((address >> 16) & 0xFFFF)
        self.H.__sendInt__(value)
        self.H.__get_ack__()

    def read_data_address(self, address):
        """
		Reads and returns the value stored at the specified address in RAM

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		address         Address to read from.  Refer to PIC24EP64GP204 programming manual|
		==============  ============================================================================================
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.READ_DATA_ADDRESS)
        self.H.__sendInt__(address & 0xFFFF)
        v = self.H.__getInt__()
        self.H.__get_ack__()
        return v

    def __write_data_address__(self, address, value):
        """
		Writes a value to the specified address in RAM

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		address         Address to write to.  Refer to PIC24EP64GP204 programming manual|
		==============  ============================================================================================
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.WRITE_DATA_ADDRESS)
        self.H.__sendInt__(address & 0xFFFF)
        self.H.__sendInt__(value)
        self.H.__get_ack__()

    def enableUartPassthrough(self, baudrate, persist=False):
        '''
		All data received by the device is relayed to an external port(SCL[TX],SDA[RX]) after this function is called

		If a period > .5 seconds elapses between two transmit/receive events, the device resets
		and resumes normal mode. This timeout feature has been implemented in lieu of a hard reset option.
		can be used to load programs into secondary microcontrollers with bootloaders such ATMEGA, and ESP8266


		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		baudrate        BAUDRATE to use
		persist         If set to True, the device will stay in passthrough mode until the next power cycle.
						Otherwise(default scenario), the device will return to normal operation if no data is sent/
						received for a period greater than one second at a time.
		==============  ============================================================================================
		'''
        self.H.__sendByte__(CP.PASSTHROUGHS)
        self.H.__sendByte__(CP.PASS_UART)
        self.H.__sendByte__(1 if persist else 0)
        self.H.__sendInt__(int(round(((64e6 / baudrate) / 4) - 1)))
        self.__print__('BRGVAL:', int(round(((64e6 / baudrate) / 4) - 1)))
        time.sleep(0.1)
        self.__print__('junk bytes read:', len(self.H.fd.read(100)))

    def estimateDistance(self):
        '''

		Read data from ultrasonic distance sensor HC-SR04/HC-SR05.  Sensors must have separate trigger and output pins.
		First a 10uS pulse is output on SQR1.  SQR1 must be connected to the TRIG pin on the sensor prior to use.

		Upon receiving this pulse, the sensor emits a sequence of sound pulses, and the logic level of its output
		pin(which we will monitor via LA1) is also set high.  The logic level goes LOW when the sound packet
		returns to the sensor, or when a timeout occurs.

		The ultrasound sensor outputs a series of 8 sound pulses at 40KHz which corresponds to a time period
		of 25uS per pulse. These pulses reflect off of the nearest object in front of the sensor, and return to it.
		The time between sending and receiving of the pulse packet is used to estimate the distance.
		If the reflecting object is either too far away or absorbs sound, less than 8 pulses may be received, and this
		can cause a measurement error of 25uS which corresponds to 8mm.

		Ensure 5V supply.  You may set SQR2 to HIGH [ I.set_state(SQR2=True) ] , and use that as the power supply.

		returns 0 upon timeout
		'''
        self.H.__sendByte__(CP.NONSTANDARD_IO)
        self.H.__sendByte__(CP.HCSR04_HEADER)

        timeout_msb = int((0.3 * 64e6)) >> 16
        self.H.__sendInt__(timeout_msb)

        A = self.H.__getLong__()
        B = self.H.__getLong__()
        tmt = self.H.__getInt__()
        self.H.__get_ack__()
        if (tmt >= timeout_msb or B == 0): return 0
        rtime = lambda t: t / 64e6
        return 330. * rtime(B - A + 20) / 2.

    """
	def TemperatureAndHumidity(self):
		'''
		init  AM2302.
		This effort was a waste.  There are better humidity and temperature sensors available which use well documented I2C
		'''
		self.H.__sendByte__(CP.NONSTANDARD_IO)
		self.H.__sendByte__(CP.AM2302_HEADER)

		self.H.__get_ack__()
		self.digital_channels_in_buffer=1
	"""

    def opticalArray(self, SS, delay, channel='CH3', **kwargs):
        '''
		read from 3648 element optical sensor array TCD3648P from Toshiba. Experimental feature.
		Neither Sine waves will be available.
		Connect SQR1 to MS , SQR2 to MS , A0 to CHannel , and CS1(on the expansion slot) to ICG

		delay : ICG low duration
		tp : clock wavelength=tp*15nS,  SS=clock/4

		'''
        samples = 3694
        res = kwargs.get('resolution', 10)
        tweak = kwargs.get('tweak', 1)
        chosa = self.oscilloscope.channels[channel].chosa

        self.H.__sendByte__(CP.NONSTANDARD_IO)
        self.H.__sendByte__(CP.TCD1304_HEADER)
        if res == 10:
            self.oscilloscope.channels[channel].resolution = 10
            self.H.__sendByte__(chosa)  # 10-bit
        else:
            self.oscilloscope.channels[channel].resolution = 12
            self.H.__sendByte__(chosa | 0x80)  # 12-bit
        self.H.__sendByte__(tweak)  # Tweak the SH low to ICG high space. =tweak*delay
        self.H.__sendInt__(delay)
        self.H.__sendInt__(int(SS * 64))
        self.timebase = SS
        self.samples = samples
        self.channels_in_buffer = 1
        time.sleep(2 * delay * 1e-6)
        self.H.__get_ack__()

    def setUARTBAUD(self, BAUD):
        self.H.__sendByte__(CP.UART_2)
        self.H.__sendByte__(CP.SET_BAUD)
        self.H.__sendInt__(int(round(((64e6 / BAUD) / 4) - 1)))
        self.__print__('BRG2VAL:', int(round(((64e6 / BAUD) / 4) - 1)))
        self.H.__get_ack__()

    def writeUART(self, character):
        self.H.__sendByte__(CP.UART_2)
        self.H.__sendByte__(CP.SEND_BYTE)
        self.H.__sendByte__(character)
        self.H.__get_ack__()

    def readUART(self):
        self.H.__sendByte__(CP.UART_2)
        self.H.__sendByte__(CP.READ_BYTE)
        return self.H.__getByte__()

    def readUARTStatus(self):
        '''
		return available bytes in UART buffer
		'''
        self.H.__sendByte__(CP.UART_2)
        self.H.__sendByte__(CP.READ_UART2_STATUS)
        return self.H.__getByte__()

    def readLog(self):
        """
		read hardware debug log.
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.READ_LOG)
        log = self.H.fd.readline().strip()
        self.H.__get_ack__()
        return log
