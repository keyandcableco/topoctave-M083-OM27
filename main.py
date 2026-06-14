import rp2
from machine import Pin, PWM
import utime

# ==================== PIO Top Octave Divider ====================

@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def divide():
    pull(block)
    mov(y, osr)

    wrap_target()
    label("start")
    mov(x, y)
    set(pins, 0)
    label("loop1")
    wait(0, pin, 0)
    jmp(x_dec, "d1")
    jmp("part2")
    label("d1")
    wait(1, pin, 0)
    jmp(x_dec, "loop1")
    label("part2")
    set(pins, 1)
    mov(x, y)
    label("loop2")
    wait(0, pin, 0)
    jmp(x_dec, "d2")
    jmp("start")
    label("d2")
    wait(1, pin, 0)
    jmp(x_dec, "loop2")
    wrap()

# ==================== Hardware Setup ====================

power = Pin(11, Pin.OUT)
power.value(1)

# ==================== Debug Mode ====================
# Jumper GPIO 15 to GND before boot for debug mode
# Then jumper GPIO 14 -> GPIO 26
debug_pin = Pin(15, Pin.IN, Pin.PULL_UP)

print("Waiting 3 seconds... jumper GPIO 15 to GND for debug mode")
utime.sleep(3)

if debug_pin.value() == 0:
    clock_out = PWM(Pin(14))
    clock_out.freq(2_000_000)
    clock_out.duty_u16(32768)
    DEBUG = True
    print("DEBUG MODE: internal 2 MHz clock on GPIO 14")
    print("Jumper GPIO 14 -> GPIO 26!")
else:
    DEBUG = False
    print("LIVE MODE: expecting external clock on GPIO 26")

clock_pin = Pin(26, Pin.IN, Pin.PULL_UP)

# ==================== Output Pins & Dividers ====================
# All 12 SMs (0-11) used for tone outputs — full chromatic scale
# M083A F1-F12, high to low:
# Notes:       C8   B7   A#7  A7   G#7  G7   F#7  F7   E7   D#7  D7   C#7
output_pins = [13,  10,  9,   8,   7,   6,   5,   4,   3,   2,   1,   0  ]
dividers    = [239, 253, 268, 284, 301, 319, 338, 358, 379, 402, 426, 451 ]

# ==================== Start State Machines (SM 0-11) ====================

state_machines = []
for i in range(12):
    sm = rp2.StateMachine(
        i,
        divide,
        freq=125_000_000,
        set_base=Pin(output_pins[i]),
        in_base=clock_pin
    )
    sm.put(dividers[i] - 1)
    sm.active(1)
    state_machines.append(sm)

print("OM-27 top octave generator running!")
print("GPIOs:", output_pins)
print("Notes: C8 B7 A#7 A7 G#7 G7 F#7 F7 E7 D#7 D7 C#7")
print("DEBUG:", DEBUG)

# ==================== Heartbeat ====================
while True:
    utime.sleep(5)
    print("running...")
