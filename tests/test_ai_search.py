"""
Unit tests for the local AI-search query parser (core/services/ai_search.py).

Pure parser tests — no database is touched: parse_query() only needs the
query string (known_brands defaults to the static vocabulary).
"""
import pytest

from core.services.ai_search import parse_query


# ---------------------------------------------------------------------------
# Budget parsing (BDT shorthand)
# ---------------------------------------------------------------------------

class TestBudgetParsing:
    def test_under_100k(self):
        r = parse_query("gaming laptop under 100k")
        assert r["budget_max"] == 100000
        assert r["budget_min"] is None

    def test_below_1_lakh(self):
        r = parse_query("phone below 1 lakh")
        assert r["budget_max"] == 100000

    def test_below_1_point_5_lakh(self):
        r = parse_query("budget phone below 1.5 lakh")
        assert r["budget_max"] == 150000

    def test_bare_range_50_80k(self):
        r = parse_query("50-80k monitor")
        assert r["budget_min"] == 50000
        assert r["budget_max"] == 80000

    def test_between_range(self):
        r = parse_query("monitor between 50k and 80k taka")
        assert r["budget_min"] == 50000
        assert r["budget_max"] == 80000

    def test_around(self):
        r = parse_query("laptop around 150000")
        assert r["budget_min"] == pytest.approx(135000)
        assert r["budget_max"] == pytest.approx(165000)

    def test_taka_symbol(self):
        r = parse_query("৳120k laptop")
        assert r["budget_max"] == 120000

    def test_thousand_word(self):
        r = parse_query("office mouse under 20 thousand")
        assert r["budget_max"] == 20000

    def test_comma_formatted_number(self):
        r = parse_query("laptop around 1,50,000")
        assert r["budget_min"] == pytest.approx(135000)
        assert r["budget_max"] == pytest.approx(165000)

    def test_over_sets_min(self):
        r = parse_query("workstation over 200k")
        assert r["budget_min"] == 200000
        assert r["budget_max"] is None

    def test_no_budget(self):
        r = parse_query("gaming laptop")
        assert r["budget_min"] is None
        assert r["budget_max"] is None

    def test_spec_numbers_do_not_leak_into_budget(self):
        r = parse_query("monitor 144hz 27 inch")
        assert r["budget_min"] is None
        assert r["budget_max"] is None


# ---------------------------------------------------------------------------
# Use-case detection
# ---------------------------------------------------------------------------

class TestUseCase:
    @pytest.mark.parametrize("query, expected", [
        ("gaming laptop under 100k", "gaming"),
        ("cheap laptop for office work", "office"),
        ("laptop for a college student", "student"),
        ("pc for video editing and streaming", "content_creation"),
        ("budget phone below 20k", "budget"),
        ("workstation for machine learning", "server_workstation"),
        ("desktop for home use", "home"),
    ])
    def test_use_cases(self, query, expected):
        assert parse_query(query)["use_case"] == expected


# ---------------------------------------------------------------------------
# Category intents -> slugs
# ---------------------------------------------------------------------------

class TestCategory:
    @pytest.mark.parametrize("query, expected_slug", [
        ("best gaming laptop", "laptop"),
        ("phone under 30k", "phone"),
        ("144hz monitor", "monitor"),
        ("graphics card for gaming", "gpu"),
        ("cpu ryzen 7", "cpu"),
        ("16gb ram stick", "ram"),
        ("1tb ssd", "storage"),
        ("wifi motherboard", "motherboard"),
        ("650 watt psu", "psu"),
        ("mechanical keyboard", "keyboard"),
        ("wireless mouse", "mouse"),
        ("gaming headset", "headset"),
        ("ipad tablet", "tablet"),
    ])
    def test_category_slugs(self, query, expected_slug):
        assert parse_query(query)["category"] == expected_slug

    def test_no_category(self):
        assert parse_query("something nice for me")["category"] is None


# ---------------------------------------------------------------------------
# Brand detection
# ---------------------------------------------------------------------------

