"""Render JUDGE_ONEPAGER.md into a clean single-page JUDGE_ONEPAGER.pdf.

A4 portrait, teal accent headings, black body text — printable on any office
printer. Run: python3 tools/make_one_pager_pdf.py
"""

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "JUDGE_ONEPAGER.md"
OUT = ROOT / "JUDGE_ONEPAGER.pdf"
COURIER = "/System/Library/Fonts/Supplemental/Courier New.ttf"
COURIER_BOLD = "/System/Library/Fonts/Supplemental/Courier New Bold.ttf"

MARGIN = 14
TEAL = (12, 96, 108)
DARK = (25, 25, 30)
GRAY = (90, 100, 105)


class Doc(FPDF):
    def footer(self):
        self.set_y(-10)
        self.set_font("cou", "", 7)
        self.set_text_color(*GRAY)
        self.cell(0, 5, "CircuitMind — one-page summary", align="C")


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    # Courier New Bold lacks these glyphs — substitute ASCII before rendering.
    text = text.replace("—", " -- ").replace("·", "|")

    pdf = Doc(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=14)
    pdf.add_font("cou", "", COURIER)
    pdf.add_font("cou", "B", COURIER_BOLD)
    pdf.set_margins(MARGIN, 13, MARGIN)
    pdf.add_page()

    lines = text.splitlines()
    i = 0

    def flush_heading(text: str, size: float) -> None:
        pdf.set_font("cou", "B", size)
        pdf.set_text_color(*TEAL)
        pdf.multi_cell(0, 5.2, text, new_x="LMARGIN", new_y="NEXT")

    def flush_body(text: str, size: float, color: tuple = DARK) -> None:
        pdf.set_font("cou", "", size)
        pdf.set_text_color(*color)
        pdf.multi_cell(0, 4.0, text, new_x="LMARGIN", new_y="NEXT")

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            pdf.ln(1.6)
            i += 1
            continue
        if line.startswith("# "):
            flush_heading(line[2:], 21)
        elif line.startswith("## "):
            pdf.ln(0.8)
            flush_heading(line[3:], 12.5)
        elif line.startswith("### "):
            flush_heading(line[4:], 10.5)
        elif line.startswith("---"):
            pdf.ln(1)
            pdf.set_draw_color(160, 175, 180)
            pdf.line(MARGIN, pdf.get_y() + 1, pdf.w - MARGIN, pdf.get_y() + 1)
            pdf.ln(2.5)
        elif line.startswith("|"):
            # Table row — render compactly, preserving alignment roughly.
            cells = [c.strip() for c in line.strip("|").split("|")]
            pdf.set_font("cou", "B" if i == 0 else "", 8.6)
            pdf.set_text_color(*TEAL) if i == 0 else pdf.set_text_color(*DARK)
            pdf.multi_cell(0, 4.0, "   " + "   ".join(cells), new_x="LMARGIN", new_y="NEXT")
        elif line.startswith("- "):
            pdf.set_font("cou", "", 9)
            pdf.set_text_color(*DARK)
            pdf.multi_cell(0, 4.0, "  - " + line[2:], new_x="LMARGIN", new_y="NEXT")
        else:
            flush_body(line, 9.3)
        i += 1

    assert pdf.page_no() == 1, f"one-pager spilled to {pdf.page_no()} pages — tighten the copy"
    pdf.output(str(OUT))
    print(f"wrote {OUT} (1 page, {OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
