#!/usr/bin/env python3
"""
================================================================================
 EDITABLE INVOICE FORM GENERATOR
================================================================================

WHAT THIS SCRIPT DOES
---------------------
Running `python3 make_invoice.py` builds `Editable_Invoice.pdf` next to this
file: a 5-page, Section 508-compliant, fillable PDF invoice with interactive
JavaScript logic that runs in Adobe Acrobat / Acrobat Reader.

HOW IT WORKS — TWO PHASES
-------------------------
PHASE 1 (reportlab): draws the visual layout (labels, colored bars, boxes)
    and creates the basic form fields (text boxes, dropdowns, checkboxes).
    reportlab can NOT add JavaScript or buttons, so phase 1 writes a
    temporary file `_invoice_base.pdf`.

PHASE 2 (pypdf): opens that temporary file and injects everything reportlab
    can't do: JavaScript actions on fields, the two buttons (logo + submit),
    required flags, accessibility tagging (the "structure tree"), and
    document metadata. The result is saved as `Editable_Invoice.pdf`.

If you change anything, just re-run the script — it rebuilds from scratch
every time. The temporary `_invoice_base.pdf` can be deleted afterwards.

THINGS A JUNIOR DEV WILL MOST LIKELY NEED TO CHANGE
---------------------------------------------------
| What you want to change            | Where to look                        |
|------------------------------------|--------------------------------------|
| Submit-to email address            | SUBMIT_EMAIL constant below          |
| Document version in the footer     | DOC_VERSION constant below           |
| HR name/email (locked fields)      | HR_NAME / HR_EMAIL constants         |
| Dropdown choices                   | SUBJECTS / INVOICE_TYPES /           |
|                                    | CATEGORIES / STATES / (and           |
|                                    | EXPENSE_CATEGORIES further down)     |
| Which Subject shows which Types    | TYPE_RULES / CAT_RULES (phase 2)     |
| Auto-picked category per Type      | AUTO_CATEGORY (phase 2)              |
| Auto-fill dollar amounts           | cat_js block + doc_js block (search  |
|                                    | for "$100,000" / 7500 / 15000)    |
| Which fields are required          | REQUIRED list (phase 2)              |
| Number of table pages              | N_TABLE_PAGES constant (page layout) |
| Colors                             | NAVY / ACCENT / ... constants        |

PREREQUISITES:  pip3 install reportlab pypdf
================================================================================
"""

import json   # used to embed Python lists/dicts into JavaScript code safely
import os

# --- PDF drawing library (phase 1) ---
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfbase.pdfmetrics import stringWidth   # measures text width in points
from reportlab.pdfgen import canvas

# --- PDF manipulation library (phase 2) ---
from pypdf import PdfReader, PdfWriter
# These "generic" classes are pypdf's wrappers for raw PDF object types.
# A PDF file is a tree of dictionaries/arrays/numbers/strings — these let us
# build those objects by hand:
from pypdf.generic import (
    ArrayObject, BooleanObject, DecodedStreamObject, DictionaryObject,
    FloatObject, NameObject, NumberObject, TextStringObject,
)

# ==============================================================================
# CONFIGURATION CONSTANTS — most simple changes happen here
# ==============================================================================

import sys

# Output files land in the same folder as this script, wherever it lives.
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Table capacity: pass the desired row count as a command-line argument
# (any positive multiple of 35 = rows per page). Default is 210.
#   python3 make_invoice.py        ->  Editable_Invoice.pdf         (210 rows)
#   python3 make_invoice.py 140    ->  Editable_Invoice_140Rows.pdf (140 rows)
TABLE_ROWS_TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 210
assert TABLE_ROWS_TARGET > 0 and TABLE_ROWS_TARGET % 35 == 0, \
    "row count must be a positive multiple of 35 (35 rows per table page)"
N_TABLE_PAGES = TABLE_ROWS_TARGET // 35
TOTAL_PAGES = N_TABLE_PAGES + 1     # + the main page (footer "Page X of Y")

TMP = os.path.join(OUT_DIR, "_invoice_base.pdf")      # phase-1 intermediate
FINAL = os.path.join(                                  # the deliverable
    OUT_DIR,
    "Editable_Invoice.pdf" if TABLE_ROWS_TARGET == 210
    else f"Editable_Invoice_{TABLE_ROWS_TARGET}Rows.pdf")

SUBMIT_EMAIL = "test@test.com"      # where the SUBMIT button emails the PDF
DOC_VERSION = "V.1.0.0"             # shown in every page footer
DOC_VERSION_DATE = "Revision Date: 07/26"   # shown next to the version
DOC_TITLE = "Service Provider Invoice Form"   # window title / metadata

# Color palette. HexColor takes normal web colors ("#RRGGBB").
NAVY = HexColor("#1F3B63")          # section header bars
ACCENT = HexColor("#2E5E9E")        # table header bars
LABEL_GRAY = HexColor("#5A6572")    # small field labels
FIELD_FILL = HexColor("#F4F7FB")    # light background inside every field
FIELD_BORDER = HexColor("#B9C4D1")  # field border lines
LINE_GRAY = HexColor("#D8DEE6")     # footer rule
RED = HexColor("#C0392B")           # required-field asterisks

# Dropdown choice lists. Order here = order shown in the dropdown.
STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]

SUBJECTS = ["T", "J", "W"]

INVOICE_TYPES = ["T-Initial", "T-Quarterly", "J-Initial",
                 "J-Quarterly", "W-Initial", "W-Quarterly"]

# NOTE: several rules below refer to these by position (CATEGORIES[0] etc.),
# so if you reorder this list, also check TYPE_RULES/CAT_RULES/AUTO_CATEGORY.
CATEGORIES = [
    "CL 1: T, Initial Stipend 1-Time Only",
    "CL 4: T, Quarterly Incentive",
    "CL 6: J, Initial Stipend 1-Time Only",
    "CL 8: J, Quarterly Incentive",
    "CL 9: W, Initial Stipend 1-Time Only",
    "CL 11: W, Quarterly Incentive",
]

# ==============================================================================
# PAGE GEOMETRY
# ==============================================================================
# PDF coordinates: origin (0,0) is the BOTTOM-LEFT corner of the page and
# units are "points" (72 points = 1 inch). Letter = 612 x 792 points.
# So "y = H - 100" means "100 points down from the top edge".
W, H = letter
ML, MR = 36, 36          # left / right page margins (0.5 inch)
CW = W - ML - MR         # usable content width (540 pt)

# The reportlab canvas is like a pen we draw with; c.acroForm creates fields.
c = canvas.Canvas(TMP, pagesize=letter)
form = c.acroForm

FIELD_H = 15             # standard height of one form field, in points

# ------------------------------------------------------------------------------
# ACCESSIBILITY BOOKKEEPING (important — read before adding/removing anything)
# ------------------------------------------------------------------------------
# Screen readers need to know the READING ORDER of everything on the page.
# Phase 2 builds that "structure tree" from this SEQ list. Therefore:
#
#   EVERY drawn text must append   ("text", role, "the text")   to SEQ, and
#   EVERY form field must append   ("field", "FieldName")       to SEQ,
#   in the exact order they are drawn/created.
#
# Roles: "P" = paragraph, "H2" = section heading, "Artifact" = decorative
# text screen readers should SKIP (we use it for page-number footers).
#
# The helper functions below (label/tfield/combo/section/footer) do this
# automatically. If you draw text directly with c.drawString(...), you MUST
# add the SEQ entry yourself or phase 2 stops with an assertion error
# ("BT blocks != text draws") — that error means SEQ and the drawn text
# got out of sync.
SEQ = []

# Some dropdowns should start EMPTY (no selection). reportlab has a bug that
# crashes when a dropdown is created with an empty value, so combo() creates
# them with a temporary value and lists their names here; phase 2 clears them.
CLEAR_VALUE = []


# ==============================================================================
# DRAWING / FIELD HELPER FUNCTIONS  (used everywhere in phase 1)
# ==============================================================================

def label(x, y, text, size=6.8, required=False):
    """Draw a small gray UPPERCASE label at (x, y).

    required=True also draws a red asterisk right after the text.
    Both the label and the asterisk are recorded in SEQ for accessibility.
    """
    c.setFont("Helvetica-Bold", size)
    c.setFillColor(LABEL_GRAY)
    c.drawString(x, y, text.upper())
    SEQ.append(("text", "P", text))
    if required:
        # stringWidth measures the label so the * lands just after it
        w = stringWidth(text.upper(), "Helvetica-Bold", size)
        c.setFillColor(RED)
        c.drawString(x + w + 2, y, "*")
        SEQ.append(("text", "P", "required"))


