# -*- coding: utf-8 -*-
# Communication Library for  Pocket Science Lab from FOSSASIA
#
# License : GNU GPL

from __future__ import print_function

import time

import PSL.commands_proto as CP
import PSL.packet_handler as packet_handler
from PSL.digital_channel import *
from PSL.oscilloscope import Oscilloscope


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
    WType = {'W1': 'sine', 'W2': 'sine'}

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
        self.oscilloscope = Oscilloscope(device=self.H)
        self.__runInitSequence__(**kwargs)

    def __runInitSequence__(self, **kwargs):
        self.aboutArray = []
        from PSL.Peripherals import I2C, SPI, NRF24L01, MCP4728
        self.connected = self.H.connected
        if not self.H.connected:
            self.__print__('Check hardware connections. Not connected')

        self.streaming = False
        self.buff = np.zeros(10000)
        self.SOCKET_CAPACITANCE = 42e-12  # 42e-12 is typical for the FOSSASIA PSLab. Actual values require calibration (currently not supported).
        self.resistanceScaling = 1.

        self.digital_channel_names = digital_channel_names
        self.allDigitalChannels = self.digital_channel_names
        self.gains = {'CH1': 0, 'CH2': 0}

        # This array of four instances of digital_channel is used to store data retrieved from the
        # logic analyzer section of the device.  It also contains methods to generate plottable data
        # from the original timestamp arrays.
        self.dchans = [digital_channel(a) for a in range(4)]

        self.I2C = I2C(self.H)
        # self.I2C.pullSCLLow(5000)
        self.SPI = SPI(self.H)
        self.hexid = ''
        if self.H.connected:
            for a in ['CH1', 'CH2']:
                self.oscilloscope.channels[a].gain = 1
            for a in ['W1', 'W2']: self.load_equation(a, 'sine')
            self.SPI.set_parameters(1, 7, 1, 0)
            self.hexid = hex(self.device_id())

        self.NRF = NRF24L01(self.H)

        self.aboutArray.append(['Radio Transceiver is :', 'Installed' if self.NRF.ready else 'Not Installed'])

        self.DAC = MCP4728(self.H, 3.3, 0)

    def get_resistance(self):
        V = self.get_average_voltage('SEN')
        if V > 3.295: return np.Inf
        I = (3.3 - V) / 5.1e3
        res = V / I
        return res * self.resistanceScaling

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

    def get_voltage(self, channel_name, **kwargs):
        self.voltmeter_autorange(channel_name)
        return self.get_average_voltage(channel_name, **kwargs)

    def voltmeter_autorange(self, channel_name):
        try:
            self.oscilloscope.channels[channel_name].gain = 1
        except TypeError:  # channel_name is not CH1 or CH2.
            return 1
        V = self.get_average_voltage(channel_name)
        return self.__autoSelectRange__(channel_name, V)

    def __autoSelectRange__(self, channel_name, V):
        keys = [8, 4, 3, 2, 1.5, 1, .5, 0]
        cutoffs = {8: 1, 4: 2, 3: 4, 2: 5, 1.5: 8, 1.: 10, .5: 16, 0: 32}
        for a in keys:
            if abs(V) > a:
                g = cutoffs[a]
                break
        self.oscilloscope.channels[channel_name].gain = g
        return g

    def __autoRangeScope__(self, tg):
        x, y1, y2 = self.oscilloscope.capture(2, 1000, tg)
        self.__autoSelectRange__('CH1', max(abs(y1)))
        self.__autoSelectRange__('CH2', max(abs(y2)))

    def get_average_voltage(self, channel_name, **kwargs):
        """
		Return the voltage on the selected channel

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		+------------+-----------------------------------------------------------------------------------------+
		|Arguments   |Description                                                                              |
		+============+=========================================================================================+
		|channel_name| 'CH1','CH2','CH3', 'MIC','IN1','SEN','V+'                                               |
		+------------+-----------------------------------------------------------------------------------------+
		|sleep       | read voltage in CPU sleep mode. not particularly useful. Also, Buggy.                   |
		+------------+-----------------------------------------------------------------------------------------+
		|\*\*kwargs  | Samples to average can be specified. eg. samples=100 will average a hundred readings    |
		+------------+-----------------------------------------------------------------------------------------+


		see :ref:`stream_video`

		Example:

		>>> self.__print__(I.get_average_voltage('CH4'))
		1.002

		"""
        self.oscilloscope.channels[channel_name].resolution = 12
        scale = self.oscilloscope.channels[channel_name].scale
        vals = [self.__get_raw_average_voltage__(channel_name, **kwargs) for a in range(int(kwargs.get('samples', 1)))]
        # if vals[0]>2052:print (vals)
        val = np.average([scale(a) for a in vals])
        return val

    def __get_raw_average_voltage__(self, channel_name, **kwargs):
        """
		Return the average of 16 raw 12-bit ADC values of the voltage on the selected channel

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================================
		**Arguments**
		==============  ============================================================================================================
		channel_name    'CH1', 'CH2', 'CH3', 'MIC', '5V', 'IN1','SEN'
		sleep           read voltage in CPU sleep mode
		==============  ============================================================================================================

		"""
        chosa = self.oscilloscope.channels[channel_name].chosa
        self.H.__sendByte__(CP.ADC)
        self.H.__sendByte__(CP.GET_VOLTAGE_SUMMED)
        self.H.__sendByte__(chosa)
        V_sum = self.H.__getInt__()
        self.H.__get_ack__()
        return V_sum / 16.  # sum(V)/16.0  #

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
		channel         channel 'CH1'... 'CH9','IN1','SEN'
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

    def __calcDChan__(self, name):
        """
		accepts a string represention of a digital input ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		and returns a corresponding number
		"""

        if name in self.digital_channel_names:
            return self.digital_channel_names.index(name)
        else:
            self.__print__(' invalid channel', name, ' , selecting ID1 instead ')
            return 0

    def __get_high_freq__backup__(self, pin):
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.GET_HIGH_FREQUENCY)
        self.H.__sendByte__(self.__calcDChan__(pin))
        scale = self.H.__getByte__()
        val = self.H.__getLong__()
        self.H.__get_ack__()
        return scale * (val) / 1.0e-1  # 100mS sampling

    def get_high_freq(self, pin):
        """
		retrieves the frequency of the signal connected to ID1. for frequencies > 1MHz
		also good for lower frequencies, but avoid using it since
		the oscilloscope cannot be used simultaneously due to hardware limitations.

		The input frequency is fed to a 32 bit counter for a period of 100mS.
		The value of the counter at the end of 100mS is used to calculate the frequency.

		see :ref:`freq_video`


		.. seealso:: :func:`get_freq`

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		pin             The input pin to measure frequency from : ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		==============  ============================================================================================

		:return: frequency
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.GET_ALTERNATE_HIGH_FREQUENCY)
        self.H.__sendByte__(self.__calcDChan__(pin))
        scale = self.H.__getByte__()
        val = self.H.__getLong__()
        self.H.__get_ack__()
        # self.__print__(hex(val))
        return scale * (val) / 1.0e-1  # 100mS sampling

    def get_freq(self, channel='CNTR', timeout=2):
        """
		Frequency measurement on IDx.
		Measures time taken for 16 rising edges of input signal.
		returns the frequency in Hertz

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		channel         The input to measure frequency from. ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		timeout         This is a blocking call which will wait for one full wavelength before returning the
						calculated frequency.
						Use the timeout option if you're unsure of the input signal.
						returns 0 if timed out
		==============  ============================================================================================

		:return float: frequency


		.. _timing_example:

			* connect SQR1 to ID1

			>>> I.sqr1(4000,25)
			>>> self.__print__(I.get_freq('ID1'))
			4000.0
			>>> self.__print__(I.r2r_time('ID1'))
			#time between successive rising edges
			0.00025
			>>> self.__print__(I.f2f_time('ID1'))
			#time between successive falling edges
			0.00025
			>>> self.__print__(I.pulse_time('ID1'))
			#may detect a low pulse, or a high pulse. Whichever comes first
			6.25e-05
			>>> I.duty_cycle('ID1')
			#returns wavelength, high time
			(0.00025,6.25e-05)

		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.GET_FREQUENCY)
        timeout_msb = int((timeout * 64e6)) >> 16
        self.H.__sendInt__(timeout_msb)
        self.H.__sendByte__(self.__calcDChan__(channel))

        self.H.waitForData(timeout)

        tmt = self.H.__getByte__()
        x = [self.H.__getLong__() for a in range(2)]
        self.H.__get_ack__()
        freq = lambda t: 16 * 64e6 / t if (t) else 0
        # self.__print__(x,tmt,timeout_msb)

        if (tmt): return 0
        return freq(x[1] - x[0])

    '''
	def r2r_time(self,channel='ID1',timeout=0.1):
		"""
		Returns the time interval between two rising edges
		of input signal on ID1

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ================================================================================================
		**Arguments**
		==============  ================================================================================================
		channel         The input to measure time between two rising edges.['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		timeout         Use the timeout option if you're unsure of the input signal time period.
						returns 0 if timed out
		==============  ================================================================================================

		:return float: time between two rising edges of input signal

		.. seealso:: timing_example_

		"""
		self.H.__sendByte__(CP.TIMING)
		self.H.__sendByte__(CP.GET_TIMING)
		timeout_msb = int((timeout*64e6))>>16
		self.H.__sendInt__(timeout_msb)
		self.H.__sendByte__( EVERY_RISING_EDGE<<2 | 2)
		self.H.__sendByte__(self.__calcDChan__(channel))
		tmt = self.H.__getInt__()
		x=[self.H.__getLong__() for a in range(2)]
		self.H.__get_ack__()
		if(tmt >= timeout_msb):return -1
		rtime = lambda t: t/64e6
		y=x[1]-x[0]
		return rtime(y)
	'''

    def r2r_time(self, channel, skip_cycle=0, timeout=5):
        """
		Return a list of rising edges that occured within the timeout period.

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ==============================================================================================================
		**Arguments**
		==============  ==============================================================================================================
		channel         The input to measure time between two rising edges.['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		skip_cycle      Number of points to skip. eg. Pendulums pass through light barriers twice every cycle. SO 1 must be skipped
		timeout         Number of seconds to wait for datapoints. (Maximum 60 seconds)
		==============  ==============================================================================================================

		:return list: Array of points

		"""
        if timeout > 60: timeout = 60
        self.start_one_channel_LA(channel=channel, channel_mode=3, trigger_mode=0)  # every rising edge
        startTime = time.time()
        while time.time() - startTime < timeout:
            a, b, c, d, e = self.get_LA_initial_states()
            if a == self.MAX_SAMPLES / 4:
                a = 0
            if a >= skip_cycle + 2:
                tmp = self.fetch_long_data_from_LA(a, 1)
                self.dchans[0].load_data(e, tmp)
                # print (self.dchans[0].timestamps)
                return [1e-6 * (self.dchans[0].timestamps[skip_cycle + 1] - self.dchans[0].timestamps[0])]
            time.sleep(0.1)
        return []

    def f2f_time(self, channel, skip_cycle=0, timeout=5):
        """
		Return a list of falling edges that occured within the timeout period.

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ==============================================================================================================
		**Arguments**
		==============  ==============================================================================================================
		channel         The input to measure time between two falling edges.['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		skip_cycle      Number of points to skip. eg. Pendulums pass through light barriers twice every cycle. SO 1 must be skipped
		timeout         Number of seconds to wait for datapoints. (Maximum 60 seconds)
		==============  ==============================================================================================================

		:return list: Array of points

		"""
        if timeout > 60: timeout = 60
        self.start_one_channel_LA(channel=channel, channel_mode=2, trigger_mode=0)  # every falling edge
        startTime = time.time()
        while time.time() - startTime < timeout:
            a, b, c, d, e = self.get_LA_initial_states()
            if a == self.MAX_SAMPLES / 4:
                a = 0
            if a >= skip_cycle + 2:
                tmp = self.fetch_long_data_from_LA(a, 1)
                self.dchans[0].load_data(e, tmp)
                # print (self.dchans[0].timestamps)
                return [1e-6 * (self.dchans[0].timestamps[skip_cycle + 1] - self.dchans[0].timestamps[0])]
            time.sleep(0.1)
        return []

    def MeasureInterval(self, channel1, channel2, edge1, edge2, timeout=0.1):
        """
		Measures time intervals between two logic level changes on any two digital inputs(both can be the same)

		For example, one can measure the time interval between the occurence of a rising edge on ID1, and a falling edge on ID3.
		If the returned time is negative, it simply means that the event corresponding to channel2 occurred first.

		returns the calculated time


		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		channel1        The input pin to measure first logic level change
		channel2        The input pin to measure second logic level change
						 -['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		edge1           The type of level change to detect in order to start the timer
							* 'rising'
							* 'falling'
							* 'four rising edges'
		edge2           The type of level change to detect in order to stop the timer
							* 'rising'
							* 'falling'
							* 'four rising edges'
		timeout         Use the timeout option if you're unsure of the input signal time period.
						returns -1 if timed out
		==============  ============================================================================================

		:return : time

		.. seealso:: timing_example_


		"""
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.INTERVAL_MEASUREMENTS)
        timeout_msb = int((timeout * 64e6)) >> 16
        self.H.__sendInt__(timeout_msb)

        self.H.__sendByte__(self.__calcDChan__(channel1) | (self.__calcDChan__(channel2) << 4))

        params = 0
        if edge1 == 'rising':
            params |= 3
        elif edge1 == 'falling':
            params |= 2
        else:
            params |= 4

        if edge2 == 'rising':
            params |= 3 << 3
        elif edge2 == 'falling':
            params |= 2 << 3
        else:
            params |= 4 << 3

        self.H.__sendByte__(params)
        A = self.H.__getLong__()
        B = self.H.__getLong__()
        tmt = self.H.__getInt__()
        self.H.__get_ack__()
        # self.__print__(A,B)
        if (tmt >= timeout_msb or B == 0): return np.NaN
        rtime = lambda t: t / 64e6
        return rtime(B - A + 20)

    def DutyCycle(self, channel='ID1', timeout=1.):
        """
		duty cycle measurement on channel

		returns wavelength(seconds), and length of first half of pulse(high time)

		low time = (wavelength - high time)

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ==============================================================================================
		**Arguments**
		==============  ==============================================================================================
		channel         The input pin to measure wavelength and high time.['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		timeout         Use the timeout option if you're unsure of the input signal time period.
						returns 0 if timed out
		==============  ==============================================================================================

		:return : wavelength,duty cycle

		.. seealso:: timing_example_

		"""
        x, y = self.MeasureMultipleDigitalEdges(channel, channel, 'rising', 'falling', 2, 2, timeout, zero=True)
        if x != None and y != None:  # Both timers registered something. did not timeout
            if y[0] > 0:  # rising edge occured first
                dt = [y[0], x[1]]
            else:  # falling edge occured first
                if y[1] > x[1]:
                    return -1, -1  # Edge dropped. return False
                dt = [y[1], x[1]]
            # self.__print__(x,y,dt)
            params = dt[1], dt[0] / dt[1]
            if params[1] > 0.5:
                self.__print__(x, y, dt)
            return params
        else:
            return -1, -1

    def PulseTime(self, channel='ID1', PulseType='LOW', timeout=0.1):
        """
		duty cycle measurement on channel

		returns wavelength(seconds), and length of first half of pulse(high time)

		low time = (wavelength - high time)

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ==============================================================================================
		**Arguments**
		==============  ==============================================================================================
		channel         The input pin to measure wavelength and high time.['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		PulseType		Type of pulse to detect. May be 'HIGH' or 'LOW'
		timeout         Use the timeout option if you're unsure of the input signal time period.
						returns 0 if timed out
		==============  ==============================================================================================

		:return : pulse width

		.. seealso:: timing_example_

		"""
        x, y = self.MeasureMultipleDigitalEdges(channel, channel, 'rising', 'falling', 2, 2, timeout, zero=True)
        if x != None and y != None:  # Both timers registered something. did not timeout
            if y[0] > 0:  # rising edge occured first
                if PulseType == 'HIGH':
                    return y[0]
                elif PulseType == 'LOW':
                    return x[1] - y[0]
            else:  # falling edge occured first
                if PulseType == 'HIGH':
                    return y[1]
                elif PulseType == 'LOW':
                    return abs(y[0])
        return -1, -1

    def MeasureMultipleDigitalEdges(self, channel1, channel2, edgeType1, edgeType2, points1, points2, timeout=0.1,
                                    **kwargs):
        """
		Measures a set of timestamped logic level changes(Type can be selected) from two different digital inputs.

		Example
			Aim : Calculate value of gravity using time of flight.
			The setup involves a small metal nut attached to an electromagnet powered via SQ1.
			When SQ1 is turned off, the set up is designed to make the nut fall through two
			different light barriers(LED,detector pairs that show a logic change when an object gets in the middle)
			placed at known distances from the initial position.

			one can measure the timestamps for rising edges on ID1 ,and ID2 to determine the speed, and then obtain value of g


		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		channel1        The input pin to measure first logic level change
		channel2        The input pin to measure second logic level change
						 -['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		edgeType1       The type of level change that should be recorded
							* 'rising'
							* 'falling'
							* 'four rising edges' [default]
		edgeType2       The type of level change that should be recorded
							* 'rising'
							* 'falling'
							* 'four rising edges'
		points1			Number of data points to obtain for input 1 (Max 4)
		points2			Number of data points to obtain for input 2 (Max 4)
		timeout         Use the timeout option if you're unsure of the input signal time period.
						returns -1 if timed out
		**kwargs
		  SQ1			set the state of SQR1 output(LOW or HIGH) and then start the timer.  eg. SQR1='LOW'
		  zero			subtract the timestamp of the first point from all the others before returning. default:True
		==============  ============================================================================================

		:return : time

		.. seealso:: timing_example_


		"""
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.TIMING_MEASUREMENTS)
        timeout_msb = int((timeout * 64e6)) >> 16
        # print ('timeout',timeout_msb)
        self.H.__sendInt__(timeout_msb)
        self.H.__sendByte__(self.__calcDChan__(channel1) | (self.__calcDChan__(channel2) << 4))
        params = 0
        if edgeType1 == 'rising':
            params |= 3
        elif edgeType1 == 'falling':
            params |= 2
        else:
            params |= 4

        if edgeType2 == 'rising':
            params |= 3 << 3
        elif edgeType2 == 'falling':
            params |= 2 << 3
        else:
            params |= 4 << 3

        if ('SQR1' in kwargs):  # User wants to toggle SQ1 before starting the timer
            params |= (1 << 6)
            if kwargs['SQR1'] == 'HIGH': params |= (1 << 7)
        self.H.__sendByte__(params)
        if points1 > 4: points1 = 4
        if points2 > 4: points2 = 4
        self.H.__sendByte__(points1 | (points2 << 4))  # Number of points to fetch from either channel

        self.H.waitForData(timeout)

        A = np.array([self.H.__getLong__() for a in range(points1)])
        B = np.array([self.H.__getLong__() for a in range(points2)])
        tmt = self.H.__getInt__()
        self.H.__get_ack__()
        # print(A,B)
        if (tmt >= timeout_msb): return None, None
        rtime = lambda t: t / 64e6
        if (kwargs.get('zero', True)):  # User wants set a reference timestamp
            return rtime(A - A[0]), rtime(B - A[0])
        else:
            return rtime(A), rtime(B)

    def capture_edges1(self, waiting_time=1., **args):
        """
		log timestamps of rising/falling edges on one digital input

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		=================   ======================================================================================================
		**Arguments**
		=================   ======================================================================================================
		waiting_time        Total time to allow the logic analyzer to collect data.
							This is implemented using a simple sleep routine, so if large delays will be involved,
							refer to :func:`start_one_channel_LA` to start the acquisition, and :func:`fetch_LA_channels` to
							retrieve data from the hardware after adequate time. The retrieved data is stored
							in the array self.dchans[0].timestamps.
		keyword arguments
		channel             'ID1',...,'ID4'
		trigger_channel     'ID1',...,'ID4'
		channel_mode        acquisition mode\n
							default value: 3

							- EVERY_SIXTEENTH_RISING_EDGE = 5
							- EVERY_FOURTH_RISING_EDGE    = 4
							- EVERY_RISING_EDGE           = 3
							- EVERY_FALLING_EDGE          = 2
							- EVERY_EDGE                  = 1
							- DISABLED                    = 0

		trigger_mode        same as channel_mode.
							default_value : 3

		=================   ======================================================================================================

		:return:  timestamp array in Seconds

		>>> I.capture_edges(0.2,channel='ID1',trigger_channel='ID1',channel_mode=3,trigger_mode = 3)
		#captures rising edges only. with rising edge trigger on ID1

		"""
        aqchan = args.get('channel', 'ID1')
        trchan = args.get('trigger_channel', aqchan)

        aqmode = args.get('channel_mode', 3)
        trmode = args.get('trigger_mode', 3)

        self.start_one_channel_LA(channel=aqchan, channel_mode=aqmode, trigger_channel=trchan, trigger_mode=trmode)

        time.sleep(waiting_time)

        data = self.get_LA_initial_states()
        tmp = self.fetch_long_data_from_LA(data[0], 1)
        # data[4][0] -> initial state
        return tmp / 64e6

    def start_one_channel_LA_backup__(self, trigger=1, channel='ID1', maximum_time=67, **args):
        """
		start logging timestamps of rising/falling edges on ID1

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		================== ======================================================================================================
		**Arguments**
		================== ======================================================================================================
		trigger            Bool . Enable edge trigger on ID1. use keyword argument edge='rising' or 'falling'
		channel            ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		maximum_time       Total time to sample. If total time exceeds 67 seconds, a prescaler will be used in the reference clock
		kwargs
		triggger_channels  array of digital input names that can trigger the acquisition.eg. trigger= ['ID1','ID2','ID3']
						   will triggger when a logic change specified by the keyword argument 'edge' occurs
						   on either or the three specified trigger inputs.
		edge               'rising' or 'falling' . trigger edge type for trigger_channels.
		================== ======================================================================================================

		:return: Nothing

		"""
        self.clear_buffer(0, self.MAX_SAMPLES / 2)
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.START_ONE_CHAN_LA)
        self.H.__sendInt__(self.MAX_SAMPLES / 4)
        # trigchan bit functions
        # b0 - trigger or not
        # b1 - trigger edge . 1 => rising. 0 => falling
        # b2, b3 - channel to acquire data from. ID1,ID2,ID3,ID4,COMPARATOR
        # b4 - trigger channel ID1
        # b5 - trigger channel ID2
        # b6 - trigger channel ID3

        if ('trigger_channels' in args) and trigger & 1:
            trigchans = args.get('trigger_channels', 0)
            if 'ID1' in trigchans: trigger |= (1 << 4)
            if 'ID2' in trigchans: trigger |= (1 << 5)
            if 'ID3' in trigchans: trigger |= (1 << 6)
        else:
            trigger |= 1 << (self.__calcDChan__(
                channel) + 4)  # trigger on specified input channel if not trigger_channel argument provided

        trigger |= 2 if args.get('edge', 0) == 'rising' else 0
        trigger |= self.__calcDChan__(channel) << 2

        self.H.__sendByte__(trigger)
        self.H.__get_ack__()
        self.digital_channels_in_buffer = 1
        for a in self.dchans:
            a.prescaler = 0
            a.datatype = 'long'
            a.length = self.MAX_SAMPLES / 4
            a.maximum_time = maximum_time * 1e6  # conversion to uS
            a.mode = self.EVERY_EDGE

            # def start_one_channel_LA(self,**args):
            """
			start logging timestamps of rising/falling edges on ID1

			.. tabularcolumns:: |p{3cm}|p{11cm}|

			================== ======================================================================================================
			**Arguments**
			================== ======================================================================================================
			args
			channel             ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
			trigger_channel     ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']

			channel_mode        acquisition mode\n
								default value: 1(EVERY_EDGE)

								- EVERY_SIXTEENTH_RISING_EDGE = 5
								- EVERY_FOURTH_RISING_EDGE    = 4
								- EVERY_RISING_EDGE           = 3
								- EVERY_FALLING_EDGE          = 2
								- EVERY_EDGE                  = 1
								- DISABLED                    = 0

			trigger_edge        1=Falling edge
								0=Rising Edge
								-1=Disable Trigger

			================== ======================================================================================================

			:return: Nothing

			self.clear_buffer(0,self.MAX_SAMPLES/2);
			self.H.__sendByte__(CP.TIMING)
			self.H.__sendByte__(CP.START_ONE_CHAN_LA)
			self.H.__sendInt__(self.MAX_SAMPLES/4)
			aqchan = self.__calcDChan__(args.get('channel','ID1'))
			aqmode = args.get('channel_mode',1)

			if 'trigger_channel' in args:
				trchan = self.__calcDChan__(args.get('trigger_channel','ID1'))
				tredge = args.get('trigger_edge',0)
				self.__print__('trigger chan',trchan,' trigger edge ',tredge)
				if tredge!=-1:
					self.H.__sendByte__((trchan<<4)|(tredge<<1)|1)
				else:
					self.H.__sendByte__(0)  #no triggering
			elif 'trigger_edge' in args:
				tredge = args.get('trigger_edge',0)
				if tredge!=-1:
					self.H.__sendByte__((aqchan<<4)|(tredge<<1)|1)  #trigger on acquisition channel
				else:
					self.H.__sendByte__(0)  #no triggering
			else:
				self.H.__sendByte__(0)  #no triggering

			self.H.__sendByte__((aqchan<<4)|aqmode)


			self.H.__get_ack__()
			self.digital_channels_in_buffer = 1

			a = self.dchans[0]
			a.prescaler = 0
			a.datatype='long'
			a.length = self.MAX_SAMPLES/4
			a.maximum_time = 67*1e6 #conversion to uS
			a.mode = args.get('channel_mode',1)
			a.initial_state_override=False
			'''
			if trmode in [3,4,5]:
				a.initial_state_override = 2
			elif trmode == 2:
				a.initial_state_override = 1
			'''
			"""

    def start_one_channel_LA(self, **args):
        """
		start logging timestamps of rising/falling edges on ID1

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		================== ======================================================================================================
		**Arguments**
		================== ======================================================================================================
		args
		channel            ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']

		channel_mode       acquisition mode.
						   default value: 1

							- EVERY_SIXTEENTH_RISING_EDGE = 5
							- EVERY_FOURTH_RISING_EDGE    = 4
							- EVERY_RISING_EDGE           = 3
							- EVERY_FALLING_EDGE          = 2
							- EVERY_EDGE                  = 1
							- DISABLED                    = 0


		================== ======================================================================================================

		:return: Nothing

		see :ref:`LA_video`

		"""
        # trigger_channel    ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
        # trigger_mode       same as channel_mode.
        #				   default_value : 3
        self.clear_buffer(0, self.MAX_SAMPLES / 2)
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.START_ALTERNATE_ONE_CHAN_LA)
        self.H.__sendInt__(self.MAX_SAMPLES / 4)
        aqchan = self.__calcDChan__(args.get('channel', 'ID1'))
        aqmode = args.get('channel_mode', 1)
        trchan = self.__calcDChan__(args.get('trigger_channel', 'ID1'))
        trmode = args.get('trigger_mode', 3)

        self.H.__sendByte__((aqchan << 4) | aqmode)
        self.H.__sendByte__((trchan << 4) | trmode)
        self.H.__get_ack__()
        self.digital_channels_in_buffer = 1

        a = self.dchans[0]
        a.prescaler = 0
        a.datatype = 'long'
        a.length = self.MAX_SAMPLES / 4
        a.maximum_time = 67 * 1e6  # conversion to uS
        a.mode = args.get('channel_mode', 1)
        a.name = args.get('channel', 'ID1')

        if trmode in [3, 4, 5]:
            a.initial_state_override = 2
        elif trmode == 2:
            a.initial_state_override = 1

    def start_two_channel_LA(self, **args):
        """
		start logging timestamps of rising/falling edges on ID1,AD2

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  =======================================================================================================
		**Arguments**
		==============  =======================================================================================================
		trigger         Bool . Enable rising edge trigger on ID1
		\*\*args
		chans			Channels to acquire data from . default ['ID1','ID2']
		modes               modes for each channel. Array .\n
							default value: [1,1]

							- EVERY_SIXTEENTH_RISING_EDGE = 5
							- EVERY_FOURTH_RISING_EDGE    = 4
							- EVERY_RISING_EDGE           = 3
							- EVERY_FALLING_EDGE          = 2
							- EVERY_EDGE                  = 1
							- DISABLED                    = 0

		maximum_time    Total time to sample. If total time exceeds 67 seconds, a prescaler will be used in the reference clock

		==============  =======================================================================================================

		::

			"fetch_long_data_from_dma(samples,1)" to get data acquired from channel 1
			"fetch_long_data_from_dma(samples,2)" to get data acquired from channel 2
			The read data can be accessed from self.dchans[0 or 1]
		"""
        # Trigger not working up to expectations. DMA keeps dumping Null values even though not triggered.

        # trigger         True/False  : Whether or not to trigger the Logic Analyzer using the first channel of the two.
        # trig_type		'rising' / 'falling' .  Type of logic change to trigger on
        # trig_chan		channel to trigger on . Any digital input. default chans[0]

        modes = args.get('modes', [1, 1])
        strchans = args.get('chans', ['ID1', 'ID2'])
        chans = [self.__calcDChan__(strchans[0]), self.__calcDChan__(strchans[1])]  # Convert strings to index
        maximum_time = args.get('maximum_time', 67)
        trigger = args.get('trigger', 0)
        if trigger:
            trigger = 1
            if args.get('edge', 'rising') == 'falling': trigger |= 2
            trigger |= (self.__calcDChan__(args.get('trig_chan', strchans[0])) << 4)
        # print (args.get('trigger',0),args.get('edge'),args.get('trig_chan',strchans[0]),hex(trigger),args)
        else:
            trigger = 0

        self.clear_buffer(0, self.MAX_SAMPLES)
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.START_TWO_CHAN_LA)
        self.H.__sendInt__(self.MAX_SAMPLES / 4)
        self.H.__sendByte__(trigger)

        self.H.__sendByte__((modes[1] << 4) | modes[0])  # Modes. four bits each
        self.H.__sendByte__((chans[1] << 4) | chans[0])  # Channels. four bits each
        self.H.__get_ack__()
        n = 0
        for a in self.dchans[:2]:
            a.prescaler = 0
            a.length = self.MAX_SAMPLES / 4
            a.datatype = 'long'
            a.maximum_time = maximum_time * 1e6  # conversion to uS
            a.mode = modes[n]
            a.channel_number = chans[n]
            a.name = strchans[n]
            n += 1
        self.digital_channels_in_buffer = 2

    def start_three_channel_LA(self, **args):
        """
		start logging timestamps of rising/falling edges on ID1,ID2,ID3

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		================== ======================================================================================================
		**Arguments**
		================== ======================================================================================================
		args
		trigger_channel     ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']

		modes               modes for each channel. Array .\n
							default value: [1,1,1]

							- EVERY_SIXTEENTH_RISING_EDGE = 5
							- EVERY_FOURTH_RISING_EDGE    = 4
							- EVERY_RISING_EDGE           = 3
							- EVERY_FALLING_EDGE          = 2
							- EVERY_EDGE                  = 1
							- DISABLED                    = 0

		trigger_mode        same as modes(previously documented keyword argument)
							default_value : 3

		================== ======================================================================================================

		:return: Nothing

		"""
        self.clear_buffer(0, self.MAX_SAMPLES)
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.START_THREE_CHAN_LA)
        self.H.__sendInt__(self.MAX_SAMPLES / 4)
        modes = args.get('modes', [1, 1, 1, 1])
        trchan = self.__calcDChan__(args.get('trigger_channel', 'ID1'))
        trmode = args.get('trigger_mode', 3)

        self.H.__sendInt__(modes[0] | (modes[1] << 4) | (modes[2] << 8))
        self.H.__sendByte__((trchan << 4) | trmode)

        self.H.__get_ack__()
        self.digital_channels_in_buffer = 3

        n = 0
        for a in self.dchans[:3]:
            a.prescaler = 0
            a.length = self.MAX_SAMPLES / 4
            a.datatype = 'int'
            a.maximum_time = 1e3  # < 1 mS between each consecutive level changes in the input signal must be ensured to prevent rollover
            a.mode = modes[n]
            a.name = a.digital_channel_names[n]
            if trmode in [3, 4, 5]:
                a.initial_state_override = 2
            elif trmode == 2:
                a.initial_state_override = 1
            n += 1

    def start_four_channel_LA(self, trigger=1, maximum_time=0.001, mode=[1, 1, 1, 1], **args):
        """
		Four channel Logic Analyzer.
		start logging timestamps from a 64MHz counter to record level changes on ID1,ID2,ID3,ID4.

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		trigger         Bool . Enable rising edge trigger on ID1

		maximum_time    Maximum delay expected between two logic level changes.\n
						If total time exceeds 1 mS, a prescaler will be used in the reference clock
						However, this only refers to the maximum time between two successive level changes. If a delay larger
						than .26 S occurs, it will be truncated by modulo .26 S.\n
						If you need to record large intervals, try single channel/two channel modes which use 32 bit counters
						capable of time interval up to 67 seconds.

		mode            modes for each channel. List with four elements\n
						default values: [1,1,1,1]

						- EVERY_SIXTEENTH_RISING_EDGE = 5
						- EVERY_FOURTH_RISING_EDGE    = 4
						- EVERY_RISING_EDGE           = 3
						- EVERY_FALLING_EDGE          = 2
						- EVERY_EDGE                  = 1
						- DISABLED                    = 0

		==============  ============================================================================================

		:return: Nothing

		.. seealso::

			Use :func:`fetch_long_data_from_LA` (points to read,x) to get data acquired from channel x.
			The read data can be accessed from :class:`~ScienceLab.dchans` [x-1]
		"""
        self.clear_buffer(0, self.MAX_SAMPLES)
        prescale = 0
        """
		if(maximum_time > 0.26):
			#self.__print__('too long for 4 channel. try 2/1 channels')
			prescale = 3
		elif(maximum_time > 0.0655):
			prescale = 3
		elif(maximum_time > 0.008191):
			prescale = 2
		elif(maximum_time > 0.0010239):
			prescale = 1
		"""
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.START_FOUR_CHAN_LA)
        self.H.__sendInt__(self.MAX_SAMPLES / 4)
        self.H.__sendInt__(mode[0] | (mode[1] << 4) | (mode[2] << 8) | (mode[3] << 12))
        self.H.__sendByte__(prescale)  # prescaler
        trigopts = 0
        trigopts |= 4 if args.get('trigger_ID1', 0) else 0
        trigopts |= 8 if args.get('trigger_ID2', 0) else 0
        trigopts |= 16 if args.get('trigger_ID3', 0) else 0
        if (trigopts == 0): trigger |= 4  # select one trigger channel(ID1) if none selected
        trigopts |= 2 if args.get('edge', 0) == 'rising' else 0
        trigger |= trigopts
        self.H.__sendByte__(trigger)
        self.H.__get_ack__()
        self.digital_channels_in_buffer = 4
        n = 0
        for a in self.dchans:
            a.prescaler = prescale
            a.length = self.MAX_SAMPLES / 4
            a.datatype = 'int'
            a.name = a.digital_channel_names[n]
            a.maximum_time = maximum_time * 1e6  # conversion to uS
            a.mode = mode[n]
            n += 1

    def get_LA_initial_states(self):
        """
		fetches the initial states of digital inputs that were recorded right before the Logic analyzer was started, and the total points each channel recorded

		:return: chan1 progress,chan2 progress,chan3 progress,chan4 progress,[ID1,ID2,ID3,ID4]. eg. [1,0,1,1]
		"""
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.GET_INITIAL_DIGITAL_STATES)
        initial = self.H.__getInt__()
        A = (self.H.__getInt__() - initial) / 2
        B = (self.H.__getInt__() - initial) / 2 - self.MAX_SAMPLES / 4
        C = (self.H.__getInt__() - initial) / 2 - 2 * self.MAX_SAMPLES / 4
        D = (self.H.__getInt__() - initial) / 2 - 3 * self.MAX_SAMPLES / 4
        s = self.H.__getByte__()
        s_err = self.H.__getByte__()
        self.H.__get_ack__()

        if A == 0: A = self.MAX_SAMPLES / 4
        if B == 0: B = self.MAX_SAMPLES / 4
        if C == 0: C = self.MAX_SAMPLES / 4
        if D == 0: D = self.MAX_SAMPLES / 4

        if A < 0: A = 0
        if B < 0: B = 0
        if C < 0: C = 0
        if D < 0: D = 0

        return A, B, C, D, {'ID1': (s & 1 != 0), 'ID2': (s & 2 != 0), 'ID3': (s & 4 != 0), 'ID4': (s & 8 != 0),
                            'SEN': (s & 16 != 16)}  # SEN is inverted comparator output.

    def stop_LA(self):
        """
		Stop any running logic analyzer function
		"""
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.STOP_LA)
        self.H.__get_ack__()

    def fetch_int_data_from_LA(self, bytes, chan=1):
        """
		fetches the data stored by DMA. integer address increments

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		bytes:          number of readings(integers) to fetch
		chan:           channel number (1-4)
		==============  ============================================================================================
		"""
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.FETCH_INT_DMA_DATA)
        self.H.__sendInt__(bytes)
        self.H.__sendByte__(chan - 1)

        ss = self.H.fd.read(int(bytes * 2))
        t = np.zeros(int(bytes) * 2)
        for a in range(int(bytes)):
            t[a] = CP.ShortInt.unpack(ss[a * 2:a * 2 + 2])[0]

        self.H.__get_ack__()

        t = np.trim_zeros(t)
        b = 1
        rollovers = 0
        while b < len(t):
            if (t[b] < t[b - 1] and t[b] != 0):
                rollovers += 1
                t[b:] += 65535
            b += 1
        return t

    def fetch_long_data_from_LA(self, bytes, chan=1):
        """
		fetches the data stored by DMA. long address increments

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		bytes:          number of readings(long integers) to fetch
		chan:           channel number (1,2)
		==============  ============================================================================================
		"""
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.FETCH_LONG_DMA_DATA)
        self.H.__sendInt__(bytes)
        self.H.__sendByte__(chan - 1)
        ss = self.H.fd.read(int(bytes * 4))
        self.H.__get_ack__()
        tmp = np.zeros(int(bytes))
        for a in range(int(bytes)):
            tmp[a] = CP.Integer.unpack(ss[a * 4:a * 4 + 4])[0]
        tmp = np.trim_zeros(tmp)
        return tmp

    def fetch_LA_channels(self):
        """
		reads and stores the channels in self.dchans.

		"""
        data = self.get_LA_initial_states()
        # print (data)
        for a in range(4):
            if (self.dchans[a].channel_number < self.digital_channels_in_buffer): self.__fetch_LA_channel__(a, data)
        return True

    def __fetch_LA_channel__(self, channel_number, initial_states):
        s = initial_states[4]
        a = self.dchans[channel_number]
        if a.channel_number >= self.digital_channels_in_buffer:
            self.__print__('channel unavailable')
            return False

        samples = a.length
        if a.datatype == 'int':
            tmp = self.fetch_int_data_from_LA(initial_states[a.channel_number], a.channel_number + 1)
            a.load_data(s, tmp)
        else:
            tmp = self.fetch_long_data_from_LA(initial_states[a.channel_number * 2], a.channel_number + 1)
            a.load_data(s, tmp)

        # offset=0
        # a.timestamps -= offset
        a.generate_axes()
        return True

    def get_states(self):
        """
		gets the state of the digital inputs. returns dictionary with keys 'ID1','ID2','ID3','ID4'

		>>> self.__print__(get_states())
		{'ID1': True, 'ID2': True, 'ID3': True, 'ID4': False}

		"""
        self.H.__sendByte__(CP.DIN)
        self.H.__sendByte__(CP.GET_STATES)
        s = self.H.__getByte__()
        self.H.__get_ack__()
        return {'ID1': (s & 1 != 0), 'ID2': (s & 2 != 0), 'ID3': (s & 4 != 0), 'ID4': (s & 8 != 0)}

    def get_state(self, input_id):
        """
		returns the logic level on the specified input (ID1,ID2,ID3, or ID4)

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**    Description
		==============  ============================================================================================
		input_id        the input channel
							'ID1' -> state of ID1
							'ID4' -> state of ID4
		==============  ============================================================================================

		>>> self.__print__(I.get_state(I.ID1))
		False

		"""
        return self.get_states()[input_id]

    def set_state(self, **kwargs):
        """

		set the logic level on digital outputs SQR1,SQR2,SQR3,SQR4

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		\*\*kwargs      SQR1,SQR2,SQR3,SQR4
						states(0 or 1)
		==============  ============================================================================================

		>>> I.set_state(SQR1=1,SQR2=0)
		sets SQR1 HIGH, SQR2 LOw, but leave SQR3,SQR4 untouched.

		"""
        data = 0
        if 'SQR1' in kwargs:
            data |= 0x10 | (kwargs.get('SQR1'))
        if 'SQR2' in kwargs:
            data |= 0x20 | (kwargs.get('SQR2') << 1)
        if 'SQR3' in kwargs:
            data |= 0x40 | (kwargs.get('SQR3') << 2)
        if 'SQR4' in kwargs:
            data |= 0x80 | (kwargs.get('SQR4') << 3)
        self.H.__sendByte__(CP.DOUT)
        self.H.__sendByte__(CP.SET_STATE)
        self.H.__sendByte__(data)
        self.H.__get_ack__()

    def countPulses(self, channel='SEN'):
        """

		Count pulses on a digital input. Retrieve total pulses using readPulseCount

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		channel         The input pin to measure rising edges on : ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
		==============  ============================================================================================
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.START_COUNTING)
        self.H.__sendByte__(self.__calcDChan__(channel))
        self.H.__get_ack__()

    def readPulseCount(self):
        """

		Read pulses counted using a digital input. Call countPulses before using this.

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		==============  ============================================================================================
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.FETCH_COUNT)
        count = self.H.__getInt__()
        self.H.__get_ack__()
        return count

    def __charge_cap__(self, state, t):
        self.H.__sendByte__(CP.ADC)
        self.H.__sendByte__(CP.SET_CAP)
        self.H.__sendByte__(state)
        self.H.__sendInt__(t)
        self.H.__get_ack__()

    def __capture_capacitance__(self, samples, tg):
        raise NotImplementedError
