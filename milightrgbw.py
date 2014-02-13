#!/usr/bin/python
# milight/easybulb/limitlessled controller
# by Chris Jones <cmsj@tenshu.net>
import logging
import socket
import struct
import time


class MiLightRGBW():
    """Class for controlling RGBW MiLight/Easybulb/LimitlessLED lights via the
    WiFi bridge.

    The API for the WiFi bridge is documented at:
        http://www.limitlessled.com/dev/

    All communication with the bridge is unidirectional, you cannot read any
    status back from it, nor do you get any replies to your commands.

    The underlying commands are three byte hex sequences, some of which have
    timing/order requirements. The timing aspect is taken care of by this
    class, however, the ordering is not. The important things to note:

     * Before sending the "rgb", "brightness" or "*_white" commands, you
       should first send the appropriate "*_on" command.
       (e.g. before sending "all_white" you should send "all_on")
       Otherwise the bridge has no way to know which zone you want to affect.
     * The rgb and brightness commands take numeric parameters, which should
       be joined to the command via a colon (e.g. "brightness:10").
       The brightness command's parameter is an integer between 2 and 27.
       The rgb command's parameter is an integer between 0 and 256.
       To quote the API docs, the following values provide the named colours:
         00 - Violet
         16 - Royal Blue
         32 - Baby Blue
         48 - Aqua
         64 - Mint Green
         80 - Seafoam Green
         96 - Green
         112 - Lime Green
         128 - Yellow
         144 - Yellowy Orange
         160 - Orange
         176 - Red
         194 - Pink
         210 - Fuscia
         226 - Lilac
         240 - Lavendar
       (you can use all the steps inbetween, these are just handy markers)
     * Each call to the disco command cycles through the preset disco patterns.
       There is no way to jump to a specific pattern. Or tell where you are in
       the sequence of patterns.
     * The groupN_on commands, if called within 2-3 seconds of a new light
       being powered on, will cause it to bind with that particular grouping.
     * Brightness settings are remembered by the bulb, independently for white
       and RGB modes.
    """

    logging.basicConfig()
    log = logging.getLogger("MiLightRGBW")
    sock = None
    bridge_address = None
    bridge_port = None
    suffix = 85  # All commands to the device end with the hex byte 0x55
    brightness_min = 2
    brightness_max = 27
    commands = {
        'all_off': 65,
        'all_on': 66,
        'disco_slower': 67,
        'disco_faster': 68,
        'group1_on': 69,
        'group1_off': 70,
        'group2_on': 71,
        'group2_off': 72,
        'group3_on': 73,
        'group3_off': 74,
        'group4_on': 75,
        'group4_off': 76,
        'disco': 77,
        'all_white': 194,
        'group1_white': 197,
        'group2_white': 199,
        'group3_white': 201,
        'group4_white': 203,
        'brightness': 78,
        'rgb': 64,
        }

    def __init__(self, bridge_address="255.255.255.255", bridge_port=8899,
                 loglevel=logging.WARNING):
        self.log.setLevel(loglevel)
        self.bridge_address = bridge_address
        self.bridge_port = bridge_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def build_command(self, command, value=0):
        return struct.pack("!BBB",
                           self.commands[command],
                           int(value),
                           self.suffix)

    def send_command(self, cmd):
        self.log.debug("Sending: %s" % ":".join("{0:x}".format(ord(c)) for c in cmd))
        self.sock.sendto(cmd, (self.bridge_address, self.bridge_port))
        time.sleep(0.1)

    def simple(self, command, value=0):
        self.send_command(self.build_command(command, value))


class TestMiLightRGBW():
    logging.basicConfig()
    log = logging.getLogger("TestMiLightRGBW")
    bridge = None
    brightness_max = None

    def __init__(self, bridge_address="255.255.255.255", bridge_port=8899,
                 loglevel=logging.WARNING):
        self.log.setLevel(loglevel)
        self.bridge = MiLightRGBW(bridge_address,
                                  bridge_port,
                                  loglevel=loglevel)
        self.brightness_max = "brightness:%s" % self.bridge.brightness_max

    def test(self, commands):
        if not hasattr(commands, '__iter__'):
            commands = [commands, ]
        for command in commands:
            self.log.debug("Command: %s" % command)
            bits = command.split(':')
            if len(bits) > 1:
                self.bridge.simple(bits[0], bits[1])
            else:
                self.bridge.simple(command)

    def sane(self):
        self.log.debug("Restoring sane state")
        self.test("all_on")
        self.log.debug("Restoring RGB brightness")
        self.test(["rgb:160", self.brightness_max])
        self.log.debug("Restoring White brightness")
        self.test(["all_white", self.brightness_max])
        time.sleep(2)
        self.log.debug("Sanity restored")

    def test_simple(self):
        self.sane()
        self.log.debug("Testing simple modes:")
        self.log.debug("All off")
        self.test('all_off')
        time.sleep(1)
        self.log.debug("All on")
        self.test('all_on')
        time.sleep(1)
        self.log.debug("Disco")
        self.test('disco')
        time.sleep(10)

    def test_white_brightness(self):
        self.sane()
        self.log.debug("Testing White brightness from min to max and back:")
        self.test('brightness:%s' % self.bridge.brightness_min)
        time.sleep(2)

        brightness_range = range(self.bridge.brightness_min,
                                 self.bridge.brightness_max+1)
        for i in brightness_range:
            self.test('brightness:%s' % i)
        brightness_range.reverse()
        for i in brightness_range:
            self.test('brightness:%s' % i)
        time.sleep(2)

    def test_rgb_brightness(self):
        self.sane()
        self.log.debug("Testing RGB brightness from min to max and back:")
        self.test('rgb:160')
        self.test('brightness:%s' % self.bridge.brightness_min)
        time.sleep(2)

        brightness_range = range(self.bridge.brightness_min,
                                 self.bridge.brightness_max+1)
        for i in brightness_range:
            self.test('brightness:%s' % i)
        brightness_range.reverse()
        for i in brightness_range:
            self.test('brightness:%s' % i)
        time.sleep(2)

    def test_rgb(self):
        self.sane()
        self.log.debug("Testing RGB from 0x00 to 0xFF")
        self.test('all_on')
        rgb_range = range(0, 256)
        self.test('rgb:%s' % rgb_range[0])
        time.sleep(2)

        for i in rgb_range:
            self.test('rgb:%s' % i)
            time.sleep(0.5)

        time.sleep(2)

    def test_all(self):
        self.test_simple()
        self.test_white_brightness()
        self.test_rgb_brightness()
        self.test_rgb()
        self.sane()


if __name__ == "__main__":
    tester = TestMiLightRGBW('10.0.88.50', loglevel=logging.DEBUG)
    tester.test_all()
