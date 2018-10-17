/* Documentation of back-end functions used in PSLab, mostly taken from sciencelab.py */

def get_resistance(self):

def __ignoreCalibration__(self):

def __print__(self, *args):

def __del__(self):

def get__version(self):

def getRadioLinks(self):

def newRadioLink(self, **args):

def reconnect(self, **kwargs):

def capture1(self, ch, ns, tg, *args, **kwargs):

def capture2(self, ns, tg, TraceOneRemap='CH1'):

def capture4(self, ns, tg, TraceOneRemap='CH1'):

def capture_multiple(self, samples, tg, *args):

def __capture_fullspeed__(self, chan, samples, tg, *args, **kwargs):

def capture_fullspeed(self, chan, samples, tg, *args, **kwargs):

def __capture_fullspeed_hr__(self, chan, samples, tg, *args):

def capture_fullspeed_hr(self, chan, samples, tg, *args):

def __retrieveBufferData__(self, chan, samples, tg):

def capture_traces(self, num, samples, tg, channel_one_input='CH1', CH123SA=0, *kwargs):

def capture_highres_traces(self, channel, samples, tg, **kwargs):

def fetch_trace(self, channel_number):

def oscilloscope_progress(self):

def __fetch_channel__(self, channel_number):

def __fetch_channel_oneshot__(self, channel_number):

def configure_trigger(self, chan, name, voltage, resolution=10, **kwargs):

def set_gain(self, channel, gain, Force=False):

def select_range(self, channel, voltage_range):

def __calcCHOSA__(self, name):

def get_voltage(self, channel_name, **kwargs):

def voltmeter_autorange(self, channel_name):

def __autoSelectRange__(self, channel_name, V):

def __autoRangeScope__(self, tg):

def get_average_voltage(self, channel_name, **kwargs):

def __get_raw_average_voltage__(self, channel_name, **kwargs):

def fetch_buffer(self, starting_position=0, total_points=100):

def clear_buffer(self, starting_position, total_points):

def fill(slef, starting_position, poin_array):

def start_streaming(self, tg, channel='CH1'):

def stop_streaming(self):

def __calcDChan__(self, name):

def __get_high_freq__backup__(self, pin):

def get_high_freq(self, pin):

def get_freq(self, channel='CNTR', timeout=2):

def r2r_time(self, channel, skip_cycle=0, timeout=5):

def f2f_time(self,channel, skip_cycle=0, timeout=5):

def MeasureInterval(self, channel1, channel2, edge1, edge2, timeout=0.1):

def DutyCycle(self, channel='ID1', timeout=1.):

def PulseTime(self, channel='ID1', PulseType='LOW', timeout=0.1):

def MeasureMultipleDigitalEdges(self, channel1, channel2, edgeType1, edgeType2, points1, points2, timeout=0.1, **kwargs):

def capture_edges1(self, waiting_time=1., **args):

def start_one_channel_LA_backup__(self, trigger=1, channel='ID1', maximum_time=67, **args):

def start_one_channel_LA(self, **args):

def start_two_channel_LA(self, **args):

def start_three_channel_LA(self, **args):

def start_four_channel_LA(self, trigger=1, maximum_time=0.001, mode=[1, 1, 1, 1], **args):

def get_LA_initial_states(self):

def stop_LA(self):

def fetch_int_data_from_LA(self, bytes, chan=1):

def fetch_LA_channels(self):

def __fetch_LA_channel__(self, channel_number, initial_states):

def get_states(self):

def get_state(self, input_id):

def set_state(self, **kwargs):

def countPulses(self, channel='SEN'):

def readPulseCount(self):

def __charge_cap__(self, state, t):

def __capture_capacitance__(self, samples, tg):

def capacitance_via_RC_discharge(self):

def __get_capacitor_range__(self, ctime):

def get_capacitor_range(self):

def get_capacitance(self):

def __calibrate_ctmu__(self, scalers):

def __get_capacitance__(self, current_range, trim, Charge_Time):

def get_temperature(self):

def __start_ctmu__(self, Crange, trim, tgen=1):

def __stop_ctmu__(self):

def resetHardware(self):

def read_flash(self, page, location):

def __stoa__(self, s):

def __atos__(self, a):

def read_bulk_flash(self, page, numbytes):

def write_flash(self, page, location, string_to_write):

def write_bulk_flash(self, location, data):

def set_wave(self, chan, freq):

def set_sine1(self, freq):

def set_sine2(self, freq):

def set_w1(self, freq, waveType=None):

def set_w2(self, freq, waveType=None):

def readbackWavefrom(self, chan):

def set_waves(self, freq, phase, f2=None):

def load_equation(self, chan, function, span=None, **kwargs):

def load_table(self, chan, points, mode='arbit', **kwargs):

def sqr1(self, freq, duty_cycle=50, onlyPrepare=False):

def sqr1_pattern(self, timing_array):

def sqr2(self, freq, duty_cycle):

def set_sqrs(self, wavelength, phase, high_time1, high_time2, prescaler=1):

def sqrPWM(self, freq, h0, p1, h1, p2, h2, p3, h3, **kwargs):

def map_reference_clock(self, scaler, *args):

def set_pv1(self, val):
 
def set_pv2(self, val):

def set_pv3(self, val):

def set_pcs(self, val):

def get_pv1(self):

def get_pv2(self):

 def get_pv3(self):
 
 def get_pcs(self):
 
 def WS2812B(self, cols, output='CS1'):
 
 def read_program_address(self, address):
 
 def device_id(self):
 
 def __write_program_address__(self, address, value):
 
 def read_data_address(self, address):
 
 def __write_data_address__(self, address, value):
 
 def __stepperMotor__(self, steps, delay, direction):
 
 def stepForward(self, steps, delay):
 
 def stepBackward(self, steps, delay):
 
 def servo(self, angle, chan='SQR1'):
 
 def servo4(self, a1, a2, a3, a4):
 
 def enableUartPassthrough(self, baudrate, persist=False):
 
 def estimateDistance(self):
 
 def opticalArray(self, SS, delay, channel='CH3', **kwargs):
 
 def setUARTBAUD(self, BAUD):
 
 def writeUART(self, character):
 
 def readUART(self):
 
 def readUARTStatus(self):
 
 def readLog(self):
 
 def raiseException(self, ex, msg):
