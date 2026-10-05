import pytest
from decimal import Decimal
from src.domain.pro_rata_calculator import ProRataCalculator
from src.domain.models import ProRataCalculationException

def test_ac_05_pro_rata_boundary_day_zero():
    """AC-05: Day 0 transition means entire cycle charged at new rate."""
    old_rent = Decimal("50.00")
    new_rent = Decimal("100.00")
    result = ProRataCalculator.calculate(old_rent, new_rent, days_used=0, cycle_days=30)
    assert result == Decimal("100.00")
    assert result >= Decimal("0.00")

def test_ac_05_pro_rata_boundary_day_max():
    """AC-05: Final cycle day transition means entire cycle charged at old rate."""
    old_rent = Decimal("50.00")
    new_rent = Decimal("100.00")
    result = ProRataCalculator.calculate(old_rent, new_rent, days_used=30, cycle_days=30)
    assert result == Decimal("50.00")
    assert result >= Decimal("0.00")

def test_ac_05_pro_rata_mid_cycle_upgrade():
    """AC-05: 10 days used in a 30-day cycle: (10/30 * 50) + (20/30 * 100) = 83.33."""
    old_rent = Decimal("50.00")
    new_rent = Decimal("100.00")
    result = ProRataCalculator.calculate(old_rent, new_rent, days_used=10, cycle_days=30)
    assert result == Decimal("83.33")
    assert result >= Decimal("0.00")

def test_ac_05_pro_rata_mid_cycle_downgrade():
    """AC-05: 15 days used in 30-day cycle downgrade: (15/30 * 100) + (15/30 * 40) = 70.00."""
    old_rent = Decimal("100.00")
    new_rent = Decimal("40.00")
    result = ProRataCalculator.calculate(old_rent, new_rent, days_used=15, cycle_days=30)
    assert result == Decimal("70.00")
    assert result >= Decimal("0.00")

@pytest.mark.parametrize("cycle_days", [28, 29, 30, 31])
def test_ac_05_pro_rata_across_all_calendar_cycle_lengths(cycle_days):
    """AC-05 & NFR-01: Invariant charges_total >= 0 holds for 28, 29 (leap year), 30, and 31 days."""
    old_rent = Decimal("69.99")
    new_rent = Decimal("129.99")
    for d in [0, 1, cycle_days // 2, cycle_days - 1, cycle_days]:
        charge = ProRataCalculator.calculate(old_rent, new_rent, days_used=d, cycle_days=cycle_days)
        assert charge >= Decimal("0.00"), f"Invariant violated for cycle_days={cycle_days}, day={d}"
        assert isinstance(charge, Decimal)

def test_ac_05_pro_rata_invalid_inputs_raise_exceptions():
    """AC-05: Out-of-bound inputs raise specific ProRataCalculationException."""
    with pytest.raises(ProRataCalculationException) as exc1:
        ProRataCalculator.calculate(Decimal("50.00"), Decimal("100.00"), days_used=-1, cycle_days=30)
    assert exc1.value.reason_code == "ERR_INVALID_DAYS_USED"

    with pytest.raises(ProRataCalculationException) as exc2:
        ProRataCalculator.calculate(Decimal("50.00"), Decimal("100.00"), days_used=35, cycle_days=30)
    assert exc2.value.reason_code == "ERR_INVALID_DAYS_USED"

    with pytest.raises(ProRataCalculationException) as exc3:
        ProRataCalculator.calculate(Decimal("50.00"), Decimal("100.00"), days_used=10, cycle_days=0)
    assert exc3.value.reason_code == "ERR_INVALID_CYCLE_DAYS"