def tfield(name, x, y, w, tooltip="", value="", flags="", font_size=9, h=FIELD_H,
           maxlen=100):
    """Create a single-line text form field.

    name     : the field's internal name — scripts find fields by this name,
               so NEVER change a name without updating every script using it.
    tooltip  : what a screen reader announces (phase 2 may override it).
    value    : pre-filled text (e.g. "Will Be Filled Back Office").
    flags    : reportlab field flags, e.g. "readOnly" or "multiline readOnly".
    maxlen   : max characters the user may type (also clips pre-filled text —
               raise it if you pre-fill something longer than 100 chars).
    """
    form.textfield(
        name=name, tooltip=tooltip or name, value=value, maxlen=maxlen,
        x=x, y=y, width=w, height=h,
        fontName="Helvetica", fontSize=font_size,
        borderColor=FIELD_BORDER, fillColor=FIELD_FILL, textColor=black,
        borderWidth=0.7, borderStyle="solid", fieldFlags=flags, forceBorder=True,
    )
    SEQ.append(("field", name))


def combo(name, x, y, w, options, tooltip="", placeholder="-- Select an option --",
          editable=False, font_size=9):
    """Create a dropdown (combo box) form field.

    placeholder : shown as the first list item AND the default selection.
                  Pass placeholder="" for a dropdown that starts blank.
    editable    : True lets the user TYPE a custom value not in the list
                  (used by the Expense Category cells on the table pages).
    """
    # reportlab crashes if a dropdown is created with an empty value
    # (an internal bug: variable 'lbextras' is never set on that code path).
    # Workaround: create it with a real value now, and phase 2 clears it —
    # see the CLEAR_VALUE loop in the post-processing section.
    if placeholder == "":
        opts = [""] + list(options)
        value = options[0]
        CLEAR_VALUE.append(name)
    else:
        opts = [placeholder] + list(options)
        value = placeholder
    form.choice(
        name=name, tooltip=tooltip or name, value=value,
        x=x, y=y, width=w, height=FIELD_H, options=opts,
        fontName="Helvetica", fontSize=font_size,
        borderColor=FIELD_BORDER, fillColor=FIELD_FILL, textColor=black,
        borderWidth=0.7, borderStyle="solid",
        fieldFlags="combo edit" if editable else "combo", forceBorder=True,
    )
    SEQ.append(("field", name))


def footer(page_no):
    """Draw the page footer: thin rule, version (left), page number (right).

    The texts are recorded with role "Artifact" — accessibility rules say
    page numbers are 'pagination artifacts' that screen readers must skip.
    """
    c.setStrokeColor(LINE_GRAY)
    c.setLineWidth(0.6)
    c.line(ML, 24, W - MR, 24)
    c.setFont("Helvetica", 7)
    c.setFillColor(LABEL_GRAY)
    c.drawString(ML, 13, f"{DOC_VERSION}  |  {DOC_VERSION_DATE}")
    SEQ.append(("text", "Artifact", f"{DOC_VERSION}  |  {DOC_VERSION_DATE}"))
    c.drawRightString(W - MR, 13, f"Page {page_no} of {TOTAL_PAGES}")
    SEQ.append(("text", "Artifact", f"Page {page_no} of {TOTAL_PAGES}"))


