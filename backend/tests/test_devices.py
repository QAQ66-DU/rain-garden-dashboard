import pytest
from app.models.enums import UnitConfirmationSummary
from app.services.devices import summarize_unit_confirmation


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ([], UnitConfirmationSummary.NO_ACTIVE_CHANNELS),
        (["pending"], UnitConfirmationSummary.PENDING),
        (["confirmed", "confirmed"], UnitConfirmationSummary.CONFIRMED),
        (["synthetic_demo_only"], UnitConfirmationSummary.SYNTHETIC_DEMO_ONLY),
        (["pending", "confirmed"], UnitConfirmationSummary.MIXED),
    ],
)
def test_unit_confirmation_summary_uses_only_channel_statuses(
    statuses: list[str], expected: UnitConfirmationSummary
) -> None:
    assert summarize_unit_confirmation(statuses) is expected


def test_unit_confirmation_summary_is_insensitive_to_status_order_and_duplicates() -> None:
    first = summarize_unit_confirmation(["pending", "confirmed", "pending"])
    second = summarize_unit_confirmation(["confirmed", "pending"])

    assert first is UnitConfirmationSummary.MIXED
    assert second is UnitConfirmationSummary.MIXED
