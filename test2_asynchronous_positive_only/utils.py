from decimal import Decimal


def round_to(number, divider) -> float:
    """Return the quotient of `number` and `divider`
    """
    fs = f'{divider:.18f}'.rstrip('0')
    decimals = num_decimals(fs)
    if decimals > 0:
        return round(number / divider // 1 * divider, decimals)
    else:
        return round(number / divider // 1 * divider)


def num_decimals(f: str):
    """Number of decimals
    """
    return len(f[f.find('.'):]) - 1

def scientific_to_float(number: Decimal) -> float:
    full_float = f"{number:.20f}".rstrip('0').rstrip('.')
    return full_float