def section(y, title):
    """Draw a navy section-header bar with white uppercase title.

    Recorded as role "H2" so screen readers treat it as a heading.
    """
    c.setFillColor(NAVY)
    c.rect(ML, y, CW, 15, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(ML + 6, y + 4.2, title.upper())
    SEQ.append(("text", "H2", title))


# ==============================================================================
# PHASE 1 — PAGE 1 LAYOUT
# ==============================================================================
# The page is drawn top-to-bottom. `y` is a cursor that starts near the top
# and moves DOWN (y -= ...) as each row is placed. If you add a row, subtract
# more from y and make sure the bottom (acknowledgement/submit row) still
# fits above the footer at y=24.

# ---------------- HEADER: logo placeholder ----------------
# A dashed box with hint text. The actual "click to add logo" button is an
# invisible widget added in phase 2, positioned exactly over this box —
# if you move/resize this box, update `lx, ly, lw, lh` in phase 2 to match.
logo_x, logo_y, logo_w, logo_h = ML, H - 100, 140, 66
c.setStrokeColor(FIELD_BORDER)
c.setDash(3, 3)                       # dashed line pattern: 3pt on, 3pt off
c.setLineWidth(1)
c.rect(logo_x, logo_y, logo_w, logo_h, fill=0, stroke=1)
c.setDash()                           # back to solid lines
c.setFont("Helvetica", 7.5)
c.setFillColor(LABEL_GRAY)
c.drawCentredString(logo_x + logo_w / 2, logo_y + logo_h / 2 + 4, "ORGANIZATION LOGO")
SEQ.append(("text", "P", "Organization logo"))
c.drawCentredString(logo_x + logo_w / 2, logo_y + logo_h / 2 - 6, "(click to add image)")
SEQ.append(("text", "P", "(click to add image)"))
SEQ.append(("field", "LogoButton"))   # placeholder in reading order; the
                                      # widget itself is created in phase 2

# ---------------- SECTION: INVOICE DETAILS ----------------
# Two-column grid: col 1 starts at ML, col 2 starts at `col2`.
col2 = ML + CW / 2 + 8    # x where the right-hand column begins
half = CW / 2 - 8         # width of one column

y = H - 122
section(y, "Invoice Details")
# small white legend on the right side of the section bar
c.setFont("Helvetica", 6.5)
c.setFillColor(white)
c.drawRightString(W - MR - 6, y + 4.6, "* Required field")
SEQ.append(("text", "P", "Fields marked with an asterisk are required"))

y -= 27
label(ML, y + FIELD_H + 3, "Subject", required=True)
combo("Subject", ML, y, half, SUBJECTS)
label(col2, y + FIELD_H + 3, "Invoice Type", required=True)
combo("InvoiceType", col2, y, half, INVOICE_TYPES)

y -= 32
# Checkbox row. The caption is drawn BEFORE the checkbox on purpose:
# SEQ order = reading order, and screen readers should hear the label first.
c.setFont("Helvetica-Bold", 8.2)
c.setFillColor(HexColor("#333B45"))
c.drawString(ML + 18, y + 3.5, "SAM Registration Active")
SEQ.append(("text", "P", "SAM Registration Active"))
c.setFillColor(RED)
c.drawString(ML + 18 + stringWidth("SAM Registration Active", "Helvetica-Bold", 8.2) + 2,
             y + 3.5, "*")
SEQ.append(("text", "P", "required"))
form.checkbox(name="RegistrationActive", tooltip="SAM Registration Active",
              checked=False, x=ML, y=y, size=13, buttonStyle="check",
              borderColor=FIELD_BORDER, fillColor=FIELD_FILL, textColor=NAVY,
              borderWidth=0.9)
SEQ.append(("field", "RegistrationActive"))
label(col2, y + FIELD_H + 3, "Have You Verified Banking Information in SAM.gov?", required=True)
combo("BankingVerified", col2, y, half, ["Yes", "No"])

# ---------------- SECTION: SERVICE PROVIDER ----------------
y -= 26
section(y, "Service Provider Information")
y -= 27
label(ML, y + FIELD_H + 3, "Service Provider Name", required=True)
tfield("ServiceProviderName", ML, y, CW)          # full-width field
y -= 31
label(ML, y + FIELD_H + 3, "Street Address", required=True)
tfield("StreetAddress", ML, y, CW)
y -= 31
# City / State / Zip share one row; the three widths must be <= CW with gaps.
w_city, w_state, w_zip = 230, 190, 104
label(ML, y + FIELD_H + 3, "City", required=True)
tfield("City", ML, y, w_city)
sx = ML + w_city + 8
label(sx, y + FIELD_H + 3, "State", required=True)
combo("State", sx, y, w_state, STATES, placeholder="-- Select State --")
zx = sx + w_state + 8
label(zx, y + FIELD_H + 3, "Zip Code", required=True)
tfield("ZipCode", zx, y, w_zip, maxlen=5)  # 5-digit ZIP (format enforced below)
y -= 31
label(ML, y + FIELD_H + 3, "POC Name", required=True)
tfield("POCName", ML, y, half)
label(col2, y + FIELD_H + 3, "POC Email", required=True)
tfield("POCEmail", col2, y, half)
y -= 31
# Three equal columns: Order Number | Registration No | Invoice Number.
w3 = (CW - 16) / 3
label(ML, y + FIELD_H + 3, "Order Number")
# Locked field with a placeholder message; back office fills it in later
# using Acrobat Pro (read-only blocks form FILLING, not form EDITING).
tfield("OrderNumber", ML, y, w3, value="Will Be Filled Back Office",
       flags="readOnly")
x2 = ML + w3 + 8
label(x2, y + FIELD_H + 3, "SAM Registration No. (UEI)", required=True)
tfield("RegistrationNo", x2, y, w3, maxlen=12)  # UEI = 12 alphanumeric chars
x3 = x2 + w3 + 8
label(x3, y + FIELD_H + 3, "Invoice Number")
tfield("InvoiceNumber", x3, y, w3, value="Will Be Filled Back Office",
       flags="readOnly")

# ---------------- SECTION: HR / DHR ----------------
y -= 26
section(y, "HR / DHR Information")
y -= 27
label(ML, y + FIELD_H + 3, "HR Name")
tfield("HRName", ML, y, half, flags="readOnly")    # filled by script
label(col2, y + FIELD_H + 3, "HR Email")
tfield("HREmail", col2, y, half, flags="readOnly")  # filled by script
y -= 31
label(ML, y + FIELD_H + 3, "DHR Name")
tfield("DHRName", ML, y, half, flags="readOnly")    # locked & empty
label(col2, y + FIELD_H + 3, "DHR Email")
tfield("DHREmail", col2, y, half, flags="readOnly")

# ---------------- SECTION: INVOICE PERIOD ----------------
y -= 26
section(y, "Invoice Period & Reference")
y -= 27
# Four equal columns. To reorder the fields, just reorder this list —
# tab order and screen-reader order follow creation order automatically.
w4 = (CW - 24) / 4
xs = [ML + i * (w4 + 8) for i in range(4)]
for x, (nm, lb, req) in zip(xs, [
    ("OperationalDate", "Operational Date (mm/dd/yyyy)", False),
    ("InvoiceStartDate", "Invoice Start Date (mm/dd/yyyy)", True),
    ("InvoiceEndDate", "Invoice End Date (mm/dd/yyyy)", True),
    ("InvoiceDate", "Invoice Date (mm/dd/yyyy)", True),
]):
    label(x, y + FIELD_H + 3, lb, size=5.9, required=req)
    if nm == "OperationalDate":
        # locked placeholder; HR fills the real date later via Acrobat Pro
        tfield(nm, x, y, w4, value="Will Be Filled By HR", flags="readOnly")
    else:
        tfield(nm, x, y, w4)
# (date VALIDATION for these fields is attached in phase 2)

# ---------------- SECTION: TOTAL INVOICE SUMMARY ----------------
y -= 26
section(y, "Total Invoice Summary")
y -= 27
label(ML, y + FIELD_H + 3, "Invoice Category")
combo("InvoiceCategory", ML, y, CW, CATEGORIES)

# --- items mini-table: 5 rows of description + amount ---
# IMPORTANT: rows 1-3 are RESERVED — JavaScript writes the roll-up summaries
# from the table pages into them (row 1 Transportation, row 2 Equipment
# Package, row 3 Quarterly Expense). Rows 4-5 are free for manual entries.
y -= 24
desc_w = CW - 140            # description column width
amt_x = ML + desc_w + 8      # where the amount column starts
c.setFillColor(ACCENT)
c.rect(ML, y, CW, 14, fill=1, stroke=0)     # blue header bar
c.setFillColor(white)
c.setFont("Helvetica-Bold", 7.5)
c.drawString(ML + 6, y + 4, "ITEM DESCRIPTION  (e.g. Transportation, Equipment)")
SEQ.append(("text", "P", "Item Description (e.g. Transportation, Equipment)"))
c.drawString(amt_x + 6, y + 4, "AMOUNT ($)")
SEQ.append(("text", "P", "Amount in dollars"))

for i in range(1, 6):
    y -= 19
    tfield(f"ItemDesc{i}", ML, y, desc_w, tooltip=f"Item {i} description")
    tfield(f"Amount{i}", amt_x, y, 132, tooltip=f"Item {i} amount")

# --- total row: label + read-only auto-summed field ---
y -= 22
c.setStrokeColor(NAVY)
c.setLineWidth(1.2)
c.line(amt_x - 90, y + FIELD_H + 4, W - MR, y + FIELD_H + 4)
c.setFont("Helvetica-Bold", 10)
c.setFillColor(NAVY)
c.drawRightString(amt_x - 8, y + 3.5, "TOTAL:")
SEQ.append(("text", "P", "Total"))
tfield("Total", amt_x, y, 132, tooltip="Auto-calculated total", flags="readOnly")
# (the SUM calculation is attached to Total in phase 2)

# --- acknowledgement checkbox (left) + submit button (right) ---
btn_w, btn_h = 190, 26
btn_y = y - 8 - btn_h
btn_x = W - MR - btn_w       # right-aligned; phase 2 places the real button
                             # widget at exactly (btn_x, btn_y)

ACK_LINES = [
    "I hereby certify that all the information provided in this document is true, accurate,",
    "and complete to the best of my knowledge and belief. By submitting this form, I affirm",
    "that I have reviewed the information and take responsibility for its accuracy.",
]
c.setFont("Helvetica-Bold", 6.5)
c.setFillColor(HexColor("#333B45"))
ack_y = btn_y + btn_h / 2 + 7      # 3 lines centered on the button row
for ln in ACK_LINES:
    c.drawString(ML + 18, ack_y, ln)
    SEQ.append(("text", "P", ln))
    ack_y -= 7
c.setFillColor(RED)
c.drawString(ML + 18 + stringWidth(ACK_LINES[-1], "Helvetica-Bold", 6.5) + 2,
             ack_y + 7, "*")
SEQ.append(("text", "P", "required"))
form.checkbox(name="Acknowledgement",
              tooltip="Acknowledgement of accuracy",
              checked=False, x=ML, y=btn_y + btn_h / 2 - 6.5, size=13,
              buttonStyle="check", borderColor=FIELD_BORDER,
              fillColor=FIELD_FILL, textColor=NAVY, borderWidth=0.9)
SEQ.append(("field", "Acknowledgement"))
SEQ.append(("field", "SubmitButton"))   # reading-order placeholder; the
                                        # button widget is created in phase 2

footer(1)

# ==============================================================================
# PHASE 1 — PAGES 2-5: ADDITIONAL ITEMIZED DETAILS (the big table)
# ==============================================================================
# Four identical table pages. Row numbers run CONTINUOUSLY across them:
#   page 2 = rows 1-35, page 3 = 36-70, page 4 = 71-105, page 5 = 106-140.
# Every cell is named  T2_R{row}_C{column}  — e.g. T2_R57_C3 is the Expense
# Category dropdown of row 57 (which sits on page 3). The JavaScript parses
# these names, so DO NOT rename them.
#
# To change the number of table pages, edit N_TABLE_PAGES and TOTAL_PAGES —
# everything else (scripts, tooltips, tagging) adapts automatically.
SEQ_P1 = SEQ    # stash page 1's reading-order list before starting page 2

# Column definitions: (full name used in tooltips, header text lines, width).
# Long headers are split into two stacked lines so they fit their column.
# Widths must add up to CW (the assert below catches mistakes).
TABLE2_COLS = [
    ("First Name", ["FIRST NAME"], 70),
    ("Middle Initial", ["MIDDLE", "INITIAL"], 45),
    ("Last Name", ["LAST NAME"], 70),
    ("Credential Number", ["CREDENTIAL", "NUMBER"], 65),
    # widest column: must fit "Initial Equipment Package" at 7pt
    ("Expense Category", ["EXPENSE", "CATEGORY"], 110),
    ("Equipment", ["EQUIPMENT"], 55),
    ("Transportation", ["TRANSPORTATION"], 65),
    ("Information Technology", ["INFORMATION", "TECHNOLOGY"], 60),
]
assert sum(cw for _, _, cw in TABLE2_COLS) == CW, "column widths must sum to CW"

# Options for the Expense Category dropdowns. Adding an option here makes it
# selectable, but it will have NO auto-fill amount until you also add a rule
# in the cat_js block AND (optionally) a summary row in the doc_js block.
EXPENSE_CATEGORIES = [
    "One-Time Transportation",
    "Initial Equipment Package",
    "Quarterly Incentive",
]

TABLE2_ROWS = 0        # global row counter, keeps counting across pages
TABLE_SEQS = []        # one reading-order list per table page
for tp in range(N_TABLE_PAGES):
    c.showPage()       # finish the current page, start a new blank one
    SEQ = []           # the helper functions append to whatever SEQ points
                       # at, so re-binding it starts this page's own list

    y = H - 50
    section(y, "Additional Itemized Details "
               f"(Use The Excel Document if Invoice is in Excess of {TABLE_ROWS_TARGET - 1} Rows)"
               + (" (Continued)" if tp else ""))

    # --- table header bar (18pt tall to fit two lines of text) ---
    y -= 25
    c.setFillColor(ACCENT)
    c.rect(ML, y, CW, 18, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 6.3)
    cx = ML
    for _, lines, cw in TABLE2_COLS:
        if len(lines) == 2:                      # two stacked header lines
            c.drawString(cx + 4, y + 10, lines[0])
            SEQ.append(("text", "P", lines[0]))
            c.drawString(cx + 4, y + 3.5, lines[1])
            SEQ.append(("text", "P", lines[1]))
        else:                                    # single centered line
            c.drawString(cx + 4, y + 7, lines[0])
            SEQ.append(("text", "P", lines[0]))
        cx += cw

    # --- data rows: keep adding 19pt-tall rows until we reach the footer ---
    y -= 19
    while y >= 40:
        TABLE2_ROWS += 1
        r = TABLE2_ROWS
        cx = ML
        for ci, (name, _, cw) in enumerate(TABLE2_COLS):
            if name == "Expense Category":
                # dropdown that starts blank and allows custom typed text
                combo(f"T2_R{r}_C{ci + 1}", cx, y, cw - 4, EXPENSE_CATEGORIES,
                      tooltip=(f"Additional details table, row {r}, Expense Category. "
                               "Choose from the list or type a custom category"),
                      placeholder="", editable=True, font_size=7)
            else:
                tfield(f"T2_R{r}_C{ci + 1}", cx, y, cw - 4,
                       tooltip=f"Additional details table, row {r}, {name}")
            cx += cw
        y -= 19

    footer(tp + 2)                # pages 2,3,4,5
    TABLE_SEQS.append(SEQ)

c.setTitle(DOC_TITLE)
c.save()                          # writes _invoice_base.pdf to disk
print("base layout written:", TMP)

# ==============================================================================
# PHASE 2 — POST-PROCESSING WITH pypdf
# ==============================================================================
# Re-open the phase-1 file and inject: JavaScript, buttons, required flags,
# tooltips, accessibility tagging, and metadata. Then save the final PDF.
reader = PdfReader(TMP)
writer = PdfWriter(clone_from=reader)   # full editable copy of the document

root = writer._root_object     # the PDF "catalog" — the document's root dict
acro = root["/AcroForm"]       # the form dictionary (lists all fields)
page = writer.pages[0]         # page 1 (buttons are added here)
page_ref = page.indirect_reference


def js(script):
    """Wrap a JavaScript string in a PDF 'action' dictionary.

    Anywhere the PDF needs to run JS (a field event, a button click),
    it expects this exact structure: {/S /JavaScript, /JS "code"}.
    """
    return DictionaryObject({
        NameObject("/S"): NameObject("/JavaScript"),
        NameObject("/JS"): TextStringObject(script),
    })


# Build a name -> (reference, dictionary) lookup for every field reportlab
# created. `obj` is the field's raw dictionary; adding keys to it changes
# the field (that's how we attach scripts and flags below).
fields_by_name = {}
for f in acro["/Fields"]:
    obj = f.get_object()
    fields_by_name[str(obj.get("/T"))] = (f, obj)

# ------------------------------------------------------------------------------
# LOGIC 1 — cascading dropdowns: Subject filters Invoice Type & Category
# ------------------------------------------------------------------------------
# When the user picks a Subject, a "validate" script replaces the option
# lists of the other two dropdowns and resets them to the placeholder.
# TO CHANGE THE PAIRINGS: edit TYPE_RULES / CAT_RULES. Keys are Subject
# values; values are the allowed lists.
PH = "-- Select an option --"
TYPE_RULES = {
    "T": ["T-Initial", "T-Quarterly"],
    "J": ["J-Initial", "J-Quarterly"],
    "W": ["W-Initial", "W-Quarterly"],
}
CAT_RULES = {
    "T": CATEGORIES[0:2],     # CL 1, CL 4
    "J": CATEGORIES[2:4],     # CL 6, CL 8
    "W": CATEGORIES[4:6],     # CL 9, CL 11
}
# json.dumps converts the Python dicts/lists into valid JavaScript literals.
cascade_js = (
    # Wrapped in (function(){...})(): Acrobat field scripts share ONE
    # global scope, so bare 'var's leak between scripts. Row scripts also
    # use a variable named 'it' — without this wrapper, nested event
    # triggering makes 'it.value = PH' write into the wrong field.
    '(function () {\n'
    f'var PH = {json.dumps(PH)};\n'
    f'var typeMap = {json.dumps(TYPE_RULES)};\n'
    f'var catMap = {json.dumps(CAT_RULES)};\n'
    f'var allTypes = {json.dumps(INVOICE_TYPES)};\n'
    f'var allCats = {json.dumps(CATEGORIES)};\n'
    'var v = event.value;\n'                      # the just-picked Subject
    'var it = this.getField("InvoiceType");\n'
    'var ic = this.getField("InvoiceCategory");\n'
    # setItems replaces a dropdown's whole option list on the fly.
    # If v isn't in the map (placeholder picked), restore the full lists.
    'it.setItems([PH].concat(typeMap[v] ? typeMap[v] : allTypes));\n'
    'ic.setItems([PH].concat(catMap[v] ? catMap[v] : allCats));\n'
    'it.value = PH;\n'                            # reset so stale choices
    'ic.value = PH;\n'                            # can never survive
    # changing Subject resets Invoice Type, so T+Initial no longer holds
    't2SetupInitialRow("none");\n'
    't2SetHRContacts("default");\n'
    '})();\n'
)

# ------------------------------------------------------------------------------
# LOGIC 2 — auto-select Invoice Category from (Subject, Invoice Type)
# ------------------------------------------------------------------------------
# TO CHANGE: edit AUTO_CATEGORY. Outer keys = Subject, inner keys = Invoice
# Type, values = the category to auto-select.
AUTO_CATEGORY = {
    "T": {
        "T-Initial": CATEGORIES[0],               # CL 1
        "T-Quarterly": CATEGORIES[1], # CL 4
    },
    "J": {
        "J-Initial": CATEGORIES[2],                 # CL 6
        "J-Quarterly": CATEGORIES[3],     # CL 8
    },
    "W": {
        "W-Initial": CATEGORIES[4],                 # CL 9
        "W-Quarterly": CATEGORIES[5],               # CL 11
    },
}
type_js = (
    '(function () {\n'   # private scope — see cascade_js comment
    f'var autoMap = {json.dumps(AUTO_CATEGORY)};\n'
    'var s = this.getField("Subject").value;\n'
    'var ic = this.getField("InvoiceCategory");\n'
    'if (autoMap[s] && autoMap[s][event.value]) {\n'
    '    ic.value = autoMap[s][event.value];\n'
    '} else {\n'
    # no mapping (placeholder picked, or unexpected combo) -> back to the
    # placeholder so a stale category can never linger
    '    ic.value = "-- Select an option --";\n'
    '}\n'
    # Subject + *-Initial => "t-initial" mode (row 1 locked Transportation,
    # rows 2+ limited to Initial Equipment Package); Subject + *-Quarterly
    # => "t-quarterly" mode (all rows limited to Quarterly Incentive);
    # anything else restores normal behavior
    'var m = "none";\n'
    'if ((s == "T" && event.value == "T-Initial") ||'
    ' (s == "J" && event.value == "J-Initial") ||'
    ' (s == "W" && event.value == "W-Initial")) m = "t-initial";\n'
    'else if ((s == "T" && event.value == "T-Quarterly") ||'
    ' (s == "J" && event.value == "J-Quarterly") ||'
    ' (s == "W" && event.value == "W-Quarterly")) m = "t-quarterly";\n'
    't2SetupInitialRow(m);\n'
    # HR/DHR team: T & J combos -> Jam/Mich; W combos -> Rok (blank DHR);
    # anything else -> defaults
    'var team = "default";\n'
    'if ((s == "T" && (event.value == "T-Initial" || event.value == "T-Quarterly")) ||'
    ' (s == "J" && (event.value == "J-Initial" || event.value == "J-Quarterly"))) team = "tj";\n'
    'else if (s == "W" && (event.value == "W-Initial" || event.value == "W-Quarterly")) team = "w";\n'
    't2SetHRContacts(team);\n'
    '})();\n'
)
# Attach as the field's "validate" action (/AA /V = fires when value changes).
_, type_obj = fields_by_name["InvoiceType"]
type_obj[NameObject("/AA")] = DictionaryObject({NameObject("/V"): js(type_js)})
# Field-flag bit 27 (1 << 26) = "commit selected value immediately":
# without it, dropdown scripts only fire when the field loses focus.
type_obj[NameObject("/Ff")] = NumberObject(int(type_obj.get("/Ff", 0)) | (1 << 26))

# Invoice Category is auto-selected by the scripts and never user-edited
_, ic_obj = fields_by_name["InvoiceCategory"]
ic_obj[NameObject("/Ff")] = NumberObject(int(ic_obj.get("/Ff", 0)) | 1)

_, subj_obj = fields_by_name["Subject"]
subj_obj[NameObject("/AA")] = DictionaryObject({NameObject("/V"): js(cascade_js)})
subj_obj[NameObject("/Ff")] = NumberObject(int(subj_obj.get("/Ff", 0)) | (1 << 26))

# ------------------------------------------------------------------------------
# FORMATTING — dates and currency (Acrobat's built-in AF* helper functions)
# ------------------------------------------------------------------------------
# /AA /K = keystroke filter (rejects bad characters as the user types)
# /AA /F = format script (how the committed value is displayed)
for nm in ("InvoiceStartDate", "InvoiceEndDate", "InvoiceDate"):
    _, obj = fields_by_name[nm]
    obj[NameObject("/AA")] = DictionaryObject({
        NameObject("/K"): js('AFDate_KeystrokeEx("mm/dd/yyyy");'),
        NameObject("/F"): js('AFDate_FormatEx("mm/dd/yyyy");'),
    })

# zip code: Acrobat's built-in 5-digit Zip Code format (rejects non-digits)
_, zip_obj = fields_by_name["ZipCode"]
zip_obj[NameObject("/AA")] = DictionaryObject({
    NameObject("/K"): js('AFSpecial_Keystroke(0);'),
    NameObject("/F"): js('AFSpecial_Format(0);'),
})

# AFNumber args: (decimals, separator style, negative style, unused,
#                 currency symbol, symbol-before-number)
amount_names = [f"Amount{i}" for i in range(1, 6)]
for nm in amount_names:
    _, obj = fields_by_name[nm]
    obj[NameObject("/AA")] = DictionaryObject({
        NameObject("/K"): js('AFNumber_Keystroke(0, 0, 0, 0, "$", true);'),
        NameObject("/F"): js('AFNumber_Format(0, 0, 0, 0, "$", true);'),
    })

# ------------------------------------------------------------------------------
# LOGIC 3 — auto-sum Total = Amount1 + ... + Amount5
# ------------------------------------------------------------------------------
total_ref, total_obj = fields_by_name["Total"]
arr = ", ".join(f'"{n}"' for n in amount_names)
total_obj[NameObject("/AA")] = DictionaryObject({
    # /C = "calculate" event — reruns whenever any field's value changes
    NameObject("/C"): js(f'AFSimple_Calculate("SUM", new Array({arr}));'),
    NameObject("/F"): js('AFNumber_Format(0, 0, 0, 0, "$", true);'),
})
# /CO = calculation order. Acrobat only runs calculate scripts for fields
# listed here.
acro[NameObject("/CO")] = ArrayObject([total_ref])

# ------------------------------------------------------------------------------
# FONT RESOURCE — make sure "Helv" exists for the buttons we add below
# ------------------------------------------------------------------------------
# Field appearance strings (/DA) reference fonts by name from the form's
# resource dictionary (/DR). Our buttons use "/Helv", so register it if
# reportlab didn't already.
dr = acro.get("/DR")
if dr is None:
    dr = DictionaryObject()
    acro[NameObject("/DR")] = dr
else:
    dr = dr.get_object()
fonts = dr.get("/Font")
if fonts is None:
    fonts = DictionaryObject()
    dr[NameObject("/Font")] = fonts
else:
    fonts = fonts.get_object()
if "/Helv" not in fonts:
    helv = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
        NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
    })
    fonts[NameObject("/Helv")] = writer._add_object(helv)


