#!/usr/bin/env python3
"""Build a professional, Section 508-compliant fillable PDF invoice (AcroForm).

Accessibility features:
- Tagged PDF: full structure tree (Document > H2/P/Form) in reading order
- All decoration (rules, bars, boxes) marked as Artifacts
- Human-readable tooltips (/TU) on every form field
- Document language (en-US), title metadata + DisplayDocTitle
- Structure-based tab order (/Tabs /S)
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject, BooleanObject, DecodedStreamObject, DictionaryObject,
    FloatObject, NameObject, NumberObject, TextStringObject,
)

# output lands next to this script, wherever it lives
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(OUT_DIR, "_invoice_base.pdf")
FINAL = os.path.join(OUT_DIR, "Editable_Invoice.pdf")

SUBMIT_EMAIL = "test@test.com"
EMAIL_SUBJECT = "Completed Invoice Submission"
DOC_TITLE = "Service Provider Invoice Form"
HR_NAME = "Mike Dale"
HR_EMAIL = "test@test.com"

NAVY = HexColor("#1F3B63")
ACCENT = HexColor("#2E5E9E")
LABEL_GRAY = HexColor("#5A6572")
FIELD_FILL = HexColor("#F4F7FB")
FIELD_BORDER = HexColor("#B9C4D1")
LINE_GRAY = HexColor("#D8DEE6")

STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]

SUBJECTS = ["ABC", "EFG", "HIJ"]
INVOICE_TYPES = ["Initial", "Weekly", "Bi-Weekly", "Monthly",
                 "Semi-Quarterly", "Quarterly", "Semi-Annually", "Annually"]
CATEGORIES = [
    "INV001 - Transportation & Equipment (Initial Stipend)",
    "INV002 - Quarterly Incentive",
    "INV003 - Customer Summer Incentive",
    "INV004 - Customer Quarterly Incentive",
    "INV005 - Employee Winter Incentive",
    "INV006 - Employee Quarterly Incentive",
]

W, H = letter  # 612 x 792
ML, MR = 36, 36
CW = W - ML - MR

c = canvas.Canvas(TMP, pagesize=letter)
form = c.acroForm

FIELD_H = 15

# Reading-order sequence for the structure tree:
# ('text', role, string) for drawn text, ('field', name) for widgets.
SEQ = []
# combo fields whose default value must be cleared in post-processing
CLEAR_VALUE = []


RED = HexColor("#C0392B")


def label(x, y, text, size=6.8, required=False):
    c.setFont("Helvetica-Bold", size)
    c.setFillColor(LABEL_GRAY)
    c.drawString(x, y, text.upper())
    SEQ.append(("text", "P", text))
    if required:
        w = stringWidth(text.upper(), "Helvetica-Bold", size)
        c.setFillColor(RED)
        c.drawString(x + w + 2, y, "*")
        SEQ.append(("text", "P", "required"))


def tfield(name, x, y, w, tooltip="", value="", flags="", font_size=9, h=FIELD_H):
    form.textfield(
        name=name, tooltip=tooltip or name, value=value,
        x=x, y=y, width=w, height=h,
        fontName="Helvetica", fontSize=font_size,
        borderColor=FIELD_BORDER, fillColor=FIELD_FILL, textColor=black,
        borderWidth=0.7, borderStyle="solid", fieldFlags=flags, forceBorder=True,
    )
    SEQ.append(("field", name))


def combo(name, x, y, w, options, tooltip="", placeholder="-- Select an option --",
          editable=False, font_size=9):
    # reportlab crashes on choice fields with an empty value (lbextras bug),
    # so blank-default combos are created with a real value and cleared in
    # post-processing (see CLEAR_VALUE below).
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


def section(y, title):
    c.setFillColor(NAVY)
    c.rect(ML, y, CW, 15, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(ML + 6, y + 4.2, title.upper())
    SEQ.append(("text", "H2", title))


# ---------------- HEADER ----------------
c.setFillColor(NAVY)
c.rect(0, H - 8, W, 8, fill=1, stroke=0)

# Logo placeholder box (dashed) — pushbutton added in post-processing
logo_x, logo_y, logo_w, logo_h = ML, H - 100, 140, 66
c.setStrokeColor(FIELD_BORDER)
c.setDash(3, 3)
c.setLineWidth(1)
c.rect(logo_x, logo_y, logo_w, logo_h, fill=0, stroke=1)
c.setDash()
c.setFont("Helvetica", 7.5)
c.setFillColor(LABEL_GRAY)
c.drawCentredString(logo_x + logo_w / 2, logo_y + logo_h / 2 + 4, "ORGANIZATION LOGO")
SEQ.append(("text", "P", "Organization logo"))
c.drawCentredString(logo_x + logo_w / 2, logo_y + logo_h / 2 - 6, "(click to add image)")
SEQ.append(("text", "P", "(click to add image)"))
SEQ.append(("field", "LogoButton"))

# ---------------- SECTION: INVOICE DETAILS ----------------
col2 = ML + CW / 2 + 8
half = CW / 2 - 8

y = H - 122
section(y, "Invoice Details")
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
# checkbox caption drawn first so reading order is label-then-field
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
label(col2, y + FIELD_H + 3, "Verified Banking Information in SAM.gov?", required=True)
combo("BankingVerified", col2, y, half, ["Yes", "No"])

# ---------------- SECTION: SERVICE PROVIDER ----------------
y -= 26
section(y, "Service Provider Information")
y -= 27
label(ML, y + FIELD_H + 3, "Service Provider Name", required=True)
tfield("ServiceProviderName", ML, y, CW)
y -= 31
label(ML, y + FIELD_H + 3, "Street Address", required=True)
tfield("StreetAddress", ML, y, CW)
y -= 31
w_city, w_state, w_zip = 230, 190, 104
label(ML, y + FIELD_H + 3, "City", required=True)
tfield("City", ML, y, w_city)
sx = ML + w_city + 8
label(sx, y + FIELD_H + 3, "State", required=True)
combo("State", sx, y, w_state, STATES, placeholder="-- Select State --")
zx = sx + w_state + 8
label(zx, y + FIELD_H + 3, "Zip Code", required=True)
tfield("ZipCode", zx, y, w_zip)
y -= 31
label(ML, y + FIELD_H + 3, "POC Name", required=True)
tfield("POCName", ML, y, half)
label(col2, y + FIELD_H + 3, "POC Email", required=True)
tfield("POCEmail", col2, y, half)
y -= 31
w3 = (CW - 16) / 3
label(ML, y + FIELD_H + 3, "Order Number")
tfield("OrderNumber", ML, y, w3)
x2 = ML + w3 + 8
label(x2, y + FIELD_H + 3, "Registration No. (EI)", required=True)
tfield("RegistrationNo", x2, y, w3)
x3 = x2 + w3 + 8
label(x3, y + FIELD_H + 3, "IRS / EIN", required=True)
tfield("IRS_EIN", x3, y, w3)

# ---------------- SECTION: HR / DHR ----------------
y -= 26
section(y, "HR / DHR Information")
y -= 27
label(ML, y + FIELD_H + 3, "HR Name")
tfield("HRName", ML, y, half, value=HR_NAME, flags="readOnly")
label(col2, y + FIELD_H + 3, "HR Email")
tfield("HREmail", col2, y, half, value=HR_EMAIL, flags="readOnly")
y -= 31
label(ML, y + FIELD_H + 3, "DHR Name")
tfield("DHRName", ML, y, half, flags="readOnly")
label(col2, y + FIELD_H + 3, "DHR Email")
tfield("DHREmail", col2, y, half, flags="readOnly")

# ---------------- SECTION: INVOICE PERIOD ----------------
y -= 26
section(y, "Invoice Period & Reference")
y -= 27
w4 = (CW - 24) / 4
xs = [ML + i * (w4 + 8) for i in range(4)]
for x, (nm, lb, req) in zip(xs, [
    ("InvoiceStartDate", "Invoice Start Date (mm/dd/yyyy)", True),
    ("InvoiceEndDate", "Invoice End Date (mm/dd/yyyy)", True),
    ("InvoiceNumber", "Invoice Number", False),
    ("InvoiceDate", "Invoice Date (mm/dd/yyyy)", True),
]):
    label(x, y + FIELD_H + 3, lb, size=5.9, required=req)
    tfield(nm, x, y, w4)

# ---------------- SECTION: TOTAL INVOICE SUMMARY ----------------
y -= 26
section(y, "Total Invoice Summary")
y -= 27
label(ML, y + FIELD_H + 3, "Invoice Category")
combo("InvoiceCategory", ML, y, CW, CATEGORIES)

# items table
y -= 24
desc_w = CW - 140
amt_x = ML + desc_w + 8
c.setFillColor(ACCENT)
c.rect(ML, y, CW, 14, fill=1, stroke=0)
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

# total row
y -= 22
c.setStrokeColor(NAVY)
c.setLineWidth(1.2)
c.line(amt_x - 90, y + FIELD_H + 4, W - MR, y + FIELD_H + 4)
c.setFont("Helvetica-Bold", 10)
c.setFillColor(NAVY)
c.drawRightString(amt_x - 8, y + 3.5, "TOTAL:")
SEQ.append(("text", "P", "Total"))
tfield("Total", amt_x, y, 132, tooltip="Auto-calculated total", flags="readOnly")

# submit button visual (widget added in post-processing)
btn_w, btn_h = 190, 26
btn_x, btn_y = ML, y - 8 - btn_h
SEQ.append(("field", "SubmitButton"))

# footer rule
c.setStrokeColor(LINE_GRAY)
c.setLineWidth(0.6)
c.line(ML, 24, W - MR, 24)

# ---------------- PAGE 2: ADDITIONAL ITEMIZED DETAILS ----------------
c.showPage()
SEQ_P1 = SEQ
SEQ = []  # helpers keep appending; this list becomes page 2's sequence

c.setFillColor(NAVY)
c.rect(0, H - 8, W, 8, fill=1, stroke=0)

y = H - 50
section(y, "Additional Itemized Details")

# (full column name, header lines as drawn, column width)
TABLE2_COLS = [
    ("Employee Name (First, Middle Initial, Last)",
     ["EMPLOYEE NAME", "(FIRST, MIDDLE INITIAL, LAST)"], 130),
    ("Credential Number", ["CREDENTIAL", "NUMBER"], 75),
    ("Expense Category", ["EXPENSE", "CATEGORY"], 85),
    ("Equipment Cost", ["EQUIPMENT", "COST"], 65),
    ("Transportation (One Time)", ["TRANSPORTATION", "(ONE TIME)"], 80),
    ("Notes/Comments", ["NOTES /", "COMMENTS"], 105),
]
assert sum(cw for _, _, cw in TABLE2_COLS) == CW
y -= 25
c.setFillColor(ACCENT)
c.rect(ML, y, CW, 18, fill=1, stroke=0)
c.setFillColor(white)
c.setFont("Helvetica-Bold", 6.3)
cx = ML
for _, lines, cw in TABLE2_COLS:
    if len(lines) == 2:
        c.drawString(cx + 4, y + 10, lines[0])
        SEQ.append(("text", "P", lines[0]))
        c.drawString(cx + 4, y + 3.5, lines[1])
        SEQ.append(("text", "P", lines[1]))
    else:
        c.drawString(cx + 4, y + 7, lines[0])
        SEQ.append(("text", "P", lines[0]))
    cx += cw

EXPENSE_CATEGORIES = [
    "Transportation (One Time)",
    "Equipment Package (One Time)",
]

TABLE2_ROWS = 0
y -= 19
while y >= 40:
    r = TABLE2_ROWS + 1
    cx = ML
    for ci, (name, _, cw) in enumerate(TABLE2_COLS):
        if name == "Expense Category":
            combo(f"T2_R{r}_C{ci + 1}", cx, y, cw - 4, EXPENSE_CATEGORIES,
                  tooltip=(f"Additional details table, row {r}, Expense Category. "
                           "Choose from the list or type a custom category"),
                  placeholder="", editable=True, font_size=7)
        else:
            tfield(f"T2_R{r}_C{ci + 1}", cx, y, cw - 4,
                   tooltip=f"Additional details table, row {r}, {name}")
        cx += cw
    TABLE2_ROWS += 1
    y -= 19

SEQ_P2 = SEQ

c.setTitle(DOC_TITLE)
c.save()
print("base layout written:", TMP)

# =====================================================================
# POST-PROCESS with pypdf: JS actions, buttons, tagging, 508 features
# =====================================================================
reader = PdfReader(TMP)
writer = PdfWriter(clone_from=reader)

root = writer._root_object
acro = root["/AcroForm"]
page = writer.pages[0]
page_ref = page.indirect_reference


def js(script):
    return DictionaryObject({
        NameObject("/S"): NameObject("/JavaScript"),
        NameObject("/JS"): TextStringObject(script),
    })


fields_by_name = {}
for f in acro["/Fields"]:
    obj = f.get_object()
    fields_by_name[str(obj.get("/T"))] = (f, obj)

# --- table-2 category logic: auto-fill and lock the matching cost column ---
# C3 = Expense Category, C4 = Equipment Cost, C5 = Transportation (One Time).
# Only auto-set (readonly) cells are cleared on change; manual entries survive.
for r in range(1, TABLE2_ROWS + 1):
    cat_js = (
        f'var eq = this.getField("T2_R{r}_C4");\n'
        f'var tr = this.getField("T2_R{r}_C5");\n'
        'var v = event.value;\n'
        'if (v == "Transportation (One Time)") {\n'
        '    tr.value = "$100,000.00"; tr.readonly = true;\n'
        '    if (eq.readonly) { eq.value = ""; eq.readonly = false; }\n'
        '} else if (v == "Equipment Package (One Time)") {\n'
        '    eq.value = "$7,500.00"; eq.readonly = true;\n'
        '    if (tr.readonly) { tr.value = ""; tr.readonly = false; }\n'
        '} else {\n'
        '    if (eq.readonly) { eq.value = ""; eq.readonly = false; }\n'
        '    if (tr.readonly) { tr.value = ""; tr.readonly = false; }\n'
        '}\n'
        f't2UpdateSummary({r}, v);\n'
    )
    _, obj = fields_by_name[f"T2_R{r}_C3"]
    obj[NameObject("/AA")] = DictionaryObject({NameObject("/V"): js(cat_js)})
    # commit on selection so the auto-fill happens on click, not on blur
    obj[NameObject("/Ff")] = NumberObject(int(obj.get("/Ff", 0)) | (1 << 26))

# --- document-level JS: roll page-2 category selections up into the
# page-1 summary table (ItemDesc1/Amount1 = Transportation,
# ItemDesc2/Amount2 = Equipment Package); Total then auto-sums ---
doc_js = (
    f'var T2_ROWS = {TABLE2_ROWS};\n'
    'function t2UpdateSummary(changedRow, changedValue) {\n'
    '    var trCount = 0, eqCount = 0;\n'
    '    for (var r = 1; r <= T2_ROWS; r++) {\n'
    '        var v = (r == changedRow) ? changedValue'
    ' : this.getField("T2_R" + r + "_C3").value;\n'
    '        if (v == "Transportation (One Time)") trCount++;\n'
    '        else if (v == "Equipment Package (One Time)") eqCount++;\n'
    '    }\n'
    '    var d = this.getField("ItemDesc1"), a = this.getField("Amount1");\n'
    '    if (trCount > 0) {\n'
    '        d.value = "Transportation (One Time)"'
    ' + (trCount > 1 ? " x " + trCount : "");\n'
    '        a.value = trCount * 100000;\n'
    '        d.readonly = true; a.readonly = true;\n'
    '    } else if (d.readonly) {\n'
    '        d.value = ""; a.value = ""; d.readonly = false; a.readonly = false;\n'
    '    }\n'
    '    d = this.getField("ItemDesc2"); a = this.getField("Amount2");\n'
    '    if (eqCount > 0) {\n'
    '        d.value = "Equipment Package (One Time)"'
    ' + (eqCount > 1 ? " x " + eqCount : "");\n'
    '        a.value = eqCount * 7500;\n'
    '        d.readonly = true; a.readonly = true;\n'
    '    } else if (d.readonly) {\n'
    '        d.value = ""; a.value = ""; d.readonly = false; a.readonly = false;\n'
    '    }\n'
    '}\n'
)
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

# --- clear the stand-in default on blank-default combos (see CLEAR_VALUE) ---
for nm in CLEAR_VALUE:
    _, obj = fields_by_name[nm]
    obj[NameObject("/V")] = TextStringObject("")
    if "/I" in obj:
        del obj[NameObject("/I")]

# --- auto-size font on every text field so typed text always fits its box;
# also on the narrow table-2 category combos ---
for name, (_, obj) in fields_by_name.items():
    if obj.get("/FT") == "/Tx" or (obj.get("/FT") == "/Ch" and name.startswith("T2_")):
        obj[NameObject("/DA")] = TextStringObject("/Helv 0 Tf 0 g")

# --- date formatting ---
for nm in ("InvoiceStartDate", "InvoiceEndDate", "InvoiceDate"):
    _, obj = fields_by_name[nm]
    obj[NameObject("/AA")] = DictionaryObject({
        NameObject("/K"): js('AFDate_KeystrokeEx("mm/dd/yyyy");'),
        NameObject("/F"): js('AFDate_FormatEx("mm/dd/yyyy");'),
    })

# --- currency formatting on amount fields ---
amount_names = [f"Amount{i}" for i in range(1, 6)]
for nm in amount_names:
    _, obj = fields_by_name[nm]
    obj[NameObject("/AA")] = DictionaryObject({
        NameObject("/K"): js('AFNumber_Keystroke(2, 0, 0, 0, "$", true);'),
        NameObject("/F"): js('AFNumber_Format(2, 0, 0, 0, "$", true);'),
    })

# --- auto-sum total ---
total_ref, total_obj = fields_by_name["Total"]
arr = ", ".join(f'"{n}"' for n in amount_names)
total_obj[NameObject("/AA")] = DictionaryObject({
    NameObject("/C"): js(f'AFSimple_Calculate("SUM", new Array({arr}));'),
    NameObject("/F"): js('AFNumber_Format(2, 0, 0, 0, "$", true);'),
})
acro[NameObject("/CO")] = ArrayObject([total_ref])

# --- cascading dropdowns: Subject filters Invoice Type & Invoice Category ---
import json

PH = "-- Select an option --"
TYPE_RULES = {
    "ABC": ["Initial", "Weekly", "Bi-Weekly"],
    "EFG": ["Monthly", "Quarterly", "Semi-Quarterly"],
    "HIJ": ["Semi-Annually", "Annually"],
}
CAT_RULES = {
    "ABC": CATEGORIES[0:2],
    "EFG": CATEGORIES[2:4],
    "HIJ": CATEGORIES[4:6],
}
cascade_js = (
    f'var PH = {json.dumps(PH)};\n'
    f'var typeMap = {json.dumps(TYPE_RULES)};\n'
    f'var catMap = {json.dumps(CAT_RULES)};\n'
    f'var allTypes = {json.dumps(INVOICE_TYPES)};\n'
    f'var allCats = {json.dumps(CATEGORIES)};\n'
    'var v = event.value;\n'
    'var it = this.getField("InvoiceType");\n'
    'var ic = this.getField("InvoiceCategory");\n'
    'it.setItems([PH].concat(typeMap[v] ? typeMap[v] : allTypes));\n'
    'ic.setItems([PH].concat(catMap[v] ? catMap[v] : allCats));\n'
    'it.value = PH;\n'
    'ic.value = PH;\n'
)
_, subj_obj = fields_by_name["Subject"]
subj_obj[NameObject("/AA")] = DictionaryObject({NameObject("/V"): js(cascade_js)})
# commit selection immediately so filtering fires on click, not on blur
subj_obj[NameObject("/Ff")] = NumberObject(int(subj_obj.get("/Ff", 0)) | (1 << 26))

# --- ensure Helv in /DR for our buttons ---
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
    btn = DictionaryObject({
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Widget"),
        NameObject("/FT"): NameObject("/Btn"),
        NameObject("/Ff"): NumberObject(65536),  # pushbutton
        NameObject("/T"): TextStringObject(name),
        NameObject("/Rect"): ArrayObject([FloatObject(v) for v in rect]),
        NameObject("/F"): NumberObject(4),
        NameObject("/MK"): mk,
        NameObject("/DA"): TextStringObject(da),
        NameObject("/A"): action,
        NameObject("/P"): page_ref,
    })
    ref = writer._add_object(btn)
    page["/Annots"].append(ref)
    acro["/Fields"].append(ref)
    return ref


# --- logo import button (invisible overlay on dashed box) ---
lx, ly, lw, lh = 36.0, 792 - 100, 140.0, 66.0
logo_btn_ref = add_button(
    "LogoButton",
    [lx, ly, lx + lw, ly + lh],
    DictionaryObject({NameObject("/TP"): NumberObject(1)}),  # icon only
    js("event.target.buttonImportIcon();"),
)

# --- submit-by-email button ---
# mailDoc (instead of a static SubmitForm mailto) so the email subject and
# body are built dynamically from the selected Subject and Invoice Type.
# required fields: (field name, kind, placeholder, human label)
# kind: dd = dropdown (invalid while on placeholder), cb = checkbox
# (must be checked), tx = text (must be non-empty)
REQUIRED = [
    ("Subject", "dd", PH, "Subject"),
    ("InvoiceType", "dd", PH, "Invoice Type"),
    ("BankingVerified", "dd", PH, "Verified Banking Information in SAM.gov"),
    ("RegistrationActive", "cb", "", "SAM Registration Active"),
    ("ServiceProviderName", "tx", "", "Service Provider Name"),
    ("StreetAddress", "tx", "", "Street Address"),
    ("City", "tx", "", "City"),
    ("State", "dd", "-- Select State --", "State"),
    ("ZipCode", "tx", "", "Zip Code"),
    ("POCName", "tx", "", "POC Name"),
    ("POCEmail", "tx", "", "POC Email"),
    ("RegistrationNo", "tx", "", "Registration No. (EI)"),
    ("IRS_EIN", "tx", "", "IRS/EIN"),
    # HRName / HREmail are pre-filled and read-only, so always satisfied
    ("InvoiceStartDate", "tx", "", "Invoice Start Date"),
    ("InvoiceEndDate", "tx", "", "Invoice End Date"),
    ("InvoiceDate", "tx", "", "Invoice Date"),
]

# set the Required flag (Ff bit 2) so Acrobat outlines the fields in red
# and screen readers announce them as required
for nm, _, _, _ in REQUIRED:
    _, obj = fields_by_name[nm]
    obj[NameObject("/Ff")] = NumberObject(int(obj.get("/Ff", 0)) | 2)

req_array = json.dumps(
    [{"n": n, "t": t, "ph": ph, "lb": lb} for n, t, ph, lb in REQUIRED])
submit_js = (
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
    '    var ref = this.getField("Subject").value + " - " + this.getField("State").value'
    ' + " - " + this.getField("ServiceProviderName").value + " - " + this.getField("InvoiceType").value + " Invoice";\n'
    '    var msg = "Hello,\\n\\nAttached is the " + ref + "\\n\\n";\n'
    f'    this.mailDoc({{bUI: true, cTo: "{SUBMIT_EMAIL}", cSubject: ref, cMsg: msg}});\n'
    '}\n'
)
submit_action = js(submit_js)
submit_btn_ref = add_button(
    "SubmitButton",
    [btn_x, btn_y, btn_x + btn_w, btn_y + btn_h],
    DictionaryObject({
        NameObject("/BG"): ArrayObject([FloatObject(v) for v in (0.12, 0.23, 0.39)]),
        NameObject("/BC"): ArrayObject([FloatObject(v) for v in (0.12, 0.23, 0.39)]),
        NameObject("/CA"): TextStringObject("SUBMIT INVOICE"),
    }),
    submit_action,
    da="/Helv 11 Tf 1 1 1 rg",
)

# all widget refs by field name (reportlab fields + our two buttons)
widget_refs = {n: r for n, (r, _) in fields_by_name.items()}
widget_refs["LogoButton"] = logo_btn_ref
widget_refs["SubmitButton"] = submit_btn_ref

# =====================================================================
# 508: human-readable tooltips (/TU) on every field
# =====================================================================
TOOLTIPS = {
    "Subject": "Subject. Choose ABC, EFG, or HIJ. Your choice filters the available Invoice Type and Invoice Category options",
    "InvoiceType": "Invoice type. Available choices depend on the selected Subject",
    "RegistrationActive": "SAM Registration Active. Check if the SAM registration is active",
    "BankingVerified": "Verified banking information in SAM.gov. Choose Yes or No",
    "ServiceProviderName": "Service provider name",
    "StreetAddress": "Street address",
    "City": "City",
    "State": "State. Choose a two-letter state abbreviation",
    "ZipCode": "Zip code",
    "POCName": "Point of contact name",
    "POCEmail": "Point of contact email address",
    "OrderNumber": "Order number",
    "RegistrationNo": "Registration number (EI)",
    "IRS_EIN": "IRS Employer Identification Number",
    "HRName": "HR name. Pre-filled and not editable",
    "HREmail": "HR email address. Pre-filled and not editable",
    "DHRName": "DHR name. Not editable",
    "DHREmail": "DHR email address. Not editable",
    "InvoiceStartDate": "Invoice start date in month, day, year format",
    "InvoiceEndDate": "Invoice end date in month, day, year format",
    "InvoiceNumber": "Invoice number",
    "InvoiceDate": "Invoice date in month, day, year format",
    "InvoiceCategory": "Invoice category. Available INV codes depend on the selected Subject",
    "Total": "Total amount. Calculated automatically as the sum of all item amounts",
    "LogoButton": "Add organization logo. Activates a file picker to import a logo image",
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

# =====================================================================
# 508: tag the content stream — text into marked content with MCIDs,
# decoration into Artifacts
# =====================================================================
def split_bt_blocks(s):
    """Split content stream into alternating segments outside/inside BT..ET,
    skipping (string) literals."""
    segments = []
    i, n, seg_start = 0, len(s), 0
    in_bt = False
    in_str, esc = False, False
    while i < n:
        ch = s[i]
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
        tok = s[i:i + 2]
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
    """True if the BT..ET block contains a text-showing operator
    (Tj, TJ, ', \") outside string literals. reportlab also emits empty
    BT/ET pairs for setFont calls — those are decoration, not text."""
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


# =====================================================================
# 508: structure tree in reading order (Document > H2/P/Form),
# built per page; MCIDs restart on each page
# =====================================================================
struct_root = DictionaryObject({NameObject("/Type"): NameObject("/StructTreeRoot")})
struct_root_ref = writer._add_object(struct_root)

doc_elem = DictionaryObject({
    NameObject("/Type"): NameObject("/StructElem"),
    NameObject("/S"): NameObject("/Document"),
    NameObject("/P"): struct_root_ref,
    NameObject("/T"): TextStringObject(DOC_TITLE),
})
doc_elem_ref = writer._add_object(doc_elem)

kids = ArrayObject()
parent_pairs = []   # (number-tree key, ref) — page MCID arrays + annots
# keys 0..n-1 are reserved for each page's MCID array (/StructParents)
annot_key = len(writer.pages)

for pg_idx, seq in enumerate([SEQ_P1, SEQ_P2]):
    pg = writer.pages[pg_idx]
    pg_ref = pg.indirect_reference

    contents = pg["/Contents"].get_object()
    if isinstance(contents, ArrayObject):
        data = b"".join(s.get_object().get_data() for s in contents)
    else:
        data = contents.get_data()
    stream = data.decode("latin-1")

    segments = split_bt_blocks(stream)
    # font-only BT blocks are decoration, not real text
    segments = [("art" if k == "bt" and not shows_text(s) else k, s)
                for k, s in segments]
    text_entries = [e for e in seq if e[0] == "text"]
    bt_count = sum(1 for k, _ in segments if k == "bt")
    assert bt_count == len(text_entries), \
        f"page {pg_idx + 1}: BT blocks ({bt_count}) != text draws ({len(text_entries)})"

    out_parts = []
    mcid = 0
    for kind, seg in segments:
        if kind == "bt":
            role = text_entries[mcid][1]
            out_parts.append(f"/{role} <</MCID {mcid}>> BDC\n{seg}\nEMC\n")
            mcid += 1
        elif seg.strip():  # 'out' and font-only 'art' segments are decoration
            out_parts.append(f"/Artifact BMC\n{seg}\nEMC\n")
    new_stream = DecodedStreamObject()
    new_stream.set_data("".join(out_parts).encode("latin-1"))
    pg[NameObject("/Contents")] = writer._add_object(new_stream)

    mcid_parents = ArrayObject()   # index = MCID -> struct elem ref
    mcid = 0
    for entry in seq:
        if entry[0] == "text":
            _, role, txt = entry
            el = DictionaryObject({
                NameObject("/Type"): NameObject("/StructElem"),
                NameObject("/S"): NameObject("/" + role),
                NameObject("/P"): doc_elem_ref,
                NameObject("/Pg"): pg_ref,
                NameObject("/K"): NumberObject(mcid),
            })
            ref = writer._add_object(el)
            kids.append(ref)
            mcid_parents.append(ref)
            mcid += 1
        else:
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
    pg[NameObject("/Tabs")] = NameObject("/S")  # tab order follows structure

doc_elem[NameObject("/K")] = kids

parent_pairs.sort(key=lambda p: p[0])  # number tree keys must be ascending
nums = ArrayObject()
for k, ref in parent_pairs:
    nums.append(NumberObject(k))
    nums.append(ref)
parent_tree = DictionaryObject({NameObject("/Nums"): nums})
struct_root[NameObject("/K")] = doc_elem_ref
struct_root[NameObject("/ParentTree")] = writer._add_object(parent_tree)
struct_root[NameObject("/ParentTreeNextKey")] = NumberObject(annot_key)

# =====================================================================
# 508: document-level catalog entries and metadata
# =====================================================================
root[NameObject("/StructTreeRoot")] = struct_root_ref
root[NameObject("/MarkInfo")] = DictionaryObject(
    {NameObject("/Marked"): BooleanObject(True)})
root[NameObject("/Lang")] = TextStringObject("en-US")
vp = root.get("/ViewerPreferences")
if vp is None:
    vp = DictionaryObject()
    root[NameObject("/ViewerPreferences")] = vp
else:
    vp = vp.get_object()
vp[NameObject("/DisplayDocTitle")] = BooleanObject(True)

writer.add_metadata({
    "/Title": DOC_TITLE,
    "/Subject": "Fillable service provider invoice with email submission",
    "/Creator": "reportlab + pypdf",
})

xmp = (
    '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>'
    '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    '<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">'
    f'<dc:title><rdf:Alt><rdf:li xml:lang="x-default">{DOC_TITLE}</rdf:li></rdf:Alt></dc:title>'
    '<dc:language><rdf:Bag><rdf:li>en-US</rdf:li></rdf:Bag></dc:language>'
    '</rdf:Description></rdf:RDF></x:xmpmeta>'
    '<?xpacket end="w"?>'
)
xmp_stream = DecodedStreamObject()
xmp_stream.set_data(xmp.encode("utf-8"))
xmp_stream[NameObject("/Type")] = NameObject("/Metadata")
xmp_stream[NameObject("/Subtype")] = NameObject("/XML")
root[NameObject("/Metadata")] = writer._add_object(xmp_stream)

# viewers should regenerate field appearances
acro[NameObject("/NeedAppearances")] = BooleanObject(True)

with open(FINAL, "wb") as fh:
    writer.write(fh)
print("final form written:", FINAL)

# sanity check
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
