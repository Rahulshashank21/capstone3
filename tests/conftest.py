import os
import pytest
from src.infrastructure.database import create_sqlite_subscription_service
from src.services.reporting_service import ReportingService
from src.seed import seed_database
import src.main as main_mod

@pytest.fixture(autouse=True)
def isolated_test_database(tmp_path):
    """Provides complete test isolation by giving each test a fresh, seeded SQLite database."""
    test_db_path = str(tmp_path / "test_telcolane.db")
    fresh_service = create_sqlite_subscription_service(test_db_path)
    seed_database(fresh_service)
    fresh_reporting = ReportingService(
        fresh_service.subscriber_repo,
        fresh_service.plan_repo,
        fresh_service.audit_repo,
        fresh_service.billing_repo
    )
    
    # Rebind app services to fresh isolated test instance
    main_mod.service = fresh_service
    main_mod.reporting_service = fresh_reporting
    main_mod.controller.service = fresh_service
    main_mod.controller.reporting_service = fresh_reporting
    
    yield
