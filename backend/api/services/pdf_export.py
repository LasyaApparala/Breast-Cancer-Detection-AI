"""
PDF export service: generates clinical reports from ClassificationResult + AuditTrail.

Uses reportlab to render a structured PDF containing:
  - Session ID and classification result
  - Severity label and confidence score
  - Low-confidence and data-sufficiency warnings (if applicable)
  - TNM staging detail (malignant cases only)
  - Full audit trail table
  - Mandatory clinical disclaimer

PDF generation must complete within 10 seconds (Requirements 5.4).

Requirements: 5.3, 5.4, 5.5
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_clinical_report(
    session_id: str,
    result: dict,
    audit_trail: list[dict],
) -> bytes:
    """
    Generate a PDF clinical report from ClassificationResult + AuditTrail.

    Returns PDF bytes. Generation completes within 10 seconds for typical
    inputs (Requirements 5.4).

    Args:
        session_id: The classification session UUID string.
        result: ClassificationResult dict with keys: severity_label,
                confidence_score, low_confidence_warning,
                data_sufficiency_warning, tnm_stage_detail.
        audit_trail: List of AuditTrailEntry dicts with keys: feature_name,
                     value_used, source, document_ref, corrected_by_user.

    Returns:
        PDF bytes.

    Requirements: 5.3, 5.4, 5.5
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # -----------------------------------------------------------------------
    # Title
    # -----------------------------------------------------------------------
    story.append(
        Paragraph(
            "Breast Tumor Severity Classification Report",
            styles["Title"],
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    # -----------------------------------------------------------------------
    # Session info
    # -----------------------------------------------------------------------
    story.append(Paragraph(f"Session ID: {session_id}", styles["Normal"]))
    story.append(Spacer(1, 0.1 * inch))

    # -----------------------------------------------------------------------
    # Severity result
    # -----------------------------------------------------------------------
    severity_label = result.get("severity_label", "Unknown")
    confidence = result.get("confidence_score", 0.0)
    story.append(
        Paragraph(
            f"<b>Severity Classification: {severity_label}</b>",
            styles["Heading2"],
        )
    )
    story.append(
        Paragraph(f"Confidence Score: {confidence:.2%}", styles["Normal"])
    )

    # -----------------------------------------------------------------------
    # Warnings
    # -----------------------------------------------------------------------
    if result.get("low_confidence_warning"):
        story.append(
            Paragraph(
                "&#9888; WARNING: Confidence score below 0.75. "
                "Additional clinical review recommended.",
                styles["Normal"],
            )
        )
    if result.get("data_sufficiency_warning"):
        story.append(
            Paragraph(
                "&#9888; WARNING: Less than 60% of features present. "
                "Result may be unreliable.",
                styles["Normal"],
            )
        )

    story.append(Spacer(1, 0.2 * inch))

    # -----------------------------------------------------------------------
    # TNM detail (malignant cases only)
    # -----------------------------------------------------------------------
    tnm = result.get("tnm_stage_detail")
    if tnm:
        story.append(Paragraph("TNM Staging", styles["Heading2"]))
        story.append(
            Paragraph(
                f"T: {tnm.get('t_value')} | "
                f"N: {tnm.get('n_value')} | "
                f"M: {tnm.get('m_value')}",
                styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                f"AJCC Stage: {tnm.get('ajcc_stage')} "
                f"(source: {tnm.get('staging_source')})",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.2 * inch))

    # -----------------------------------------------------------------------
    # Audit trail table
    # -----------------------------------------------------------------------
    story.append(Paragraph("Audit Trail", styles["Heading2"]))
    table_data = [["Feature", "Value", "Source", "Document Ref", "Corrected"]]
    for entry in audit_trail:
        table_data.append(
            [
                entry.get("feature_name", ""),
                str(entry.get("value_used", "—") or "—"),
                entry.get("source", ""),
                entry.get("document_ref", "—") or "—",
                "Yes" if entry.get("corrected_by_user") else "No",
            ]
        )

    table = Table(
        table_data,
        colWidths=[1.5 * inch, 1 * inch, 1 * inch, 2 * inch, 0.7 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.lightgrey],
                ),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.3 * inch))

    # -----------------------------------------------------------------------
    # Mandatory disclaimer (Requirement 5.5)
    # -----------------------------------------------------------------------
    story.append(
        Paragraph(
            "<b>DISCLAIMER:</b> This classification is a decision-support tool "
            "and does not replace professional medical diagnosis. All results "
            "must be reviewed by a qualified clinician.",
            styles["Normal"],
        )
    )

    doc.build(story)
    return buffer.getvalue()
