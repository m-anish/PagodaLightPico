"""
PWM controller for LED intensity or other output on specified GPIO pin.

Controls PWM frequency and duty cycle with debug logging.
"""

from machine import Pin, PWM
from lib.config_manager import LED_PWM_PIN, PWM_FREQUENCY
from simple_logger import Logger


log = Logger()


class PWMController:
    """
    PWM controller class.
    Args:
        freq (int): PWM frequency in Hz.
        pin (int): GPIO pin number for PWM output.

    Methods:
        set_freq(freq) - Set PWM frequency.
        set_duty_percent(percent) - Set PWM duty cycle in %.
        deinit() - Deinitialize PWM.
    """
    def __init__(self, freq=PWM_FREQUENCY, pin=LED_PWM_PIN):
        self.pwm = PWM(Pin(pin))
        self.freq = freq
        self.pwm.freq(self.freq)
        self.set_duty_percent(0)
        log.info("[PWM] Controller initialized at freq {} Hz on pin {}".format(
            self.freq, pin))

    def set_freq(self, freq):
        self.freq = freq
        self.pwm.freq(self.freq)
        log.info("[PWM] Frequency set to {} Hz".format(freq))

    def set_duty_percent(self, percent):
        duty_value = int(percent * 65535 / 100)
        self.pwm.duty_u16(duty_value)
        log.debug("[PWM] Duty cycle set to {}% (duty_u16={})".format(
            percent, duty_value))

    def deinit(self):
        self.pwm.deinit()
        log.info("[PWM] Controller deinitialized")
