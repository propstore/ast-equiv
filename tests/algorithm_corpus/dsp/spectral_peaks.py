"""Spectral peak picking variants.

Different strategies for finding peaks in a magnitude spectrum:
naive local-maximum, prominence-based, and threshold-then-sort.
"""

PAIRS = [
    {
        "name": "naive_local_max_rename",
        "body_a": """
def find_peaks_naive(spectrum, min_distance):
    peaks = []
    for i in range(1, len(spectrum) - 1):
        if spectrum[i] > spectrum[i - 1] and spectrum[i] > spectrum[i + 1]:
            if len(peaks) == 0 or (i - peaks[-1]) >= min_distance:
                peaks.append(i)
    return peaks
""",
        "body_b": """
def detect_spectral_peaks(mag, min_sep):
    found = []
    idx = 1
    while idx < len(mag) - 1:
        if mag[idx] > mag[idx - 1] and mag[idx] > mag[idx + 1]:
            if len(found) == 0 or (idx - found[-1]) >= min_sep:
                found.append(idx)
        idx += 1
    return found
""",
        "bindings_a": {
            "spectrum": "magnitude_spectrum",
            "min_distance": "minimum_peak_separation",
            "peaks": "peak_indices",
        },
        "bindings_b": {
            "mag": "magnitude_spectrum",
            "min_sep": "minimum_peak_separation",
            "found": "peak_indices",
        },
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "naive_vs_prominence_based",
        "body_a": """
def find_peaks_simple(spectrum):
    peaks = []
    for i in range(1, len(spectrum) - 1):
        if spectrum[i] > spectrum[i - 1] and spectrum[i] > spectrum[i + 1]:
            peaks.append(i)
    return peaks
""",
        "body_b": """
def find_peaks_prominence(spectrum, min_prominence):
    peaks = []
    for i in range(1, len(spectrum) - 1):
        if spectrum[i] > spectrum[i - 1] and spectrum[i] > spectrum[i + 1]:
            left_min = min(spectrum[max(0, i - 10):i])
            right_min = min(spectrum[i + 1:min(len(spectrum), i + 11)])
            prominence = spectrum[i] - max(left_min, right_min)
            if prominence >= min_prominence:
                peaks.append(i)
    return peaks
""",
        "bindings_a": {
            "spectrum": "magnitude_spectrum",
            "peaks": "peak_indices",
        },
        "bindings_b": {
            "spectrum": "magnitude_spectrum",
            "min_prominence": "prominence_threshold",
            "peaks": "peak_indices",
            "left_min": "left_valley",
            "right_min": "right_valley",
            "prominence": "peak_prominence",
        },
        "expected_equivalent": False,
        "expected_min_tier": 4,
        "known_values": {},
    },
    {
        "name": "threshold_sort_vs_threshold_scan",
        "body_a": """
def top_peaks_sorted(spectrum, threshold, n_peaks):
    candidates = []
    for i in range(1, len(spectrum) - 1):
        if spectrum[i] > spectrum[i - 1] and spectrum[i] > spectrum[i + 1]:
            if spectrum[i] >= threshold:
                candidates.append((spectrum[i], i))
    candidates.sort(reverse=True)
    return [idx for _, idx in candidates[:n_peaks]]
""",
        "body_b": """
def top_peaks_greedy(mag, thresh, max_peaks):
    result = []
    for k in range(1, len(mag) - 1):
        if mag[k] > mag[k - 1] and mag[k] > mag[k + 1]:
            if mag[k] >= thresh:
                result.append((mag[k], k))
                if len(result) >= max_peaks * 3:
                    break
    result.sort(reverse=True)
    return [pos for _, pos in result[:max_peaks]]
""",
        "bindings_a": {
            "spectrum": "magnitude_spectrum",
            "threshold": "amplitude_threshold",
            "n_peaks": "max_peak_count",
            "candidates": "peak_candidates",
        },
        "bindings_b": {
            "mag": "magnitude_spectrum",
            "thresh": "amplitude_threshold",
            "max_peaks": "max_peak_count",
            "result": "peak_candidates",
        },
        "expected_equivalent": False,
        "expected_min_tier": 4,
        "known_values": {},
    },
]