class TestBrands:
    def test_simple_brand(self):
        assert parse_query("asus gaming laptop")["brands"] == ["asus"]

    def test_case_insensitive(self):
        assert parse_query("ASUS ROG laptop")["brands"] == ["asus"]

    def test_alias_geforce_to_nvidia(self):
        assert "nvidia" in parse_query("geforce gpu")["brands"]

    def test_alias_macbook_to_apple(self):
        assert parse_query("macbook air")["brands"] == ["apple"]

    def test_multiple_brands(self):
        brands = parse_query("logitech mouse or razer keyboard")["brands"]
        assert set(brands) == {"logitech", "razer"}


# ---------------------------------------------------------------------------
# Spec keyword extraction
# ---------------------------------------------------------------------------

class TestSpecs:
    def test_ram(self):
        assert parse_query("laptop with 16gb ram")["specs"] == {"ram_gb": 16}

    def test_storage_ssd(self):
        assert parse_query("laptop 512gb ssd")["specs"] == {"storage_gb": 512}

    def test_storage_tb_converted_to_gb(self):
        assert parse_query("1tb hdd")["specs"] == {"storage_gb": 1024}

    def test_gpu_rtx(self):
        assert parse_query("rtx 4070 build")["specs"] == {"gpu": "rtx 4070"}

    def test_gpu_radeon(self):
        assert parse_query("rx 7800xt")["specs"] == {"gpu": "rx 7800xt"}

    def test_cpu_ryzen(self):
        assert parse_query("ryzen 7 desktop")["specs"] == {"cpu": "ryzen 7"}

    def test_cpu_intel(self):
        assert parse_query("core i5 laptop")["specs"] == {"cpu": "i5"}

    def test_refresh_rate(self):
        assert parse_query("165hz monitor")["specs"] == {"refresh_hz": 165}

    def test_screen_size(self):
        assert parse_query("27 inch monitor")["specs"] == {"size_inch": 27.0}

    def test_panel(self):
        assert parse_query("oled monitor")["specs"] == {"panel": "oled"}

    def test_multiple_specs(self):
        specs = parse_query("laptop 16gb ram 512gb ssd 144hz")["specs"]
        assert specs == {"ram_gb": 16, "storage_gb": 512, "refresh_hz": 144}


# ---------------------------------------------------------------------------
# Combined queries + structural contract
# ---------------------------------------------------------------------------

class TestCombinedAndContract:
    def test_combined_gaming_query(self):
        r = parse_query("gaming laptop under 100k with rtx 4060")
        assert r["budget_max"] == 100000
        assert r["use_case"] == "gaming"
        assert r["category"] == "laptop"
        assert r["specs"]["gpu"] == "rtx 4060"
        assert r["budget_min"] is None

    def test_full_student_query(self):
        r = parse_query("student laptop around 60000 with 16gb ram and 512gb ssd")
        assert r["use_case"] == "student"
        assert r["category"] == "laptop"
        assert r["budget_min"] == pytest.approx(54000)
        assert r["budget_max"] == pytest.approx(66000)
        assert r["specs"] == {"ram_gb": 16, "storage_gb": 512}

    def test_interpretation_contract_keys(self):
        r = parse_query("gaming laptop under 100k")
        for key in ("budget_min", "budget_max", "use_case", "category",
                    "brands", "specs", "keywords", "notes"):
            assert key in r

    def test_notes_are_strings(self):
        r = parse_query("gaming laptop under 100k with rtx 4060")
        assert isinstance(r["notes"], list)
        assert all(isinstance(n, str) for n in r["notes"])

    def test_known_brands_parameter_extends_vocabulary(self):
        r = parse_query("starlink router", known_brands=["starlink"])
        assert r["brands"] == ["starlink"]

    def test_empty_query_is_safe(self):
        r = parse_query("   ")
        assert r["budget_min"] is None
        assert r["budget_max"] is None
        assert r["use_case"] is None
        assert r["category"] is None
        assert r["brands"] == []
        assert r["specs"] == {}
