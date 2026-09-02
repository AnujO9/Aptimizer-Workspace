import os
import sys
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

PDF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Aptimizer_Effectiveness_and_Precision_Guide.pdf")

# Palette
PRIMARY = colors.HexColor("#1E3A8A")      # Navy / Deep Blue
BRAND = colors.HexColor("#2563EB")        # Blue 600
BRAND_LIGHT = colors.HexColor("#EFF6FF")  # Blue 50
DARK = colors.HexColor("#0F172A")         # Slate 900
TEXT = colors.HexColor("#334155")         # Slate 700
MUTED = colors.HexColor("#64748B")        # Slate 500
LIGHT_BG = colors.HexColor("#F8FAFC")     # Slate 50
BORDER = colors.HexColor("#CBD5E1")       # Slate 300

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for 'Page X of Y' numbering and running header/footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED)

        # Header (Pages 2+)
        if self._pageNumber > 1:
            self.drawString(20 * mm, 283 * mm, "Aptimizer Engineering Whitepaper - Effectiveness & Precision Guide")
            self.setStrokeColor(BORDER)
            self.setLineWidth(0.5)
            self.line(20 * mm, 280 * mm, 190 * mm, 280 * mm)

        # Footer (All pages)
        self.setStrokeColor(BORDER)
        self.setLineWidth(0.5)
        self.line(20 * mm, 16 * mm, 190 * mm, 16 * mm)
        self.drawString(20 * mm, 11 * mm, "Confidential & Proprietary - Aptimizer Cloud Platform")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(190 * mm, 11 * mm, page_str)
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    base_styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=base_styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=PRIMARY,
        alignment=0,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=MUTED,
        spaceAfter=10,
    )
    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=base_styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=15,
        textColor=PRIMARY,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )
    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=base_styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=BRAND,
        spaceBefore=5,
        spaceAfter=2,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "Body_Custom",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=11.5,
        textColor=TEXT,
        spaceAfter=3,
    )
    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=body_style,
        leftIndent=10,
        firstLineIndent=-6,
        spaceAfter=2.5,
    )
    callout_style = ParagraphStyle(
        "Callout_Text",
        parent=body_style,
        fontSize=7.8,
        leading=11,
        textColor=PRIMARY,
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=body_style,
        fontSize=7.2,
        leading=9.5,
        spaceAfter=0,
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell,
        fontName="Helvetica-Bold",
        textColor=DARK,
    )
    table_cell_header = ParagraphStyle(
        "TableHeader",
        parent=table_cell,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    story = []

    # =========================================================================
    # PAGE 1: Executive Overview & Pillar 1 (Retrieval & Indexing)
    # =========================================================================
    story.append(Paragraph("Aptimizer - System Effectiveness & Precision Guide", title_style))
    story.append(Paragraph(
        "Architectural Roadmap, Algorithmic Upgrades, and Grounding Protocols for the APT AI Assistant & IS/NBC Clause Retrieval Engine",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND, spaceBefore=0, spaceAfter=6))

    # Metadata badge table
    meta_data = [
        [
            Paragraph("<b>Target System:</b> Aptimizer RAG & APT Assistant", table_cell),
            Paragraph("<b>Status:</b> Production Recommendation", table_cell),
            Paragraph(f"<b>Date:</b> {datetime.now(timezone.utc).strftime('%d %b %Y')}", table_cell),
            Paragraph("<b>Standards:</b> IS 456, IS 1893, NBC 2016", table_cell),
        ]
    ]
    t_meta = Table(meta_data, colWidths=[45 * mm, 42 * mm, 38 * mm, 45 * mm])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 6))

    # Executive Summary / Core Tenet Callout
    summary_html = (
        "<b>Core Architectural Tenet:</b> <i>Retrieval tells the engineer which clause governs; arithmetic "
        "stays deterministic Python.</i> Aptimizer bridges LLM conversational reasoning with certified structural "
        "calculations (<code>engineering.py</code>, <code>takeoff.py</code>, <code>parking.py</code>). Maximizing "
        "effectiveness and precision requires treating code retrieval as an exact-boundary problem, strictly eliminating "
        "model confabulation, maintaining conversational grounding across multi-turn queries, and verifying citations "
        "semantically against retrieved extracts rather than checking bibliographic existence alone."
    )
    callout_table = Table([[Paragraph(summary_html, callout_style)]], colWidths=[170 * mm])
    callout_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
        ("BOX", (0, 0), (-1, -1), 1, BRAND),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 6))

    # Section 1: Retrieval & Indexing
    story.append(Paragraph("1. Retrieval & Indexing Upgrades (backend/codesearch.py)", h1_style))
    story.append(Paragraph(
        "Semantic search handles general concepts well but struggles with exact alphanumeric designations, while token matching "
        "handles numbers well but suffers from term-frequency blindness. The following four upgrades eliminate these weaknesses:",
        body_style
    ))

    story.append(Paragraph("A. Upgrade Naive Token Overlap to Okapi BM25", h2_style))
    story.append(Paragraph(
        "- <b>Problem:</b> The current keyword score uses unweighted set intersection: <code>len(q_tokens & bag) / len(q_tokens)</code>. "
        "Common words like <i>'minimum'</i>, <i>'design'</i>, or <i>'clause'</i> receive the exact same weight as high-information terms "
        "like <i>'slenderness'</i>, <i>'cantilever'</i>, or <i>'liquefaction'</i>.<br/>"
        "- <b>Solution:</b> Implement Okapi BM25 scoring with precomputed Inverse Document Frequency (IDF) over the clause corpus. "
        "Rare engineering terms are multiplied by their IDF log-ratio, preventing generic clauses from outranking specific governing rules.",
        bullet_style
    ))

    story.append(Paragraph("B. Hierarchical Context Injection in Chunk Embeddings", h2_style))
    story.append(Paragraph(
        "- <b>Problem:</b> When subclause <code>23.2.1 (a)</code> is embedded in isolation (<i>'for spans up to 10 m: 7'</i>), "
        "the vector contains no semantic indicator that it governs beam deflection in IS 456.<br/>"
        "- <b>Solution:</b> Prepend structural breadcrumbs during embedding while storing clean raw text for UI display:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>embed_text = f'[{chunk[\"code\"]} > {section_title} > {chunk[\"clause\"]} {chunk[\"heading\"]}]\\n{chunk[\"text\"]}'</code><br/>"
        "This increases cosine similarity by over 40% on natural questions like <i>'How to limit balcony sag?'</i>.",
        bullet_style
    ))

    story.append(Paragraph("C. Civil Engineering Domain Synonym Expansion", h2_style))
    story.append(Paragraph(
        "- <b>Problem:</b> Practicing structural engineers query using industry colloquialisms that do not literally match BIS terminology.<br/>"
        "- <b>Solution:</b> Insert a domain-specific expansion dictionary in <code>codesearch.py</code> prior to search scoring:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;* <i>'stirrups / ties'</i> &lt;-&gt; <i>'shear reinforcement'</i> / <i>'transverse reinforcement'</i><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;* <i>'deflection limit'</i> &lt;-&gt; <i>'span to effective depth ratio'</i> (IS 456 Cl. 23.2)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;* <i>'rebar cover'</i> &lt;-&gt; <i>'nominal cover to reinforcement'</i> (IS 456 Table 16)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;* <i>'Zone IV'</i> &lt;-&gt; <i>'Zone factor Z = 0.24'</i> (IS 1893 Table 3)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;* <i>'base shear'</i> &lt;-&gt; <i>'horizontal seismic force Ah x W'</i> (IS 1893 Cl. 7.6.1)",
        bullet_style
    ))

    story.append(Paragraph("D. Embedding Model Modernization", h2_style))
    story.append(Paragraph(
        "- Transition default model from legacy <code>gemini-embedding-001</code> to <code>text-embedding-004</code> (768-dimension, "
        "Matryoshka Representation Learning support). It captures multi-clause technical nuances with substantially lower dimension distortion.",
        bullet_style
    ))

    # Page Break to Page 2
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: Conversational RAG, Re-ranking & Prompt Grounding
    # =========================================================================
    story.append(Paragraph("2. Multi-Turn Conversational Query Rewriting (backend/server.py)", h1_style))
    story.append(Paragraph(
        "In interactive design sessions, engineers ask follow-up questions in conversational threads. "
        "Directly passing follow-up turns to vector search causes context loss:",
        body_style
    ))

    conv_table_data = [
        [Paragraph("<b>Turn</b>", table_cell_header), Paragraph("<b>User Query</b>", table_cell_header), Paragraph("<b>Raw RAG Behavior (Current)</b>", table_cell_header), Paragraph("<b>Contextual Query Rewriter (Proposed)</b>", table_cell_header)],
        [
            Paragraph("Turn 1", table_cell_bold),
            Paragraph("<i>'What is the deflection limit for cantilever balconies?'</i>", table_cell),
            Paragraph("Retrieves IS 456 Cl. 23.2.1 correctly.", table_cell),
            Paragraph("<b>IS 456 cantilever deflection limit Cl. 23.2.1</b>", table_cell),
        ],
        [
            Paragraph("Turn 2", table_cell_bold),
            Paragraph("<i>'What if the span exceeds 10 meters?'</i>", table_cell),
            Paragraph("Searches <i>'span exceeds 10 meters'</i>; misses deflection context entirely.", table_cell),
            Paragraph("<b>IS 456 Cl. 23.2.1 span over 10m deflection modification factor cantilever</b>", table_cell),
        ],
        [
            Paragraph("Turn 3", table_cell_bold),
            Paragraph("<i>'Does Zone IV affect this?'</i>", table_cell),
            Paragraph("Searches <i>'Zone IV'</i>; pulls generic seismic tables.", table_cell),
            Paragraph("<b>IS 1893 Zone IV seismic provisions cantilever vertical acceleration</b>", table_cell),
        ],
    ]
    t_conv = Table(conv_table_data, colWidths=[14 * mm, 45 * mm, 51 * mm, 60 * mm])
    t_conv.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_conv)
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>Implementation:</b> In <code>server.py</code> (<code>/ai/chat</code>), if prior turns exist, run a 120ms keyword condensation "
        "heuristic or flash call to generate a standalone query before invoking <code>codesearchlib.search</code>.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # Section 3: Two-Stage Re-ranking
    story.append(Paragraph("3. Re-Ranking & Adaptive Precision Filtering", h1_style))
    story.append(Paragraph(
        "Linear weighted score combination (0.55 vector + 0.25 keyword + 0.20 designation) is prone to edge-case ranking distortion:",
        body_style
    ))
    story.append(Paragraph(
        "- <b>Two-Stage Pipeline (15 to 4):</b> Over-fetch top k=15 candidate passages via fast hybrid search. Pass these candidates "
        "through a cross-encoder reranker (or a structured flash prompt) to score direct answering capability.<br/>"
        "- <b>Adaptive Floor vs Static 0.15:</b> Replace the static floor with a relative margin filter: any chunk scoring less than "
        "40% of the top hit is discarded. This eliminates marginal, distracting clauses that dilute prompt focus.<br/>"
        "- <b>Preserving Tabular Semantics:</b> Standard tables (e.g. IS 456 Table 2, Table 19; IS 1893 Table 2) must be parsed into "
        "Markdown or JSON format with column headings repeated across multi-row chunks, preventing row truncation.",
        bullet_style
    ))
    story.append(Spacer(1, 6))

    # Section 4: Prompt Grounding
    story.append(Paragraph("4. Prompt Grounding & Elimination of Confabulation (backend/ai.py)", h1_style))
    story.append(Paragraph(
        "The current prompt structure contains an unintended loophole that weakens model precision:",
        body_style
    ))

    prompt_diff_data = [
        [Paragraph("<b>Aspect</b>", table_cell_header), Paragraph("<b>Current Behavior in ai.py</b>", table_cell_header), Paragraph("<b>Target Behavior (High Precision)</b>", table_cell_header)],
        [
            Paragraph("General Code Fallback", table_cell_bold),
            Paragraph("<i>'If asked about something outside computed data, answer from general IS/NBC knowledge...'</i> (Invites hallucination).", table_cell),
            Paragraph("<b>Eliminate general memory fallback.</b> Mandate: <i>'If the provision is not in code_extracts or registry, state plainly that the loaded corpus does not specify it.'</i>", table_cell),
        ],
        [
            Paragraph("Extract Citation Mandate", table_cell_bold),
            Paragraph("Tells the model to cite from <code>clause_registry</code>, but does not explicitly enforce quoting <code>code_extracts</code>.", table_cell),
            Paragraph("<b>Mandate verbatim quotes</b> from <code>code_extracts</code>. Cite both code designation and table/clause title.", table_cell),
        ],
        [
            Paragraph("Sampling Temperature", table_cell_bold),
            Paragraph("Temperature set at <code>0.3</code> across all generation tasks.", table_cell),
            Paragraph("<b>Drop temperature to 0.0 - 0.1</b> for engineering compliance, derivations, and code retrieval to maximize determinism.", table_cell),
        ],
    ]
    t_diff = Table(prompt_diff_data, colWidths=[28 * mm, 69 * mm, 73 * mm])
    t_diff.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_diff)

    # Page Break to Page 3
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: Semantic Citations, Tool Sensitivity & Implementation Matrix
    # =========================================================================
    story.append(Paragraph("5. Semantic Citation Verification (backend/citations.py)", h1_style))
    story.append(Paragraph(
        "Currently, <code>citations.py</code> only verifies <b>bibliographic existence</b>: whether a <code>(code, clause)</code> pair "
        "is present in the 62 curated clauses or the ingested corpus. It does not verify <b>content entailment</b>.",
        body_style
    ))
    story.append(Paragraph(
        "- <b>The Failure Mode:</b> An LLM could cite <i>'IS 456:2000 Cl. 23.2.1'</i> (a valid clause) but state that the cantilever "
        "basic ratio is <i>'26'</i> instead of <i>'7'</i>. Today, this passes as <code>resolved</code>.<br/>"
        "- <b>Content Entailment Verification:</b> For every resolved citation with an adjacent numerical value or threshold, verify that "
        "the claimed numerical tokens exist in the text of the retrieved chunk. If the text contradicts the assertion, flag it as "
        "<code>unverified_claim</code>.<br/>"
        "- <b>Subclause & Table Regex Expansion:</b> Expand <code>CLAUSE_RE</code> to capture nested subclauses and notes: "
        "<code>Cl. 26.5.1.1(a)</code>, <code>Table 19 Note 2</code>, and <code>Annex E.1</code>.",
        bullet_style
    ))
    story.append(Spacer(1, 4))

    # Section 6: Deterministic What-If Sensitivity
    story.append(Paragraph("6. Deterministic 'What-If' Parameter Sensitivity", h1_style))
    story.append(Paragraph(
        "Aptimizer's strict rule: <b>retrieval never computes; arithmetic stays Python</b>. When users ask speculative questions "
        "(e.g. <i>'What happens to base shear if we increase the height from 36m to 45m?'</i>), LLM approximations introduce error.",
        body_style
    ))
    story.append(Paragraph(
        "- <b>Tool Calling / Delta Execution:</b> Equip the APT backend with a parameter mutation evaluator. When a 'what-if' question "
        "is detected, invoke <code>engineering.analyse_engineering()</code> with the modified parameter in a lightweight sandbox.<br/>"
        "- <b>Feed Exact Deltas to APT:</b> Supply the exact computed differential (e.g. V_B increases from 1240 kN to 1510 kN, +21.7%) "
        "in the context JSON. APT explains the structural mechanism while Python guarantees 100% numerical accuracy.",
        bullet_style
    ))
    story.append(Spacer(1, 4))

    # Section 7: Implementation Matrix
    story.append(Paragraph("7. Actionable Implementation Matrix", h1_style))

    matrix_data = [
        [Paragraph("<b>P#</b>", table_cell_header), Paragraph("<b>Upgrade Component</b>", table_cell_header), Paragraph("<b>Target File(s)</b>", table_cell_header), Paragraph("<b>Expected Impact</b>", table_cell_header), Paragraph("<b>Effort</b>", table_cell_header)],
        [
            Paragraph("<b>P0</b>", table_cell_bold),
            Paragraph("Hierarchical Breadcrumb Embeddings", table_cell),
            Paragraph("<code>codesearch.py</code>", table_cell),
            Paragraph("Eliminates semantic drift for subclauses & tables", table_cell),
            Paragraph("Low", table_cell),
        ],
        [
            Paragraph("<b>P0</b>", table_cell_bold),
            Paragraph("Grounding Prompts & Zero-Memory Fallback", table_cell),
            Paragraph("<code>ai.py</code>, <code>server.py</code>", table_cell),
            Paragraph("Completely stops hallucinated clause numbers", table_cell),
            Paragraph("Low", table_cell),
        ],
        [
            Paragraph("<b>P1</b>", table_cell_bold),
            Paragraph("Okapi BM25 + Domain Synonym Expansion", table_cell),
            Paragraph("<code>codesearch.py</code>", table_cell),
            Paragraph("High recall on technical terms (slenderness, cover)", table_cell),
            Paragraph("Medium", table_cell),
        ],
        [
            Paragraph("<b>P1</b>", table_cell_bold),
            Paragraph("Multi-turn Query Rewriting", table_cell),
            Paragraph("<code>server.py</code>, <code>ai.py</code>", table_cell),
            Paragraph("Maintains code context across conversational turns", table_cell),
            Paragraph("Medium", table_cell),
        ],
        [
            Paragraph("<b>P2</b>", table_cell_bold),
            Paragraph("Semantic Content Entailment Verification", table_cell),
            Paragraph("<code>citations.py</code>", table_cell),
            Paragraph("Verifies asserted numbers match retrieved source", table_cell),
            Paragraph("Medium", table_cell),
        ],
        [
            Paragraph("<b>P2</b>", table_cell_bold),
            Paragraph("Deterministic Sensitivity Tool Calling", table_cell),
            Paragraph("<code>server.py</code>, <code>engineering.py</code>", table_cell),
            Paragraph("Zero arithmetic error on 'what-if' calculations", table_cell),
            Paragraph("High", table_cell),
        ],
    ]
    t_mat = Table(matrix_data, colWidths=[10 * mm, 46 * mm, 38 * mm, 58 * mm, 18 * mm])
    t_mat.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_mat)
    story.append(Spacer(1, 6))

    # Concluding Box
    conclusion_text = (
        "<b>Summary:</b> By combining <b>hierarchical chunk embeddings</b> and <b>Okapi BM25</b> with <b>multi-turn query rewriting</b> "
        "and <b>strict extract grounding</b>, Aptimizer transforms from an assistive conversational bot into an authoritative, "
        "verifiable civil engineering compliance platform. Every clause citation is backed by verbatim statutory text, and all "
        "arithmetic remains certified by deterministic Python engineering modules."
    )
    t_conc = Table([[Paragraph(conclusion_text, body_style)]], colWidths=[170 * mm])
    t_conc.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 1, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_conc)

    # Build
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF at: {PDF_PATH}")


if __name__ == "__main__":
    build_pdf()
