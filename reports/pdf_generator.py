from fpdf import FPDF
from fpdf.enums import XPos, YPos
from typing import Any, Dict

from engine.diagnostic_receipt import extract_diagnostic_receipt

# PyFPDF core fonts (helvetica) are latin-1 only. Map the unicode
# punctuation the pipeline emits (em-dashes, causal arrows, bullets)
# to ASCII equivalents before rendering, so PDF export never crashes.
_UNICODE_TO_ASCII = {
    '—': '-', '–': '-', '→': '->', '←': '<-', '×': 'x', '·': '-', '•': '-',
    '’': "'", '‘': "'", '“': '"', '”': '"', '…': '...', '≥': '>=', '≤': '<=',
}


def _ascii_safe(text: Any) -> str:
    """Return a latin-1-safe copy of ``text`` for FPDF rendering."""
    if not isinstance(text, str):
        text = str(text)
    for source, target in _UNICODE_TO_ASCII.items():
        text = text.replace(source, target)
    return text.encode('latin-1', errors='replace').decode('latin-1')


class PDFReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.set_text_color(40, 40, 40)
        self.cell(0, 8, 'FAILURE INVESTIGATION DOSSIER', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font('helvetica', 'B', 9)
        self.set_text_color(110, 110, 110)
        case_no = getattr(self, 'case_number', None)
        classification = 'STRUCTURED EVIDENCE REASONING'
        status_line = case_no if case_no else classification
        self.cell(0, 6, f'{status_line}  |  {classification}', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(200, 200, 200)
        self.line(10, 26, 200, 26)
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)

def _build_pdf(report: Dict[str, Any]) -> PDFReport:
    """
    Generates a professional PDF forensic report from the orchestrator output.
    """
    pdf = PDFReport()
    pdf.case_number = report.get('case_number', '')
    pdf.add_page()
    
    # Board Info
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, f"Board ID: {report.get('board_id', 'UNKNOWN')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if pdf.case_number:
        pdf.set_font('helvetica', '', 10)
        pdf.cell(0, 8, f"Case No: {pdf.case_number}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    status = report.get('status', 'UNKNOWN')
    pdf.set_text_color(220, 53, 69) if status == 'FAIL' else pdf.set_text_color(40, 167, 69)
    pdf.cell(0, 10, f"Status: {status}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)

    versions = report.get('versions') or {}
    pdf.set_font('helvetica', '', 8)
    pdf.set_text_color(110, 110, 110)
    pdf.cell(0, 5, _ascii_safe(
        f"Engine {versions.get('engine', '?')}  |  data schema {versions.get('data_schema', '?')}  |  "
        f"policy {versions.get('evidence_policy', '?')}  |  generated at {versions.get('generated_at', '?')}"
    ), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    ood = report.get('ood_state') or {}
    if ood.get('state'):
        pdf.set_x(pdf.l_margin)
        pdf.set_font('helvetica', 'B', 9)
        pdf.set_text_color(200, 140, 60) if ood['state'] != 'KNOWN' else pdf.set_text_color(40, 120, 80)
        pdf.cell(0, 6, f"Pattern familiarity: {ood['state']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('helvetica', '', 8)
        pdf.set_text_color(110, 110, 110)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 4.5, _ascii_safe(
            " ".join(ind['detail'] for ind in ood.get('indicators', []))[:400]
        ))
        pdf.set_text_color(0, 0, 0)

    dq = report.get('data_quality') or {}
    if dq.get('status'):
        pdf.set_x(pdf.l_margin)
        pdf.set_font('helvetica', 'B', 9)
        color = {'GREEN': (40, 120, 80), 'AMBER': (200, 140, 60), 'RED': (200, 60, 60)}.get(dq['status'], (0, 0, 0))
        pdf.set_text_color(*color)
        pdf.cell(0, 6, _ascii_safe(f"Data quality: {dq['status']} — {dq.get('label', '')}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        for issue in dq.get('issues', [])[:4]:
            pdf.set_x(pdf.l_margin)
            pdf.set_font('helvetica', '', 8)
            pdf.set_text_color(110, 110, 110)
            pdf.multi_cell(0, 4.5, _ascii_safe(f"  - [{issue.get('level')}] {issue.get('message', '')}"))
        pdf.set_text_color(0, 0, 0)
    pdf.ln(4)
    
    if status == 'PASS':
        pdf.set_font('helvetica', '', 10)
        pdf.multi_cell(0, 8, report.get('narrative', 'All tests passed.'))
        return pdf
        
    # Narrative Summary
    pdf.set_font('helvetica', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, " Forensic Summary", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('helvetica', '', 10)
    pdf.ln(2)
    pdf.multi_cell(0, 6, _ascii_safe(report.get('narrative', '').replace('**', '')))
    pdf.ln(4)

    tier = report.get('confidence_tier')
    if tier:
        pdf.set_font('helvetica', 'B', 10)
        pdf.cell(0, 6, f"Confidence: {tier}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    precedent = report.get('cited_precedent')
    if precedent:
        pdf.set_font('helvetica', '', 9)
        pdf.cell(0, 6, _ascii_safe(
            f"Cited precedent: {precedent['repair_id']} ({float(precedent['similarity']):.1f}% match) -> "
            f"{precedent['root_cause_component']}"
        ), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    repair_notes = report.get('repair_notes', '')
    if repair_notes:
        pdf.set_font('helvetica', '', 9)
        pdf.multi_cell(0, 5, _ascii_safe(f"Repair notes: {repair_notes}"))
    pdf.ln(6)
    
    # Top Suspects
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 8, " Suspect Ranking & Alibi Checks", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    
    suspects = report.get('suspects', [])
    for i, s in enumerate(suspects[:3]):
        pdf.set_font('helvetica', 'B', 10)
        pdf.cell(0, 6, _ascii_safe(f"#{i+1}: {s['refdes']} - {s['desc']} (Score: {s['score']:.1f}/100)"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        fault_mode = s.get('fault_mode') or {}
        if fault_mode.get('label'):
            pdf.set_font('helvetica', 'B', 9)
            pdf.set_text_color(40, 120, 140)
            pdf.cell(0, 5.5, _ascii_safe(f"    Fault mode: {s['refdes']} / {fault_mode['label']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            if fault_mode.get('verification'):
                pdf.set_font('helvetica', '', 8)
                pdf.set_text_color(110, 110, 110)
                pdf.cell(0, 5, _ascii_safe(f"    Verification: {fault_mode['verification']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)

        pdf.set_font('helvetica', '', 9)
        pdf.set_text_color(40, 167, 69) # Green
        for ev in s.get('positive_evidence', []):
            pdf.cell(10, 5, "", new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.cell(0, 5, _ascii_safe(f"+ {ev}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
        pdf.set_text_color(220, 53, 69) # Red
        for ev in s.get('negative_evidence', []):
            pdf.cell(10, 5, "", new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.cell(0, 5, _ascii_safe(f"- {ev}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)
        
    # Next Best Test
    nbt = report.get('next_best_test', {})
    if nbt and nbt.get('active'):
        pdf.ln(5)
        pdf.set_font('helvetica', 'B', 11)
        pdf.set_fill_color(204, 229, 255)
        pdf.cell(0, 8, " Recommended Next Action", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('helvetica', '', 10)
        pdf.ln(2)
        recommendation = f"{nbt.get('test', '')} on {nbt.get('net', '')} — {nbt.get('reason', '')}".strip(' —')
        pdf.multi_cell(0, 6, _ascii_safe(recommendation))
        meta = []
        if nbt.get('info_gain'): meta.append(f"info gain: {nbt['info_gain']}")
        if nbt.get('risk'): meta.append(f"risk: {nbt['risk']}")
        if nbt.get('effort'): meta.append(f"effort: {nbt['effort']}")
        if nbt.get('separation') is not None: meta.append(f"separation: {nbt['separation']:.0f}/100")
        if meta:
            pdf.set_font('helvetica', 'I', 8)
            pdf.set_text_color(90, 90, 90)
            pdf.cell(0, 5, _ascii_safe(' | '.join(meta)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)

    multi = report.get('multi_fault_analysis') or {}
    if multi.get('verdict_text'):
        pdf.ln(4)
        pdf.set_font('helvetica', 'B', 10)
        pdf.set_text_color(200, 120, 60)
        pdf.cell(0, 6, _ascii_safe(multi['verdict_text']), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)

    observability = report.get('observability') or {}
    if isinstance(observability, dict) and observability.get('failed_functions'):
        pdf.ln(4)
        pdf.set_font('helvetica', 'B', 10)
        pdf.cell(0, 6, _ascii_safe(
            "Observed functions: " + ", ".join(observability.get('failed_functions', []))
        ), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if observability.get('unmapped_tests'):
            pdf.set_font('helvetica', '', 8)
            pdf.set_text_color(110, 110, 110)
            pdf.cell(0, 5, _ascii_safe(
                "Unmapped tests: " + ", ".join(observability.get('unmapped_tests'))
            ), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)

    ledger = report.get('evidence_ledger', [])
    if ledger:
        pdf.ln(5)
        pdf.set_font('helvetica', 'B', 11)
        pdf.set_fill_color(230, 240, 242)
        pdf.cell(0, 8, ' Chain of Evidence', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('helvetica', '', 9)
        for item in ledger[:8]:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.epw, 5, _ascii_safe(f"{item['id']} - {item['source']} - {item['strength']}: {item['observation']}"))

    # ── DIAGNOSTIC RECEIPT ──
    receipt = extract_diagnostic_receipt(report)
    if receipt:
        pdf.ln(6)
        pdf.set_font('helvetica', 'B', 12)
        pdf.set_fill_color(220, 235, 240)
        pdf.cell(0, 8, ' DIAGNOSTIC RECEIPT', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('helvetica', '', 8)
        pdf.set_text_color(110, 110, 110)
        pdf.cell(0, 5, _ascii_safe(
            f"Receipt v{receipt['receipt_version']}  |  "
            f"Case {receipt['case_number']}  |  Board {receipt['board_id']}  |  "
            f"{receipt['timestamp']}"
        ), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        # OBSERVED
        obs = receipt['observed']
        pdf.set_font('helvetica', 'B', 9)
        pdf.cell(0, 5, 'OBSERVED', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('helvetica', '', 9)
        pdf.cell(0, 5, _ascii_safe(
            f"{obs['failed_test_count']} failed test(s)  |  {obs['primary_domain']}  |  "
            f"{obs['severity']}  |  deviation {obs['deviation_range'][0]}-{obs['deviation_range'][1]}"
        ), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # INFERRED
        inf = receipt['inferred']
        pdf.set_font('helvetica', 'B', 9)
        pdf.cell(0, 5, 'INFERRED', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('helvetica', '', 9)
        pdf.cell(0, 5, _ascii_safe(
            f"{inf['leading_refdes']} - {inf['leading_desc']}  |  "
            f"Score {inf['evidence_score']:.1f}  |  Coverage {inf['mechanism_coverage_pct']}%  |  "
            f"{inf['confidence_tier']}"
        ), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # REJECTED
        if receipt['rejected']:
            pdf.set_font('helvetica', 'B', 9)
            pdf.cell(0, 5, 'REJECTED', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font('helvetica', '', 8)
            for alt in receipt['rejected']:
                pdf.cell(0, 4.5, _ascii_safe(
                    f"{alt['refdes']} ({alt['score']:.1f}, {alt['mechanism_coverage_pct']}%) - {alt['rejection_reason']}"
                ), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # RECOMMENDED
        rec = receipt['recommended']
        pdf.set_font('helvetica', 'B', 9)
        pdf.cell(0, 5, 'RECOMMENDED', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('helvetica', '', 9)
        pdf.cell(0, 5, _ascii_safe(
            f"{rec['action']}  |  {rec['target']}  |  {rec['rationale']}"
        ), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # VERIFICATION
        verif = receipt['verification']
        pdf.set_font('helvetica', 'B', 9)
        pdf.cell(0, 5, 'VERIFICATION', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('helvetica', '', 9)
        pdf.cell(0, 5, _ascii_safe(f"{verif['state']}  |  {verif['disclaimer']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    pdf.ln(4)
    pdf.set_font('helvetica', 'I', 8)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(0, 5, 'This report contains a leading diagnostic hypothesis based on structured evidence. Physical verification is required before repair confirmation.')
    pdf.set_text_color(0, 0, 0)
    return pdf


def generate_pdf_bytes(report: Dict[str, Any]) -> bytes:
    """Return an in-memory PDF suitable for Streamlit downloads."""
    return bytes(_build_pdf(report).output())


def generate_pdf(report: Dict[str, Any], filepath: str = "forensic_report.pdf"):
    """Generate a professional PDF report at ``filepath`` for CLI workflows."""
    pdf = _build_pdf(report)
    pdf.output(filepath)
    return filepath
