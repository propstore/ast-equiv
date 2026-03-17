"""Formant bandwidth to resonator coefficient B variants.

From Klatt (1980): B = 2*exp(-pi*BW*T)*cos(2*pi*F*T)
"""

PAIRS = [
    {
        "name": "coeff_b_explicit_vs_factored",
        "body_a": """
def coeff_b(formant_freq, bandwidth, sample_rate):
    import math
    T = 1.0 / sample_rate
    r = math.exp(-math.pi * bandwidth * T)
    theta = 2.0 * math.pi * formant_freq * T
    return 2.0 * r * math.cos(theta)
""",
        "body_b": """
def compute_B(f, bw, fs):
    import math
    period = 1.0 / fs
    decay = math.exp(-math.pi * bw * period)
    angle = 2.0 * math.pi * f * period
    b_coeff = 2.0 * decay * math.cos(angle)
    return b_coeff
""",
        "bindings_a": {
            "formant_freq": "formant_frequency",
            "bandwidth": "formant_bandwidth",
            "sample_rate": "sampling_rate",
            "T": "sampling_period",
            "r": "pole_radius",
            "theta": "pole_angle",
        },
        "bindings_b": {
            "f": "formant_frequency",
            "bw": "formant_bandwidth",
            "fs": "sampling_rate",
            "period": "sampling_period",
            "decay": "pole_radius",
            "angle": "pole_angle",
            "b_coeff": "resonator_coefficient_B",
        },
        "expected_equivalent": False,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "coeff_b_inline_vs_precomputed_period",
        "body_a": """
def resonator_b(freq, bw, sr):
    import math
    return 2.0 * math.exp(-math.pi * bw / sr) * math.cos(2.0 * math.pi * freq / sr)
""",
        "body_b": """
def resonator_b(formant_hz, bandwidth_hz, rate):
    import math
    inv_rate = 1.0 / rate
    exp_term = math.exp(-math.pi * bandwidth_hz * inv_rate)
    cos_term = math.cos(2.0 * math.pi * formant_hz * inv_rate)
    return 2.0 * exp_term * cos_term
""",
        "bindings_a": {
            "freq": "formant_frequency",
            "bw": "formant_bandwidth",
            "sr": "sampling_rate",
        },
        "bindings_b": {
            "formant_hz": "formant_frequency",
            "bandwidth_hz": "formant_bandwidth",
            "rate": "sampling_rate",
            "inv_rate": "sampling_period",
            "exp_term": "pole_radius",
            "cos_term": "pole_cosine",
        },
        "expected_equivalent": False,
        "expected_min_tier": 3,
        "known_values": {"sampling_rate": 10000.0},
    },
]
