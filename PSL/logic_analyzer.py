import time

import numpy as np

import PSL.commands_proto as CP
from PSL import digital_channel, packet_handler


class LogicAnalyzer:
    def __init__(self, device: packet_handler.Handler = None):
        self.H = device
        self.digital_channel_names = digital_channel.digital_channel_names
        # This array of four instances of digital_channel is used to store data retrieved from the
        # logic analyzer section of the device.  It also contains methods to generate plottable data
        # from the original timestamp arrays.
        self.dchans = [digital_channel.digital_channel(a) for a in range(4)]

    def __calcDChan__(self, name):
        """accepts a string represention of a digital input ['ID1','ID2','ID3','ID4','SEN','EXT','CNTR']
        and returns a corresponding number
        """

        if name in self.digital_channel_names:
            return self.digital_channel_names.index(name)
        else:
            # self.__print__('invalid channel', name, ' , selecting ID1 instead ')
            return 0

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
            if a == CP.MAX_SAMPLES / 4:
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
            if a == CP.MAX_SAMPLES / 4:
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
        if x is not None and y is not None:  # Both timers registered something. did not timeout
            if y[0] > 0:  # rising edge occured first
                dt = [y[0], x[1]]
            else:  # falling edge occured first
                if y[1] > x[1]:
                    return -1, -1  # Edge dropped. return False
                dt = [y[1], x[1]]
            # self.__print__(x,y,dt)
            params = dt[1], dt[0] / dt[1]
            # if params[1] > 0.5:
            #     self.__print__(x, y, dt)
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
        if x is not None and y is not None:  # Both timers registered something. did not timeout
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
        self.clear_buffer(0, int(CP.MAX_SAMPLES / 2))
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.START_ALTERNATE_ONE_CHAN_LA)
        self.H.__sendInt__(CP.MAX_SAMPLES // 4)
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
        a.length = CP.MAX_SAMPLES / 4
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

        self.clear_buffer(0, CP.MAX_SAMPLES)
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.START_TWO_CHAN_LA)
        self.H.__sendInt__(CP.MAX_SAMPLES // 4)
        self.H.__sendByte__(trigger)

        self.H.__sendByte__((modes[1] << 4) | modes[0])  # Modes. four bits each
        self.H.__sendByte__((chans[1] << 4) | chans[0])  # Channels. four bits each
        self.H.__get_ack__()
        n = 0
        for a in self.dchans[:2]:
            a.prescaler = 0
            a.length = CP.MAX_SAMPLES // 4
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
        self.clear_buffer(0, CP.MAX_SAMPLES)
        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.START_THREE_CHAN_LA)
        self.H.__sendInt__(CP.MAX_SAMPLES // 4)
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
            a.length = CP.MAX_SAMPLES // 4
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
        self.clear_buffer(0, CP.MAX_SAMPLES)
        prescale = 0

        if(maximum_time > 0.26):
            #self.__print__('too long for 4 channel. try 2/1 channels')
            prescale = 3
        elif(maximum_time > 0.0655):
            prescale = 3
        elif(maximum_time > 0.008191):
            prescale = 2
        elif(maximum_time > 0.0010239):
            prescale = 1

        self.H.__sendByte__(CP.TIMING)
        self.H.__sendByte__(CP.START_FOUR_CHAN_LA)
        self.H.__sendInt__(CP.MAX_SAMPLES // 4)
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
            a.length = CP.MAX_SAMPLES // 4
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
        A = (self.H.__getInt__() - initial) // 2
        B = (self.H.__getInt__() - initial) // 2 - CP.MAX_SAMPLES // 4
        C = (self.H.__getInt__() - initial) // 2 - 2 * CP.MAX_SAMPLES // 4
        D = (self.H.__getInt__() - initial) // 2 - 3 * CP.MAX_SAMPLES // 4
        s = self.H.__getByte__()
        s_err = self.H.__getByte__()
        self.H.__get_ack__()

        if A == 0: A = CP.MAX_SAMPLES // 4
        if B == 0: B = CP.MAX_SAMPLES // 4
        if C == 0: C = CP.MAX_SAMPLES // 4
        if D == 0: D = CP.MAX_SAMPLES // 4

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
            # self.__print__('channel unavailable')
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

    def clear_buffer(self, starting_position, total_points):
        """
		clears a section of the ADC hardware buffer
		"""
        self.H.__sendByte__(CP.COMMON)
        self.H.__sendByte__(CP.CLEAR_BUFFER)
        self.H.__sendInt__(starting_position)
        self.H.__sendInt__(total_points)
        self.H.__get_ack__()
