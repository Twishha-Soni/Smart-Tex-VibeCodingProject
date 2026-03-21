import re
from fpdf import FPDF


class LatexPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Courier", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def clean_latex(text: str) -> str:
    """Strip LaTeX commands and return readable plain text."""

    # Remove \begin{...} and \end{...} blocks
    text = re.sub(r'\\(begin|end)\{[^}]*\}(\[[^\]]*\])?', '', text)

    # Remove \documentclass, \usepackage, \geometry etc.
    text = re.sub(r'\\(documentclass|usepackage|geometry|pagestyle|setlength|renewcommand|newcommand)[^\n]*', '', text)

    # Replace \item with a bullet dash
    text = re.sub(r'\\item\s*', '  - ', text)

    # Replace \section*{...} or \section{...} with the title text
    text = re.sub(r'\\section\*?\{([^}]+)\}', r'\1', text)

    # Replace \textbf{...} → just the text
    text = re.sub(r'\\textbf\{([^}]+)\}', r'\1', text)

    # Replace \textit{...} → just the text
    text = re.sub(r'\\textit\{([^}]+)\}', r'\1', text)

    # Replace \underline{...} → just the text
    text = re.sub(r'\\underline\{([^}]+)\}', r'\1', text)

    # Replace \hspace{...} with blank spaces
    text = re.sub(r'\\hspace\{[^}]+\}', '______', text)

    # Remove \hfill, \vspace{}, \noindent, \centering, \hrulefill etc.
    text = re.sub(r'\\(hfill|hrulefill|noindent|centering|maketitle|tableofcontents)', '', text)
    text = re.sub(r'\\vspace\{[^}]*\}', '', text)
    text = re.sub(r'\\(large|Large|LARGE|huge|Huge|small|footnotesize|normalsize)\b', '', text)

    # Remove math mode wrappers but keep content: $...$ and \(...\)
    text = re.sub(r'\$([^$]+)\$', r'\1', text)
    text = re.sub(r'\\\(([^)]+)\\\)', r'\1', text)

    # Remove remaining backslash commands like \\, \quad, \left, \right etc.
    text = re.sub(r'\\(quad|qquad|left|right|cdot|ldots|dots|pm|times|div)\b', ' ', text)
    text = re.sub(r'\\\\', '\n', text)  # \\ → newline
    text = re.sub(r'\\[a-zA-Z]+\*?(\{[^}]*\})*', '', text)  # catch-all for remaining commands

    # Clean up extra whitespace and blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()

    return text


def generate_pdf(latex_code: str, sections: list) -> bytes:
    """
    Generates a clean readable PDF from parsed Gemini output.

    Args:
        latex_code: full cleaned LaTeX string (fallback)
        sections:   list of {"title": str, "content": str}

    Returns:
        PDF file as bytes
    """

    pdf = LatexPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Case 1: Sections available ──
    if sections:
        for section in sections:
            # Section title bar
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_fill_color(79, 110, 247)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 10, section["title"], new_x="LMARGIN", new_y="NEXT", fill=True)

            # Clean and write section content
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(30, 30, 30)
            pdf.set_fill_color(248, 249, 255)
            clean_content = clean_latex(section["content"])
            pdf.multi_cell(0, 7, clean_content, fill=True)
            pdf.ln(6)

    # ── Case 2: No sections — clean full latex code ──
    else:
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(30, 30, 30)
        clean_content = clean_latex(latex_code)
        pdf.multi_cell(0, 7, clean_content)

    return bytes(pdf.output())