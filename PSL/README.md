/* Documentation of back-end functions used in PSLab, taken from sciencelab.py */

get_resistance(self):

get__version(self):

getRadioLinks(self):

newRadioLink(self, **args):

reconnect(self, **kwargs):

capture1(self, ch, ns, tg, *args, **kwargs):

capture2(self, ns, tg, TraceOneRemap='CH1'):

capture4(self, ns, tg, TraceOneRemap='CH1'):

capture_multiple(self, samples, tg, *args):

capture_fullspeed(self, chan, samples, tg, *args, **kwargs):

capture_fullspeed_hr(self, chan, samples, tg, *args):

capture_traces(self, num, samples, tg, channel_one_input='CH1', CH123SA=0, *kwargs):

capture_highres_traces(self, channel, samples, tg, **kwargs):

fetch_trace(self, channel_number):

oscilloscope_progress(self):

configure_trigger(self, chan, name, voltage, resolution=10, **kwargs):

set_gain(self, channel, gain, Force=False):

select_range(self, channel, voltage_range):

get_voltage(self, channel_name, **kwargs):

voltmeter_autorange(self, channel_name):

get_average_voltage(self, channel_name, **kwargs):

fetch_buffer(self, starting_position=0, total_points=100):

clear_buffer(self, starting_position, total_points):

fill(slef, starting_position, poin_array):

start_streaming(self, tg, channel='CH1'):

stop_streaming(self):

get_high_freq(self, pin):

get_freq(self, channel='CNTR', timeout=2):

r2r_time(self, channel, skip_cycle=0, timeout=5):

f2f_time(self,channel, skip_cycle=0, timeout=5):

MeasureInterval(self, channel1, channel2, edge1, edge2, timeout=0.1):

DutyCycle(self, channel='ID1', timeout=1.):

PulseTime(self, channel='ID1', PulseType='LOW', timeout=0.1):

MeasureMultipleDigitalEdges(self, channel1, channel2, edgeType1, edgeType2, points1, points2, timeout=0.1, **kwargs):

capture_edges1(self, waiting_time=1., **args):

start_one_channel_LA_backup__(self, trigger=1, channel='ID1', maximum_time=67, **args):

start_one_channel_LA(self, **args):

start_two_channel_LA(self, **args):

start_three_channel_LA(self, **args):

start_four_channel_LA(self, trigger=1, maximum_time=0.001, mode=[1, 1, 1, 1], **args):

get_LA_initial_states(self):

stop_LA(self):

fetch_int_data_from_LA(self, bytes, chan=1):

fetch_LA_channels(self):

get_states(self):

get_state(self, input_id):

set_state(self, **kwargs):

countPulses(self, channel='SEN'):

readPulseCount(self):

capacitance_via_RC_discharge(self):

get_capacitor_range(self):

get_capacitance(self):

get_temperature(self):

resetHardware(self):

read_flash(self, page, location):

read_bulk_flash(self, page, numbytes):

write_flash(self, page, location, string_to_write):

write_bulk_flash(self, location, data):

set_wave(self, chan, freq):

set_sine1(self, freq):

set_sine2(self, freq):

set_w1(self, freq, waveType=None):

set_w2(self, freq, waveType=None):

readbackWavefrom(self, chan):

set_waves(self, freq, phase, f2=None):

load_equation(self, chan, function, span=None, **kwargs):

load_table(self, chan, points, mode='arbit', **kwargs):

sqr1(self, freq, duty_cycle=50, onlyPrepare=False):

sqr1_pattern(self, timing_array):

sqr2(self, freq, duty_cycle):

set_sqrs(self, wavelength, phase, high_time1, high_time2, prescaler=1):

sqrPWM(self, freq, h0, p1, h1, p2, h2, p3, h3, **kwargs):

map_reference_clock(self, scaler, *args):

set_pv1(self, val):
 
set_pv2(self, val):

set_pv3(self, val):

set_pcs(self, val):

get_pv1(self):

get_pv2(self):

 get_pv3(self):
 
 get_pcs(self):
 
 WS2812B(self, cols, output='CS1'):
 
 read_program_address(self, address):
 
 device_id(self):
 
 read_data_address(self, address):
 
 stepForward(self, steps, delay):
 
 stepBackward(self, steps, delay):
 
 servo(self, angle, chan='SQR1'):
 
 servo4(self, a1, a2, a3, a4):
 
 enableUartPassthrough(self, baudrate, persist=False):
 
 estimateDistance(self):
 
 opticalArray(self, SS, delay, channel='CH3', **kwargs):
 
 setUARTBAUD(self, BAUD):
 
 writeUART(self, character):
 
 readUART(self):
 
 readUARTStatus(self):
 
 readLog(self):
 
 raiseException(self, ex, msg):