def add_button(name, rect, mk, action, da="/Helv 10 Tf 1 1 1 rg"):
    """Create a pushbutton widget on page 1 (reportlab can't make buttons).

    rect   : [x1, y1, x2, y2] in page coordinates (bottom-left origin).
    mk     : appearance dict — /BG background color, /BC border color,
             /CA caption text, /TP 1 means "icon only" (used by the logo).
    action : what happens on click (use the js() helper).
    da     : default appearance = font + size + text color for the caption
             ("1 1 1 rg" = white text).
    """
    btn = DictionaryObject({
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Widget"),
        NameObject("/FT"): NameObject("/Btn"),
        NameObject("/Ff"): NumberObject(65536),   # bit 17 = pushbutton type
        NameObject("/T"): TextStringObject(name),
        NameObject("/Rect"): ArrayObject([FloatObject(v) for v in rect]),
        NameObject("/F"): NumberObject(4),        # annotation flag: printable
        NameObject("/MK"): mk,
        NameObject("/DA"): TextStringObject(da),
        NameObject("/A"): action,
        NameObject("/P"): page_ref,
    })
    ref = writer._add_object(btn)
    page["/Annots"].append(ref)     # visible on the page
    acro["/Fields"].append(ref)     # registered as a form field
    return ref


# ------------------------------------------------------------------------------
# LOGO BUTTON — invisible click target over the dashed logo box
# ------------------------------------------------------------------------------
# These coordinates MUST match logo_x/logo_y/logo_w/logo_h from phase 1.
# buttonImportIcon() opens Acrobat's file picker; the chosen image becomes
# the button's face — i.e., the logo appears in the box.
lx, ly, lw, lh = 36.0, 792 - 100, 140.0, 66.0
logo_btn_ref = add_button(
    "LogoButton",
    [lx, ly, lx + lw, ly + lh],
    DictionaryObject({NameObject("/TP"): NumberObject(1)}),   # icon only
    js("event.target.buttonImportIcon();"),
)

