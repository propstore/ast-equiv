"""LF model opening phase variants.

From Fant (1985): E(t) = E_0 * exp(alpha*t) * sin(omega_g*t)
for 0 < t < t_e (opening phase).
"""

PAIRS = [
    {
        "name": "opening_phase_for_vs_range",
        "body_a": """
def lf_opening_phase(E0, alpha, omega_g, dt, n_samples):
    import math
    signal = []
    for i in range(n_samples):
        t = i * dt
        sample = E0 * math.exp(alpha * t) * math.sin(omega_g * t)
        signal.append(sample)
    return signal
""",
        "body_b": """
def compute_opening(amplitude, growth, angular_freq, time_step, count):
    import math
    output = []
    for k in range(count):
        time = k * time_step
        value = amplitude * math.exp(growth * time) * math.sin(angular_freq * time)
        output.append(value)
    return output
""",
        "bindings_a": {
            "E0": "lf_initial_amplitude",
            "alpha": "lf_growth_constant",
            "omega_g": "lf_angular_frequency",
            "dt": "time_step",
            "n_samples": "sample_count",
            "signal": "output_signal",
            "t": "current_time",
            "sample": "current_sample",
        },
        "bindings_b": {
            "amplitude": "lf_initial_amplitude",
            "growth": "lf_growth_constant",
            "angular_freq": "lf_angular_frequency",
            "time_step": "time_step",
            "count": "sample_count",
            "output": "output_signal",
            "time": "current_time",
            "value": "current_sample",
        },
        "expected_equivalent": True,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "opening_phase_while_loop",
        "body_a": """
def lf_opening(E0, alpha, omega, dt, N):
    import math
    result = []
    for idx in range(N):
        t = idx * dt
        result.append(E0 * math.exp(alpha * t) * math.sin(omega * t))
    return result
""",
        "body_b": """
def lf_opening(e0, a, w, step, num):
    import math
    buf = []
    n = 0
    while n < num:
        time = n * step
        val = e0 * math.exp(a * time) * math.sin(w * time)
        buf.append(val)
        n += 1
    return buf
""",
        "bindings_a": {
            "E0": "lf_initial_amplitude",
            "alpha": "lf_growth_constant",
            "omega": "lf_angular_frequency",
            "dt": "time_step",
            "N": "sample_count",
            "result": "output_buffer",
            "t": "current_time",
        },
        "bindings_b": {
            "e0": "lf_initial_amplitude",
            "a": "lf_growth_constant",
            "w": "lf_angular_frequency",
            "step": "time_step",
            "num": "sample_count",
            "buf": "output_buffer",
            "time": "current_time",
            "val": "current_sample",
        },
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "opening_phase_zero_vs_one_based",
        "body_a": """
def opening_phase(E0, alpha, omega_g, dt, N):
    import math
    y = [0.0] * N
    for i in range(N):
        t = i * dt
        y[i] = E0 * math.exp(alpha * t) * math.sin(omega_g * t)
    return y
""",
        "body_b": """
def opening_phase(amp, grow, freq_rad, delta_t, length):
    import math
    y = [0.0] * length
    for j in range(1, length + 1):
        t = (j - 1) * delta_t
        y[j - 1] = amp * math.exp(grow * t) * math.sin(freq_rad * t)
    return y
""",
        "bindings_a": {
            "E0": "lf_initial_amplitude",
            "alpha": "lf_growth_constant",
            "omega_g": "lf_angular_frequency",
            "dt": "time_step",
            "N": "sample_count",
            "y": "output_array",
        },
        "bindings_b": {
            "amp": "lf_initial_amplitude",
            "grow": "lf_growth_constant",
            "freq_rad": "lf_angular_frequency",
            "delta_t": "time_step",
            "length": "sample_count",
            "y": "output_array",
        },
        "expected_equivalent": False,  # requires loop index offset transform: range(N) vs range(1, N+1) with j-1 (not implemented)
        "expected_min_tier": 4,
        "known_values": {},
    },
]
