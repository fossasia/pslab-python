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
self.dchans = [digital_channel(a) for a in range(4)]

        self.I2C = I2C(self.H)
        # self.I2C.pullSCLLow(5000)
        self.SPI = SPI(self.H)
        self.hexid = ''
        if self.H.connected:
            for a in ['CH1', 'CH2']:
                self.oscilloscope._channels[a].gain = 1
            for a in ['W1', 'W2']: self.load_equation(a, 'sine')
            self.SPI.set_parameters(1, 7, 1, 0)
            self.hexid = hex(self.device_id())

        self.NRF = NRF24L01(self.H)

        self.aboutArray.append(['Radio Transceiver is :', 'Installed' if self.NRF.ready else 'Not Installed'])

        self.DAC = MCP4728(self.H, 3.3, 0)
