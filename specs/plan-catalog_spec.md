# Feature Specification: Plan Catalog Management (AC-03)

**Specification ID:** SPEC-PLAN-CATALOG-01  
**Target Criteria:** AC-03, NFR-02, NFR-05  
**Domain Area:** Plan Catalog & Product Definitions  

---

## 1. Overview
The Plan Catalog service manages telecommunications plan products offered to subscribers. It supports two primary plan families:
- **Prepaid Plans**: Characterized by a fixed validity period (e.g., 28 days, 84 days, 365 days), fixed data allocation (GB), daily SMS caps, and unlimited voice minutes. Changes take effect immediately upon activation.
- **Postpaid Plans**: Characterized by recurring monthly billing cycles (typically 30 days), higher data allowances with rollover, and monthly rental fees computed using fixed-point `Decimal`.

All published plan versions are strictly immutable. Any modification to rent, quota, or entitlements requires incrementing the version number (`version = version + 1`) and creating a new immutable record.

---

## 2. Plan Entity Attributes
| Field | Type | Description |
| :--- | :--- | :--- |
| `plan_id` | `str` | Unique business key (e.g. `PLAN-PRE-01`, `PLAN-POST-01`) |
| `version` | `int` | Sequential version counter (starts at 1) |
| `name` | `str` | Display name (e.g. "Silver 5G Unlimited", "Prepaid Max 28D") |
| `plan_type` | `PlanType` | Enum (`PREPAID` or `POSTPAID`) |
| `monthly_rent` | `Decimal` | Fixed-point rental charge (e.g. `Decimal("49.99")`) |
| `validity_days` | `int` | Validity period in calendar days (e.g., 28 or 30) |
| `data_gb` | `int` | Data allowance per billing cycle or validity period |
| `voice_minutes`| `int` | Included voice minutes (-1 for unlimited) |
| `sms_count` | `int` | Included SMS count (-1 for unlimited) |
| `min_tenure_days`| `int` | Minimum subscription duration required before switching |
| `is_published` | `bool` | Once `True`, all fields are sealed and immutable |
| `created_at` | `datetime` | UTC timestamp of version creation |

---

## 3. Acceptance Criteria

### AC-03.1: Support for Prepaid and Postpaid Families
- **Given** plan definition requests for PREPAID and POSTPAID products,
- **When** the plans are registered in the catalog,
- **Then** PREPAID plans validate positive validity days, and POSTPAID plans validate positive monthly rental amounts.

### AC-03.2: Immutability of Published Plan Versions
- **Given** a plan version marked with `is_published=True`,
- **When** any mutation is attempted on rental rate, validity, quota, or name,
- **Then** the catalog engine rejects the mutation, raises `PlanImmutableException` (`ERR_PLAN_IMMUTABLE`), and leaves the original plan unaltered.

### AC-03.3: Version Incrementing for Plan Updates
- **Given** an existing published plan `PLAN-POST-01` at version 1,
- **When** a revised tariff or quota is approved,
- **Then** a new record is created with `plan_id="PLAN-POST-01"` and `version=2`, preserving historical version 1 for active subscribers.

---

## 4. Error Codes
- `ERR_PLAN_IMMUTABLE`: Raised when trying to modify or delete a published plan.
- `ERR_PLAN_NOT_FOUND`: Raised when a requested plan identifier does not exist.
- `ERR_INVALID_PLAN_DATA`: Raised when plan values (rent, validity) are invalid or non-positive.
