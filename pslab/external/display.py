"""Control display devices such as OLED screens.

Example
-------
>>> from pslab.bus import I2CMaster
>>> from pslab.external.display import SSD1306
>>> i2c = I2CMaster()  # Initialize bus
>>> i2c.configure(1e6)  # Set bus speed to 1 MHz.
>>> oled = SSD1306("fast")
>>> oled.clear()
>>> oled.write_string("Hello world!")
>>> oled.scroll("topright")
>>> time.sleep(2.8)
>>> oled.scroll("stop")
"""
import json
import os.path

try:
    from PIL import Image

    HASPIL = True
except ImportError:
    HASPIL = False

from pslab.bus import I2CSlave

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class SSD1306(I2CSlave):
    """Interface to a monochrome OLED display driven by an SSD1306 chip.

    Parameters
    ----------
    speed : {'slow' ,'medium', 'fast'}, optional
        Controls how many bytes of data are written to the display at once.
        More bytes written at once means faster draw rate, but requires that
        the baudrate of the underlying I2C bus is high enough to avoid timeout.
        The default value is 'slow'.
    sh1106 : bool, optional
        Set this to True if the OLED is driven by a SH1106 chip rather than a
        SSD1306.
    """

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
    _LOWCOLUMNOFFSET = 0

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
    _SETPAGESTART = 0xB0
    _COMSCANINC = 0xC0
    _COMSCANDEC = 0xC8
    _SEGREMAP = 0xA0
    _CHARGEPUMP = 0x8D
    _EXTERNALVCC = 0x1
    _SWITCHCAPVCC = 0x2

    # fmt: off
    _INIT_DATA = [
        _DISPLAYOFF,
        _SETDISPLAYCLOCKDIV, 0x80,  # Default aspect ratio.
        _SETMULTIPLEX, 0x3F,
        _SETDISPLAYOFFSET, 0x0,  # No offset.
        _SETSTARTLINE | 0x0,  # Line #0.
        _CHARGEPUMP, 0x14,
        _MEMORYMODE, 0x02,  # Page addressing
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

    def __init__(self, device=None, speed="slow"):
        super().__init__(device=device, address=self._ADDRESS)
        self._buffer = [0 for a in range(1024)]
        self.cursor = [0, 0]
        self.textsize = 1
        self.textcolor = 1
        self.textbgcolor = 0
        self.wrap = True
        self._contrast = 0xFF
        self.speed = speed

        with open(os.path.join(__location__, "ssd1306_gfx.json"), "r") as f:
            gfx = json.load(f)

        self._logo = gfx["logo"]
        self._font = gfx["font"]

        for command in self._INIT_DATA:
            self._write_command(command)

        self.display_logo()

    def display_logo(self):
        """Display pslab.io logo."""
        self.scroll("stop")
        self._buffer = self._logo[:]
        self.update()

    def _write_command(self, command: int):
        self.write_byte(command)

    def _write_data(self, data: list):
        self.write(data, register_address=0x40)

    def clear(self):
        """Clear the display."""
        self.cursor = [0, 0]
        self._buffer = [0] * (self._WIDTH * self._HEIGHT // 8)
        self.update()

    def update(self):
        """Redraw display."""
        for i in range(8):
            self._write_command(self._SETLOWCOLUMN | self._LOWCOLUMNOFFSET)
            self._write_command(self._SETHIGHCOLUMN | 0)
            self._write_command(self._SETPAGESTART | i)

            if self.speed == "slow":
                for j in range(self._WIDTH):
                    self._write_data([self._buffer[i * self._WIDTH + j]])
            elif self.speed == "medium":
                for j in range(self._WIDTH // 8):
                    self._write_data(
                        self._buffer[
                            i * self._WIDTH + j * 8 : i * self._WIDTH + 8 * (j + 1)
                        ]
                    )
            else:
                self._write_data(self._buffer[self._WIDTH * i : self._WIDTH * (i + 1)])

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
        self.draw_pixel(x0, y0 + r, color, False)
        self.draw_pixel(x0, y0 - r, color, False)
        self.draw_pixel(x0 + r, y0, color, False)
        self.draw_pixel(x0 - r, y0, color, False)

        while x < y:
            if f >= 0:
                y -= 1
                ddF_y += 2
                f += ddF_y

            x += 1
            ddF_x += 2
            f += ddF_x
            self.draw_pixel(x0 + x, y0 + y, color, False)
            self.draw_pixel(x0 - x, y0 + y, color, False)
            self.draw_pixel(x0 + x, y0 - y, color, False)
            self.draw_pixel(x0 - x, y0 - y, color, False)
            self.draw_pixel(x0 + y, y0 + x, color, False)
            self.draw_pixel(x0 - y, y0 + x, color, False)
            self.draw_pixel(x0 + y, y0 - x, color, False)
            self.draw_pixel(x0 - y, y0 - x, color, False)

        self._draw(update)

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
                self.draw_pixel(y0, x0, color, False)
            else:
                self.draw_pixel(x0, y0, color, False)
            err -= dy

            if err < 0:
                y0 += ystep
                err += dx
            x0 += 1

        self._draw(update)

    def draw_rectangle(self, x0, y0, width, height, color, update: bool = True):
        """Draw a rectangle."""
        self.draw_horizontal_line(x0, y0, width, color, False)
        self.draw_horizontal_line(x0, y0 + height - 1, width, color, False)
        self.draw_vertical_line(x0, y0, height, color, False)
        self.draw_vertical_line(x0 + width - 1, y0, height, color, False)
        self._draw(update)

    def draw_vertical_line(self, x0, y0, length, color, update: bool = True):
        """Draw a vertical line."""
        self.draw_line(x0, y0, x0, y0 + length - 1, color, update)

    def draw_horizontal_line(self, x0, y0, length, color, update: bool = True):
        """Draw a horizontal line."""
        self.draw_line(x0, y0, x0 + length - 1, y0, color, update)

    def fill_rectangle(self, x0, y0, width, height, color, update: bool = True):
        """Draw a filled rectangle."""
        for i in range(x0, x0 + width):
            self.draw_vertical_line(i, y0, height, color, False)
        self._draw(update)

    def write_string(self, s: str, update: bool = True):
        """Write a string on screen."""
        for a in s:
            self._write_char(ord(a), False)
        self._draw(update)

    def _write_char(self, c: int, update: bool = True):
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
                        self.fill_rectangle(
                            x0 + (i * size), y0 + (j * size), size, size, color, False
                        )
                elif bg != color:
                    if size == 1:
                        self.draw_pixel(x0 + i, y0 + j, bg, False)
                    else:
                        self.fill_rectangle(
                            x0 + i * size, y0 + j * size, size, size, bg, False
                        )
                line >>= 1

    def scroll(self, direction: str):
        """Scroll the screen contents.

        Parameters
        ----------
        direction : {'left', 'right', 'stop'}
            Scrolling direction.
        """
        if direction == "left":
            self._write_command(0x27)  # up-0x29 ,2A left-0x27 right0x26
        if direction == "right":
            self._write_command(0x26)  # up-0x29 ,2A left-0x27 right0x26
        if direction in ["topright", "bottomright"]:
            self._write_command(0x29)  # up-0x29 ,2A left-0x27 right0x26
        if direction in ["topleft", "bottomleft"]:
            self._write_command(0x2A)  # up-0x29 ,2A left-0x27 right0x26

        if direction in [
            "left",
            "right",
            "topright",
            "topleft",
            "bottomleft",
            "bottomright",
        ]:
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

    def poweron(self):
        """Turn the display on."""
        self._write_command(self._DISPLAYON)

    def poweroff(self):
        """Turn the display off."""
        self._write_command(self._DISPLAYOFF)

    def display(self, image: Image):
        """Display an image.

        Parameters
        ----------
        image : Image
            A PIL.Image instance.
        """
        if not HASPIL:
            raise ImportError(
                "Displaying images requires PIL, but it is not installed."
            )

        if not image.size == (128, 64):
            image = image.resize((128, 64))

        if not image.mode == "1":
            image = image.convert("1")

        image_data = image.getdata()
        pixels_per_page = self._WIDTH * 8
        buf = bytearray(self._WIDTH)
        buffer = []

        for y in range(0, int(8 * pixels_per_page), pixels_per_page):
            offsets = [y + self._WIDTH * i for i in range(8)]

            for x in range(self._WIDTH):
                buf[x] = (
                    (image_data[x + offsets[0]] and 0x01)
                    | (image_data[x + offsets[1]] and 0x02)
                    | (image_data[x + offsets[2]] and 0x04)
                    | (image_data[x + offsets[3]] and 0x08)
                    | (image_data[x + offsets[4]] and 0x10)
                    | (image_data[x + offsets[5]] and 0x20)
                    | (image_data[x + offsets[6]] and 0x40)
                    | (image_data[x + offsets[7]] and 0x80)
                )

            buffer += list(buf)

        self._buffer = buffer
        self.update()


class SH1106(SSD1306):
    """Interface to a monochrome OLED display driven by an SH1106 chip.

    SH1106 is a common OLED driver which is almost identical to the SSD1306.
    OLED displays are sometimes advertised as using SSD1306 when they in fact
    use SH1106.
    """

    _LOWCOLUMNOFFSET = 2
