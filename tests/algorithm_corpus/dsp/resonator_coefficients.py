"""Resonator coefficient calculation variants.

From Klatt (1980):
  C = -exp(-2*pi*BW*T)
  B = 2*exp(-pi*BW*T)*cos(2*pi*F*T)
  A = 1 - B - C
"""

import math

PAIRS = [
    {
        "name": "coeff_c_direct_vs_intermediate",
        "body_a": """
def calc_coeff_c(bandwidth, sample_period):
    import math
    c = -math.exp(-2.0 * math.pi * bandwidth * sample_period)
    return c
""",
        "body_b": """
def calc_coeff_c(bw, T):
    import math
    two_pi_bw_t = 2.0 * math.pi * bw * T
    c = -math.exp(-two_pi_bw_t)
    return c
""",
        "bindings_a": {
            "bandwidth": "formant_bandwidth",
            "sample_period": "sampling_period",
            "c": "resonator_coefficient_C",
        },
        "bindings_b": {
            "bw": "formant_bandwidth",
            "T": "sampling_period",
            "two_pi_bw_t": "angular_bandwidth_product",
            "c": "resonator_coefficient_C",
        },
        "expected_equivalent": False,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "coeff_c_negation_order",
        "body_a": """
def compute_c(bw, dt):
    import math
    return -math.exp(-2.0 * math.pi * bw * dt)
""",
        "body_b": """
def compute_c(bandwidth_hz, period_s):
    import math
    exponent = -2.0 * math.pi * bandwidth_hz * period_s
    magnitude = math.exp(exponent)
    return -magnitude
""",
        "bindings_a": {
            "bw": "formant_bandwidth",
            "dt": "sampling_period",
        },
        "bindings_b": {
            "bandwidth_hz": "formant_bandwidth",
            "period_s": "sampling_period",
            "exponent": "decay_exponent",
            "magnitude": "decay_magnitude",
        },
        "expected_equivalent": False,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "all_coefficients_separate_vs_bundled",
        "body_a": """
def resonator_coefficients(freq, bw, fs):
    import math
    T = 1.0 / fs
    C = -math.exp(-2.0 * math.pi * bw * T)
    B = 2.0 * math.exp(-math.pi * bw * T) * math.cos(2.0 * math.pi * freq * T)
    A = 1.0 - B - C
    return A, B, C
""",
        "body_b": """
def compute_resonator_params(formant_freq, bandwidth, sample_rate):
    import math
    period = 1.0 / sample_rate
    pi_bw_t = math.pi * bandwidth * period
    two_pi_f_t = 2.0 * math.pi * formant_freq * period
    coeff_c = -math.exp(-2.0 * pi_bw_t)
    coeff_b = 2.0 * math.exp(-pi_bw_t) * math.cos(two_pi_f_t)
    coeff_a = 1.0 - coeff_b - coeff_c
    return coeff_a, coeff_b, coeff_c
""",
        "bindings_a": {
            "freq": "formant_frequency",
            "bw": "formant_bandwidth",
            "fs": "sampling_rate",
            "T": "sampling_period",
            "A": "resonator_coefficient_A",
            "B": "resonator_coefficient_B",
            "C": "resonator_coefficient_C",
        },
        "bindings_b": {
            "formant_freq": "formant_frequency",
            "bandwidth": "formant_bandwidth",
            "sample_rate": "sampling_rate",
            "period": "sampling_period",
            "pi_bw_t": "half_angular_bandwidth_product",
            "two_pi_f_t": "angular_frequency_product",
            "coeff_a": "resonator_coefficient_A",
            "coeff_b": "resonator_coefficient_B",
            "coeff_c": "resonator_coefficient_C",
        },
        "expected_equivalent": False,
        "expected_min_tier": 2,
        "known_values": {},
    },
]
