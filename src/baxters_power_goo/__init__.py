"""Baxters Power Goo — Linux"""

try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("baxters-power-goo")
    except PackageNotFoundError:
        __version__ = "1.0.0"
except ImportError:
    __version__ = "1.0.0"
