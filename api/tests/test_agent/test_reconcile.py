from app.agent.reconcile import detect_report_conflicts
from app.agent.tools.retriever import RetrievedChunk


def chunk(report_id: str) -> RetrievedChunk:
    return RetrievedChunk(
        report_id=report_id,
        page=1,
        text="Market data",
        score=0.9,
        title="Report",
        sector="Utilities",
        access="paid",
    )


def test_reconciliation_triggers_when_both_reports_are_in_retrieval():
    conflicts = detect_report_conflicts("What is the market size?", [chunk("R-101"), chunk("R-102")])

    assert len(conflicts) == 1
    assert conflicts[0].reports == ["R-101", "R-102"]


def test_reconciliation_triggers_for_explicit_report_comparison():
    conflicts = detect_report_conflicts("Compare R-101 with R-102", [])

    assert len(conflicts) == 1


def test_reconciliation_does_not_treat_larger_numbers_as_report_ids():
    conflicts = detect_report_conflicts("Compare 1101 and 1102", [])

    assert conflicts == []


def test_reconciliation_does_not_trigger_for_single_report():
    conflicts = detect_report_conflicts("Tell me about R-101", [chunk("R-101")])

    assert conflicts == []