# ------------------------------------------------------------------------------
# LOGIC 4 — required fields + the SUBMIT button
# ------------------------------------------------------------------------------
# One list drives BOTH the red "required" outline AND the submit-time check.
# Each entry: (field name, kind, placeholder, label shown in the alert).
#   kind "dd" = dropdown  -> invalid while still on its placeholder
#   kind "cb" = checkbox  -> invalid while unchecked (value "Off")
#   kind "tx" = text      -> invalid while empty
# TO ADD/REMOVE A REQUIRED FIELD: edit this list only.
REQUIRED = [
    ("Subject", "dd", PH, "Subject"),
    ("InvoiceType", "dd", PH, "Invoice Type"),
    ("BankingVerified", "dd", PH, "Have You Verified Banking Information in SAM.gov"),
    ("RegistrationActive", "cb", "", "SAM Registration Active"),
    ("ServiceProviderName", "tx", "", "Service Provider Name"),
    ("StreetAddress", "tx", "", "Street Address"),
    ("City", "tx", "", "City"),
    ("State", "dd", "-- Select State --", "State"),
    ("ZipCode", "tx", "", "Zip Code"),
    ("POCName", "tx", "", "POC Name"),
    ("POCEmail", "tx", "", "POC Email"),
    ("RegistrationNo", "tx", "", "SAM Registration No. (UEI)"),
    # OperationalDate is pre-filled and read-only (HR fills it later)
    # HRName / HREmail are pre-filled and read-only, so always satisfied
    ("InvoiceStartDate", "tx", "", "Invoice Start Date"),
    ("InvoiceEndDate", "tx", "", "Invoice End Date"),
    ("InvoiceDate", "tx", "", "Invoice Date"),
    ("Acknowledgement", "cb", "", "Acknowledgement of accuracy"),
]

# Field-flag bit 2 = "Required": Acrobat outlines the field in red and
# screen readers announce it as required. NOTE: the flag alone does NOT
# block our JavaScript submit — the submit script below does that.
for nm, _, _, _ in REQUIRED:
    _, obj = fields_by_name[nm]
    obj[NameObject("/Ff")] = NumberObject(int(obj.get("/Ff", 0)) | 2)

# The submit script: check everything in REQUIRED; if anything is missing,
# show ONE alert listing all of it and stop. Otherwise call mailDoc, which
# opens the user's email client with THIS filled PDF attached and a
# subject/body built live from the form values.
# (We use mailDoc instead of a static "SubmitForm mailto" action precisely
# because mailto can't include field values in the subject line.)
req_array = json.dumps(
    [{"n": n, "t": t, "ph": ph, "lb": lb} for n, t, ph, lb in REQUIRED])
submit_js = (
    '(function () {\n'   # private scope — see cascade_js comment
    f'var required = {req_array};\n'
    'var missing = [];\n'
    'for (var i = 0; i < required.length; i++) {\n'
    '    var r = required[i];\n'
    '    var v = this.getField(r.n).value;\n'
    '    if (r.t == "dd" && v == r.ph) missing.push(r.lb);\n'
    '    else if (r.t == "cb" && v == "Off") missing.push(r.lb);\n'
    '    else if (r.t == "tx" && (v == null || String(v) == "")) missing.push(r.lb);\n'
    '}\n'
    'if (missing.length > 0) {\n'
    '    app.alert("Please complete the following required fields before submitting:\\n\\n- " + missing.join("\\n- "), 1);\n'
    '} else {\n'
    # email subject, e.g.:  T - TX - Acme LLC - Weekly Invoice
    '    var ref = this.getField("Subject").value + " - " + this.getField("State").value'
    ' + " - " + this.getField("ServiceProviderName").value + " - " + this.getField("InvoiceType").value + " Invoice";\n'
    '    var msg = "Hello,\\n\\nAttached is the " + ref + "\\n\\n";\n'
    f'    this.mailDoc({{bUI: true, cTo: "{SUBMIT_EMAIL}", cSubject: ref, cMsg: msg}});\n'
    '}\n'
    '})();\n'
)
submit_action = js(submit_js)
submit_btn_ref = add_button(
    "SubmitButton",
    # btn_x/btn_y/btn_w/btn_h come from the phase-1 layout (bottom-right)
    [btn_x, btn_y, btn_x + btn_w, btn_y + btn_h],
    DictionaryObject({
        NameObject("/BG"): ArrayObject([FloatObject(v) for v in (0.12, 0.23, 0.39)]),
        NameObject("/BC"): ArrayObject([FloatObject(v) for v in (0.12, 0.23, 0.39)]),
        NameObject("/CA"): TextStringObject("SUBMIT INVOICE"),
    }),
    submit_action,
    da="/Helv 11 Tf 1 1 1 rg",
)

# Complete name -> widget-reference map (reportlab fields + our 2 buttons).
# Used by the tooltip loop and the accessibility tagging below.
widget_refs = {n: r for n, (r, _) in fields_by_name.items()}
widget_refs["LogoButton"] = logo_btn_ref
widget_refs["SubmitButton"] = submit_btn_ref

