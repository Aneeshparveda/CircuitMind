"""Render the complete CircuitMind source tree into A_TO_Z_CODE.pdf.

Every source file is printed in full (monospace, Unicode) under a header band
that names the path and line count. A two-pass render produces a table of
contents with accurate page numbers.
"""

import time
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "A_TO_Z_CODE.pdf"
COURIER = "/System/Library/Fonts/Supplemental/Courier New.ttf"
COURIER_BOLD = "/System/Library/Fonts/Supplemental/Courier New Bold.ttf"

MARGIN = 13
CODE_SIZE = 7.6
WRAP = 100  # characters per line at CODE_SIZE
INDENT = 6  # continuation indent (chars)
HEADER_H = 7.2  # mm, file header band
TEAL = (12, 96, 108)
LIGHT = (235, 240, 242)

SECTIONS = [
    ("PART I — THE PYTHON ENGINE (the 5-layer pipeline)", [
        "engine/orchestrator.py",
        "engine/signature_extractor.py",
        "engine/topology_dag.py",
        "engine/semantic_memory.py",
        "engine/evidence_fusion.py",
        "engine/narrative_generator.py",
    ]),
    ("PART II — REPORTS (PDF + CSV export)", [
        "reports/pdf_generator.py",
        "reports/csv_generator.py",
    ]),
    ("PART III — HOST & DATA SCRIPTS", [
        "app.py",
        "data/schema_adapter.py",
        "data/generate_synthetic.py",
        "data/evidence_policy.json",
    ]),
    ("PART IV — TESTS & VALIDATION", [
        "tests/test_engine.py",
        "validation/validate_accuracy.py",
    ]),
    ("PART V — THE REACT CONSOLE", [
        "frontend-vite/src/main.tsx",
        "frontend-vite/src/App.tsx",
        "frontend-vite/src/components/console/types.ts",
        "frontend-vite/src/components/console/Effects.tsx",
        "frontend-vite/src/components/console/ForensicsConsole.tsx",
        "frontend-vite/src/components/console/StarBorder.tsx",
        "frontend-vite/src/components/console/StarBorder.css",
        "frontend-vite/src/components/console/StrokeText.tsx",
        "frontend-vite/src/components/console/StrokeText.css",
        "frontend-vite/src/components/console/SideRays.tsx",
        "frontend-vite/src/components/console/SideRays.css",
        "frontend-vite/src/index.css",
    ]),
    ("PART VI — CONFIGURATION & PITCH", [
        "frontend-vite/package.json",
        "frontend-vite/vite.config.ts",
        "frontend-vite/tsconfig.json",
        "frontend-vite/tsconfig.app.json",
        "frontend-vite/tsconfig.node.json",
        "frontend-vite/.oxlintrc.json",
        "PITCH.md",
    ]),
]

ALL_FILES = [path for _, files in SECTIONS for path in files]


DINGBATS = {"✅": "[OK]", "✓": "[OK]", "✕": "[X]"}  # Courier New has no dingbat glyphs


def read_file(path: str) -> list[str]:
    text = (ROOT / path).read_text(encoding="utf-8").replace("\t", "    ")
    for glyph, ascii_form in DINGBATS.items():
        text = text.replace(glyph, ascii_form)
    return text.splitlines()


def wrap_line(line: str, width: int = WRAP, indent: int = INDENT) -> list[str]:
    if len(line) <= width:
        return [line]
    out, current = [], line
    while len(current) > width:
        out.append(current[:width])
        current = " " * indent + current[width:]
    out.append(current)
    return out


class Doc(FPDF):
    def footer(self):
        self.set_y(-11)
        self.set_font("cou", "", 7)
        self.set_text_color(120, 130, 135)
        self.cell(0, 7, f"CircuitMind — Complete Source Code  ·  page {self.page_no()}", align="C")


def make_doc() -> Doc:
    pdf = Doc(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=16)
    pdf.add_font("cou", "", COURIER)
    pdf.add_font("cou", "B", COURIER_BOLD)
    pdf.set_margins(MARGIN, 14, MARGIN)
    return pdf


