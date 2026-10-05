from decimal import Decimal, ROUND_HALF_UP
from typing import Dict
from src.domain.models import ProRataCalculationException

class ProRataCalculator:
    """Fixed-point financial calculation engine enforcing non-negative invariants and exact component sum matching."""

    TWO_PLACES = Decimal("0.01")

    @classmethod
    def calculate(
        cls,
        old_rent: Decimal,
        new_rent: Decimal,
        days_used: int,
        cycle_days: int
    ) -> Decimal:
        itemized = cls.calculate_itemized(old_rent, new_rent, days_used, cycle_days)
        return itemized["total_charge"]

    @classmethod
    def calculate_itemized(
        cls,
        old_rent: Decimal,
        new_rent: Decimal,
        days_used: int,
        cycle_days: int
    ) -> Dict[str, Decimal]:
        if cycle_days <= 0:
            raise ProRataCalculationException("Billing cycle duration must be strictly positive", "ERR_INVALID_CYCLE_DAYS")
        if days_used < 0 or days_used > cycle_days:
            raise ProRataCalculationException(
                f"Days used ({days_used}) must fall within cycle bounds [0, {cycle_days}]",
                "ERR_INVALID_DAYS_USED"
            )
        if not isinstance(old_rent, Decimal) or not isinstance(new_rent, Decimal):
            raise ProRataCalculationException("All financial amounts must be Decimal", "ERR_NON_DECIMAL_CURRENCY")
        if old_rent < Decimal("0.00") or new_rent < Decimal("0.00"):
            raise ProRataCalculationException("Rental charges cannot be negative", "ERR_NEGATIVE_RENT")

        days_used_dec = Decimal(str(days_used))
        cycle_days_dec = Decimal(str(cycle_days))
        days_remaining_dec = cycle_days_dec - days_used_dec

        # Exact boundary pinning
        if days_used == 0:
            old_charge = Decimal("0.00")
            new_charge = new_rent.quantize(cls.TWO_PLACES, rounding=ROUND_HALF_UP)
            total_charge = new_charge
        elif days_used == cycle_days:
            old_charge = old_rent.quantize(cls.TWO_PLACES, rounding=ROUND_HALF_UP)
            new_charge = Decimal("0.00")
            total_charge = old_charge
        else:
            old_raw = (days_used_dec / cycle_days_dec) * old_rent
            new_raw = (days_remaining_dec / cycle_days_dec) * new_rent
            total_raw = old_raw + new_raw
            total_charge = total_raw.quantize(cls.TWO_PLACES, rounding=ROUND_HALF_UP)
            old_charge = old_raw.quantize(cls.TWO_PLACES, rounding=ROUND_HALF_UP)
            new_charge = total_charge - old_charge

        if total_charge < Decimal("0.00"):
            raise ProRataCalculationException(
                f"Pro-rata invariant failed: calculated total {total_charge} < 0.00",
                "ERR_NEGATIVE_PRO_RATA"
            )

        return {
            "days_used": days_used_dec,
            "days_remaining": days_remaining_dec,
            "cycle_days": cycle_days_dec,
            "old_component": old_charge,
            "new_component": new_charge,
            "total_charge": total_charge
        }
