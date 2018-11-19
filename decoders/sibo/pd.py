##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2018 Alex Brown <mail@alexbrown.info>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
##

#// TODO: Look for state of DATA on the RISING edge of CLK
#// TODO: Ignore if DATA is rising at the same time as CLK
#// TODO: Ignore anything on the DATA line that isn't accompanied by a signal on CLK
#// TODO: Show length of DATA transmissions for both directions.
#// TODO: Detect direction of traffic from protocol as alterntive to SDIR
#// TODO: Tidy the definitions at the beginning of the document.
#// TODO: Ignore if DATA is rising at the same time as CLK
#// TODO: If 12 CLK pulses are received within 50us, wait for the first valid high bit on both DATA and CLK and start the frame there.
# TODO: Decode control codes and give them proper descriptions (e.g. Code 3: Select Block X and Offset Y)
# TODO: Ignore anything on the CLK line faster than 100ns (currently ignores anything at one samples)


import sigrokdecode as srd
from .lists import *

'''
Test
'''

class Decoder(srd.Decoder):
    api_version = 3
    id = 'sibo'
    name = 'SIBO'
    longname = 'SIBO Serial Protocol'
    desc = 'Two-wire serial bus for Psion sixteen bit organisers.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = ['sibo']
    channels = (
        {'id': 'clk', 'name': 'CLK', 'desc': 'Serial clock line'},
        {'id': 'data', 'name': 'DATA', 'desc': 'Serial data line'},
    )
    optional_channels = (
        {'id': 'sdir', 'name': 'SDIR', 'desc': 'ASIC4 direction pin'},
    )
    options = (
        {'id': 'show_clk', 'desc': 'Show CLK pulses',
            'default': 'no', 'values': ('no', 'yes')},
        {'id': 'show_bit', 'desc': 'Show detected bits',
            'default': 'no', 'values': ('no', 'yes')},
        {'id': 'show_debug', 'desc': 'Show Debug Bit Line',
            'default': 'no', 'values': ('no', 'yes')},
        {'id': 'show_expected_ssd', 'desc': 'Guess ASIC Tx from Protocol',
            'default': 'no', 'values': ('no', 'yes')},
    )
    annotations = (
        ('clk', 'Clock pulse'),
        ('bit', 'Data/address bit'),
        ('repeat-start', 'Repeat start condition'),
        ('stop', 'Stop condition'),
        ('fctrl', 'Control Frame'),
        ('fdata', 'Data Frame'),
        ('fctrl-type', 'Slave Select/Slave Control'),
        ('sctl-register', 'Slave Control Register'),
        ('data-read', 'Data read'),
        ('nullframe', 'Null Frame'),
        ('dataframecount', 'Data Frame Count'),
        ('ssel-reset', 'Reset Slave'),
        ('data', 'Data'),
        ('ctrl-mode', 'Control Mode'),
        ('decode', 'Decoded'),
        ('asic-data', 'Data from ASIC'),
        ('data2', 'Data'),
        ('data3', 'Expect SSD Data'),
    )
    annotation_rows = (
        ('clk', 'CLK', (0,)),
        ('bits', 'Bits', (1,)),
        ('debug', 'Debug', (8, 12,)),
        ('frame', 'Frame', (2, 3, 4, 5, 6, 7, 13,)),
        ('ctrlcmd', 'Ctrl Command', (9, 11,)),
        ('data', 'SIBO Data Tx', (15,)),
        ('asictx', 'ASIC Tx', (16,)),
        ('expectssd', 'ASIC Tx (Guessed)', (17,)),
        ('dataframecount', 'Data Frame Count', (10,)),
        ('decode', 'Decoded', (14,)),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.clkstartsamplenum = 0
        self.data_frame_count = 0
        self.state = 'FIND START'
        self.clk_start_samples = []
        self.frame = []
        self.cur_sctl_register = 0
        self.data_start = 0
        self.prev_frame_end = 0
        self.device = False

    def start(self):
        self.out_python = self.register(srd.OUTPUT_PYTHON)
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.out_binary = self.register(srd.OUTPUT_BINARY)

    def arraytoint(self, binArray):
        result = 0
        for curbit in binArray:
            result = (result <<1) | curbit
        return result

    # Annotate using the clock sample number of the frame
    def putcsn(self, clksamplenum_begin, clksamplenum_end, data):
        self.put(self.clk_start_samples[clksamplenum_begin], self.clk_start_samples[clksamplenum_end], self.out_ann, data)

    # Annotate using specific sample numbers and protocol code
    def putprotoatsample(self, start, end, protocol_name):
        self.put(start, end, self.out_ann, [proto[protocol_name][2], proto[protocol_name][3:]])

    # Annotate using the full protocol code details
    def putproto(self, protocol_name, append=""):
        self.put(self.clk_start_samples[proto[protocol_name][0]],
                 self.clk_start_samples[proto[protocol_name][1]],
                 self.out_ann,
                 [proto[protocol_name][2], proto[protocol_name][3:] if append == "" else [s + append for s in proto[protocol_name][3:]]]
        )

    def putdata(self, annotation_number, byte):
        self.put(self.clk_start_samples[proto['DATA'][0]],
                 self.clk_start_samples[proto['DATA'][1]],
                 self.out_ann,
                 [annotation_number, [chr(byte)]]
        )


    def decode(self):
        clkstartsamplenum = 0
        framestartsamplenum = 0
        asictx = False
        current_bit = False
        expect_ssd_data = False


        while True:
            # Wait for any clock edge.
            clkstartsamplenum = self.samplenum
            clk, data, sdir = self.wait([{0: 'e'}, {1: 'e'}])

            # If both rise at the same time, it's interference and should be ignored.
            while self.matched == (True, True) and clk == 1 and data == 1:
                self.wait({0: 'f'})
                clk, data, sdir = self.wait([{0: 'e'}, {1: 'e'}])

            # If data falls before clk, don't worry about it! Just get the next edge.
            # (This could be a while or an if. I've gone for if.)
            # TODO: Loop back to the previous "while self-matched" loop if this is true to eliminate potential interference
            # TODO: (This might mean that they need to be merged)
            if self.matched == (False, True) and clk == 1:
                clk, data, sdir = self.wait([{0: 'e'}, {1: 'e'}])


            if self.matched[0]:                     # is there a clock edge?
                if clk == 1:                        # is it rising?
                    clkstartsamplenum = self.samplenum
                    current_bit = data

                    if (self.state == 'FIND START' and current_bit == 1) or self.frame == []:
                        framestartsamplenum = self.samplenum
                        self.frame = []
                        self.clk_start_samples = []
                        self.state = 'START'

                # If clk is falling and the clock pulse wasn't just a blip add it to the frame
                # TODO: Change blip calculation to time rather than number of samples
                elif clk == 0 and (self.samplenum - clkstartsamplenum > 1):
                    # Has the user asked to see the clock pulses?
                    if self.options['show_clk'] == 'yes':
                        self.putprotoatsample(clkstartsamplenum, self.samplenum, 'CLK')
                    # Has the user asked to see the bits?
                    if self.options['show_bit'] == 'yes':
                        self.put(clkstartsamplenum, self.samplenum, self.out_ann, [1, [str(current_bit)]])
                    self.frame.append(current_bit)
                    self.clk_start_samples.append(clkstartsamplenum)

                    # If the SSD is transmitting and we know about it, flag it up
                    # TODO: Might need rewriting to mitigate possible errors
                    if len(self.frame) == 4 and sdir == 1 and not(sdir == ''):
                        asictx = True

                    while len(self.frame) > 12:
                        self.frame.pop(0)
                        self.clk_start_samples.pop(0)
                    if len(self.frame) == 12: # do we have a complete frame?
                        byte = self.frame[3:11]

                        #
                        # *** CONTROL FRAME ***
                        #
                        if self.frame[0:2] == [1,0]: # This is a control frame
                            self.putproto('FCTRL')
                            expect_ssd_data = False

                            # Has there been any data frames between this control frame and the last one? If so, show the count and reset.
                            if self.data_start != 0:
                                self.put(self.data_start, self.prev_frame_end, self.out_ann, [10, [str(self.data_frame_count)]])
                                self.data_start = 0
                                self.data_frame_count = 0


                            if byte[7] == 0:
                                # ** SLAVE SELECT (AND RESET) **
                                # D7 (Bit 10) == 0
                                #
                                self.putproto('SSR')
                                cur_ssel_slave = self.arraytoint(reversed(byte[0:6])) # Get device (slave) number
                                self.putcsn(3, 9, [7, [str(cur_ssel_slave) + " " + hex(cur_ssel_slave), str(cur_ssel_slave)]])
                                if byte[6] == 0:
                                    self.putproto('SRES')
                                    if cur_ssel_slave == 0: # Reset Slave(s)
                                        self.putproto('SRALL')
                                    else:
                                        self.putproto('SRESx', str(cur_ssel_slave))
                                else:
                                    self.putproto('SSEL')
                                    if self.arraytoint(byte[0:7]) == 0: # Select Slave or Deselect All Slaves
                                        self.putproto('SDES')
                                    else:
                                        self.putproto('SSELx', str(cur_ssel_slave))
                                        expect_ssd_data = True


                            else:
                                # ** SLAVE CONTROL **
                                # D7 (Bit 10) == 1
                                #
                                self.putproto('SCTL')
                                # Single or Multi
                                self.putcsn(7, 8, [13, sctl_mode_bits[4][byte[4]]])
                                # Byte or Word
                                self.putcsn(8, 9, [13, sctl_mode_bits[5][byte[5]]])
                                # Read or Write
                                self.putcsn(9, 10, [13, sctl_mode_bits[6][byte[6]]])
                                if byte[6] == 1:
                                    expect_ssd_data = True

                                cur_sctl_mode = self.arraytoint(reversed(byte[4:7]))
                                self.cur_sctl_register = self.arraytoint(reversed(byte[0:4]))
                                self.putcsn(3, 7, [7, [str(self.cur_sctl_register) + " " + hex(self.cur_sctl_register), str(self.cur_sctl_register)]])
                                self.putcsn(0, 11, [9, [sctl_modes[cur_sctl_mode][0] + " (Register " + str(self.cur_sctl_register) + ")", sctl_modes[cur_sctl_mode][1] + ":" +str(self.cur_sctl_register)]])


                        #
                        # DATA FRAME
                        #
                        elif self.frame[0:2] == [1,1]: # This is a data frame
                            self.putproto('FDATA')
                            # If it's the first data frame after a control frame, remember the location of the first bit
                            if self.data_start == 0:
                                self.data_start = self.clk_start_samples[0]
                            datavalue = self.arraytoint(reversed(byte))

                            self.putcsn(3, 11, [7, [str(datavalue) + " " + hex(datavalue), str(datavalue)]])

                            # Put the data annotation in the correct row, based on the state of the asictx flag
                            if asictx == False and not(self.options['show_expected_ssd'] == 'yes' and expect_ssd_data):
                                self.putdata(15, datavalue)
                            if asictx:
                                self.putdata(16, datavalue)
                            if self.options['show_expected_ssd'] == 'yes' and expect_ssd_data:
                                self.putdata(17, datavalue)

                            asictx = False # ...so that the next frame isn't automatically misidentified

                            # We're counting data frames, so remember where this frame ends and increment the count
                            self.prev_frame_end = self.samplenum
                            self.data_frame_count += 1

                        # No matter what happens, if 12 lows are found on DATA, it's a null frame so we wait for the next high bit
                        if self.frame == [0,0,0,0,0,0,0,0,0,0,0,0]:
                            self.putprotoatsample(self.samplenum, self.samplenum, 'NULL FRAME')
                            self.state = 'FIND START'
                        elif self.state != 'FIND START':
                            if self.options['show_debug'] == 'yes':
                                self.putcsn(0, 11, [8, [str(self.frame).replace(",", "")]])
                            self.frame = []
                            self.clk_start_samples = []
                            framestartsamplenum = 0
