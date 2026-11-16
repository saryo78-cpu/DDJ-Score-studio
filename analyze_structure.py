import numpy as np
from scipy.signal import stft


def _safe_mean(arr, default=0.0):
    return float(np.mean(arr)) if len(arr) > 0 else float(default)


def analyze_pcm_structure(
    pcm_int16: bytes,
    sr: int = 11025,
    bpm: float = 128.0,
    first_downbeat: float = 0.0,
    duration: float = 0.0,
    cue_secs=None,
):
    """
    Beat/bar-synchronous MIR structural analyzer using:
    1) 20-band log-magnitude STFT + spectral flux + kick-pulse features
    2) Cosine Self-Similarity Matrix (SSM) + Foote checkerboard novelty curve
    3) 1-bar step-jump boundary snapping + Drop-reference semantic labeling
    """
    samples = np.frombuffer(pcm_int16, dtype=np.int16).astype(np.float32) / 32768.0
    if duration <= 0:
        duration = len(samples) / float(sr)
    bar_sec = (60.0 / max(40.0, float(bpm))) * 4.0
    if len(samples) < int(sr * bar_sec * 4):
        return {"sections": [], "blocks": [], "engine": "py-mir-short"}

    # 1. STFT Spectrogram
    nperseg = 1024
    noverlap = 512
    freqs, times, Z = stft(samples, fs=sr, nperseg=nperseg, noverlap=noverlap, boundary=None)
    mag = np.abs(Z)  # shape: (F, T)
    log_mag = np.log1p(mag * 12.0)

    # 20 log-spaced frequency bands (30 Hz .. 5500 Hz)
    edges = np.geomspace(30.0, min(5500.0, sr * 0.49), 21)
    band_masks = []
    for b_idx in range(20):
        mask = (freqs >= edges[b_idx]) & (freqs < edges[b_idx + 1])
        if not np.any(mask):
            nearest = int(np.argmin(np.abs(freqs - 0.5 * (edges[b_idx] + edges[b_idx + 1]))))
            mask = np.zeros_like(freqs, dtype=bool)
            mask[nearest] = True
        band_masks.append(mask)

    band_spec = np.vstack([np.mean(log_mag[m], axis=0) for m in band_masks])  # (20, T)

    # Spectral flux (positive frame-to-frame onset energy)
    diff = np.maximum(0.0, np.diff(log_mag, axis=1, prepend=log_mag[:, :1]))
    flux_frames = np.mean(diff, axis=0)

    # Band RMS proxies
    low_mask = (freqs >= 25.0) & (freqs < 150.0)
    mid_mask = (freqs >= 280.0) & (freqs < 2800.0)
    high_mask = freqs >= 3000.0
    low_frames = np.sqrt(np.mean(mag[low_mask] ** 2, axis=0)) if np.any(low_mask) else np.zeros(len(times))
    mid_frames = np.sqrt(np.mean(mag[mid_mask] ** 2, axis=0)) if np.any(mid_mask) else np.zeros(len(times))
    high_frames = np.sqrt(np.mean(mag[high_mask] ** 2, axis=0)) if np.any(high_mask) else np.zeros(len(times))
    rms_frames = np.sqrt(np.mean(mag ** 2, axis=0))

    # 2. Aggregate onto 1-bar grid starting at first_downbeat
    beat_sec = bar_sec / 4.0
    bar_vecs = []
    blocks = []
    t_cur = float(first_downbeat)
    bar_idx = 1
    while t_cur + 0.4 * bar_sec < duration:
        t_end = min(duration, t_cur + bar_sec)
        f_mask = (times >= t_cur) & (times < t_end)
        if np.any(f_mask):
            vec = np.mean(band_spec[:, f_mask], axis=1)
            low_v = _safe_mean(low_frames[f_mask])
            mid_v = _safe_mean(mid_frames[f_mask])
            high_v = _safe_mean(high_frames[f_mask])
            rms_v = _safe_mean(rms_frames[f_mask])
            flux_v = _safe_mean(flux_frames[f_mask])

            # Kick pulse: on-beat (phase < 0.30) vs off-beat (0.45..0.85) low energy
            t_sub = times[f_mask]
            phases = ((t_sub - first_downbeat) % beat_sec) / beat_sec
            on_m = phases < 0.30
            off_m = (phases >= 0.45) & (phases < 0.85)
            on_low = _safe_mean(low_frames[f_mask][on_m], low_v)
            off_low = _safe_mean(low_frames[f_mask][off_m], low_v)
            kick_pulse = float((on_low + 1e-5) / (off_low + 1e-5))
        else:
            vec = np.zeros(20, dtype=np.float32)
            low_v = mid_v = high_v = rms_v = flux_v = 0.0
            kick_pulse = 1.0

        bar_vecs.append(vec)
        blocks.append({
            "barIndex": bar_idx,
            "startSec": round(t_cur, 3),
            "lowRms": low_v,
            "midRms": mid_v,
            "highRms": high_v,
            "rms": rms_v,
            "flux": flux_v,
            "kickPulse": round(kick_pulse, 3),
        })
        t_cur += bar_sec
        bar_idx += 1

    n_bars = len(blocks)
    if n_bars < 8:
        return {"sections": [], "blocks": [], "engine": "py-mir-short"}

    # Normalize scalar band features (using 98th percentile to ignore single-frame clicks)
    max_low = max(1e-5, float(np.percentile([b["lowRms"] for b in blocks], 98)))
    max_mid = max(1e-5, float(np.percentile([b["midRms"] for b in blocks], 98)))
    max_high = max(1e-5, float(np.percentile([b["highRms"] for b in blocks], 98)))
    max_rms = max(1e-5, float(np.percentile([b["rms"] for b in blocks], 98)))
    max_flux = max(1e-5, float(np.percentile([b["flux"] for b in blocks], 98)))

    for b in blocks:
        b["low"] = round(min(1.0, b["lowRms"] / max_low), 3)
        b["mid"] = round(min(1.0, b["midRms"] / max_mid), 3)
        b["high"] = round(min(1.0, b["highRms"] / max_high), 3)
        b["energy"] = round(min(1.0, b["rms"] / max_rms), 3)
        b["fluxNorm"] = round(min(1.0, b["flux"] / max_flux), 3)

    # 2.5 Auto-detect Track Profile: HIGH_CONTRAST (プログレ/EDM型) vs STEADY_GROOVE (テック/ディープ/節目が弱い持続型)
    low_vals = [b["low"] for b in blocks]
    en_vals = [b["energy"] for b in blocks]
    low_contrast = float(np.percentile(low_vals, 90) - np.percentile(low_vals, 25))
    en_contrast = float(np.percentile(en_vals, 90) - np.percentile(en_vals, 25))
    is_steady_groove = (low_contrast < 0.34 and en_contrast < 0.30)
    track_profile = "STEADY_GROOVE" if is_steady_groove else "HIGH_CONTRAST"

    # 3. Cosine Self-Similarity Matrix + Foote Checkerboard Novelty Curve
    X = np.vstack(bar_vecs)  # (N, 20)
    norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-6
    X_norm = X / norms
    ssm = X_norm @ X_norm.T

    L = min(6, max(3, n_bars // 12))
    # Gaussian-tapered checkerboard kernel of size (2L, 2L)
    coords = np.arange(-L, L)
    g = np.exp(-0.5 * ((coords + 0.5) / (L * 0.5)) ** 2)
    g2d = np.outer(g, g)
    sign = np.ones((2 * L, 2 * L), dtype=np.float32)
    sign[:L, L:] = -1.0
    sign[L:, :L] = -1.0
    kernel = sign * g2d
    kernel /= (np.sum(np.abs(kernel)) + 1e-6)

    novelty = np.zeros(n_bars, dtype=np.float32)
    for i in range(L, n_bars - L):
        patch = ssm[i - L:i + L, i - L:i + L]
        ssm_nov = max(0.0, float(np.sum(patch * kernel)))
        p_low = np.mean([b["low"] for b in blocks[max(0, i - 4):i]])
        n_low = np.mean([b["low"] for b in blocks[i:min(n_bars, i + 4)]])
        p_en = np.mean([b["energy"] for b in blocks[max(0, i - 4):i]])
        n_en = np.mean([b["energy"] for b in blocks[i:min(n_bars, i + 4)]])
        p_hi = np.mean([b["high"] for b in blocks[max(0, i - 4):i]])
        n_hi = np.mean([b["high"] for b in blocks[i:min(n_bars, i + 4)]])
        if is_steady_groove:
            # 持続グルーヴ型: 音圧差ではなく、20バンド音色変化(SSM)＋高域レイヤー変化を重視
            novelty[i] = ssm_nov * 5.0 + abs(n_hi - p_hi) * 1.4 + abs(n_low - p_low) * 0.5 + abs(n_en - p_en) * 0.5
        else:
            # メリハリ型(プログレ/EDM): 低音・音圧の段差＋SSMをバランスよく重視
            novelty[i] = ssm_nov * 3.5 + abs(n_low - p_low) * 1.1 + abs(n_en - p_en) * 0.9

    # Rekordbox cue anchors
    cue_bars = set()
    if cue_secs:
        for cs in cue_secs:
            if cs > first_downbeat + bar_sec:
                c_bar = int(round((cs - first_downbeat) / bar_sec)) + 1
                if 1 < c_bar <= n_bars:
                    cue_bars.add(c_bar)

    # Pick novelty peaks (min spacing 8 bars) + snap ±2 bars to sharpest 1-bar jump
    if is_steady_groove:
        nov_thresh = max(0.20, float(np.percentile(novelty[L:n_bars - L], 55))) if n_bars > 2 * L + 2 else 0.20
    else:
        nov_thresh = max(0.28, float(np.percentile(novelty[L:n_bars - L], 65))) if n_bars > 2 * L + 2 else 0.28
    peaks = []
    for i in range(4, n_bars - 4):
        is_peak = (
            novelty[i] >= nov_thresh
            and novelty[i] >= novelty[i - 1]
            and novelty[i] >= novelty[i + 1]
            and novelty[i] >= novelty[i - 2]
            and novelty[i] >= novelty[i + 2]
        )
        if is_peak or blocks[i]["barIndex"] in cue_bars:
            peaks.append((i, 9.9 if blocks[i]["barIndex"] in cue_bars else float(novelty[i])))

    peaks.sort(key=lambda x: x[1], reverse=True)
    boundaries = [0]
    for idx, _ in peaks:
        if all(abs(b - idx) >= 8 for b in boundaries) and idx <= n_bars - 4:
            best_k = idx
            best_jump = -1.0
            for k in range(max(4, idx - 2), min(n_bars - 3, idx + 3)):
                spec_jump = float(1.0 - np.dot(X_norm[k], X_norm[k - 1]))
                lvl_jump = abs(blocks[k]["low"] - blocks[k - 1]["low"]) * 1.4 + abs(blocks[k]["energy"] - blocks[k - 1]["energy"]) * 1.2
                hi_jump = abs(blocks[k]["high"] - blocks[k - 1]["high"]) * 1.1
                phrase_bonus = 0.08 if (is_steady_groove and (blocks[k]["barIndex"] - 1) % 8 == 0) else 0.0
                j_score = (spec_jump * 2.5 + hi_jump + phrase_bonus) if is_steady_groove else (spec_jump * 2.0 + lvl_jump)
                if j_score > best_jump:
                    best_jump = j_score
                    best_k = k
            boundaries.append(best_k)
    boundaries.sort()

    # 4. Compute Drop Reference (top 20% 8-bar windows)
    win8 = []
    for i in range(0, max(1, n_bars - 7), 2):
        sl = blocks[i:i + 8]
        m_low = _safe_mean([b["low"] for b in sl])
        m_en = _safe_mean([b["energy"] for b in sl])
        m_hi = _safe_mean([b["high"] for b in sl])
        m_fl = _safe_mean([b["fluxNorm"] for b in sl])
        m_kp = _safe_mean([b["kickPulse"] for b in sl])
        if m_kp >= 1.05:
            if is_steady_groove:
                sc = 0.35 * m_low + 0.25 * m_en + 0.25 * m_hi + 0.15 * m_fl
            else:
                sc = 0.45 * m_low + 0.35 * m_en + 0.20 * m_fl
            win8.append((sc, m_low, m_en, m_hi, i))
    win8.sort(key=lambda x: x[0], reverse=True)
    top_w = win8[:max(1, int(np.ceil(len(win8) * 0.20)))]
    ref_drop_low = _safe_mean([w[1] for w in top_w], 0.72)
    ref_drop_en = _safe_mean([w[2] for w in top_w], 0.72)
    ref_drop_hi = _safe_mean([w[3] for w in top_w], 0.65)
    ref_vec = np.mean(X_norm[top_w[0][4]:top_w[0][4] + 8], axis=0) if top_w else np.mean(X_norm, axis=0)
    ref_vec /= (np.linalg.norm(ref_vec) + 1e-6)

    # 5. Classify each segment
    for s_idx in range(len(boundaries)):
        st = boundaries[s_idx]
        en = boundaries[s_idx + 1] if s_idx + 1 < len(boundaries) else n_bars
        sl = blocks[st:en]
        if not sl:
            continue
        m_low = _safe_mean([b["low"] for b in sl])
        m_mid = _safe_mean([b["mid"] for b in sl])
        m_hi = _safe_mean([b["high"] for b in sl])
        m_en = _safe_mean([b["energy"] for b in sl])
        m_kp = _safe_mean([b["kickPulse"] for b in sl])
        seg_vec = np.mean(X_norm[st:en], axis=0)
        seg_vec /= (np.linalg.norm(seg_vec) + 1e-6)
        timbre_sim = float(np.dot(seg_vec, ref_vec))
        ratio = sl[0]["startSec"] / max(1.0, duration)

        if is_steady_groove:
            # 持続グルーヴ型: 曲全体がDROPにならないよう、高域＋低域＋音圧が揃うピーク層だけをDROPとし、他をGROOVEに分離
            is_drop = (
                ratio < 0.94
                and m_low >= ref_drop_low * 0.88
                and m_en >= ref_drop_en * 0.88
                and m_hi >= ref_drop_hi * 0.84
            )
            is_break = (m_low < ref_drop_low * 0.65 and m_en < ref_drop_en * 0.82)
        else:
            is_drop = (
                ratio < 0.94
                and m_low >= ref_drop_low * 0.82
                and m_en >= ref_drop_en * 0.82
                and (m_kp >= 1.07 or (timbre_sim >= 0.90 and m_low >= ref_drop_low * 0.88))
            )
            is_break = (m_low < ref_drop_low * 0.56 and m_en < ref_drop_en * 0.78)

        if is_drop:
            seg_type = "DROP"
        elif is_break:
            seg_type = "VOCAL" if (m_mid >= m_low * 1.25 and m_mid >= 0.36) else "BREAK"
        elif ratio >= 0.76:
            seg_type = "OUTRO"
        elif ratio < 0.22 and sl[0]["barIndex"] <= 17:
            seg_type = "INTRO"
        else:
            seg_type = "GROOVE"

        for b in sl:
            b["type"] = seg_type

    # Post-pass: trailing GROOVE/BREAK after final DROP -> OUTRO
    drop_indices = [i for i, b in enumerate(blocks) if b["type"] == "DROP"]
    if drop_indices:
        last_drop = drop_indices[-1]
        for i in range(last_drop + 1, n_bars):
            if (blocks[i]["startSec"] / max(1.0, duration)) >= 0.74 and blocks[i]["type"] in ("GROOVE", "BREAK"):
                blocks[i]["type"] = "OUTRO"

    # Carve out 4-bar rising BUILD right before DROP
    for i in range(4, n_bars):
        if blocks[i]["type"] == "DROP" and blocks[i - 1]["type"] not in ("DROP", "OUTRO"):
            pre_en = _safe_mean([b["energy"] for b in blocks[i - 4:i]])
            if pre_en < blocks[i]["energy"] * 0.95 and blocks[i - 4]["barIndex"] > 4:
                for j in range(i - 4, i):
                    blocks[j]["type"] = "BUILD"

    # Build merged sections (respecting Rekordbox Cue boundaries)
    sections = []
    drop_counter = 0
    for b in blocks:
        last = sections[-1] if sections else None
        is_cue = b["barIndex"] in cue_bars
        if last and last["type"] == b["type"] and not is_cue:
            last["endBar"] = b["barIndex"]
            last["blockCount"] += 1
            last["sumLow"] += b["low"]
            last["sumMid"] += b["mid"]
            last["sumHigh"] += b["high"]
            last["sumKick"] += b["kickPulse"]
            c = last["blockCount"]
            last["avgLow"] = round(last["sumLow"] / c, 3)
            last["avgMid"] = round(last["sumMid"] / c, 3)
            last["avgHigh"] = round(last["sumHigh"] / c, 3)
            last["avgKick"] = round(last["sumKick"] / c, 3)
        else:
            if b["type"] == "DROP":
                drop_counter += 1
            sections.append({
                "type": b["type"],
                "dropIndex": drop_counter if b["type"] == "DROP" else None,
                "startBar": b["barIndex"],
                "endBar": b["barIndex"],
                "startSec": b["startSec"],
                "blockCount": 1,
                "sumLow": b["low"],
                "sumMid": b["mid"],
                "sumHigh": b["high"],
                "sumKick": b["kickPulse"],
                "avgLow": b["low"],
                "avgMid": b["mid"],
                "avgHigh": b["high"],
                "avgKick": b["kickPulse"],
            })

    return {"sections": sections, "blocks": blocks, "engine": "py-mir-ssm", "profile": track_profile}
