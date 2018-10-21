/* Documentation of back-end functions used in PSLab, taken from sciencelab.py */

<details>
<summary><code>get_resistance(self)</code></summary><br />
</details>

<details>
<summary><code>get__version(self)</code></summary><br />
</details>

<details>
<summary><code>getRadioLinks(self)</code></summary><br />
</details>

<details>
<summary><code>newRadioLink(self, **args)</code></summary><br />
</details>

<details>
<summary><code>reconnect(self, **kwargs)</code></summary><br />
</details>

<details>
<summary><code>capture1(self, ch, ns, tg, *args, **kwargs)</code></summary><br />
</details>

<details>
<summary><code>capture2(self, ns, tg, TraceOneRemap='CH1')</code></summary><br />
</details>

<details>
<summary><code>capture4(self, ns, tg, TraceOneRemap='CH1')</code></summary><br />
</details>

<details>
<summary><code>capture_multiple(self, samples, tg, *args)</code></summary><br />
</details>

<details>
<summary><code>capture_fullspeed(self, chan, samples, tg, *args, **kwargs)</code></summary><br />
</details>

<details>
<summary><code>capture_fullspeed_hr(self, chan, samples, tg, *args)</code></summary><br />
</details>

<details>
<summary><code>capture_traces(self, num, samples, tg, channel_one_input='CH1', CH123SA=0, *kwargs)</code></summary><br />
</details>

<details>
<summary><code>capture_highres_traces(self, channel, samples, tg, **kwargs)</code></summary><br />
</details>

<details>
<summary><code>fetch_trace(self, channel_number)</code></summary><br />
</details>

<details>
<summary><code>oscilloscope_progress(self)</code></summary><br />
</details>

<details>
<summary><code>configure_trigger(self, chan, name, voltage, resolution=10, **kwargs)</code></summary><br />
</details>

<details>
<summary><code>set_gain(self, channel, gain, Force=False)</code></summary><br />
</details>

<details>
<summary><code>select_range(self, channel, voltage_range)</code></summary><br />
</details>

<details>
<summary><code>get_voltage(self, channel_name, **kwargs)</code></summary><br />
</details>

<details>
<summary><code>voltmeter_autorange(self, channel_name)</code></summary><br />
</details>

<details>
<summary><code>get_average_voltage(self, channel_name, **kwargs)</code></summary><br />
</details>

<details>
<summary><code>fetch_buffer(self, starting_position=0, total_points=100)</code></summary><br />
</details>

<details>
<summary><code>clear_buffer(self, starting_position, total_points)</code></summary><br />
</details>

<details>
<summary><code>fill(slef, starting_position, poin_array)</code></summary><br />
</details>

<details>
<summary><code>start_streaming(self, tg, channel='CH1')</code></summary><br />
</details>

<details>
<summary><code>stop_streaming(self)</code></summary><br />
</details>

<details>
<summary><code>get_high_freq(self, pin)</code></summary><br />
</details>

<details>
<summary><code>get_freq(self, channel='CNTR', timeout=2)</code></summary><br />
</details>

<details>
<summary><code>r2r_time(self, channel, skip_cycle=0, timeout=5)</code></summary><br />
</details>

<details>
<summary><code>f2f_time(self,channel, skip_cycle=0, timeout=5)</code></summary><br />
</details>

<details>
<summary><code>MeasureInterval(self, channel1, channel2, edge1, edge2, timeout=0.1)</code></summary><br />
</details>

<details>
<summary><code>DutyCycle(self, channel='ID1', timeout=1.)</code></summary><br />
</details>

<details>
<summary><code>PulseTime(self, channel='ID1', PulseType='LOW', timeout=0.1)</code></summary><br />
</details>

<details>
<summary><code>MeasureMultipleDigitalEdges(self, channel1, channel2, edgeType1, edgeType2, points1, points2, timeout=0.1, **kwargs)</code></summary><br />
</details>

<details>
<summary><code>capture_edges1(self, waiting_time=1., **args)</code></summary><br />
</details>

<details>
<summary><code>start_one_channel_LA_backup__(self, trigger=1, channel='ID1', maximum_time=67, **args)</code></summary><br />
</details>

<details>
<summary><code>start_one_channel_LA(self, **args)</code></summary><br />
</details>

<details>
<summary><code>start_two_channel_LA(self, **args)</code></summary><br />
</details>

<details>
<summary><code>start_three_channel_LA(self, **args)</code></summary><br />
</details>

<details>
<summary><code>start_four_channel_LA(self, trigger=1, maximum_time=0.001, mode=[1, 1, 1, 1], **args)</code></summary><br />
</details>

<details>
<summary><code>get_LA_initial_states(self)</code></summary><br />
</details>

<details>
<summary><code>stop_LA(self)</code></summary><br />
</details>

<details>
<summary><code>fetch_int_data_from_LA(self, bytes, chan=1)</code></summary><br />
</details>

<details>
<summary><code>fetch_LA_channels(self)</code></summary><br />
</details>

<details>
<summary><code>get_states(self)</code></summary><br />
</details>

