"""Area balance equation solving for the LF model.

From Fant (1985): integral(E(t), 0, T0) = 0
Alpha must be found such that the opening-phase integral balances
the return-phase integral. Newton-Raphson and bisection are both
used in practice -- they are NOT equivalent algorithms.
"""

PAIRS = [
    {
        "name": "newton_raphson_vs_bisection",
        "body_a": """
def solve_alpha_newton(omega_g, t_e, E_e, epsilon, t_a, alpha_init, tol, max_iter):
    import math
    alpha = alpha_init
    for _ in range(max_iter):
        denom = alpha * alpha + omega_g * omega_g
        integral_open = (E_e / denom) * (
            alpha * math.sin(omega_g * t_e)
            - omega_g * math.cos(omega_g * t_e)
        ) + omega_g / denom
        integral_open_scaled = math.exp(alpha * t_e) * integral_open
        target = E_e / (epsilon * t_a)
        residual = integral_open_scaled - target
        d_integral = t_e * integral_open_scaled
        if abs(d_integral) < 1e-30:
            break
        alpha = alpha - residual / d_integral
        if abs(residual) < tol:
            break
    return alpha
""",
        "body_b": """
def solve_alpha_bisect(w, te, ee, eps, ta, lo, hi, tolerance, iterations):
    import math
    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        d = mid * mid + w * w
        sin_wt = math.sin(w * te)
        cos_wt = math.cos(w * te)
        integral = math.exp(mid * te) * (
            (mid * sin_wt - w * cos_wt) / d + w / d
        )
        target = ee / (eps * ta)
        if integral < target:
            lo = mid
        else:
            hi = mid
        if abs(hi - lo) < tolerance:
            break
    return (lo + hi) / 2.0
""",
        "bindings_a": {
            "omega_g": "lf_angular_frequency",
            "t_e": "lf_excitation_time",
            "E_e": "lf_excitation_amplitude",
            "epsilon": "lf_decay_rate",
            "t_a": "lf_return_time_constant",
            "alpha_init": "initial_guess",
            "tol": "convergence_tolerance",
            "max_iter": "max_iterations",
            "alpha": "lf_growth_constant",
        },
        "bindings_b": {
            "w": "lf_angular_frequency",
            "te": "lf_excitation_time",
            "ee": "lf_excitation_amplitude",
            "eps": "lf_decay_rate",
            "ta": "lf_return_time_constant",
            "lo": "search_lower_bound",
            "hi": "search_upper_bound",
            "tolerance": "convergence_tolerance",
            "iterations": "max_iterations",
            "mid": "midpoint",
        },
        "expected_equivalent": False,
        "expected_min_tier": 4,
        "known_values": {},
    },
    {
        "name": "newton_raphson_two_styles",
        "body_a": """
def newton_alpha(wg, te, ee, eps, ta, a0, tol, nmax):
    import math
    a = a0
    for iteration in range(nmax):
        d = a * a + wg * wg
        exp_at = math.exp(a * te)
        sin_wt = math.sin(wg * te)
        cos_wt = math.cos(wg * te)
        f_val = exp_at * ((a * sin_wt - wg * cos_wt) / d + wg / d) - ee / (eps * ta)
        f_prime = te * exp_at * ((a * sin_wt - wg * cos_wt) / d + wg / d)
        if abs(f_prime) < 1e-30:
            break
        a = a - f_val / f_prime
        if abs(f_val) < tol:
            break
    return a
""",
        "body_b": """
def find_alpha_nr(omega, t_exc, exc_amp, decay, ret_tau, guess, tolerance, limit):
    import math
    alpha = guess
    for step in range(limit):
        denom = alpha ** 2 + omega ** 2
        e_factor = math.exp(alpha * t_exc)
        s = math.sin(omega * t_exc)
        c = math.cos(omega * t_exc)
        residual = e_factor * ((alpha * s - omega * c + omega) / denom) - exc_amp / (decay * ret_tau)
        jacobian = t_exc * e_factor * ((alpha * s - omega * c + omega) / denom)
        if abs(jacobian) < 1e-30:
            break
        alpha -= residual / jacobian
        if abs(residual) < tolerance:
            break
    return alpha
""",
        "bindings_a": {
            "wg": "lf_angular_frequency",
            "te": "lf_excitation_time",
            "ee": "lf_excitation_amplitude",
            "eps": "lf_decay_rate",
            "ta": "lf_return_time_constant",
            "a0": "initial_guess",
            "tol": "convergence_tolerance",
            "nmax": "max_iterations",
            "a": "lf_growth_constant",
        },
        "bindings_b": {
            "omega": "lf_angular_frequency",
            "t_exc": "lf_excitation_time",
            "exc_amp": "lf_excitation_amplitude",
            "decay": "lf_decay_rate",
            "ret_tau": "lf_return_time_constant",
            "guess": "initial_guess",
            "tolerance": "convergence_tolerance",
            "limit": "max_iterations",
            "alpha": "lf_growth_constant",
        },
        "expected_equivalent": False,
        "expected_min_tier": 2,
        "known_values": {},
    },
]
