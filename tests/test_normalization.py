from ml.preprocessing import normalization as norm
from ml.preprocessing import performance_lookup as perf


def test_normalize_ram_gb_variants():
    assert norm.normalize_ram_gb("16GB") == 16
    assert norm.normalize_ram_gb("16 GB") == 16
    assert norm.normalize_ram_gb("16384MB") == 16
    assert norm.normalize_ram_gb(16) == 16
    assert norm.normalize_ram_gb(None) is None
    assert norm.normalize_ram_gb("") is None


def test_normalize_storage_gb_variants():
    assert norm.normalize_storage_gb("512GB") == 512
    assert norm.normalize_storage_gb("1TB") == 1024
    assert norm.normalize_storage_gb("1 TB") == 1024
    assert norm.normalize_storage_gb("512000MB") == 500.0


def test_normalize_price_strips_currency():
    assert norm.normalize_price("৳95,000") == 95000
    assert norm.normalize_price("95000 BDT") == 95000
    assert norm.normalize_price("Tk. 95,000") == 95000
    assert norm.normalize_price(95000) == 95000
    assert norm.normalize_price(0) is None
    assert norm.normalize_price(-100) is None


def test_normalize_display_inches():
    assert norm.normalize_display_inches('15.6"') == 15.6
    assert norm.normalize_display_inches("15.6 inch") == 15.6
    assert norm.normalize_display_inches("39.6cm") == 15.59


def test_normalize_weight_kg():
    assert norm.normalize_weight_kg("1.5kg") == 1.5
    assert norm.normalize_weight_kg("1500g") == 1.5
    assert round(norm.normalize_weight_kg("3.3lb"), 2) == 1.5


def test_normalize_battery_mah():
    assert norm.normalize_battery_mah("5000mAh") == 5000
    assert norm.normalize_battery_mah("5Ah") == 5000


def test_normalize_resolution_pixels():
    assert norm.normalize_resolution_pixels("1920x1080") == 1920 * 1080
    assert norm.normalize_resolution_pixels("3840 x 2160") == 3840 * 2160
    assert norm.normalize_resolution_pixels("not-a-resolution") is None


def test_unparseable_returns_none_not_zero():
    assert norm.normalize_ram_gb("unspecified") is None
    assert norm.normalize_storage_gb("N/A") is None


def test_cpu_performance_lookup():
    assert perf.normalize_cpu_performance("Intel Core i7-13700H") == 78
    assert perf.normalize_cpu_performance("Apple M2 Pro") == 82
    assert perf.normalize_cpu_performance("SomeUnknownChip 9999") is None


def test_gpu_performance_lookup_and_integrated_fallback():
    assert perf.normalize_gpu_performance("RTX 4060") == 68
    assert perf.normalize_gpu_performance("Intel Iris Xe integrated graphics") == 15
    assert perf.normalize_gpu_performance("Totally unknown GPU") is None
