def ab2ascii(data: bytearray) -> str:
    """Converts an array of bytes to an ASCII string."""
    return data.decode('ascii')


def ascii2ab(text: str) -> bytearray:
    """Converts an ASCII string to an array of bytes."""
    return bytearray(text.encode('ascii'))
