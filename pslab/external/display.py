"""Control display devices such as OLED screens.

Example
-------
>>> from pslab.bus import I2CMaster
>>> from pslab.external.display import SSD1306
>>> i2c = I2CMaster()  # Initialize bus
>>> oled = SSD1306()
>>> oled.display_logo()
>>> oled.scroll("topright")
>>> time.sleep(2.8)
>>> oled.scroll("stop")
"""
import json
import time
import os.path

from pslab.bus import DeviceNotFoundError, I2CSlave

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class SSD1306(I2CSlave):
    _COPYRIGHT = """
    Copyright (c) 2021, FOSSASIA
    Copyright (c) 2012, Adafruit Industries
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:
    1. Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.
    3. Neither the name of the copyright holders nor the
    names of its contributors may be used to endorse or promote products
    derived from this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ''AS IS'' AND ANY
    EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
    DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
    ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
    """
    _ADDRESS = 0x3C
    _WIDTH = 128
    _HEIGHT = 64

    _SETCONTRAST = 0x81
    _DISPLAYALLON_RESUME = 0xA4
    _DISPLAYALLON = 0xA5
    _NORMALDISPLAY = 0xA6
    _INVERTDISPLAY = 0xA7
    _DISPLAYOFF = 0xAE
    _DISPLAYON = 0xAF
    _SETDISPLAYOFFSET = 0xD3
    _SETCOMPINS = 0xDA
    _SETVCOMDETECT = 0xDB
    _SETDISPLAYCLOCKDIV = 0xD5
    _SETPRECHARGE = 0xD9
    _SETMULTIPLEX = 0xA8
    _SETLOWCOLUMN = 0x00
    _SETHIGHCOLUMN = 0x10
    _SETSTARTLINE = 0x40
    _MEMORYMODE = 0x20
    _COMSCANINC = 0xC0
    _COMSCANDEC = 0xC8
    _SEGREMAP = 0xA0
    _CHARGEPUMP = 0x8D
    _EXTERNALVCC = 0x1
    _SWITCHCAPVCC = 0x2
    _SET_COL_ADDR = 0x21
    _SET_PAGE_ADDR = 0x22

    # fmt: off
    _INIT_DATA = [
        _DISPLAYOFF,
        _SETDISPLAYCLOCKDIV, 0x80,  # Default aspect ratio.
        _SETMULTIPLEX, 0x3F,
        _SETDISPLAYOFFSET, 0x0,  # No offset.
        _SETSTARTLINE | 0x0,  # Line #0.
        _CHARGEPUMP, 0x14,
        _MEMORYMODE, 0x0,  # Act like ks0108.
        _SEGREMAP | 0x1,
        _COMSCANDEC,
        _SETCOMPINS, 0x12,
        _SETCONTRAST, 0xFF,
        _SETPRECHARGE, 0xF1,
        _SETVCOMDETECT, 0x40,
        _DISPLAYALLON_RESUME,
        _NORMALDISPLAY,
        _DISPLAYON,
    ]
    # fmt: on

    def __init__(self):
        super().__init__(self._ADDRESS)

        if not self.ping():
            pass
            # raise DeviceNotFoundError

        self._buffer = [0 for a in range(1024)]
        self.cursor = [0, 0]
        self.textsize = 1
        self.textcolor = 1
        self.textbgcolor = 0
        self.wrap = True
        self._contrast = 0xFF

        with open(os.path.join(__location__, "ssd1306_gfx.json"), "r") as f:
            gfx = json.load(f)

        self._logo = gfx["logo"]
        self._font = gfx["font"]

        print("init oled")
        for command in self._INIT_DATA:
            self._write_command(command)

    def draw_logo(self):
        """Print someone's logo on the display."""
        print("draw logo")
        self.scroll("stop")
        self.clear()
        self._buffer = self._logo
        self.update()

    def _write_command(self, command: int):
        print(hex(command))
        self.write_byte(command)

    def _write_data(self, data: list):
        self.write(bytes(data), register_address=0x40)

    def clear(self):
        """Clear the display."""
        self.cursor = [0, 0]
        for a in range(self._WIDTH * self._HEIGHT // 8):
            self._buffer[a] = 0
        self.update()

    def update(self):
        """Redraw display."""
        self._write_command(self._SETLOWCOLUMN | 0x0)
        self._write_command(self._SETHIGHCOLUMN | 0x0)
        self._write_command(self._SETSTARTLINE | 0x0)
        a = 0

        while a < self._WIDTH * self._HEIGHT // 8:
            self._write_data(self._buffer[a : a + 16])
            a += 16

    def show(self):
        x0 = 0
        x1 = self._WIDTH - 1
        self._write_command(self._SET_COL_ADDR)
        self._write_command(x0)
        self._write_command(x1)
        self._write_command(self._SET_PAGE_ADDR)
        self._write_command(0)
        self._write_command(self._HEIGHT // 8)
        self._write_data(self._buffer[0 : 16])

    @property
    def contrast(self) -> int:
        """int: Screen contrast."""
        return self._contrast

    @contrast.setter
    def contrast(self, value: int):
        self._write_command(self._SETCONTRAST)
        self._write_command(value)
        self._contrast = value

    def _draw(self, update: bool = True):
        if update:
            self.update()

    def draw_pixel(self, x: int, y: int, color: int, update: bool = True):
        """Draw a single pixel."""
        if color == 1:
            self._buffer[x + (y // 8) * self._WIDTH] |= 1 << (y % 8)
        else:
            self._buffer[x + (y // 8) * self._WIDTH] &= ~(1 << (y % 8))
        self._draw(update)

    def draw_circle(self, x0, y0, r, color, update: bool = True):
        """Draw a circle."""
        f = 1 - r
        ddF_x = 1
        ddF_y = -2 * r
        x = 0
        y = r
        self.draw_pixel(x0, y0 + r, color, update)
        self.draw_pixel(x0, y0 - r, color, update)
        self.draw_pixel(x0 + r, y0, color, update)
        self.draw_pixel(x0 - r, y0, color, update)

        while x < y:
            if f >= 0:
                y -= 1
                ddF_y += 2
                f += ddF_y

            x += 1
            ddF_x += 2
            f += ddF_x
            self.draw_pixel(x0 + x, y0 + y, color, update)
            self.draw_pixel(x0 - x, y0 + y, color, update)
            self.draw_pixel(x0 + x, y0 - y, color, update)
            self.draw_pixel(x0 - x, y0 - y, color, update)
            self.draw_pixel(x0 + y, y0 + x, color, update)
            self.draw_pixel(x0 - y, y0 + x, color, update)
            self.draw_pixel(x0 + y, y0 - x, color, update)
            self.draw_pixel(x0 - y, y0 - x, color, update)

    def draw_line(self, x0, y0, x1, y1, color, update: bool = True):
        """Draw a line."""
        is_steep = abs(y1 - y0) > abs(x1 - x0)

        if is_steep:
            tmp = y0
            y0 = x0
            x0 = tmp
            tmp = y1
            y1 = x1
            x1 = tmp

        if x0 > x1:
            tmp = x1
            x1 = x0
            x0 = tmp
            tmp = y1
            y1 = y0
            y0 = tmp

        dx = x1 - x0
        dy = abs(y1 - y0)
        err = dx / 2

        if y0 < y1:
            ystep = 1
        else:
            ystep = -1

        while x0 <= x1:
            if is_steep:
                self.draw_pixel(y0, x0, color, update)
            else:
                self.draw_pixel(x0, y0, color, update)
            err -= dy

            if err < 0:
                y0 += ystep
                err += dx
            x0 += 1

    def draw_rectangle(self, x0, y0, width, height, color, update: bool = True):
        """Draw a rectangle."""
        self.draw_horizontal_line(x0, y0, width, color, update)
        self.draw_horizontal_line(x0, y0 + height - 1, width, color, update)
        self.draw_horizontal_line(x0, y0, height, color, update)
        self.draw_horizontal_line(x0 + width - 1, y0, height, color, update)

    def draw_vertical_line(self, x0, y0, length, color, update: bool = True):
        """Draw a vertical line."""
        self.draw_line(x0, y0, x0, y0 + length - 1, color, update)

    def draw_horizontal_line(self, x0, y0, length, color, update: bool = True):
        """Draw a horizontal line."""
        self.draw_line(x0, y0, x0 + length - 1, y0, color, update)

    def fill_rectangle(self, x0, y0, width, height, color, update: bool = True):
        """Draw a filled rectangle."""
        for i in range(x0, x0 + width):
            self.draw_vertical_line(i, y0, height, color, update)

    def write_string(self, s: str, update: bool = True):
        """Write a string on screen."""
        for a in s:
            self.write_char(ord(a), update=False)
        self._draw(update)

    def write_char(self, c: int, update: bool = True):
        """Write a single character on screen."""
        if c == "\n":
            self.cursor[1] += self.textsize * 8
            self.cursor[0] = 0
        elif c == "\r":
            pass
        else:
            self._draw_char(
                self.cursor[0],
                self.cursor[1],
                c,
                self.textcolor,
                self.textbgcolor,
                self.textsize,
            )
            self.cursor[0] += self.textsize * 6

            if self.wrap and (self.cursor[0] > (self._WIDTH - self.textsize * 6)):
                self.cursor[1] += self.textsize * 8
                self.cursor[0] = 0

        self._draw(update)

    def _draw_char(self, x0, y0, c, color, bg, size):
        if (
            (x0 >= self._WIDTH)
            or (y0 >= self._HEIGHT)
            or ((x0 + 5 * size - 1) < 0)
            or ((y0 + 8 * size - 1) < 0)
        ):
            return
        for i in range(6):
            if i == 5:
                line = 0x0
            else:
                line = self._font[c * 5 + i]
            for j in range(8):
                if line & 0x1:
                    if size == 1:
                        self.draw_pixel(x0 + i, y0 + j, color, False)
                    else:
                        self.fill_rectangle(x0 + (i * size), y0 + (j * size), size, size, color, False)
                elif bg != color:
                    if size == 1:
                        self.draw_pixel(x0 + i, y0 + j, bg, False)
                    else:
                        self.fill_rect(x0 + i * size, y0 + j * size, size, size, bg, False)
                line >>= 1

    def scroll(self, direction):
        """Scroll the screen contents."""
        if direction == "left":
            self._write_command(0x27)  # up-0x29 ,2A left-0x27 right0x26
        if direction == "right":
            self._write_command(0x26)  # up-0x29 ,2A left-0x27 right0x26
        if direction in ["topright", "bottomright"]:
            self._write_command(0x29)  # up-0x29 ,2A left-0x27 right0x26
        if direction in ["topleft", "bottomleft"]:
            self._write_command(0x2A)  # up-0x29 ,2A left-0x27 right0x26

        if direction in ["left", "right", "topright", "topleft", "bottomleft", "bottomright"]:
            self._write_command(0x0)  # dummy
            self._write_command(0x0)  # start page
            self._write_command(0x7)  # time interval 0b100 - 3 frames
            self._write_command(0xF)  # end page
            if direction in ["topleft", "topright"]:
                self._write_command(0x02)
            elif direction in ["bottomleft", "bottomright"]:
                self._write_command(0xFE)

            if direction in ["left", "right"]:
                self._write_command(0x02)
                self._write_command(0xFF)

            self._write_command(0x2F)

        if direction == "stop":
            self._write_command(0x2E)

    def pulse(self):
        for a in range(2):
            self._write_command(0xD6)
            self._write_command(0x01)
            time.sleep(0.1)
            self._write_command(0xD6)
            self._write_command(0x00)
            time.sleep(0.1)