# ==============================================================================
# 508 — TOOLTIPS (/TU): the text screen readers announce for each field
# ==============================================================================
# EVERY field must have an entry here — the loop at the end raises KeyError
# if one is missing (that's intentional: it catches forgotten fields).
TOOLTIPS = {
    "Subject": "Subject. Choose T, J, or W. Your choice filters the available Invoice Type and Invoice Category options",
    "InvoiceType": "Invoice type. Available choices depend on the selected Subject",
    "RegistrationActive": "SAM Registration Active. Check if the SAM registration is active",
    "BankingVerified": "Have you verified banking information in SAM.gov. Choose Yes or No",
    "ServiceProviderName": "Service provider name",
    "StreetAddress": "Street address",
    "City": "City",
    "State": "State. Choose a two-letter state abbreviation",
    "ZipCode": "Zip code. Five digits",
    "POCName": "Point of contact name",
    "POCEmail": "Point of contact email address",
    "OrderNumber": "Order number. Will be filled by the back office. Not editable",
    "RegistrationNo": "SAM registration number (UEI). Twelve characters",
    "HRName": "HR name. Filled automatically from the Subject and Invoice Type. Not editable",
    "HREmail": "HR email address. Filled automatically from the Subject and Invoice Type. Not editable",
    "DHRName": "DHR name. Filled automatically from the Subject and Invoice Type. Not editable",
    "DHREmail": "DHR email address. Filled automatically from the Subject and Invoice Type. Not editable",
    "InvoiceStartDate": "Invoice start date in month, day, year format",
    "InvoiceEndDate": "Invoice end date in month, day, year format",
    "InvoiceNumber": "Invoice number. Will be filled by the back office. Not editable",
    "InvoiceDate": "Invoice date in month, day, year format",
    "OperationalDate": "Operational date. Will be filled by HR. Not editable",
    "InvoiceCategory": "Invoice category. Selected automatically from the Subject and Invoice Type. Not editable",
    "Total": "Total amount. Calculated automatically as the sum of all item amounts",
    "LogoButton": "Add organization logo. Activates a file picker to import a logo image",
    "Acknowledgement": "I hereby certify that all the information provided in this document is true, accurate, and complete to the best of my knowledge and belief. By submitting this form, I affirm that I have reviewed the information and take responsibility for its accuracy. Check to confirm before submitting",
    "SubmitButton": f"Submit invoice. Sends the completed PDF by email to {SUBMIT_EMAIL}",
}
for i in range(1, 6):
    TOOLTIPS[f"ItemDesc{i}"] = f"Item {i} description, for example Transportation or Equipment"
    TOOLTIPS[f"Amount{i}"] = f"Item {i} amount in dollars"
for r in range(1, TABLE2_ROWS + 1):
    for ci, (name, _, _) in enumerate(TABLE2_COLS):
        if name == "Expense Category":
            TOOLTIPS[f"T2_R{r}_C{ci + 1}"] = (
                f"Additional details table, row {r}, Expense Category. "
                "Choose from the list or type a custom category. Choosing "
                "Transportation auto-fills the Transportation column; choosing "
                "Equipment Package auto-fills the Equipment Cost column")
        else:
            TOOLTIPS[f"T2_R{r}_C{ci + 1}"] = \
                f"Additional details table, row {r}, {name}"

for name, ref in widget_refs.items():
    ref.get_object()[NameObject("/TU")] = TextStringObject(TOOLTIPS[name])

# ==============================================================================
# LOGIC 5 — table-page Expense Category: auto-fill & lock cost cells
# ==============================================================================
# Column meaning per row r:  C5 = Expense Category (dropdown),
# C6 = Equipment Cost, C7 = Transportation (One Time), C8 = IT.
# (C1-C3 = First/Middle Initial/Last name, C4 = Credential Number.)
#
# Behavior when the user picks a category in row r:
#   Transportation (One Time)    -> C5 = $100,000, locked
#   Equipment Package (One Time) -> C4 = $7,500,  locked
#   Quarterly Expense            -> C4 AND C6 = $7,500 each, locked
#   anything else (blank/custom) -> unlock & clear only auto-set cells
#
# clr() only clears cells that are read-only, i.e. cells THIS script locked.
# A cost the user typed by hand is never touched.
# TO CHANGE THE AMOUNTS: edit the dollar strings below (display text) — and
# keep the numeric amounts in doc_js (LOGIC 6) in sync for the summary math.
for r in range(1, TABLE2_ROWS + 1):
    cat_js = (
        '(function () {\n'   # private scope — see cascade_js comment
        f'var eq = this.getField("T2_R{r}_C6");\n'
        f'var tr = this.getField("T2_R{r}_C7");\n'
        f'var it = this.getField("T2_R{r}_C8");\n'
        'var v = event.value;\n'
        'function clr(f) { if (f.readonly) { f.value = ""; f.readonly = false; } }\n'
        # set() writes only when needed — avoids redundant redraws that
        # make the next dropdown click feel unresponsive
        'function set(f, val) {\n'
        '    if (f.value != val) f.value = val;\n'
        '    if (!f.readonly) f.readonly = true;\n'
        '}\n'
        'if (v == "One-Time Transportation") {\n'
        '    set(tr, "$100,000");\n'
        '    clr(eq); clr(it);\n'
        '} else if (v == "Initial Equipment Package") {\n'
        '    set(eq, "$7,500");\n'
        '    clr(tr); clr(it);\n'
        '} else if (v == "Quarterly Incentive") {\n'
        '    set(eq, "$7,500");\n'
        '    set(it, "$7,500");\n'
        '    clr(tr);\n'
        '} else {\n'
        '    clr(eq); clr(tr); clr(it);\n'
        '}\n'
        # refresh the page-1 summary (function defined in LOGIC 6).
        # We pass this row's number and NEW value because a validate event
        # fires BEFORE the new value is stored in the field.
        f'if (!t2Bulk) t2UpdateSummary({r}, v);\n'
        '})();\n'
    )
    _, obj = fields_by_name[f"T2_R{r}_C5"]
    obj[NameObject("/AA")] = DictionaryObject({NameObject("/V"): js(cat_js)})
    # commit-on-click, same as the Subject/InvoiceType dropdowns
    obj[NameObject("/Ff")] = NumberObject(int(obj.get("/Ff", 0)) | (1 << 26))

