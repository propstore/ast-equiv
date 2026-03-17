"""dB conversion variants.

20*log10(x) vs 10*log10(x**2) are algebraically equivalent.
Loop accumulation vs vectorized approaches are structurally different.
"""

PAIRS = [
    {
        "name": "db_20log_vs_10log_squared",
        "body_a": """
def amplitude_to_db(amplitude):
    import math
    if amplitude <= 0:
        return -120.0
    return 20.0 * math.log10(amplitude)
""",
        "body_b": """
def amp_to_decibels(x):
    import math
    if x <= 0:
        return -120.0
    return 10.0 * math.log10(x * x)
""",
        "bindings_a": {
            "amplitude": "signal_amplitude",
        },
        "bindings_b": {
            "x": "signal_amplitude",
        },
        "expected_equivalent": False,
        "expected_min_tier": 3,
        "known_values": {"signal_amplitude": 1.0},
    },
    {
        "name": "db_power_vs_amplitude_convention",
        "body_a": """
def to_db_power(power_value):
    import math
    if power_value <= 0:
        return -100.0
    return 10.0 * math.log10(power_value)
""",
        "body_b": """
def to_db_amplitude(amp_value):
    import math
    if amp_value <= 0:
        return -100.0
    return 20.0 * math.log10(amp_value)
""",
        "bindings_a": {
            "power_value": "signal_level",
        },
        "bindings_b": {
            "amp_value": "signal_level",
        },
        "expected_equivalent": False,
        "expected_min_tier": 3,
        "known_values": {"signal_level": 2.0},
    },
    {
        "name": "db_array_loop_vs_comprehension",
        "body_a": """
def db_array(amplitudes):
    import math
    result = []
    for amp in amplitudes:
        if amp <= 0:
            result.append(-120.0)
        else:
            result.append(20.0 * math.log10(amp))
    return result
""",
        "body_b": """
def db_array(values):
    import math
    return [
        -120.0 if v <= 0 else 20.0 * math.log10(v)
        for v in values
    ]
""",
        "bindings_a": {
            "amplitudes": "amplitude_array",
            "result": "db_array_output",
            "amp": "current_amplitude",
        },
        "bindings_b": {
            "values": "amplitude_array",
            "v": "current_amplitude",
        },
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
]