#        from PSL.analyticsClass import analyticsClass
#        self.AC = analyticsClass()
#        self.__charge_cap__(1, 50000)
#        x, y = self.capture_fullspeed_hr('CAP', samples, tg, 'READ_CAP')
#        fitres = self.AC.fit_exp(x * 1e-6, y)
#        if fitres:
#            cVal, newy = fitres
#            # from PSL import *
#            # plot(x,newy)
#            # show()
#            return x, y, newy, cVal
#        else:
#            return None

    def capacitance_via_RC_discharge(self):
        cap = self.get_capacitor_range()[1]
        T = 2 * cap * 20e3 * 1e6  # uS
        samples = 500
        if T > 5000 and T < 10e6:
            if T > 50e3: samples = 250
            RC = self.__capture_capacitance__(samples, int(T / samples))[3][1]
            return RC / 10e3
        else:
            self.__print__('cap out of range %f %f' % (T, cap))
            return 0

    def __get_capacitor_range__(self, ctime):
        self.__charge_cap__(0, 30000)
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.GET_CAP_RANGE)
        self.H.__sendInt__(ctime)
        V_sum = self.H.__getInt__()
        self.H.__get_ack__()
        V = V_sum * 3.3 / 16 / 4095
        C = -ctime * 1e-6 / 1e4 / np.log(1 - V / 3.3)
        return V, C

    def get_capacitor_range(self):
        """
		Charges a capacitor connected to IN1 via a 20K resistor from a 3.3V source for a fixed interval
		Returns the capacitance calculated using the formula Vc = Vs(1-exp(-t/RC))
		This function allows an estimation of the parameters to be used with the :func:`get_capacitance` function.

		"""
        t = 10
        P = [1.5, 50e-12]
        for a in range(4):
            P = list(self.__get_capacitor_range__(50 * (10 ** a)))
            if (P[0] > 1.5):
                if a == 0 and P[0] > 3.28:  # pico farads range. Values will be incorrect using this method
                    P[1] = 50e-12
                break
        return P

    def get_capacitance(self):  # time in uS
        """
		measures capacitance of component connected between CAP and ground


		:return: Capacitance (F)

		Constant Current Charging

		.. math::

			Q_{stored} = C*V

			I_{constant}*time = C*V

			C = I_{constant}*time/V_{measured}

		Also uses Constant Voltage Charging via 20K resistor if required.

		"""
        GOOD_VOLTS = [2.5, 2.8]
        CT = 10
        CR = 1
        iterations = 0
        start_time = time.time()

        while (time.time() - start_time) < 1:
            # self.__print__('vals',CR,',',CT)
            if CT > 65000:
                self.__print__('CT too high')
                return self.capacitance_via_RC_discharge()
            V, C = self.__get_capacitance__(CR, 0, CT)
            # print(CR,CT,V,C)
            if CT > 30000 and V < 0.1:
                self.__print__('Capacitance too high for this method')
                return 0

            elif V > GOOD_VOLTS[0] and V < GOOD_VOLTS[1]:
                return C
            elif V < GOOD_VOLTS[0] and V > 0.01 and CT < 40000:
                if GOOD_VOLTS[0] / V > 1.1 and iterations < 10:
                    CT = int(CT * GOOD_VOLTS[0] / V)
                    iterations += 1
                    self.__print__('increased CT ', CT)
                elif iterations == 10:
                    return 0
                else:
                    return C
            elif V <= 0.1 and CR < 3:
                CR += 1
            elif CR == 3:
                self.__print__('Capture mode ')
                return self.capacitance_via_RC_discharge()

    def __get_capacitance__(self, current_range, trim, Charge_Time):  # time in uS
        self.__charge_cap__(0, 30000)
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.GET_CAPACITANCE)
        self.H.__sendByte__(current_range)
        if (trim < 0):
            self.H.__sendByte__(int(31 - abs(trim) / 2) | 32)
        else:
            self.H.__sendByte__(int(trim / 2))
        self.H.__sendInt__(Charge_Time)
        time.sleep(Charge_Time * 1e-6 + .02)
        VCode = self.H.__getInt__()
        V = 3.3 * VCode / 4095
        self.H.__get_ack__()
        Charge_Current = self.currents[current_range] * (100 + trim) / 100.0
        if V:
            C = (Charge_Current * Charge_Time * 1e-6 / V - self.SOCKET_CAPACITANCE) / self.currentScalers[
                current_range]
        else:
            C = 0
        return V, C

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

    # |===============================================WAVEGEN SECTION====================================================|
    # |This section has commands related to waveform generators W1, W2, PWM outputs, servo motor control etc.            |
    # -------------------------------------------------------------------------------------------------------------------#

    def set_wave(self, chan, freq):
        """
		Set the frequency of wavegen

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		chan       	Channel to set frequency for. W1 or W2
		frequency       Frequency to set on wave generator
		==============  ============================================================================================


		:return: frequency
		"""
        if chan == 'W1':
            self.set_w1(freq)
        elif chan == 'W2':
            self.set_w2(freq)

    def set_sine1(self, freq):
        """
		Set the frequency of wavegen 1 after setting its waveform type to sinusoidal

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		frequency       Frequency to set on wave generator 1.
		==============  ============================================================================================


		:return: frequency
		"""
        return self.set_w1(freq, 'sine')

    def set_sine2(self, freq):
        """
		Set the frequency of wavegen 2 after setting its waveform type to sinusoidal

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		frequency       Frequency to set on wave generator 1.
		==============  ============================================================================================


		:return: frequency
		"""
        return self.set_w2(freq, 'sine')

    def set_w1(self, freq, waveType=None):
        """
		Set the frequency of wavegen 1

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		frequency       Frequency to set on wave generator 1.
		waveType		'sine','tria' . Default : Do not reload table. and use last set table
		==============  ============================================================================================


		:return: frequency
		"""
        if freq < 0.1:
            self.__print__('freq too low')
            return 0
        elif freq < 1100:
            HIGHRES = 1
            table_size = 512
        else:
            HIGHRES = 0
            table_size = 32

        if waveType:  # User wants to set a particular waveform type. sine or tria
            if waveType in ['sine', 'tria']:
                if (self.WType['W1'] != waveType):
                    self.load_equation('W1', waveType)
            else:
                print('Not a valid waveform. try sine or tria')

        p = [1, 8, 64, 256]
        prescaler = 0
        while prescaler <= 3:
            wavelength = int(round(64e6 / freq / p[prescaler] / table_size))
            freq = (64e6 / wavelength / p[prescaler] / table_size)
            if wavelength < 65525: break
            prescaler += 1
        if prescaler == 4:
            self.__print__('out of range')
            return 0

        self.H.__sendByte__(CP.WAVEGEN)
        self.H.__sendByte__(CP.SET_SINE1)
        self.H.__sendByte__(HIGHRES | (prescaler << 1))  # use larger table for low frequencies
        self.H.__sendInt__(wavelength - 1)
        self.H.__get_ack__()
        self.sine1freq = freq
        return freq

    def set_w2(self, freq, waveType=None):
        """
		Set the frequency of wavegen 2

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		frequency       Frequency to set on wave generator 1.
		==============  ============================================================================================

		:return: frequency
		"""
        if freq < 0.1:
            self.__print__('freq too low')
            return 0
        elif freq < 1100:
            HIGHRES = 1
            table_size = 512
        else:
            HIGHRES = 0
            table_size = 32

        if waveType:  # User wants to set a particular waveform type. sine or tria
            if waveType in ['sine', 'tria']:
                if (self.WType['W2'] != waveType):
                    self.load_equation('W2', waveType)
            else:
                print('Not a valid waveform. try sine or tria')

        p = [1, 8, 64, 256]
        prescaler = 0
        while prescaler <= 3:
            wavelength = int(round(64e6 / freq / p[prescaler] / table_size))
            freq = (64e6 / wavelength / p[prescaler] / table_size)
            if wavelength < 65525: break
            prescaler += 1
        if prescaler == 4:
            self.__print__('out of range')
            return 0

        self.H.__sendByte__(CP.WAVEGEN)
        self.H.__sendByte__(CP.SET_SINE2)
        self.H.__sendByte__(HIGHRES | (prescaler << 1))  # use larger table for low frequencies
        self.H.__sendInt__(wavelength - 1)
        self.H.__get_ack__()
        self.sine2freq = freq

        return freq

    def readbackWaveform(self, chan):
        """
		Set the frequency of wavegen 1

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		chan            Any of W1,W2,SQR1,SQR2,SQR3,SQR4
		==============  ============================================================================================


		:return: frequency
		"""
        if chan == 'W1':
            return self.sine1freq
        elif chan == 'W2':
            return self.sine2freq
        elif chan[:3] == 'SQR':
            return self.sqrfreq.get(chan, None)

    def set_waves(self, freq, phase, f2=None):
        """
		Set the frequency of wavegen

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		frequency       Frequency to set on both wave generators
		phase           Phase difference between the two. 0-360 degrees
		f2              Only specify if you require two separate frequencies to be set
		==============  ============================================================================================

		:return: frequency
		"""
        if f2:
            freq2 = f2
        else:
            freq2 = freq

        if freq < 0.1:
            self.__print__('freq1 too low')
            return 0
        elif freq < 1100:
            HIGHRES = 1
            table_size = 512
        else:
            HIGHRES = 0
            table_size = 32

        if freq2 < 0.1:
            self.__print__('freq2 too low')
            return 0
        elif freq2 < 1100:
            HIGHRES2 = 1
            table_size2 = 512
        else:
            HIGHRES2 = 0
            table_size2 = 32
        if freq < 1. or freq2 < 1.:
            self.__print__('extremely low frequencies will have reduced amplitudes due to AC coupling restrictions')

        p = [1, 8, 64, 256]
        prescaler1 = 0
        while prescaler1 <= 3:
            wavelength = int(round(64e6 / freq / p[prescaler1] / table_size))
            retfreq = (64e6 / wavelength / p[prescaler1] / table_size)
            if wavelength < 65525: break
            prescaler1 += 1
        if prescaler1 == 4:
            self.__print__('#1 out of range')
            return 0

        p = [1, 8, 64, 256]
        prescaler2 = 0
        while prescaler2 <= 3:
            wavelength2 = int(round(64e6 / freq2 / p[prescaler2] / table_size2))
            retfreq2 = (64e6 / wavelength2 / p[prescaler2] / table_size2)
            if wavelength2 < 65525: break
            prescaler2 += 1
        if prescaler2 == 4:
            self.__print__('#2 out of range')
            return 0

        phase_coarse = int(table_size2 * (phase) / 360.)
        phase_fine = int(wavelength2 * (phase - (phase_coarse) * 360. / table_size2) / (360. / table_size2))

        self.H.__sendByte__(CP.WAVEGEN)
        self.H.__sendByte__(CP.SET_BOTH_WG)

        self.H.__sendInt__(wavelength - 1)  # not really wavelength. time between each datapoint
        self.H.__sendInt__(wavelength2 - 1)  # not really wavelength. time between each datapoint
        self.H.__sendInt__(phase_coarse)  # table position for phase adjust
        self.H.__sendInt__(phase_fine)  # timer delay / fine phase adjust

        self.H.__sendByte__((prescaler2 << 4) | (prescaler1 << 2) | (HIGHRES2 << 1) | (
            HIGHRES))  # use larger table for low frequencies
        self.H.__get_ack__()
        self.sine1freq = retfreq
        self.sine2freq = retfreq2

        return retfreq

    def load_equation(self, chan, function, span=None, **kwargs):
        '''
		Load an arbitrary waveform to the waveform generators

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		chan             The waveform generator to alter. W1 or W2
		function            A function that will be used to generate the datapoints
		span                the range of values in which to evaluate the given function
		==============  ============================================================================================

		.. code-block:: python

		  fn = lambda x:abs(x-50)  #Triangular waveform
		  self.I.load_waveform('W1',fn,[0,100])
		  #Load triangular wave to wavegen 1

		  #Load sinusoidal wave to wavegen 2
		  self.I.load_waveform('W2',np.sin,[0,2*np.pi])

		'''
        if function == 'sine' or function == np.sin:
            function = np.sin
            span = [0, 2 * np.pi]
            self.WType[chan] = 'sine'
        elif function == 'tria':
            function = lambda x: abs(x % 4 - 2) - 1
            span = [-1, 3]
            self.WType[chan] = 'tria'
        else:
            self.WType[chan] = 'arbit'

        self.__print__('reloaded wave equation for %s : %s' % (chan, self.WType[chan]))
        x1 = np.linspace(span[0], span[1], 512 + 1)[:-1]
        y1 = function(x1)
        self.load_table(chan, y1, self.WType[chan], **kwargs)

    def load_table(self, chan, points, mode='arbit', **kwargs):
        '''
		Load an arbitrary waveform table to the waveform generators

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		chan             The waveform generator to alter. 'W1' or 'W2'
		points          A list of 512 datapoints exactly
		mode			Optional argument. Type of waveform. default value 'arbit'. accepts 'sine', 'tria'
		==============  ============================================================================================

		example::

		  >>> self.I.load_waveform_table(1,range(512))
		  #Load sawtooth wave to wavegen 1
		'''
        self.__print__('reloaded wave table for %s : %s' % (chan, mode))
        self.WType[chan] = mode
        chans = ['W1', 'W2']
        if chan in chans:
            num = chans.index(chan) + 1
        else:
            print('Channel does not exist. Try W2 or W2')
            return

        # Normalize and scale .
        # y1 = array with 512 points between 0 and 512
        # y2 = array with 32 points between 0 and 64

        amp = kwargs.get('amp', 0.95)
        LARGE_MAX = 511 * amp  # A form of amplitude control. This decides the max PWM duty cycle out of 512 clocks
        SMALL_MAX = 63 * amp  # Max duty cycle out of 64 clocks
        y1 = np.array(points)
        y1 -= min(y1)
        y1 = y1 / float(max(y1))
        y1 = 1. - y1
        y1 = list(np.int16(np.round(LARGE_MAX - LARGE_MAX * y1)))

        y2 = np.array(points[::16])
        y2 -= min(y2)
        y2 = y2 / float(max(y2))
        y2 = 1. - y2
        y2 = list(np.int16(np.round(SMALL_MAX - SMALL_MAX * y2)))

        self.H.__sendByte__(CP.WAVEGEN)
        if (num == 1):
            self.H.__sendByte__(CP.LOAD_WAVEFORM1)
        elif (num == 2):
            self.H.__sendByte__(CP.LOAD_WAVEFORM2)

        for a in y1:
            self.H.__sendInt__(a)
        for a in y2:
            self.H.__sendByte__(CP.Byte.pack(a))
        time.sleep(0.01)
        self.H.__get_ack__()

    def sqr1(self, freq, duty_cycle=50, onlyPrepare=False):
        """
		Set the frequency of sqr1

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		frequency       Frequency
		duty_cycle      Percentage of high time
		==============  ============================================================================================
		"""
        if freq == 0 or duty_cycle == 0: return None
        if freq > 10e6:
            print('Frequency is greater than 10MHz. Please use map_reference_clock for 16 & 32MHz outputs')
            return 0

        p = [1, 8, 64, 256]
        prescaler = 0
        while prescaler <= 3:
            wavelength = int(64e6 / freq / p[prescaler])
            if wavelength < 65525: break
            prescaler += 1
        if prescaler == 4 or wavelength == 0:
            self.__print__('out of range')
            return 0
        high_time = wavelength * duty_cycle / 100.
        self.__print__(wavelength, ':', high_time, ':', prescaler)
        if onlyPrepare: self.set_state(SQR1=False)

        self.H.__sendByte__(CP.WAVEGEN)
        self.H.__sendByte__(CP.SET_SQR1)
        self.H.__sendInt__(int(round(wavelength)))
        self.H.__sendInt__(int(round(high_time)))
        if onlyPrepare: prescaler |= 0x4  # Instruct hardware to prepare the square wave, but do not connect it to the output.
        self.H.__sendByte__(prescaler)
        self.H.__get_ack__()

        self.sqrfreq['SQR1'] = 64e6 / wavelength / p[prescaler & 0x3]
        return self.sqrfreq['SQR1']

    def sqr1_pattern(self, timing_array):
        """
		output a preset sqr1 frequency in fixed intervals. Can be used for sending IR signals that are packets
		of 38KHz pulses.
		refer to the example

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		timing_array    A list of on & off times in uS units
		==============  ============================================================================================

		.. code-block:: python
			I.sqr1(38e3 , 50, True )   # Prepare a 38KHz, 50% square wave. Do not output it yet
			I.sqr1_pattern([1000,1000,1000,1000,1000])  #On:1mS (38KHz packet), Off:1mS, On:1mS (38KHz packet), Off:1mS, On:1mS (38KHz packet), Off: indefinitely..
		"""
        self.fill_buffer(self.MAX_SAMPLES / 2, timing_array)  # Load the array to the ADCBuffer(second half)

        self.H.__sendByte__(CP.WAVEGEN)
        self.H.__sendByte__(CP.SQR1_PATTERN)
        self.H.__sendInt__(len(timing_array))
        time.sleep(sum(timing_array) * 1e-6)  # Sleep for the whole duration
        self.H.__get_ack__()

        return True

    def sqr2(self, freq, duty_cycle):
        """
		Set the frequency of sqr2

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		frequency       Frequency
		duty_cycle      Percentage of high time
		==============  ============================================================================================
		"""
        p = [1, 8, 64, 256]
        prescaler = 0
        while prescaler <= 3:
            wavelength = 64e6 / freq / p[prescaler]
            if wavelength < 65525: break
            prescaler += 1

        if prescaler == 4 or wavelength == 0:
            self.__print__('out of range')
            return 0

        high_time = wavelength * duty_cycle / 100.
        self.__print__(wavelength, high_time, prescaler)
        self.H.__sendByte__(CP.WAVEGEN)
        self.H.__sendByte__(CP.SET_SQR2)
        self.H.__sendInt__(int(round(wavelength)))
        self.H.__sendInt__(int(round(high_time)))
        self.H.__sendByte__(prescaler)
        self.H.__get_ack__()

        self.sqrfreq['SQR2'] = 64e6 / wavelength / p[prescaler & 0x3]
        return self.sqrfreq['SQR2']

    def set_sqrs(self, wavelength, phase, high_time1, high_time2, prescaler=1):
        """
		Set the frequency of sqr1,sqr2, with phase shift

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		wavelength      Number of 64Mhz/prescaler clock cycles per wave
		phase           Clock cycles between rising edges of SQR1 and SQR2
		high time1      Clock cycles for which SQR1 must be HIGH
		high time2      Clock cycles for which SQR2 must be HIGH
		prescaler       0,1,2. Divides the 64Mhz clock by 8,64, or 256
		==============  ============================================================================================

		"""

        self.H.__sendByte__(CP.WAVEGEN)
        self.H.__sendByte__(CP.SET_SQRS)
        self.H.__sendInt__(wavelength)
        self.H.__sendInt__(phase)
        self.H.__sendInt__(high_time1)
        self.H.__sendInt__(high_time2)
        self.H.__sendByte__(prescaler)
        self.H.__get_ack__()

    def sqrPWM(self, freq, h0, p1, h1, p2, h2, p3, h3, **kwargs):
        """
		Initialize phase correlated square waves on SQR1,SQR2,SQR3,SQR4

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		freq            Frequency in Hertz
		h0              Duty Cycle for SQR1 (0-1)
		p1              Phase shift for SQR2 (0-1)
		h1              Duty Cycle for SQR2 (0-1)
		p2              Phase shift for OD1  (0-1)
		h2              Duty Cycle for OD1  (0-1)
		p3              Phase shift for OD2  (0-1)
		h3              Duty Cycle for OD2  (0-1)
		==============  ============================================================================================

		"""
        if freq == 0 or h0 == 0 or h1 == 0 or h2 == 0 or h3 == 0: return 0
        if freq > 10e6:
            print('Frequency is greater than 10MHz. Please use map_reference_clock for 16 & 32MHz outputs')
            return 0

        p = [1, 8, 64, 256]
        prescaler = 0
        while prescaler <= 3:
            wavelength = int(64e6 / freq / p[prescaler])
            if wavelength < 65525: break
            prescaler += 1
        if prescaler == 4 or wavelength == 0:
            self.__print__('out of range')
            return 0

        if not kwargs.get('pulse', False): prescaler |= (1 << 5)

        A1 = int(p1 % 1 * wavelength)
        B1 = int((h1 + p1) % 1 * wavelength)
        A2 = int(p2 % 1 * wavelength)
        B2 = int((h2 + p2) % 1 * wavelength)
        A3 = int(p3 % 1 * wavelength)
        B3 = int((h3 + p3) % 1 * wavelength)

        self.H.__sendByte__(CP.WAVEGEN)
        self.H.__sendByte__(CP.SQR4)
        self.H.__sendInt__(wavelength - 1)
        self.H.__sendInt__(int(wavelength * h0) - 1)

        self.H.__sendInt__(max(0, A1 - 1))
        self.H.__sendInt__(max(1, B1 - 1))
        self.H.__sendInt__(max(0, A2 - 1))
        self.H.__sendInt__(max(1, B2 - 1))
        self.H.__sendInt__(max(0, A3 - 1))
        self.H.__sendInt__(max(1, B3 - 1))
        self.H.__sendByte__(prescaler)
        self.H.__get_ack__()

        for a in ['SQR1', 'SQR2', 'SQR3', 'SQR4']: self.sqrfreq[a] = 64e6 / wavelength / p[prescaler & 0x3]
        return 64e6 / wavelength / p[prescaler & 0x3]

    def map_reference_clock(self, scaler, *args):
        """
		Map the internal oscillator output  to SQR1,SQR2,SQR3,SQR4 or WAVEGEN
		The output frequency is 128/(1<<scaler) MHz

		scaler [0-15]

			* 0 -> 128MHz
			* 1 -> 64MHz
			* 2 -> 32MHz
			* 3 -> 16MHz
			* .
			* .
			* 15 ->128./32768 MHz

		example::

		>>> I.map_reference_clock(2,'SQR1','SQR2')

		outputs 32 MHz on SQR1, SQR2 pins

		.. note::
			if you change the reference clock for 'wavegen' , the external waveform generator(AD9833) resolution and range will also change.
			default frequency for 'wavegen' is 16MHz. Setting to 1MHz will give you 16 times better resolution, but a usable range of
			0Hz to about 100KHz instead of the original 2MHz.

		"""
        self.H.__sendByte__(CP.WAVEGEN)
        self.H.__sendByte__(CP.MAP_REFERENCE)
        chan = 0
        if 'SQR1' in args: chan |= 1
        if 'SQR2' in args: chan |= 2
        if 'SQR3' in args: chan |= 4
        if 'SQR4' in args: chan |= 8
        if 'WAVEGEN' in args: chan |= 16
        self.H.__sendByte__(chan)
        self.H.__sendByte__(scaler)
        if 'WAVEGEN' in args: self.DDS_CLOCK = 128e6 / (1 << scaler)
        self.H.__get_ack__()

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

    # -------------------------------------------------------------------------------------------------------------------#

    # |==============================================MOTOR SIGNALLING====================================================|
    # |Set servo motor angles via SQ1-4. Control one stepper motor using SQ1-4											|
    # -------------------------------------------------------------------------------------------------------------------#

    def __stepperMotor__(self, steps, delay, direction):
        self.H.__sendByte__(CP.NONSTANDARD_IO)
        self.H.__sendByte__(CP.STEPPER_MOTOR)
        self.H.__sendInt__((steps << 1) | direction)
        self.H.__sendInt__(delay)

        time.sleep(steps * delay * 1e-3)  # convert mS to S

    def stepForward(self, steps, delay):
        """
		Control stepper motors using SQR1-4

		take a fixed number of steps in the forward direction with a certain delay( in milliseconds ) between each step.

		"""
        self.__stepperMotor__(steps, delay, 1)

    def stepBackward(self, steps, delay):
        """
		Control stepper motors using SQR1-4

		take a fixed number of steps in the backward direction with a certain delay( in milliseconds ) between each step.

		"""
        self.__stepperMotor__(steps, delay, 0)

    def servo(self, angle, chan='SQR1'):
        '''
		Output A PWM waveform on SQR1/SQR2 corresponding to the angle specified in the arguments.
		This is used to operate servo motors.  Tested with 9G SG-90 Servo motor.

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		angle           0-180. Angle corresponding to which the PWM waveform is generated.
		chan            'SQR1' or 'SQR2'. Whether to use SQ1 or SQ2 to output the PWM waveform used by the servo
		==============  ============================================================================================
		'''
        if chan == 'SQR1':
            self.sqr1(100, 7.5 + 19. * angle / 180)  # 100Hz
        elif chan == 'SQR2':
            self.sqr2(100, 7.5 + 19. * angle / 180)  # 100Hz

    def servo4(self, a1, a2, a3, a4):
        """
		Operate Four servo motors independently using SQR1, SQR2, SQR3, SQR4.
		tested with SG-90 9G servos.
		For high current servos, please use a different power source, and a level convertor for the PWm output signals(if needed)

		.. tabularcolumns:: |p{3cm}|p{11cm}|

		==============  ============================================================================================
		**Arguments**
		==============  ============================================================================================
		a1              Angle to set on Servo which uses SQR1 as PWM input. [0-180]
		a2              Angle to set on Servo which uses SQR2 as PWM input. [0-180]
		a3              Angle to set on Servo which uses SQR3 as PWM input. [0-180]
		a4              Angle to set on Servo which uses SQR4 as PWM input. [0-180]
		==============  ============================================================================================

		"""
        params = (1 << 5) | 2  # continuous waveform.  prescaler 2( 1:64)
        self.H.__sendByte__(CP.WAVEGEN)
        self.H.__sendByte__(CP.SQR4)
        self.H.__sendInt__(10000)  # 10mS wavelength
        self.H.__sendInt__(750 + int(a1 * 1900 / 180))
        self.H.__sendInt__(0)
        self.H.__sendInt__(750 + int(a2 * 1900 / 180))
        self.H.__sendInt__(0)
        self.H.__sendInt__(750 + int(a3 * 1900 / 180))
        self.H.__sendInt__(0)
        self.H.__sendInt__(750 + int(a4 * 1900 / 180))
        self.H.__sendByte__(params)
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
		pin(which we will monitor via ID1) is also set high.  The logic level goes LOW when the sound packet
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