<details>
<summary><code>get_state(self, input_id)</code></summary><br />
</details>

<details>
<summary><code>set_state(self, **kwargs)</code></summary><br />
</details>

<details>
<summary><code>countPulses(self, channel='SEN')</code></summary><br />
</details>

<details>
<summary><code>readPulseCount(self)</code></summary><br />
</details>

<details>
<summary><code>capacitance_via_RC_discharge(self)</code></summary><br />
</details>

<details>
<summary><code>get_capacitor_range(self)</code></summary><br />
</details>

<details>
<summary><code>get_capacitance(self)</code></summary><br />
</details>

<details>
<summary><code>get_temperature(self)</code></summary><br />
</details>

<details>
<summary><code>resetHardware(self)</code></summary><br />
</details>

<details>
<summary><code>read_flash(self, page, location)</code></summary><br />
</details>

<details>
<summary><code>read_bulk_flash(self, page, numbytes)</code></summary><br />
</details>

<details>
<summary><code>write_flash(self, page, location, string_to_write)</code></summary><br />
</details>

<details>
<summary><code>write_bulk_flash(self, location, data)</code></summary><br />
</details>

<details>
<summary><code>set_wave(self, chan, freq)</code></summary><br />
</details>

<details>
<summary><code>set_sine1(self, freq)</code></summary><br />
</details>

<details>
<summary><code>set_sine2(self, freq)</code></summary><br />
</details>

<details>
<summary><code>set_w1(self, freq, waveType=None)</code></summary><br />
</details>

<details>
<summary><code>set_w2(self, freq, waveType=None)</code></summary><br />
</details>

<details>
<summary><code>readbackWavefrom(self, chan)</code></summary><br />
</details>

<details>
<summary><code>set_waves(self, freq, phase, f2=None)</code></summary><br />
</details>

<details>
<summary><code>load_equation(self, chan, function, span=None, **kwargs)</code></summary><br />
</details>

<details>
<summary><code>load_table(self, chan, points, mode='arbit', **kwargs)</code></summary><br />
</details>

<details>
<summary><code>sqr1(self, freq, duty_cycle=50, onlyPrepare=False)</code></summary><br />
</details>

<details>
<summary><code>sqr1_pattern(self, timing_array)</code></summary><br />
</details>

<details>
<summary><code>sqr2(self, freq, duty_cycle)</code></summary><br />
</details>

<details>
<summary><code>set_sqrs(self, wavelength, phase, high_time1, high_time2, prescaler=1)</code></summary><br />
</details>

<details>
<summary><code>sqrPWM(self, freq, h0, p1, h1, p2, h2, p3, h3, **kwargs)</code></summary><br />
</details>

<details>
<summary><code>map_reference_clock(self, scaler, *args)</code></summary><br />
</details>

<details>
<summary><code>set_pv1(self, val)</code></summary><br />
</details>
 
<details>
<summary><code>set_pv2(self, val)</code></summary><br />
</details>

<details>
<summary><code>set_pv3(self, val)</code></summary><br />
</details>

<details>
<summary><code>set_pcs(self, val)</code></summary><br />
</details>

<details>
<summary><code>get_pv1(self)</code></summary><br />
</details>

<details>
<summary><code>get_pv2(self)</code></summary><br />
</details>

<details>
<summary><code>get_pv3(self)</code></summary><br />
</details>
 
<details>
<summary><code>get_pcs(self)</code></summary><br />
</details>
 
<details>
<summary><code>WS2812B(self, cols, output='CS1')</code></summary><br />
</details>
 
<details>
<summary><code>read_program_address(self, address)</code></summary><br />
</details>
 
<details>
<summary><code>device_id(self)</code></summary><br />
</details>
 
<details>
<summary><code>read_data_address(self, address)</code></summary><br />
</details>
 
<details>
<summary><code>stepForward(self, steps, delay)</code></summary><br />
</details>
 
<details>
<summary><code>stepBackward(self, steps, delay)</code></summary><br />
</details>
 
<details>
<summary><code>servo(self, angle, chan='SQR1')</code></summary><br />
</details>
 
<details>
<summary><code>servo4(self, a1, a2, a3, a4)</code></summary><br />
</details>
 
<details>
<summary><code>enableUartPassthrough(self, baudrate, persist=False)</code></summary><br />
</details>
 
<details>
<summary><code>estimateDistance(self)</code></summary><br />
</details>
 
<details>
<summary><code>opticalArray(self, SS, delay, channel='CH3', **kwargs)</code></summary><br />
</details>
 
<details>
<summary><code>setUARTBAUD(self, BAUD)</code></summary><br />
</details>
 
<details>
<summary><code>writeUART(self, character)</code></summary><br />
</details>
 
<details>
<summary><code>readUART(self)</code></summary><br />
</details>
 
<details>
<summary><code>readUARTStatus(self)</code></summary><br />
</details>
 
<details>
<summary><code>readLog(self)</code></summary><br />
</details>
 
<details>
<summary><code>raiseException(self, ex, msg)</code></summary><br />
</details>
