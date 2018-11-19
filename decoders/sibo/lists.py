# CMD: [start-bit, end-bit, annotation-type-index, annotations...]
proto = {
    'CLK':              [False, False, 0,     'CLK',                 'C'],
    'BIT':              [False, False, 1,     'Bit',                 'B'],
    'NULL FRAME':       [False, False, 2,     'N'],
    'FCTRL':            [0,     2,     3,     'Control Frame',       'CTRL', 'C'],
    'FDATA':            [0,     2,     4,     'Data Frame',          'DATA', 'D'],
    'SSR':              [10,    11,    5,     'Slave Select/Reset',  'SSelRes', 'S'],
    'SCTL':             [10,    11,    6,     'Slave Control',       'C'],
    'SRES':             [9,     10,    13,    'Slave Reset',         'Reset', 'R'],
    'SSEL':             [9,     10,    13,    'Slave (De)Select',    'S'],
    'SDES':             [0,     11,    11,    'Deselect All Slaves', 'SDesAll', 'SS0'],
    'SSELx':            [0,     11,    11,    'Select Slave ',       'SSel:', 'SS'],
    'SRALL':            [0,     11,    11,    'Reset All Slaves',    'SResAll', 'SR0'],
    'SRESx':            [0,     11,    11,    'Reset Slave ',        'SRes:', 'SR'],
    'DATA':             [3,     11,    False, '']
}

sctl_modes = {
    0: ["Single Byte Write", "SiByWr"],
    1: ["Multi-Byte Write",  "MuByWr"],
    2: ["Single Word Write", "SiWoWr"],
    3: ["Multi-Word Write",  "MuWoWr"],
    4: ["Single Byte Read",  "SiByRe"],
    5: ["Multi-Byte Read",   "MuByRe"],
    6: ["Single Word Read",  "SiWoRe"],
    7: ["Multi-Word Read",   "MuWoRe"],
}

sctl_mode_bits = {
    4: [["Single", "Si", "S"], ["Multi", "Mu", "M"]],
    5: [["Byte", "By", "B"],   ["Word", "Wo", "W"]],
    6: [["Write", "Wr", "W"],  ["Read", "Re", "R"]],
}

device_type = {
    2: "ASIC5",
    6: "ASIC4 Extended",
}

asic4_ssd_typeid = {
    0: "RAM",
    1: "Flash I",
    2: "Flash II",
    6: "ROM",
    7: "Write Protected",
}

# asic4_ssd_sizeid (D2-D0)
# If SizeID > 0 then size = (2^(SizeID+5)) else size = 0
# Note that this is per-chip. There is also a multiplier in D4-D3.

