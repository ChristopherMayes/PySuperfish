from .superfish import Superfish

try:
    from ._version import __version__
except ImportError:
    __version__ = "0.0.0"

__all__ = ["Superfish"]
