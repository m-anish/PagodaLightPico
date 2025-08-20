"""
Sunrise/Sunset provider with JSON-backed data and weekly fallback.

- Reads sun_times.json if available. Expected flexible formats:
  1) Flat keys: "dd,mm->rise": "HH:MM", "dd,mm->set": "HH:MM"
  2) days map: { "days": { "dd-mm": {"rise": "HH:MM", "set": "HH:MM"}, ... } }
  3) List of entries: [ {"dd": 1, "mm": 1, "rise": "07:12", "set": "17:42"}, ... ]

- get_sunrise_sunset(mm, dd) returns (rise_h, rise_m, set_h, set_m)
- If an exact day is missing, falls back to the last prior date available (weekly buckets supported).
- If JSON is missing or invalid, falls back to built-in Leh table (lib.sun_times_leh).
"""

import json

try:
    # MicroPython-compatible import fallback
    from lib import sun_times_leh as fallback_sun
except Exception:
    try:
        import sun_times_leh as fallback_sun  # type: ignore
    except Exception:
        fallback_sun = None  # ultimate fallback

_location = None
_lat = None
_lon = None
_entries = []  # list of tuples: (mm, dd, rise_h, rise_m, set_h, set_m)
_sorted_keys = []  # list of (mm, dd) sorted


def _parse_time_str(s):
    try:
        parts = s.strip().split(':')
        return int(parts[0]), int(parts[1])
    except Exception:
        return 0, 0


def _load_json():
    global _location, _lat, _lon, _entries, _sorted_keys
    _location = None
    _lat = None
    _lon = None
    _entries = []
    _sorted_keys = []

    filename = 'sun_times.json'  # relative; compatible with device root
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except Exception:
        return False

    # Capture meta if present
    if isinstance(data, dict):
        _location = data.get('location')
        _lat = data.get('lat')
        _lon = data.get('lon')

    # Detect format and normalize to entries
    try:
        if isinstance(data, dict) and 'days' in data and isinstance(data['days'], dict):
            # days map format: { "dd-mm": {"rise": "HH:MM", "set": "HH:MM"} }
            for key, val in data['days'].items():
                if not isinstance(val, dict):
                    continue
                ddmm = key.replace('/', '-').replace(',', '-').strip()
                parts = ddmm.split('-')
                if len(parts) != 2:
                    continue
                dd = int(parts[0])
                mm = int(parts[1])
                rh, rm = _parse_time_str(val.get('rise', '0:0'))
                sh, sm = _parse_time_str(val.get('set', '0:0'))
                _entries.append((mm, dd, rh, rm, sh, sm))

        elif isinstance(data, dict) and any('->rise' in k for k in data.keys() if isinstance(k, str)):
            # flat key format
            # Build intermediate map
            tmp = {}
            for k, v in data.items():
                if not isinstance(k, str):
                    continue
                if '->rise' in k or '->set' in k:
                    date_part = k.split('->')[0].strip()
                    parts = date_part.replace('/', ',').split(',')
                    if len(parts) != 2:
                        continue
                    dd = int(parts[0])
                    mm = int(parts[1])
                    entry = tmp.setdefault((mm, dd), {})
                    if 'rise' in k:
                        entry['rise'] = v
                    else:
                        entry['set'] = v
            for (mm, dd), val in tmp.items():
                rh, rm = _parse_time_str(val.get('rise', '0:0'))
                sh, sm = _parse_time_str(val.get('set', '0:0'))
                _entries.append((mm, dd, rh, rm, sh, sm))

        elif isinstance(data, dict) and 'entries' in data and isinstance(data['entries'], list):
            for e in data['entries']:
                mm = int(e.get('mm'))
                dd = int(e.get('dd'))
                rh, rm = _parse_time_str(e.get('rise', '0:0'))
                sh, sm = _parse_time_str(e.get('set', '0:0'))
                _entries.append((mm, dd, rh, rm, sh, sm))
        elif isinstance(data, list):
            for e in data:
                mm = int(e.get('mm'))
                dd = int(e.get('dd'))
                rh, rm = _parse_time_str(e.get('rise', '0:0'))
                sh, sm = _parse_time_str(e.get('set', '0:0'))
                _entries.append((mm, dd, rh, rm, sh, sm))
        else:
            # Unknown format
            return False

        # Sort keys
        _entries.sort(key=lambda t: (t[0], t[1]))
        _sorted_keys = [(mm, dd) for (mm, dd, _, _, _, _) in _entries]
        return len(_entries) > 0
    except Exception:
        return False


# Attempt to load data at import
_loaded = _load_json()


def get_location_info():
    """Return (location, lat, lon) if available, else (None, None, None)."""
    return _location, _lat, _lon


def get_sunrise_sunset(month, day):
    """
    Get sunrise/sunset for given date.
    Falls back to last available date not after (mm, dd). Wraps to last entry if none before.
    If JSON not loaded, use fallback table if available.
    Returns tuple: (rise_h, rise_m, set_h, set_m)
    """
    if _loaded and _entries:
        target = (int(month), int(day))
        # Binary-like search over sorted keys to find last <= target
        last_idx = -1
        for i, key in enumerate(_sorted_keys):
            if key[0] < target[0] or (key[0] == target[0] and key[1] <= target[1]):
                last_idx = i
            else:
                break
        if last_idx == -1:
            last_idx = len(_entries) - 1  # wrap to last available (previous year assumption)
        mm, dd, rh, rm, sh, sm = _entries[last_idx]
        return rh, rm, sh, sm

    # Fallback: static table
    if fallback_sun is not None:
        try:
            return fallback_sun.get_sunrise_sunset(month, day)
        except Exception:
            pass

    # Ultimate fallback
    return 7, 0, 18, 0