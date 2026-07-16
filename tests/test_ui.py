"""UI route tests — pair-first finder + pair quote."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.app import app


def c():
    return app.test_client()


def test_finder_pair_results_render():
    r = c().get("/?od_sph=-2&od_cyl=0&os_sph=-1.5&os_cyl=0")
    assert r.status_code == 200
    b = r.data.decode()
    assert "OD" in b and "OS" in b and "tnum" in b


def test_pair_quote_two_skus():
    r = c().get("/quote?sku_r=HOY-NLX-160-HMC-70&sku_l=HOY-NLX-150-HMC-70")
    assert r.status_code == 200
    b = r.data.decode()
    assert "HOY-NLX-160-HMC-70" in b and "HOY-NLX-150-HMC-70" in b


def test_quote_single_sku_backcompat_and_404():
    assert c().get("/quote?sku=HOY-NLX-160-HMC-70").status_code == 200
    assert c().get("/quote?sku_r=NOPE").status_code == 404
