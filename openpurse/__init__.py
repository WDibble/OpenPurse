"""
OpenPurse: A lightweight Python package to dynamically parse, flatten, and translate 
complex ISO 20022 XML and SWIFT MT financial messages into usable structured data.
"""

from .builder import MessageBuilder
from .models import PaymentMessage
from .parser import OpenPurseParser
from .translator import Translator

__all__ = ["OpenPurseParser", "PaymentMessage", "Translator", "MessageBuilder"]
