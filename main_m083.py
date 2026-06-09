import rp2
from machine import Pin
import utime
from ws2812 import WS2812  # Keep your LED lib

# ==================== PIO Divider Program ====================
@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def divide():
    pull(noblock)
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

    label("part2")  # second half of the output wave
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

# ==================== Setup ====================
# Master clock input (square wave, ~2 MHz recommended)
pin0 = Pin(26, Pin.IN, Pin.PULL_UP)  # or no pull if driven strongly

# LED stuff (optional)
power = Pin(11, Pin.OUT)
power.value(1)
led = WS2812(12, 1)  # Adjust as needed
activecolour = (0, 255, 255)  # CYAN for active

# ==================== 12 Divider Values (for ~2MHz clock) ====================
# Note -> Divider -> Approx Freq (Hz) with 2MHz clock
dividers = [
    451,  # C#8 ~4435 Hz
    426,  # D8  ~4695 Hz
    402,  # D#8 ~4975 Hz
    379,  # E8  ~5277 Hz
    358,  # F8  ~5587 Hz
    338,  # F#8 ~5918 Hz
    319,  # G8  ~6270 Hz
    301,  # G#8 ~6645 Hz
    284,  # A8  ~7043 Hz
    268,  # A#8 ~7463 Hz
    253,  # B8  ~7906 Hz
    239,  # C9 ~8369 Hz
]

# Output pins - change these for your PCB layout
output_pins = [4,5,6,7,8,9,10,11,12,13,14,15]  # GPIO 0-11 for example

# Create and start 12 state machines
state_machines = []
for i in range(12):
    sm = rp2.StateMachine(
        i, 
        divide, 
        set_base=Pin(output_pins[i]), 
        in_base=pin0
    )
    sm.put(dividers[i])
    sm.active(1)
    state_machines.append(sm)

# LED heartbeat
while True:
    utime.sleep(2)
    led.pixels_fill((0, 0, 0))
    led.pixels_show()
    utime.sleep(0.1)
    led.pixels_fill(activecolour)
    led.pixels_show()
