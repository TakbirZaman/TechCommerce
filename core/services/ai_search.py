"""
AI Product Search - local natural-language query parser + searcher.

Pure Python stdlib + SQLAlchemy. No external APIs, no ML runtime.

Pipeline:
    1. parse_query(q)          -> structured interpretation (no DB needed)
    2. get_known_brands(db)    -> brand vocabulary from the Brand table + aliases
    3. search_products(db, ..) -> hard-filter (with graceful relaxation),
                                  soft-score, return ranked products
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import and_, exists, func, or_
from sqlalchemy.orm import joinedload

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

MULTIPLIERS = {
    "k": 1_000,
    "thousand": 1_000,
    "hazar": 1_000,
    "hajar": 1_000,
    "lakh": 100_000,
    "lac": 100_000,
    "crore": 10_000_000,
    "koti": 10_000_000,
}

# Brands detected even when the Brand table is empty / not provided.
DEFAULT_BRANDS = [
    "asus", "msi", "gigabyte", "acer", "lenovo", "dell", "hp", "apple",
    "samsung", "lg", "razer", "logitech", "corsair", "nzxt", "deepcool",
    "cooler master", "thermaltake", "xiaomi", "redmi", "realme", "oppo",
    "vivo", "oneplus", "infinix", "walton", "kingston", "crucial", "adata",
    "seagate", "western digital", "wd", "intel", "amd", "nvidia", "gskill",
    "teamgroup", "nzxt", "symphony", "tcl", "hisense", "bitmain",
]
DEFAULT_BRANDS = sorted({b.lower() for b in DEFAULT_BRANDS}, key=len, reverse=True)

# alias -> canonical brand token we search for
BRAND_ALIASES = {
    "hewlett-packard": "hp",
    "hewlett packard": "hp",
    "geforce": "nvidia",
    "radeon": "amd",
    "macbook": "apple",
    "western digital": "wd",
    "cooler-master": "cooler master",
    "g skill": "gskill",
    "g-skill": "gskill",
}

USE_CASES = {
    "gaming": [r"\bgaming\b", r"\bgamer\b", r"\besports\b", r"\bfps\b",
               r"\bvalorant\b", r"\bpubg\b", r"\bcsgo\b", r"\bdota\b"],
    "office": [r"\boffice\b", r"\bwork\b(?!station)", r"\bbusiness\b",
               r"\bproductivity\b", r"\bmeetings?\b", r"\bexcel\b"],
    "student": [r"\bstudent\b", r"\bstudy\b", r"\bcollege\b",
                r"\buniversity\b", r"\bschool\b", r"\bclass\b"],
    "content_creation": [r"\bcontent\s*creation\b", r"\bediting\b",
                         r"\bvideo\s*edit\b", r"\bphoto\s*edit\b",
                         r"\bstreaming\b", r"\bstreamer\b", r"\brendering\b",
                         r"\byoutube\b", r"\bpremiere\b", r"\bdavinci\b",
                         r"\bphotoshop\b", r"\bdesigner\b"],
    "home": [r"\bhome\b", r"\bfamily\b", r"\bbrowsing\b", r"\bmedia\b",
             r"\bnetflix\b"],
    "server_workstation": [r"\bserver\b", r"\bworkstation\b",
                           r"\bprogramming\b", r"\bdeveloper\b",
                           r"\bmachine\s*learning\b", r"\bvirtuali[sz]ation\b",
                           r"\bcompil\w*\b", r"\bvm\b"],
    "budget": [r"\bbudget\b", r"\bcheap\b", r"\bcheapest\b",
               r"\baffordable\b", r"\blow\s*price\b", r"\bvalue\b"],
}

# label -> candidate category slugs (resolved against the DB at search time)
CATEGORIES = {
    "laptop": ["laptop", "laptops", "notebook", "notebooks"],
    "phone": ["phone", "smartphone", "mobile", "mobiles"],
    "monitor": ["monitor", "monitors", "display"],
    "gpu": ["gpu", "graphics-card", "graphics-cards", "video-card"],
    "cpu": ["cpu", "processor", "processors"],
    "ram": ["ram", "memory"],
    "storage": ["storage", "ssd", "hdd", "hard-drive", "hard-drives", "nvme"],
    "motherboard": ["motherboard", "motherboards", "mobo"],
    "psu": ["psu", "power-supply", "power-supplies"],
    "case": ["case", "pc-case", "casing", "chassis"],
    "keyboard": ["keyboard", "keyboards"],
    "mouse": ["mouse", "mice"],
    "headset": ["headset", "headphone", "headphones", "earbuds", "earphone"],
    "tablet": ["tablet", "tablets", "ipad"],
    "accessory": ["accessory", "accessories"],
}

# Category patterns; longest / most specific first where it matters.
CATEGORY_PATTERNS = [
    ("laptop", r"\b(?:laptops?|notebooks?|macbook)\b"),
    ("phone", r"\b(?:phones?|smartphones?|mobiles?)\b"),
    ("monitor", r"\b(?:monitors?|displays?)\b"),
    ("gpu", r"\b(?:gpus?|graphics\s*cards?|video\s*cards?|graphics)\b"),
    ("cpu", r"\b(?:cpus?|processors?)\b"),
    ("ram", r"\b(?:ram|memory)\b"),
    ("storage", r"\b(?:ssds?|hdds?|nvme|hard\s*drives?|hard\s*disks?|storage)\b"),
    ("motherboard", r"\b(?:motherboards?|mobo)\b"),
    ("psu", r"\b(?:psu|power\s*suppl\w+)\b"),
    ("case", r"\b(?:pc\s*cases?|cases?|casing|chassis)\b"),
    ("keyboard", r"\bkeyboards?\b"),
    ("mouse", r"\bm(?:ouse|ice)\b"),
    ("headset", r"\b(?:headsets?|headphones?|earbuds?|earphones?)\b"),
    ("tablet", r"\b(?:tablets?|ipads?)\b"),
    ("accessory", r"\baccessor(?:y|ies)\b"),
]

# Spec patterns. Each entry: (compiled regex, spec_key builder fn)
_NUM = r"(\d+(?:\.\d+)?)"

def _gpu_val(m: re.Match) -> str:
    val = f"{m.group(1)} {m.group(2)}"
    if m.group(3):
        val += m.group(3)
    return val.lower()

def _storage_val(m: re.Match) -> float:
    val = float(m.group(1))
    if m.group(2).lower() == "tb":
        val *= 1024
    return val

SPEC_PATTERNS = [
    # RAM: "16gb ram", "ram 16gb", "8 gb memory"
    (re.compile(rf"\b{_NUM}\s*gb\s*(?:ram|memory)\b"),
     lambda m: ("ram_gb", int(float(m.group(1))))),
    (re.compile(rf"\b(?:ram|memory)\s*(?:of\s*)?{_NUM}\s*gb\b"),
     lambda m: ("ram_gb", int(float(m.group(1))))),
    # Storage: "512gb ssd", "1tb hdd", "ssd 1tb"
    (re.compile(rf"\b{_NUM}\s*(tb|gb)\s*(?:ssd|hdd|nvme|storage|hard\s*drive|hard\s*disk)\b"),
     lambda m: ("storage_gb", _storage_val(m))),
    (re.compile(rf"\b(?:ssd|hdd|nvme)\s*(?:of\s*)?{_NUM}\s*(tb|gb)\b"),
     lambda m: ("storage_gb", _storage_val(m))),
    # GPU: "rtx 4070", "gtx 1660 super", "rx 7800xt"
    (re.compile(r"\b(rtx|gtx|rx)\s*(\d{3,4})\s*(ti|xt|xtx|super|oc)?\b"),
     lambda m: ("gpu", _gpu_val(m))),
    # CPU: "ryzen 7", "core i7", "i5"
    (re.compile(r"\bryzen\s*(3|5|7|9)\b"),
     lambda m: ("cpu", f"ryzen {m.group(1)}")),
    (re.compile(r"\b(?:intel\s*)?core\s*i([3579])\b"),
     lambda m: ("cpu", f"i{m.group(1)}")),
    (re.compile(r"\bi([3579])\b(?!\d)"),
     lambda m: ("cpu", f"i{m.group(1)}")),
    # Refresh rate: "144hz"
    (re.compile(rf"\b(\d{{2,3}})\s*hz\b"),
     lambda m: ("refresh_hz", int(m.group(1)))),
    # Screen size: "27 inch", '27"', "27in"
    (re.compile(rf"\b(\d{{2}}(?:\.\d+)?)\s*(?:inch(?:es)?|in|\u2033|\")\b"),
     lambda m: ("size_inch", float(m.group(1)))),
    # Panel type: "oled", "qled", "ips"
    (re.compile(r"\b(oled|qled|ips)\b"),
     lambda m: ("panel", m.group(1))),
    # Battery: "8 hours battery", "battery 10 hours"
    (re.compile(rf"\b(\d{{1,2}})\s*(?:hours?|hrs?)\s*(?:of\s*)?battery\b"),
     lambda m: ("battery_hours", int(m.group(1)))),
    (re.compile(rf"\bbattery\s*(?:life\s*)?(?:of\s*)?(\d{{1,2}})\s*(?:hours?|hrs?)\b"),
     lambda m: ("battery_hours", int(m.group(1)))),
]

# Which DB spec_key column names to try for each parsed spec key.
# Candidate lists include the real scraped keys found in the DB
# (verified against product_specifications) so recall is not silently
# killed by key-name drift.
SPEC_DB_KEYS = {
    "ram_gb": ["ram_gb", "memory_gb", "ram", "memory"],
    "storage_gb": ["storage_gb", "capacity_gb", "ssd", "capacity",
                    "capacity_gb_tb", "storage", "disk_gb"],
    "gpu": ["gpu", "gpu_graphics", "graphics", "graphics_card", "video_card"],
    "cpu": ["cpu", "processor", "processor_type"],
    "refresh_hz": ["refresh_hz", "refresh_rate_hz", "refresh_rate", "refresh"],
    "size_inch": ["screen_size", "size_inch", "screen_size_inch",
                   "display_size", "display_size_inch"],
    "panel": ["panel", "panel_type", "display_type"],
    "battery_hours": ["battery_hours", "battery_life", "battery"],
}
NUMERIC_SPEC_KEYS = {"ram_gb", "storage_gb", "refresh_hz", "size_inch", "battery_hours"}

# Unit family for each real DB spec_key. Values sharing a family are
# directly comparable after unit conversion ("1 TB" -> 1024 for size_gb).
# Conversion is NEVER done across incompatible families.
DB_SPEC_KEY_UNIT_FAMILY = {
    # capacity / memory size -> GB
    "ram_gb": "size_gb", "memory_gb": "size_gb", "ram": "size_gb",
    "memory": "size_gb", "storage_gb": "size_gb", "capacity_gb": "size_gb",
    "ssd": "size_gb", "capacity": "size_gb", "capacity_gb_tb": "size_gb",
    "storage": "size_gb", "disk_gb": "size_gb", "hdd": "size_gb",
    # frequency -> Hz
    "refresh_hz": "freq_hz", "refresh_rate_hz": "freq_hz",
    "refresh_rate": "freq_hz", "refresh": "freq_hz",
    # screen size -> inches
    "screen_size": "inch", "size_inch": "inch", "screen_size_inch": "inch",
    "display_size": "inch", "display_size_inch": "inch",
    # battery runtime -> hours
    "battery_hours": "hours", "battery_life": "hours", "battery": "hours",
}
UNIT_FAMILIES = {
    "tb": "size_gb", "gb": "size_gb", "mb": "size_gb",
    "hz": "freq_hz",
    "inch": "inch", "inches": "inch", "in": "inch", "\u2033": "inch", '"': "inch",
    "hour": "hours", "hours": "hours", "hr": "hours", "hrs": "hours", "h": "hours",
}

# Text-prefix units per parsed spec key, used as a LIKE fallback when a
# numeric spec is stored with numeric_value IS NULL ("144Hz", "8GB ...").
NUMERIC_TEXT_PREFIX_UNITS = {
    "ram_gb": ["GB"],
    "storage_gb": ["GB", "TB"],
    "refresh_hz": ["HZ"],
    "size_inch": ["INCH", "IN", '"'],
    "battery_hours": ["HOUR", "HRS", "H"],
}

_LEADING_NUMBER_RE = re.compile(
    r"^\s*(?P<num>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>TB|GB|MB|HZ|INCHES|INCH|IN|\u2033|\"|HOURS|HRS|HR|H)?",
    re.IGNORECASE,
)


def _fmt_num(v: float) -> str:
    """Format a float without a trailing .0 for LIKE prefixes."""
    return str(int(v)) if float(v) == int(v) else str(v)


def parse_spec_number(spec_key: str | None, value: Any) -> float | None:
    """
    Best-effort numeric extraction from a spec value string, unit- and
    key-aware. Returns None when the key has no known unit family, the
    value does not start with a number, or the unit is incompatible with
    the key's family (never converts across units).

    Examples: ("refresh_rate_hz", "100Hz") -> 100.0;
              ("ram", "8GB LPDDR5-5500")  -> 8.0;
              ("ssd", "1 TB")             -> 1024.0;
              ("battery", "6000mAh")      -> None (incompatible trailing unit).
    """
    if value is None:
        return None
    family = DB_SPEC_KEY_UNIT_FAMILY.get((spec_key or "").lower())
    if family is None:
        return None
    m = _LEADING_NUMBER_RE.match(str(value))
    if not m:
        return None
    num = float(m.group("num"))
    unit = (m.group("unit") or "").lower()
    if unit:
        if UNIT_FAMILIES.get(unit) != family:
            return None  # incompatible units - do not convert across
        if family == "size_gb":
            if unit == "tb":
                num *= 1024
            elif unit == "mb":
                num /= 1024
        return num
    # No unit: only trust a bare number when the remainder does not start
    # with a letter (rejects "6000mAh" -> hours, "10-core" -> GB, etc.)
    rest = str(value)[m.end():].lstrip()
    if rest and rest[0].isalpha():
        return None
    return num


def _numeric_text_prefixes(key: str, val: Any) -> list[str]:
    """LIKE prefixes matching a numeric spec stored as text, e.g. for
    (ram_gb, 8): "8GB..." and "8 GB...". The unit token must follow the
    number directly so 8 never matches "80mm"."""
    units = NUMERIC_TEXT_PREFIX_UNITS.get(key)
    if not units:
        return []
    try:
        v = float(val)
    except (TypeError, ValueError):
        return []
    variants = [(_fmt_num(v), units)]
    # "1 TB" text values for a 1024 GB parsed storage query
    if key == "storage_gb" and v >= 1024 and v % 1024 == 0:
        variants.append((_fmt_num(v / 1024), ["TB"]))
    prefixes: list[str] = []
    for num, us in variants:
        for u in us:
            prefixes.extend([f"{num} {u}%", f"{num}{u}%", f"{num}-{u}%"])
    return prefixes

STOPWORDS = {
    "with", "for", "under", "over", "below", "above", "around", "about",
    "best", "good", "need", "want", "buy", "price", "bdt", "taka", "tk",
    "and", "the", "any", "get", "give", "show", "find", "looking", "some",
    "from", "that", "have", "has", "can", "should", "will", "would", "new",
    "please", "suggest", "recommend", "between", "than", "less", "more",
    "max", "minimum", "approx", "approximately", "budget",
    "cheap",
    # 'gaming' is a deliberate stopword: the use-case detector consumes it,
    # so product names containing "Gaming" earn NO keyword boost by design
    # (almost every gaming SKU would otherwise drown out other signals).
    "gaming",
}

TOKEN = rf"৳?\s*{_NUM}\s*(lakh|lac|crore|koti|k|thousand|hazar|hajar)?"

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _token_value(num: str, unit: str | None) -> float:
    val = float(num)
    if unit:
        val *= MULTIPLIERS[unit.lower()]
    return val


def _blank_spans(text: str, spans: list[tuple[int, int]]) -> str:
    out = list(text)
    for start, end in spans:
        for i in range(start, min(end, len(out))):
            if out[i] != " ":
                out[i] = " "
    return "".join(out)


def _parse_specs(text: str) -> tuple[dict[str, Any], list[tuple[int, int]]]:
    """Extract structured specs; returns (specs, consumed_spans)."""
    specs: dict[str, Any] = {}
    spans: list[tuple[int, int]] = []
    for regex, builder in SPEC_PATTERNS:
        for m in regex.finditer(text):
            # skip overlapping spans already consumed
            if any(s <= m.start() and m.end() <= e for s, e in spans):
                continue
            key, val = builder(m)
            specs.setdefault(key, val)
            spans.append((m.start(), m.end()))
    return specs, spans


def _parse_budget(text: str, specs_spans: list[tuple[int, int]],
                  notes: list[str]) -> tuple[float | None, float | None]:
    """Parse BDT budget shorthand. Spec spans are blanked first so '144hz'
    or 'rtx 4060' never leak into budget parsing."""
    work = _blank_spans(text, specs_spans)

    budget_min: float | None = None
    budget_max: float | None = None

    # explicit range: "between 50k and 80k"
    m = re.search(rf"between\s+{TOKEN}\s*(?:and|&|to)\s*{TOKEN}", work)
    if m:
        budget_min = _token_value(*m.group(1, 2))
        budget_max = _token_value(*m.group(3, 4))
        return _norm_range(budget_min, budget_max, notes, "between X and Y")

    # bare range: "50-80k", "50k-80k", "50 to 80k" (first token may inherit unit)
    m = re.search(rf"{TOKEN}\s*(?:-|\u2013|\u2014|to)\s*{TOKEN}", work)
    if m:
        lo_num, lo_unit = m.group(1), m.group(2)
        hi_num, hi_unit = m.group(3), m.group(4)
        if not lo_unit and hi_unit:
            lo_unit = hi_unit
        budget_min = _token_value(lo_num, lo_unit)
        budget_max = _token_value(hi_num, hi_unit)
        return _norm_range(budget_min, budget_max, notes, "range")

    # upper bound: "under 100k", "below 1 lakh"
    m = re.search(
        rf"\b(?:under|below|less\s+than|up\s+to|within|cheaper\s+than|"
        rf"not\s+more\s+than|max(?:imum)?(?:\s+of)?|budget(?:\s+of)?)\s+{TOKEN}", work)
    if m:
        budget_max = _token_value(*m.group(1, 2))
        notes.append("budget upper bound detected")
        return budget_min, budget_max

    # lower bound: "over 50k", "above 1 lakh"
    m = re.search(
        rf"\b(?:over|above|more\s+than|min(?:imum)?(?:\s+of)?|at\s+least|"
        rf"starting\s+from|from)\s+{TOKEN}", work)
    if m:
        budget_min = _token_value(*m.group(1, 2))
        notes.append("budget lower bound detected")
        return budget_min, budget_max

    # approximate: "around 150000", "about 1.5 lakh"
    m = re.search(rf"\b(?:around|about|approx(?:imately)?|~|\u2248)\s*{TOKEN}", work)
    if m:
        center = _token_value(*m.group(1, 2))
        return center * 0.9, center * 1.1

    # currency-marked bare amount: "৳120k", "100k taka" -> treat as max
    m = re.search(rf"(?:\u09f3|tk|taka|bdt)\s*{TOKEN}", work)
    if not m:
        m = re.search(rf"{TOKEN}\s*(?:tk|taka|bdt)\b", work)
    if m:
        budget_max = _token_value(*m.group(1, 2))
        notes.append("currency-marked amount treated as budget max")
        return budget_min, budget_max

    # bare amount: "gaming laptop 100k" -> assume max, only for large values
    for m in re.finditer(TOKEN, work):
        v = _token_value(*m.group(1, 2))
        if v >= 5000:
            budget_max = v
            notes.append("bare amount assumed to be budget max")
            return budget_min, budget_max

    return budget_min, budget_max


def _norm_range(lo: float, hi: float, notes: list[str], label: str):
    if lo > hi:
        lo, hi = hi, lo
    notes.append(f"budget {label} detected")
    return lo, hi


def _detect_use_case(text: str, notes: list[str]) -> str | None:
    for use_case, patterns in USE_CASES.items():
        for pat in patterns:
            if re.search(pat, text):
                notes.append(f"use case inferred: {use_case}")
                return use_case
    return None


def _detect_category(text: str, notes: list[str]) -> tuple[str | None, list[str]]:
    for label, pattern in CATEGORY_PATTERNS:
        m = re.search(pattern, text)
        if m:
            candidates = CATEGORIES[label]
            notes.append(f"category intent detected: {label}")
            return candidates[0], candidates
    return None, []


def _detect_brands(text: str, known_brands: list[str] | None,
                   notes: list[str]) -> list[str]:
    vocabulary = set(known_brands or []) | set(DEFAULT_BRANDS) | set(BRAND_ALIASES)
    vocabulary = {v.lower() for v in vocabulary if v}
    found: set[str] = set()
    for brand in sorted(vocabulary, key=len, reverse=True):
        if re.search(rf"\b{re.escape(brand)}\b", text):
            canonical = BRAND_ALIASES.get(brand, brand)
            found.add(canonical)
    if found:
        notes.append(f"brands matched: {', '.join(sorted(found))}")
    return sorted(found)


def parse_query(q: str, known_brands: list[str] | None = None) -> dict[str, Any]:
    """
    Parse a natural-language shopping query into a structured interpretation:
    {
        budget_min, budget_max, use_case, category (slug),
        brands (list of slugs), specs ({key: value}),
        keywords (leftover significant words), notes (list of str)
    }
    """
    text = (q or "").lower().replace(",", "")
    notes: list[str] = []

    specs, spec_spans = _parse_specs(text)
    if specs:
        notes.append("specs detected: " + ", ".join(f"{k}={v}" for k, v in specs.items()))

    budget_min, budget_max = _parse_budget(text, spec_spans, notes)
    use_case = _detect_use_case(text, notes)
    category, category_candidates = _detect_category(text, notes)
    brands = _detect_brands(text, known_brands, notes)

    # leftover keywords: blank everything we consumed, then keep significant words
    consumed = list(spec_spans)
    for m in re.finditer(TOKEN, text):
        consumed.append((m.start(), m.end()))
    remaining = _blank_spans(text, consumed)
    keywords = [
        w for w in re.findall(r"[a-z0-9][a-z0-9\-\+\.]*", remaining)
        if len(w) > 2 and w not in STOPWORDS
        and w not in brands
        and not any(re.fullmatch(rf"{re.escape(w)}", c) for c in
                    [s for cands in CATEGORIES.values() for s in cands])
    ]

    return {
        "budget_min": budget_min,
        "budget_max": budget_max,
        "use_case": use_case,
        "category": category,
        "category_candidates": category_candidates if category else [],
        "brands": brands,
        "specs": specs,
        "keywords": keywords,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Brand vocabulary from DB
# ---------------------------------------------------------------------------

def get_known_brands(session) -> list[str]:
    """Load brand names from the Brand table (lowercase) + alias tokens."""
    try:
        from core.models.catalog import Brand
        names = [b.name.lower() for b in session.query(Brand).all() if b.name]
    except Exception:
        names = []
    vocab = set(names) | set(BRAND_ALIASES.keys())
    return sorted({v.lower() for v in vocab if v}, key=len, reverse=True)


def interpret(session, q: str) -> dict[str, Any]:
    """parse_query seeded with brand vocabulary from the DB."""
    return parse_query(q, known_brands=get_known_brands(session))


# ---------------------------------------------------------------------------
# Search / scoring
# ---------------------------------------------------------------------------

# Relaxation order: least confident filters are dropped first.
RELAXATION_ORDER = ["spec_filters", "budget_min", "brands", "budget_max", "category"]


def _spec_condition(session, key: str, val: Any):
    """SQLAlchemy EXISTS condition matching a parsed spec against
    ProductSpecification rows (numeric_value for numeric specs, ILIKE for text).

    Numeric specs ALSO fall back to text matching when numeric_value IS NULL
    ("144Hz", "8GB LPDDR5..."): the number must be followed (optionally after
    one space / hyphen) by the key's unit token, so 8 never matches "80mm".
    """
    from core.models.specification import Product, ProductSpecification

    db_keys = SPEC_DB_KEYS.get(key, [key])
    if key in NUMERIC_SPEC_KEYS or isinstance(val, (int, float)):
        conds = [ProductSpecification.numeric_value == float(val)]
        for prefix in _numeric_text_prefixes(key, val):
            conds.append(and_(
                ProductSpecification.numeric_value.is_(None),
                ProductSpecification.value.like(prefix),
            ))
        sub = (
            session.query(ProductSpecification.id)
            .filter(
                ProductSpecification.product_id == Product.id,
                ProductSpecification.spec_key.in_(db_keys),
                or_(*conds),
            )
            .exists()
        )
    else:
        sub = (
            session.query(ProductSpecification.id)
            .filter(
                ProductSpecification.product_id == Product.id,
                ProductSpecification.spec_key.in_(db_keys),
                ProductSpecification.value.ilike(f"%{val}%"),
            )
            .exists()
        )
    return sub


def _product_matches_spec(specs_by_key: dict[str, Any], name_lower: str,
                          key: str, val: Any) -> bool:
    """Python-side spec check used for matched_on + soft scoring."""
    db_keys = SPEC_DB_KEYS.get(key, [key])
    for db_key in db_keys:
        spec = specs_by_key.get(db_key)
        if spec is None:
            continue
        if key in NUMERIC_SPEC_KEYS or isinstance(val, (int, float)):
            if spec.numeric_value is not None and float(spec.numeric_value) == float(val):
                return True
            # tolerate values stored only as text ("8GB LPDDR5-5500...",
            # "1 TB", "144Hz") via the shared unit-aware parser
            parsed = parse_spec_number(db_key, spec.value)
            if parsed is not None and abs(parsed - float(val)) < 1e-9:
                return True
        else:
            if str(val).lower() in str(spec.value).lower():
                return True
    # name fallback for string specs (gpu/cpu/panel often appear in the name)
    if key not in NUMERIC_SPEC_KEYS and str(val).lower() in name_lower:
        return True
    return False


def _norm_brand_token(s: str | None) -> str:
    """Normalize a brand token: lowercase, strip '-'/'_', collapse spaces,
    so 'cooler-master' and 'cooler master' compare equal."""
    return " ".join(re.sub(r"[-_]+", " ", (s or "").lower()).split())


def _resolve_category_ids(session, interpretation: dict) -> list[int]:
    from core.models.catalog import Category

    candidates = interpretation.get("category_candidates") or (
        [interpretation["category"]] if interpretation.get("category") else []
    )
    if not candidates:
        return []
    categories = session.query(Category).filter(Category.is_active == True).all()
    by_slug = {c.slug.lower(): c for c in categories}
    primary = next((c for slug in candidates if (c := by_slug.get(slug))), None)
    # fallback: name contains the primary slug keyword
    if primary is None:
        kw = candidates[0].split("-")[0]
        primary = next((c for c in categories if kw in c.name.lower()), None)
    if primary is None:
        return []
    ids = [primary.id]
    ids += [c.id for c in categories if c.parent_id == primary.id]
    return ids


def _score_product(product, interpretation: dict) -> tuple[float, list[str]]:
    score = 0.0
    matched: list[str] = []
    specs_by_key = {s.spec_key: s for s in product.specifications}
    name_lower = product.name.lower()

    # explicit spec matches
    for key, val in interpretation.get("specs", {}).items():
        if _product_matches_spec(specs_by_key, name_lower, key, val):
            score += 1.5
            matched.append(f"spec:{key}={val}")

    def num(key: str) -> float | None:
        spec = specs_by_key.get(key)
        return float(spec.numeric_value) if spec and spec.numeric_value is not None else None

    # use-case fit
    use_case = interpretation.get("use_case")
    price = product.price or 0.0
    budget_max = interpretation.get("budget_max")
    if use_case == "gaming":
        if specs_by_key.get("gpu") or "gpu" in interpretation.get("specs", {}):
            score += 2.0
            matched.append("use_case:gaming->gpu")
        if (num("refresh_hz") or 0) >= 120:
            score += 1.5
            matched.append("use_case:gaming->high_refresh")
        if specs_by_key.get("cpu"):
            score += 1.0
            matched.append("use_case:gaming->cpu")
    elif use_case == "content_creation":
        if (num("ram_gb") or 0) >= 16:
            score += 2.0
            matched.append("use_case:content->ram>=16")
        if specs_by_key.get("gpu"):
            score += 1.5
            matched.append("use_case:content->gpu")
        if (num("storage_gb") or 0) >= 512:
            score += 1.0
            matched.append("use_case:content->storage>=512")
    elif use_case == "student":
        if budget_max and price <= 0.7 * budget_max:
            score += 2.0
            matched.append("use_case:student->within_budget")
        if (num("battery_hours") or 0) >= 6:
            score += 1.5
            matched.append("use_case:student->battery>=6h")
        if price <= 60000:
            score += 1.0
            matched.append("use_case:student->affordable")
    elif use_case == "office":
        if budget_max and price <= 0.6 * budget_max:
            score += 2.0
            matched.append("use_case:office->within_budget")
        if (num("ram_gb") or 0) >= 8:
            score += 0.5
            matched.append("use_case:office->ram>=8")
    elif use_case == "server_workstation":
        if (num("ram_gb") or 0) >= 32:
            score += 2.0
            matched.append("use_case:workstation->ram>=32")
        if specs_by_key.get("cpu"):
            score += 1.5
            matched.append("use_case:workstation->cpu")
        if (num("storage_gb") or 0) >= 1000:
            score += 1.0
            matched.append("use_case:workstation->storage>=1tb")
    elif use_case == "home":
        if budget_max and price <= 0.7 * budget_max:
            score += 1.0
            matched.append("use_case:home->within_budget")
    elif use_case == "budget":
        if budget_max and price <= 0.7 * budget_max:
            score += 2.5
            matched.append("use_case:budget->well_under_budget")

    # closeness to budget center
    bmin, bmax = interpretation.get("budget_min"), interpretation.get("budget_max")
    if bmin is not None or bmax is not None:
        lo = bmin if bmin is not None else 0.0
        hi = bmax if bmax is not None else max(price, lo * 2, 1.0)
        center = (lo + hi) / 2 if bmin is not None and bmax is not None else (bmax or lo)
        if center > 0:
            closeness = 1 - min(abs(price - center) / center, 1.0)
            score += 2.0 * closeness
            matched.append("budget_closeness")

    # brand match bonus (both sides normalized: 'cooler-master' slug vs
    # parsed 'cooler master' token)
    if product.brand:
        wanted = {_norm_brand_token(b) for b in interpretation.get("brands", [])}
        if _norm_brand_token(product.brand.slug) in wanted:
            score += 1.0
            matched.append(f"brand:{product.brand.slug}")

    # keyword hits in the name
    for kw in interpretation.get("keywords", []):
        if kw in name_lower:
            score += 0.5
            matched.append(f"keyword:{kw}")

    # popularity (bounded contribution)
    pop = product.popularity_score or 0.0
    if pop > 0:
        score += 2.0 * min(pop / 100.0, 1.0)
        matched.append("popularity")

    return score, matched


def search_products(session, interpretation: dict | str, limit: int = 12) -> list[dict]:
    """
    Search + rank products for an interpretation (or a raw query string).

    Hard-filters where confident; if that yields 0 results, the least
    confident filters are relaxed one tier at a time (recorded in
    interpretation["notes"]) instead of returning empty.

    Returns a list of {"product": Product, "score": float, "matched_on": [...]}
    sorted by score desc, at most `limit` items.
    """
    from core.models.catalog import Brand, Category
    from core.models.specification import Product

    if isinstance(interpretation, str):
        interpretation = interpret(session, interpretation)
    notes = interpretation.setdefault("notes", [])

    category_ids = _resolve_category_ids(session, interpretation) \
        if interpretation.get("category") else []
    brands = interpretation.get("brands") or []
    # slug variants so a parsed 'cooler master' also matches slug 'cooler-master'
    brand_slug_variants = sorted({v for b in brands for v in (b, b.replace(" ", "-"))})

    tier_filters: dict[str, list] = {
        "spec_filters": [
            _spec_condition(session, k, v) for k, v in (interpretation.get("specs") or {}).items()
        ],
        "budget_min": (
            [Product.price >= interpretation["budget_min"]]
            if interpretation.get("budget_min") is not None else []
        ),
        "brands": (
            [or_(Brand.slug.in_(brand_slug_variants), func.lower(Brand.name).in_(brands))]
            if brands else []
        ),
        "budget_max": (
            [Product.price <= interpretation["budget_max"]]
            if interpretation.get("budget_max") is not None else []
        ),
        "category": (
            [Product.category_id.in_(category_ids)] if category_ids else []
        ),
    }

    active_tiers = list(RELAXATION_ORDER)
    products: list = []
    while True:
        # Never run a filter-free query: with no active filters left, the
        # result would be "popular products" even for garbage queries like
        # "xyzzy qqq". A query we cannot interpret at all must return 0
        # results so the caller can fall back to normal keyword search.
        if not any(tier_filters.get(t) for t in active_tiers):
            products = []
            break
        query = (
            session.query(Product)
            .join(Brand, Product.brand_id == Brand.id)
            .join(Category, Product.category_id == Category.id)
            .options(
                joinedload(Product.brand),
                joinedload(Product.category),
                joinedload(Product.images),
                joinedload(Product.specifications),
            )
            .filter(Product.is_active == True, Brand.is_active == True, Category.is_active == True)
        )
        for tier in active_tiers:
            for cond in tier_filters.get(tier, []):
                query = query.filter(cond)
        products = query.order_by(Product.popularity_score.desc()).limit(300).all()
        if products:
            break
        # relax the least confident remaining tier (skip tiers with no filters)
        while active_tiers and not tier_filters.get(active_tiers[0]):
            active_tiers.pop(0)
        if not active_tiers:
            products = []
            break
        relaxed = active_tiers.pop(0)
        notes.append(
            f"no products matched all filters - relaxed '{relaxed}' filter(s) and re-searched"
        )

    scored = []
    for product in products:
        score, matched_on = _score_product(product, interpretation)
        if interpretation.get("category") and category_ids:
            matched_on.insert(0, f"category:{interpretation['category']}")
        if interpretation.get("budget_max") is not None and product.price <= interpretation["budget_max"]:
            matched_on.insert(0, "budget_max")
        if interpretation.get("budget_min") is not None and product.price >= interpretation["budget_min"]:
            matched_on.insert(0, "budget_min")
        scored.append({"product": product, "score": score, "matched_on": matched_on})

    scored.sort(key=lambda m: (-m["score"], -(m["product"].popularity_score or 0),
                               m["product"].price or 0))
    return scored[:limit]
