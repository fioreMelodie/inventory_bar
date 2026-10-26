import re

from rest_framework.exceptions import ValidationError


def normalize_approval_reference(value):
    if not isinstance(value, str):
        raise ValidationError("Enter the terminal approval reference.")
    reference = value.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9._/-]{2,39}", reference):
        raise ValidationError("Use 3 to 40 letters, numbers, dots, hyphens, underscores or slashes.")
    # No se aceptan numeros largos ni grupos de digitos que puedan ser un PAN.
    if re.search(r"\d(?:[._/-]*\d){12,}", reference):
        raise ValidationError("Do not enter a card number. Use the terminal approval reference.")
    return reference