def render_content(pdf: Doc, record=None) -> None:
    """Draw every section and file. When ``record`` is given, store the
    starting page of each file so the TOC can reference it."""
    for title, files in SECTIONS:
        if pdf.get_y() > 230:
            pdf.add_page()
        pdf.set_font("cou", "B", 13)
        pdf.set_text_color(*TEAL)
        pdf.cell(0, 9, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(150, 165, 170)
        pdf.line(MARGIN, pdf.get_y() + 0.5, pdf.w - MARGIN, pdf.get_y() + 0.5)
        pdf.ln(4)

        for path in files:
            if record is not None:
                record[path] = pdf.page_no()
            lines = read_file(path)

            # header band
            if pdf.get_y() > 252:
                pdf.add_page()
            pdf.set_fill_color(*TEAL)
            pdf.rect(MARGIN, pdf.get_y(), pdf.w - 2 * MARGIN, HEADER_H, "F")
            pdf.set_xy(MARGIN + 2.5, pdf.get_y() + 1.6)
            pdf.set_font("cou", "B", 8.5)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(pdf.w - 2 * MARGIN - 40, 4, f"  {path}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("cou", "", 8)
            pdf.set_text_color(200, 235, 238)
            pdf.set_xy(pdf.w - MARGIN - 34, pdf.get_y() - 4.8)
            pdf.cell(32, 4, f"{len(lines)} lines", align="R")
            pdf.ln(3.2)

            pdf.set_font("cou", "", CODE_SIZE)
            pdf.set_text_color(25, 25, 30)
            for line in lines:
                if pdf.get_y() > 280:
                    pdf.add_page()
                for chunk in wrap_line(line):
                    pdf.multi_cell(0, 3.3, chunk, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2.4)


def main() -> None:
    # Pass 1: record where every file starts.
    probe = make_doc()
    probe.add_page()
    record: dict[str, int] = {}
    render_content(probe, record)

    total_lines = sum(len(read_file(path)) for path in ALL_FILES)

    # Pass 2: title page + one-page TOC, then the content (content starts on page 2).
    pdf = make_doc()
    pdf.add_page()

    pdf.set_font("cou", "B", 24)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 12, "CIRCUITMIND", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("cou", "", 11)
    pdf.set_text_color(60, 70, 75)
    pdf.cell(0, 6, "Complete Source Code — A-to-Z", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("cou", "", 8.5)
    pdf.set_text_color(110, 120, 125)
    pdf.cell(
        0, 5,
        f"{len(ALL_FILES)} files  ·  {total_lines:,} lines  ·  generated {time.strftime('%B %d, %Y')}",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_font("cou", "", 7)
    pdf.set_text_color(130, 140, 145)
    pdf.cell(0, 4.5, "decorative check/cross glyphs render as [OK]/[X] in this code font",
        align="C", new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(4)

    # TOC — every entry references page 2 + the recorded start offset.
    pdf.set_font("cou", "B", 9.5)
    pdf.set_text_color(20, 20, 25)
    pdf.cell(0, 5, "TABLE OF CONTENTS", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.5)
    for title, files in SECTIONS:
        pdf.set_font("cou", "B", 8.5)
        pdf.set_text_color(*TEAL)
        pdf.cell(0, 4.4, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("cou", "", 8)
        pdf.set_text_color(40, 40, 45)
        for path in files:
            page = record[path] + 1  # pass 1 started on page 1; pass 2 content starts on page 2
            pdf.cell(0, 4.1, f"    {path}  . . . . . . . . . . . . . . . .  p. {page}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    assert pdf.page_no() == 1, f"TOC spilled onto page {pdf.page_no()} — shrink it"

    render_content(pdf)
    pdf.output(str(OUT))
    print(f"wrote {OUT} ({pdf.page_no()} pages, {OUT.stat().st_size / 1024:.0f} KB, {len(ALL_FILES)} files, {total_lines:,} lines)")


if __name__ == "__main__":
    main()
