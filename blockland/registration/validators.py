# registration/validators.py
from django.core.exceptions import ValidationError

def validate_ethereum_address(value):
    """
    Validate that the value is a valid Ethereum address.
    Ethereum addresses are 42 characters long, start with '0x', and contain only hex digits.
    """
    if not isinstance(value, str):
        raise ValidationError("Ethereum address must be a string.")

    if not (value.startswith('0x') and len(value) == 42):
        raise ValidationError("Invalid Ethereum address format.")

    hex_part = value[2:]
    if not all(c in '0123456789abcdefABCDEF' for c in hex_part):
        raise ValidationError("Ethereum address contains invalid characters.")
