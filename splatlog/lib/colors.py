from colorsys import hsv_to_rgb
from zlib import crc32

# HSV_tuples = [(x*1.0/N, 0.75, 0.75) for x in range(N)]
# RGB_tuples = [colorsys.hsv_to_rgb(*x) for x in HSV_tuples]


def as_hex_byte(n: float):
    """Convert `n` in [0, 1] to a hex byte as you would use in a hex
    representation of an RGB color.

    ##### Examples #####

    ```python
    >>> as_hex_byte(0)
    '00'

    >>> as_hex_byte(1)
    'ff'

    >>> as_hex_byte(0.12345)
    '1f'

    >>> as_hex_byte(1.23)
    Traceback (most recent call last):
      ...
    ValueError: `n` must be between 0 and 1 (inclusive), given 1.23

    ```
    """
    if not (0 <= n <= 1):
        raise ValueError(
            f"`n` must be between 0 and 1 (inclusive), given {n!r}"
        )
    return format(round(n * 255), "02x")


class ColorPallet:
    DEFAULT_SATURATION = 0.75
    DEFAULT_VALUE = 0.75

    _size: int
    _saturation: float
    _value: float
    _hues: tuple[float, ...]
    _colors: tuple[str, ...]

    def __init__(
        self,
        size: int = 32,
        saturation: float = DEFAULT_SATURATION,
        value: float = DEFAULT_VALUE,
    ):
        self._size = size
        self._saturation = saturation
        self._value = value
        self._hues = tuple((float(i) / size) for i in range(size))
        self._colors = tuple(self.rgb_hex_for(hue) for hue in self._hues)

    @property
    def hues(self) -> tuple[float, ...]:
        return self._hues

    @property
    def colors(self) -> tuple[str, ...]:
        return self._colors

    def rgb_hex_for(self, hue: float) -> str:
        return "#{:02x}{:02x}{:02x}".format(
            *(
                round(n * 255)
                for n in hsv_to_rgb(hue, self._saturation, self._value)
            )
        )

    def modulo(self, label: str) -> str:
        return self._colors[crc32(bytes(label, encoding="utf-8")) % self._size]