# ==============================================================================
# LOGIC 6 — document-level script: roll table selections up into page 1
# ==============================================================================
# Document-level JavaScript runs when the PDF opens, and its functions stay
# available to every field script. t2UpdateSummary counts how many table
# rows use each category and writes "label x count" + (count * unit price)
# into page-1 summary rows 1-3, locking them. The Total then auto-sums.
#   ItemDesc1/Amount1 = Transportation      @ $100,000 per row
#   ItemDesc2/Amount2 = Equipment Package   @ $7,500  per row
#   ItemDesc3/Amount3 = Quarterly Expense   @ $15,000 per row (7,500+7,500)
doc_js = (
    f'var T2_ROWS = {TABLE2_ROWS};\n'
    # t2Bulk: suppresses per-row summary recounts during mass updates.
    # t2Mode: which special table mode is active — "none", "t-initial"
    # (T + T-Initial), or "t-quarterly" (T + T-Quarterly). Remembered so
    # the whole-table option swap only runs when the mode changes.
    'var t2Bulk = false;\n'
    'var t2Mode = "none";\n'
    'function t2SetSummaryRow(descName, amtName, label, count, unit) {\n'
    '    var d = this.getField(descName), a = this.getField(amtName);\n'
    '    if (count > 0) {\n'
    # only write when the value actually changes: every field write forces
    # a redraw + recalc, and needless redraws make dropdowns feel like they
    # need two clicks
    '        var nd = label + (count > 1 ? " x " + count : "");\n'
    '        var na = count * unit;\n'
    '        if (d.value != nd) d.value = nd;\n'
    '        if (a.value != na) a.value = na;\n'
    '        if (!d.readonly) { d.readonly = true; a.readonly = true; }\n'
    '    } else if (d.readonly) {\n'
    # count dropped to zero -> clear and unlock the summary row
    '        d.value = ""; a.value = ""; d.readonly = false; a.readonly = false;\n'
    '    }\n'
    '}\n'
    'function t2UpdateSummary(changedRow, changedValue) {\n'
    '    var trCount = 0, eqCount = 0, qeCount = 0;\n'
    '    for (var r = 1; r <= T2_ROWS; r++) {\n'
    # the changing row reports its new value directly (see LOGIC 5 note)
    '        var v = (r == changedRow) ? changedValue'
    ' : this.getField("T2_R" + r + "_C5").value;\n'
    '        if (v == "One-Time Transportation") trCount++;\n'
    '        else if (v == "Initial Equipment Package") eqCount++;\n'
    '        else if (v == "Quarterly Incentive") qeCount++;\n'
    '    }\n'
    '    t2SetSummaryRow("ItemDesc1", "Amount1",'
    ' "One-Time Transportation", trCount, 100000);\n'
    '    t2SetSummaryRow("ItemDesc2", "Amount2",'
    ' "Initial Equipment Package", eqCount, 7500);\n'
    '    t2SetSummaryRow("ItemDesc3", "Amount3",'
    ' "Quarterly Incentive (Equipment + Information Technology)", qeCount, 15000);\n'
    '}\n'
    # Special table modes, driven by Subject + Invoice Type (called from
    # the Subject and InvoiceType scripts with a mode string):
    #  "t-initial"   (T + T-Initial): row 1 forced to One-Time
    #                Transportation and LOCKED (category, $100k cost, name
    #                cells); rows 2+ offer ONLY Initial Equipment Package.
    #  "t-quarterly" (T + T-Quarterly): ALL rows offer ONLY Quarterly
    #                Incentive; no row-1 lock.
    #  "none"        anything else: full lists everywhere, all unlocked.
    'function t2SetupInitialRow(mode) {\n'
    # runs only when the mode actually changes — the option swaps touch up
    # to 140 dropdowns and must not fire on every Subject click
    '    if (mode == t2Mode) return;\n'
    '    t2Mode = mode;\n'
    '    var cat = this.getField("T2_R1_C5");\n'
    '    var eq = this.getField("T2_R1_C6");\n'
    '    var tr = this.getField("T2_R1_C7");\n'
    '    var itf = this.getField("T2_R1_C8");\n'
    '    function u(f) { if (f.readonly) { f.value = ""; f.readonly = false; } }\n'
    '    t2Bulk = true;\n'
    f'    var fullOpts = {json.dumps([""] + EXPENSE_CATEGORIES)};\n'
    '    var initOpts = ["", "Initial Equipment Package"];\n'
    '    var qOpts = ["", "Quarterly Incentive"];\n'
    '    if (mode == "t-initial") {\n'
    '        cat.setItems(fullOpts);\n'
    '        cat.value = "One-Time Transportation";\n'
    '        cat.readonly = true;\n'
    '        if (tr.value != "$100,000") tr.value = "$100,000";\n'
    '        if (!tr.readonly) tr.readonly = true;\n'
    '        u(eq); u(itf);\n'
    '        for (var ci = 1; ci <= 4; ci++) {\n'
    '            var nf = this.getField("T2_R1_C" + ci);\n'
    '            if (!nf.readonly) nf.readonly = true;\n'
    '        }\n'
    '        for (var r = 2; r <= T2_ROWS; r++) {\n'
    '            this.getField("T2_R" + r + "_C5").setItems(initOpts);\n'
    '            u(this.getField("T2_R" + r + "_C6"));\n'
    '            u(this.getField("T2_R" + r + "_C7"));\n'
    '            u(this.getField("T2_R" + r + "_C8"));\n'
    '        }\n'
    '    } else if (mode == "t-quarterly") {\n'
    '        if (cat.readonly) cat.readonly = false;\n'
    '        u(tr); u(eq); u(itf);\n'
    '        for (var ci = 1; ci <= 4; ci++) {\n'
    '            var nf = this.getField("T2_R1_C" + ci);\n'
    '            if (nf.readonly) nf.readonly = false;\n'
    '        }\n'
    '        for (var r = 1; r <= T2_ROWS; r++) {\n'
    '            this.getField("T2_R" + r + "_C5").setItems(qOpts);\n'
    '            u(this.getField("T2_R" + r + "_C6"));\n'
    '            u(this.getField("T2_R" + r + "_C7"));\n'
    '            u(this.getField("T2_R" + r + "_C8"));\n'
    '        }\n'
    '    } else {\n'
    '        if (cat.readonly) cat.readonly = false;\n'
    '        u(tr); u(eq); u(itf);\n'
    '        for (var ci = 1; ci <= 4; ci++) {\n'
    '            var nf = this.getField("T2_R1_C" + ci);\n'
    '            if (nf.readonly) nf.readonly = false;\n'
    '        }\n'
    '        for (var r = 1; r <= T2_ROWS; r++) {\n'
    '            this.getField("T2_R" + r + "_C5").setItems(fullOpts);\n'
    '            u(this.getField("T2_R" + r + "_C6"));\n'
    '            u(this.getField("T2_R" + r + "_C7"));\n'
    '            u(this.getField("T2_R" + r + "_C8"));\n'
    '        }\n'
    '    }\n'
    '    t2Bulk = false;\n'
    '    t2UpdateSummary(0, "");\n'
    '}\n'
    # HR/DHR contact auto-fill by team: "tj" (Subjects T & J) = Jam/Mich,
    # "w" (Subject W) = Rok with blank DHR, anything else = all empty.
    # The fields are permanently read-only; scripts can still write them.
    'function t2SetHRContacts(team) {\n'
    '    var vals;\n'
    '    if (team == "tj") vals = ["Jam", "jam@test.com", "Mich", "mich@test.com"];\n'
    '    else if (team == "w") vals = ["Rok", "rok@test.com", "", ""];\n'
    '    else vals = ["", "", "", ""];\n'
    '    var names = ["HRName", "HREmail", "DHRName", "DHREmail"];\n'
    '    for (var i = 0; i < 4; i++) {\n'
    '        var f = this.getField(names[i]);\n'
    '        if (f.value != vals[i]) f.value = vals[i];\n'
    '        if (!f.readonly) f.readonly = true;\n'
    '    }\n'
    '}\n'
)
# Register as a "document JavaScript" — PDF stores these in a name tree at
# catalog /Names /JavaScript.
names_root = root.get("/Names")
if names_root is None:
    names_root = DictionaryObject()
    root[NameObject("/Names")] = names_root
else:
    names_root = names_root.get_object()
js_name_tree = DictionaryObject({
    NameObject("/Names"): ArrayObject([
        TextStringObject("t2Summary"), writer._add_object(js(doc_js)),
    ]),
})
names_root[NameObject("/JavaScript")] = writer._add_object(js_name_tree)

# ------------------------------------------------------------------------------
# Clear the stand-in defaults on blank-start dropdowns (see combo() helper)
# ------------------------------------------------------------------------------
for nm in CLEAR_VALUE:
    _, obj = fields_by_name[nm]
    obj[NameObject("/V")] = TextStringObject("")
    if "/I" in obj:               # /I = selected-index; stale after clearing
        del obj[NameObject("/I")]

# ------------------------------------------------------------------------------
# Auto-size fonts: "/Helv 0 Tf" (size 0 = auto) makes Acrobat shrink text to
# fit the box, so long entries are never clipped. Applied to every text
# field, plus the narrow Expense Category dropdowns on the table pages.
# ------------------------------------------------------------------------------
for name, (_, obj) in fields_by_name.items():
    if obj.get("/FT") == "/Ch" and name.startswith("T2_"):
        # fixed 7pt: uniform across all rows, and the widened column fits
        # every predefined option at this size
        obj[NameObject("/DA")] = TextStringObject("/Helv 7 Tf 0 g")
    elif obj.get("/FT") == "/Tx":
        obj[NameObject("/DA")] = TextStringObject("/Helv 0 Tf 0 g")

# ==============================================================================
# 508 — TAGGING THE PAGE CONTENT
# ==============================================================================
# Background: a PDF page's visuals live in a "content stream" — a list of
# drawing operators. Text sits between BT ("begin text") and ET ("end text").
# To make the PDF accessible we wrap:
#   real text     ->  /P <</MCID n>> BDC ... EMC   (tagged, numbered)
#   decoration    ->  /Artifact BMC ... EMC        (screen readers skip it)
# The MCID numbers link each piece of text to the structure tree built below.
# You should not need to touch these two functions.

def split_bt_blocks(s):
    """Split a content stream into alternating segments outside/inside
    BT..ET pairs. Skips over (string) literals so text containing 'BT'
    can't confuse the parser."""
    segments = []
    i, n, seg_start = 0, len(s), 0
    in_bt = False
    in_str, esc = False, False
    while i < n:
        ch = s[i]
        if in_str:                       # inside a (...) string literal
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == ")":
                in_str = False
            i += 1
            continue
        if ch == "(":
            in_str = True
            i += 1
            continue
        tok = s[i:i + 2]
        # only treat BT/ET as operators when surrounded by whitespace
        prev_ok = i == 0 or s[i - 1] in " \t\r\n"
        next_ok = i + 2 >= n or s[i + 2] in " \t\r\n"
        if not in_bt and tok == "BT" and prev_ok and next_ok:
            segments.append(("out", s[seg_start:i]))
            seg_start = i
            in_bt = True
            i += 2
            continue
        if in_bt and tok == "ET" and prev_ok and next_ok:
            segments.append(("bt", s[seg_start:i + 2]))
            seg_start = i + 2
            in_bt = False
            i += 2
            continue
        i += 1
    segments.append(("out", s[seg_start:]))
    return segments


