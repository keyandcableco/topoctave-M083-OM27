import rp2
import array
import time
from machine import Pin, PWM
import utime

# ==================== WS2812 via PIO (SM 11) ====================

@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW,
             out_shiftdir=rp2.PIO.SHIFT_LEFT,
             autopull=True,
             pull_thresh=24)
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)              .side(0) [T3 - 1]
    jmp(not_x, "do_zero")  .side(1) [T1 - 1]
    jmp("bitloop")         .side(1) [T2 - 1]
    label("do_zero")
    nop()                  .side(0) [T2 - 1]
    wrap()


class WS2812:
    def __init__(self, pin_num, led_count, brightness=0.2, sm_id=11):
        self.led_count = led_count
        self.brightness = brightness
        self.sm = rp2.StateMachine(sm_id, ws2812,
                                   freq=8_000_000,
                                   sideset_base=Pin(pin_num))
        self.sm.active(1)
        self.ar = array.array("I", [0] * led_count)

    def pixels_show(self):
        dimmer_ar = array.array("I", [0] * self.led_count)
        for i, c in enumerate(self.ar):
            r = int(((c >> 8) & 0xFF) * self.brightness)
            g = int(((c >> 16) & 0xFF) * self.brightness)
            b = int((c & 0xFF) * self.brightness)
            dimmer_ar[i] = (g << 16) + (r << 8) + b
        self.sm.put(dimmer_ar, 8)
        time.sleep_ms(10)

    def pixels_set(self, i, color):
        # GRB order
        self.ar[i] = (color[0] << 16) + (color[1] << 8) + color[2]

    def pixels_fill(self, color):
        for i in range(self.led_count):
            self.pixels_set(i, color)


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

BLACK  = (0,   0,   0)
RED    = (255, 0,   0)
YELLOW = (255, 150, 0)
GREEN  = (0,   255, 0)
CYAN   = (0,   255, 255)
BLUE   = (0,   0,   255)
PURPLE = (180, 0,   255)
WHITE  = (255, 255, 255)

power = Pin(11, Pin.OUT)
power.value(1)

led = WS2812(pin_num=16, led_count=1, brightness=0.2, sm_id=11)

# ==================== Boot Sequence ====================
# 1. White flash - booting
led.pixels_fill(WHITE)
led.pixels_show()
utime.sleep(0.5)

# 2. Yellow - waiting for debug jumper (GPIO 15 to GND)
print("Waiting for debug jumper on GPIO 15...")
print("Jumper GPIO 15 to GND now for debug mode, or wait 3 seconds for live mode.")
led.pixels_fill(YELLOW)
led.pixels_show()
utime.sleep(3)

# 3. Read debug pin after window
debug_pin = Pin(15, Pin.IN, Pin.PULL_UP)

if debug_pin.value() == 0:
    clock_out = PWM(Pin(14))
    clock_out.freq(2_000_000)
    clock_out.duty_u16(32768)
    DEBUG = True
    ACTIVE_COLOUR = YELLOW
    print("DEBUG MODE: internal 2 MHz clock on GPIO 14")
    print("Jumper GPIO 14 -> GPIO 26 if not already done!")
else:
    DEBUG = False
    ACTIVE_COLOUR = GREEN
    print("LIVE MODE: expecting external clock on GPIO 26")

clock_pin = Pin(26, Pin.IN, Pin.PULL_UP)

# ==================== Output Pins & Dividers ====================
# 11 notes (SM 0-10), SM 11 reserved for WS2812
# Notes:       C#7   D7    D#7   E7    F7    F#7   G7    G#7   A7    A#7   B7
output_pins = [0,    1,    2,    3,    4,    5,    6,    7,    8,    9,    10]
dividers    = [451,  426,  402,  379,  358,  338,  319,  301,  284,  268,  253]

# ==================== Start State Machines (SM 0-10) ====================

state_machines = []
for i in range(11):
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
print("Notes: C#7 D7 D#7 E7 F7 F#7 G7 G#7 A7 A#7 B7")
print("DEBUG:", DEBUG)

led.pixels_fill(ACTIVE_COLOUR)
led.pixels_show()

# ==================== Heartbeat ====================
# Green blink = live mode (external clock)
# Yellow blink = debug mode (internal 2 MHz PWM clock)
while True:
    utime.sleep(2)
    led.pixels_fill(BLACK)
    led.pixels_show()
    utime.sleep(0.1)
    led.pixels_fill(ACTIVE_COLOUR)
    led.pixels_show()
