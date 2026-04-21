"""Klatt digital resonator variants.

Based on the difference equation: y(nT) = A*x(nT) + B*y(nT-T) + C*y(nT-2T)
from Klatt (1980).
"""

PAIRS = [
    {
        "name": "direct_form_ii_variable_rename",
        "body_a": """
def resonator(input_signal, coeff_a, coeff_b, coeff_c, delay_1, delay_2):
    output = coeff_a * input_signal + coeff_b * delay_1 + coeff_c * delay_2
    delay_2 = delay_1
    delay_1 = output
    return output, delay_1, delay_2
""",
        "body_b": """
def resonator(x, a, b, c, y_prev, y_prev2):
    y = a * x + b * y_prev + c * y_prev2
    y_prev2 = y_prev
    y_prev = y
    return y, y_prev, y_prev2
""",
        "bindings_a": {
            "input_signal": "resonator_input",
            "coeff_a": "resonator_coefficient_A",
            "coeff_b": "resonator_coefficient_B",
            "coeff_c": "resonator_coefficient_C",
            "delay_1": "delay_line_1",
            "delay_2": "delay_line_2",
            "output": "resonator_output",
        },
        "bindings_b": {
            "x": "resonator_input",
            "a": "resonator_coefficient_A",
            "b": "resonator_coefficient_B",
            "c": "resonator_coefficient_C",
            "y_prev": "delay_line_1",
            "y_prev2": "delay_line_2",
            "y": "resonator_output",
        },
        "expected_equivalent": True,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "direct_form_ii_vs_transposed",
        "body_a": """
def resonator_df2(x_n, a, b, c, w1, w2):
    w0 = x_n + b * w1 + c * w2
    y_n = a * w0
    w2 = w1
    w1 = w0
    return y_n, w1, w2
""",
        "body_b": """
def resonator_tdf2(sample, gain, fb1, fb2, state1, state2):
    output = gain * sample + state1
    state1 = fb1 * sample + state2
    state2 = fb2 * sample
    return output, state1, state2
""",
        "bindings_a": {
            "x_n": "resonator_input",
            "a": "resonator_coefficient_A",
            "b": "resonator_coefficient_B",
            "c": "resonator_coefficient_C",
            "w1": "state_variable_1",
            "w2": "state_variable_2",
            "w0": "intermediate",
            "y_n": "resonator_output",
        },
        "bindings_b": {
            "sample": "resonator_input",
            "gain": "resonator_coefficient_A",
            "fb1": "resonator_coefficient_B",
            "fb2": "resonator_coefficient_C",
            "state1": "state_variable_1",
            "state2": "state_variable_2",
            "output": "resonator_output",
        },
        "expected_equivalent": False,
        "expected_min_tier": 4,
        "known_values": {},
    },
    {
        "name": "resonator_loop_vs_unrolled",
        "body_a": """
def process_block(samples, a, b, c):
    y1 = 0.0
    y2 = 0.0
    output = []
    for n in range(len(samples)):
        y0 = a * samples[n] + b * y1 + c * y2
        output.append(y0)
        y2 = y1
        y1 = y0
    return output
""",
        "body_b": """
def process_block(x, coeff_a, coeff_b, coeff_c):
    prev = 0.0
    prev2 = 0.0
    result = []
    idx = 0
    while idx < len(x):
        val = coeff_a * x[idx] + coeff_b * prev + coeff_c * prev2
        result.append(val)
        prev2 = prev
        prev = val
        idx += 1
    return result
""",
        "bindings_a": {
            "samples": "input_buffer",
            "a": "resonator_coefficient_A",
            "b": "resonator_coefficient_B",
            "c": "resonator_coefficient_C",
            "y1": "delay_line_1",
            "y2": "delay_line_2",
            "y0": "current_output",
            "output": "output_buffer",
        },
        "bindings_b": {
            "x": "input_buffer",
            "coeff_a": "resonator_coefficient_A",
            "coeff_b": "resonator_coefficient_B",
            "coeff_c": "resonator_coefficient_C",
            "prev": "delay_line_1",
            "prev2": "delay_line_2",
            "val": "current_output",
            "result": "output_buffer",
        },
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
]