def shows_text(seg):
    """True if a BT..ET block actually draws text (contains Tj/TJ/'/\").
    reportlab also emits EMPTY BT/ET pairs for setFont calls — those are
    decoration, not text, and must not consume a SEQ entry."""
    i, n = 0, len(seg)
    in_str, esc = False, False
    while i < n:
        ch = seg[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == ")":
                in_str = False
            i += 1
            continue
        if ch == "(":
            in_str = True
            i += 1
            continue
        if seg[i:i + 2] in ("Tj", "TJ") and (i + 2 >= n or seg[i + 2] in " \t\r\n"):
            return True
        if ch in ("'", '"') and (i + 1 >= n or seg[i + 1] in " \t\r\n"):
            return True
        i += 1
    return False


# ==============================================================================
# 508 — STRUCTURE TREE (what screen readers actually walk through)
# ==============================================================================
# Shape:  StructTreeRoot -> Document -> [H2/P/Form elements in reading order]
# Text elements point at their MCID in the page content; Form elements point
# at their widget annotation. The "parent tree" is a reverse index the PDF
# spec requires (page + MCID -> element, and annotation -> element).
struct_root = DictionaryObject({NameObject("/Type"): NameObject("/StructTreeRoot")})
struct_root_ref = writer._add_object(struct_root)

doc_elem = DictionaryObject({
    NameObject("/Type"): NameObject("/StructElem"),
    NameObject("/S"): NameObject("/Document"),
    NameObject("/P"): struct_root_ref,
    NameObject("/T"): TextStringObject(DOC_TITLE),
})
doc_elem_ref = writer._add_object(doc_elem)

kids = ArrayObject()      # children of the Document element, all pages
parent_pairs = []         # (number-tree key, element ref) for the parent tree
# Keys 0..4 are reserved for the five pages' MCID arrays; annotation keys
# continue from there.
annot_key = len(writer.pages)

for pg_idx, seq in enumerate([SEQ_P1] + TABLE_SEQS):
    pg = writer.pages[pg_idx]
    pg_ref = pg.indirect_reference

    # ---- 1) read this page's content stream ----
    contents = pg["/Contents"].get_object()
    if isinstance(contents, ArrayObject):     # streams can be split in parts
        data = b"".join(s.get_object().get_data() for s in contents)
    else:
        data = contents.get_data()
    stream = data.decode("latin-1")

    # ---- 2) find the text blocks and sanity-check against SEQ ----
    segments = split_bt_blocks(stream)
    segments = [("art" if k == "bt" and not shows_text(s) else k, s)
                for k, s in segments]
    text_entries = [e for e in seq if e[0] == "text"]
    bt_count = sum(1 for k, _ in segments if k == "bt")
    # If this assertion fires, a c.drawString call and its SEQ.append got
    # out of sync somewhere in phase 1 — find the draw call missing its entry.
    assert bt_count == len(text_entries), \
        f"page {pg_idx + 1}: BT blocks ({bt_count}) != text draws ({len(text_entries)})"

    # ---- 3) rewrite the stream with marked-content wrappers ----
    out_parts = []
    mcid = 0     # marked-content IDs restart at 0 on every page
    ti = 0       # index into text_entries
    for kind, seg in segments:
        if kind == "bt":
            role = text_entries[ti][1]
            ti += 1
            if role == "Artifact":   # footer text — skip-able pagination
                out_parts.append(f"/Artifact BMC\n{seg}\nEMC\n")
            else:
                out_parts.append(f"/{role} <</MCID {mcid}>> BDC\n{seg}\nEMC\n")
                mcid += 1
        elif seg.strip():            # everything else = visual decoration
            out_parts.append(f"/Artifact BMC\n{seg}\nEMC\n")
    new_stream = DecodedStreamObject()
    new_stream.set_data("".join(out_parts).encode("latin-1"))
    pg[NameObject("/Contents")] = writer._add_object(new_stream)

    # ---- 4) build this page's structure elements in reading order ----
    mcid_parents = ArrayObject()     # index = MCID -> owning element ref
    mcid = 0
    for entry in seq:
        if entry[0] == "text":
            _, role, txt = entry
            if role == "Artifact":   # pagination is not document structure
                continue
            el = DictionaryObject({
                NameObject("/Type"): NameObject("/StructElem"),
                NameObject("/S"): NameObject("/" + role),   # /P or /H2
                NameObject("/P"): doc_elem_ref,
                NameObject("/Pg"): pg_ref,
                NameObject("/K"): NumberObject(mcid),
            })
            ref = writer._add_object(el)
            kids.append(ref)
            mcid_parents.append(ref)
            mcid += 1
        else:
            # a form field: the element points at the widget via an OBJR
            _, fname = entry
            annot_ref = widget_refs[fname]
            objr = DictionaryObject({
                NameObject("/Type"): NameObject("/OBJR"),
                NameObject("/Obj"): annot_ref,
                NameObject("/Pg"): pg_ref,
            })
            el = DictionaryObject({
                NameObject("/Type"): NameObject("/StructElem"),
                NameObject("/S"): NameObject("/Form"),
                NameObject("/P"): doc_elem_ref,
                NameObject("/Pg"): pg_ref,
                NameObject("/Alt"): TextStringObject(TOOLTIPS[fname]),
                NameObject("/K"): objr,
            })
            ref = writer._add_object(el)
            kids.append(ref)
            annot_ref.get_object()[NameObject("/StructParent")] = NumberObject(annot_key)
            parent_pairs.append((annot_key, ref))
            annot_key += 1

    parent_pairs.append((pg_idx, writer._add_object(mcid_parents)))
    pg[NameObject("/StructParents")] = NumberObject(pg_idx)
    # /Tabs /S = keyboard tab order follows the structure (reading) order
    pg[NameObject("/Tabs")] = NameObject("/S")

doc_elem[NameObject("/K")] = kids

# The parent tree is a "number tree" — its keys MUST be ascending.
parent_pairs.sort(key=lambda p: p[0])
nums = ArrayObject()
for k, ref in parent_pairs:
    nums.append(NumberObject(k))
    nums.append(ref)
parent_tree = DictionaryObject({NameObject("/Nums"): nums})
struct_root[NameObject("/K")] = doc_elem_ref
struct_root[NameObject("/ParentTree")] = writer._add_object(parent_tree)
struct_root[NameObject("/ParentTreeNextKey")] = NumberObject(annot_key)

# ==============================================================================
# 508 — DOCUMENT-LEVEL METADATA
# ==============================================================================
root[NameObject("/StructTreeRoot")] = struct_root_ref
# MarkInfo/Marked tells viewers "this PDF is tagged"
root[NameObject("/MarkInfo")] = DictionaryObject(
    {NameObject("/Marked"): BooleanObject(True)})
# document language, announced by screen readers
root[NameObject("/Lang")] = TextStringObject("en-US")
# show the document TITLE in the window/tab bar instead of the filename
vp = root.get("/ViewerPreferences")
if vp is None:
    vp = DictionaryObject()
    root[NameObject("/ViewerPreferences")] = vp
else:
    vp = vp.get_object()
vp[NameObject("/DisplayDocTitle")] = BooleanObject(True)

# classic Info-dictionary metadata.
# /Creator ("Application") and /Producer ("PDF Producer") normally identify
# the authoring tools; we blank them so no tool names appear in
# Document Properties. Put your organization name there instead if desired.
writer.add_metadata({
    "/Title": DOC_TITLE,
    "/Subject": "Fillable service provider invoice with email submission",
    "/Creator": "",
    "/Producer": "",
    "/Author": "",   # reportlab defaults this to "anonymous"
})
# also drop the timestamps and prepress flag reportlab stamped in
try:
    info_obj = writer._info.get_object()
    for k in ("/CreationDate", "/ModDate", "/Trapped"):
        if k in info_obj:
            del info_obj[NameObject(k)]
except AttributeError:
    pass  # pypdf version without _info — entries then remain, harmless

# NOTE: no XMP metadata packet is embedded (removed by request — it carried
# the standard Dublin Core namespace URL). The document title/language live
# in the Info dictionary and catalog /Lang instead. Be aware that stricter
# PDF/UA checkers prefer an XMP dc:title, and that Acrobat re-creates an
# XMP packet (including that URL) whenever someone saves the file in Acrobat.

# NeedAppearances = viewers regenerate how field values look (needed because
# we changed values/fonts after reportlab drew the original appearances)
acro[NameObject("/NeedAppearances")] = BooleanObject(True)

# ==============================================================================
# WRITE THE FINAL FILE + SELF-CHECK
# ==============================================================================
with open(FINAL, "wb") as fh:
    writer.write(fh)
print("final form written:", FINAL)

# Quick self-check: re-open the file we just wrote and print the vitals.
# If any of these look wrong (e.g. "missing tooltips" lists names), fix the
# cause and re-run — do NOT ship the PDF.
chk = PdfReader(FINAL)
cat = chk.trailer["/Root"]
print("Lang:", cat.get("/Lang"), "| Marked:", cat["/MarkInfo"]["/Marked"],
      "| Tabs:", chk.pages[0].get("/Tabs"),
      "| DisplayDocTitle:", cat["/ViewerPreferences"]["/DisplayDocTitle"])
st = cat["/StructTreeRoot"]
doc = st["/K"].get_object()
print("Structure: Document with", len(doc["/K"]), "children;",
      "ParentTree entries:", len(st["/ParentTree"]["/Nums"]) // 2)
flds = chk.get_fields()
missing_tu = [n for n, f in flds.items() if not f.get("/TU")]
print(f"{len(flds)} fields; missing tooltips: {missing_tu or 'none'}")
