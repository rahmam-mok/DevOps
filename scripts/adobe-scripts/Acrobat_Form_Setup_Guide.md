# Building the Interactive Invoice Form in Adobe Acrobat Pro
## A Complete Step-by-Step Guide (Junior-Friendly Edition)

This guide walks you through recreating every field, dropdown, calculation,
and button behavior of `Editable_Invoice.pdf` using **Adobe Acrobat Pro**,
starting from zero forms experience. Follow the parts in order — later steps
depend on earlier ones.

**Time estimate:** 3–5 hours for a first-timer (most of it is the 35-row
table on page 2).

---

# PART A — Before You Start

## A1. What you need

| Requirement | Why |
|---|---|
| **Adobe Acrobat Pro** (not the free Reader) | Only Pro can create/edit form fields |
| A **base PDF** with the visual layout | Prepare Form adds fields ON TOP of an existing PDF — it does not draw tables, labels, or colored bars |
| This guide open on a second monitor (or printed) | You will copy-paste scripts from it |

## A2. Getting a base layout PDF

Prepare Form does **not** create the visual design (section headers, the
table grid, labels like "SUBJECT *"). You need that as a normal PDF first.
Two options:

- **Option 1 (recommended):** design the two pages in Microsoft Word or
  Excel — the navy section bars, all the labels with red asterisks, the
  dashed logo box, the 8-column table grid on page 2 — then **File → Save
  As → PDF**. Leave empty space where fields will go.
- **Option 2:** reuse the existing `Editable_Invoice.pdf` as your canvas.
  If you do this, the fields already exist; this guide then serves as a
  reference for *how* everything is wired so you can modify it.

The rest of this guide assumes Option 1: a static PDF with no fields yet.

## A3. Open the form editor

1. Open your base PDF in Acrobat Pro.
2. Click **All tools** (left panel) → **Prepare a form**.
   - Older Acrobat: **Tools** tab (top) → **Prepare Form** → **Open**.
3. If Acrobat asks *"Do you want Acrobat to detect form fields?"* click
   **No / Start from scratch**. Auto-detection creates messy field names,
   and our scripts need exact names.
4. You are now in form-editing mode. Learn these three UI landmarks:
   - **Top toolbar:** icons to add each field type — Text Field,
     Checkbox, Radio, Dropdown (a small list icon), Button, etc. Hover
     over each icon to see its name.
   - **Right panel — "Fields" list:** every field you create appears
     here, grouped by page. Use it to find/rename fields later.
   - **PREVIEW / EDIT toggle** (top right): PREVIEW lets you try the form
     like an end user; EDIT returns to placing fields. You will switch
     between these constantly while testing.

## A4. The two skills you'll repeat 246 times

**Placing a field:**
1. Click the field-type icon in the toolbar (e.g., "Add a text field").
2. Your cursor becomes a crosshair — click-drag a rectangle where the
   field belongs.
3. A small yellow box pops up asking for the **Field Name**. Type the
   exact name from this guide (e.g., `ServiceProviderName`). Spelling
   and capitalization must match **exactly** — the scripts look fields
   up by name.
4. Press Enter. To fine-tune position/size, drag the field or its
   handles; arrow keys nudge by 1pt.

**Opening a field's Properties:**
- Double-click the field (or right-click → **Properties…**).
- A dialog opens with tabs: **General, Appearance, Position, Options,
  Actions, Format, Validate, Calculate** (tabs vary by field type).
  Everything in this guide happens in these tabs.
- Click **Close** when done — changes save immediately.

> **Save your file often** (Ctrl/Cmd+S). Acrobat has no undo history for
> some form operations.

---

# PART B — Create All Page-1 Fields

Work top to bottom. For each row of the table below: place the field
where its label sits in your layout, give it the exact name, set the type.
Leave all Properties at defaults for now — Parts D–G configure them.

| # | Field name | Type | Where on the page |
|---|---|---|---|
| 1 | `LogoButton` | **Button** | covering the dashed logo box |
| 2 | `Subject` | **Dropdown** | under SUBJECT label |
| 3 | `InvoiceType` | **Dropdown** | under INVOICE TYPE |
| 4 | `RegistrationActive` | **Checkbox** | left of "SAM Registration Active" text |
| 5 | `BankingVerified` | **Dropdown** | under HAVE YOU VERIFIED BANKING INFORMATION IN SAM.GOV? |
| 6 | `ServiceProviderName` | Text Field | full width |
| 7 | `StreetAddress` | Text Field | full width |
| 8 | `City` | Text Field | left third |
| 9 | `State` | **Dropdown** | middle |
| 10 | `ZipCode` | Text Field | right |
| 11 | `POCName` | Text Field | left half |
| 12 | `POCEmail` | Text Field | right half |
| 13 | `OrderNumber` | Text Field | left third |
| 14 | `RegistrationNo` | Text Field | middle third |
| 15 | `InvoiceNumber` | Text Field | right third |
| 16 | `HRName` | Text Field | left half |
| 17 | `HREmail` | Text Field | right half |
| 18 | `DHRName` | Text Field | left half |
| 19 | `DHREmail` | Text Field | right half |
| 20 | `InvoiceStartDate` | Text Field | first quarter |
| 21 | `InvoiceEndDate` | Text Field | second quarter |
| 22 | `OperationalDate` | Text Field | third quarter |
| 23 | `InvoiceDate` | Text Field | fourth quarter |
| 24 | `InvoiceCategory` | **Dropdown** | full width |
| 25–29 | `ItemDesc1` … `ItemDesc5` | Text Field | 5 rows, wide left column of items table |
| 30–34 | `Amount1` … `Amount5` | Text Field | 5 rows, narrow right column |
| 35 | `Total` | Text Field | right column, total row |
| 36 | `SubmitButton` | **Button** | bottom left |

**Tips for the items table (25–34):** place `ItemDesc1` and `Amount1`,
select both (Shift-click), copy-paste (Ctrl/Cmd+C, Ctrl/Cmd+V), position
the copies on row 2, then **rename** the copies in the right-hand Fields
panel (right-click → Rename) to `ItemDesc2`/`Amount2`, and so on.
⚠️ If you paste without renaming, Acrobat treats same-named fields as ONE
field shown in two places (typing in one fills the other) — not what we
want here.

**Alignment:** select several fields → right-click → **Align, Distribute
or Center** to line them up neatly.

---

# PART C — Create the Table Pages (pages 2–7, 35 rows × 8 columns each)

Row numbers run CONTINUOUSLY across the six table pages: page 2 = rows
1–35, page 3 = 36–70, page 4 = 71–105, page 5 = 106–140, page 6 =
141–175, page 7 = 176–210.

Field names follow the pattern **`T2_R{row}_C{column}`** — e.g., the
Expense Category cell of row 12 is `T2_R12_C5`. The scripts *parse* these
names, so the pattern is mandatory.

| Column | Name pattern | Type |
|---|---|---|
| First Name | `T2_R{r}_C1` | Text Field |
| Middle Initial | `T2_R{r}_C2` | Text Field |
| Last Name | `T2_R{r}_C3` | Text Field |
| Credential Number | `T2_R{r}_C4` | Text Field |
| Expense Category | `T2_R{r}_C5` | **Dropdown** |
| Equipment | `T2_R{r}_C6` | Text Field |
| Transportation | `T2_R{r}_C7` | Text Field |
| Information Technology | `T2_R{r}_C8` | Text Field |

## C1. Build row 1 by hand

Create the eight fields `T2_R1_C1` … `T2_R1_C8` in the first table row,
sized to their columns. Get the sizing/alignment perfect NOW — every
other row will be a copy of this one.

## C2. Configure row 1's dropdown before copying

Do Part D's Expense-Category setup (options list, custom text, commit
immediately) on `T2_R1_C5` **now**, so all copies inherit it and you
only paste the options list once instead of 35 times.

## C3. Duplicate the row 34 times

Acrobat's "Create Multiple Copies" renames fields with suffixes
(`T2_R1_C1.0.0`) which breaks our naming pattern, so use copy-paste +
rename instead:

1. Select all eight row-1 fields (drag a rubber-band selection around the row).
2. Ctrl/Cmd+C, Ctrl/Cmd+V → drag the pasted row into table row 2
   (hold Shift while dragging to keep it horizontally aligned).
3. In the Fields panel, rename each of the eight new fields: change the
   `R1` part to `R2` (e.g., `T2_R1_C5#1` → `T2_R2_C5`). Keep the column
   number the same.
4. Repeat for rows 3–35.

**Faster alternative:** copy the whole *block* of finished rows each
time (copy rows 1–2 → paste as rows 3–4, copy 1–4 → paste as 5–8, …).
You still must rename every field, but positioning gets faster.

This is tedious — budget an hour, be careful with the renaming, and
Ctrl/Cmd+S after every few rows.

---

# PART D — Dropdown Option Lists

For each dropdown: double-click it → **Options tab**. Type each entry in
the **Item** box and click **Add** (top entry = default shown).

## D1. `Subject`
```
-- Select an option --
T
J
W
```
Also on the Options tab: ☑ **Commit selected value immediately**.

## D2. `InvoiceType`
Enter the FULL list — the Subject script narrows it at runtime:
```
-- Select an option --
T-Initial
T-Quarterly
J-Initial
J-Quarterly
W-Initial
W-Quarterly
```
Also: ☑ **Commit selected value immediately**.

## D3. `BankingVerified`
```
-- Select an option --
Yes
No
```

## D4. `State`
First item `-- Select State --`, then all 50 codes, one Add per code:
```
AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD
MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC
SD TN TX UT VT VA WA WV WI WY
```

## D5. `InvoiceCategory`
Full list (narrowed at runtime):
```
-- Select an option --
CL 1: T, Initial Stipend 1-Time Only
CL 4: T, Quarterly Incentive
CL 6: J, Initial Stipend 1-Time Only
CL 8: J, Quarterly Incentive
CL 9: W, Initial Stipend 1-Time Only
CL 11: W, Quarterly Incentive
```

## D6. Every `T2_R{r}_C5` (Expense Category — 210 fields)
First item is an **empty line**: click in the Item box, press nothing,
click **Add** (creates a blank entry), then:
```
One-Time Transportation
Initial Equipment Package
Quarterly Incentive
```
Also check BOTH: ☑ **Allow user to enter custom text**
and ☑ **Commit selected value immediately**.
(If you configured `T2_R1_C5` before copying — step C2 — every copy
already has all of this. Spot-check a few.)

> **Why "Commit selected value immediately" matters:** without it, a
> dropdown's scripts run only when the user clicks elsewhere. With it,
> the cascade/auto-fill happens the instant an option is picked.

---

# PART E — Formatting, Defaults, Read-Only, Required

## E1. Date fields
For `InvoiceStartDate`, `InvoiceEndDate`, `InvoiceDate` (NOT
`InvoiceNumber` or `OperationalDate` — those hold placeholder text): Properties → **Format tab** → Select format category:
**Date** → choose `mm/dd/yyyy`. Acrobat now rejects non-dates and shows
a date-entry hint.

## E2. Currency fields
For `Amount1` … `Amount5` and `Total`: **Format tab** → Category:
**Number** → Decimal Places: **0**, Currency Symbol: **$**, symbol
location: before. Entries now display as `$1,000` (no cents shown).

## E2b. Length limits & ZIP format
- `RegistrationNo`: Properties → **Options tab** → ☑ "Limit of __
  characters" → **12** (a SAM UEI is 12 alphanumeric characters).
- `ZipCode`: Options tab → limit of **5** characters, AND **Format tab**
  → Category **Special** → **Zip Code** (rejects non-digits).

## E3. Auto-size text (so long entries always fit)
For EVERY text field: **Appearance tab** → Font Size: **Auto**.
Do this in bulk: click one text field, Ctrl/Cmd+click (or rubber-band)
many at once, right-click → Properties → Appearance → Auto. Repeat per
page.

## E4. Pre-filled, locked fields
- `HRName`, `HREmail`, `DHRName`, `DHREmail`: **General tab** → ☑ Read
  Only, NO default value — the Invoice Type script fills them per team.
- `OperationalDate`: Default Value: `Will Be Filled By HR`; ☑ Read Only.
- `InvoiceCategory`: ☑ Read Only — it is auto-selected by the Invoice
  Type script and never operated by the user.
- `HREmail`: Default Value: `test@test.com`; ☑ Read Only.
- `DHRName`, `DHREmail`: no default; ☑ Read Only.
- `Total`: ☑ Read Only (its value comes from the calculation).

After setting defaults, use **More (in Prepare Form toolbar) → Clear
Form** then check the defaults appear; or close/reopen Properties.

## E5. Required fields
For each of these 16 fields: **General tab** → ☑ **Required**:
`Subject`, `InvoiceType`, `BankingVerified`, `RegistrationActive`,
`ServiceProviderName`, `StreetAddress`, `City`, `State`, `ZipCode`,
`POCName`, `POCEmail`, `RegistrationNo`,
`InvoiceStartDate`, `InvoiceEndDate`, `InvoiceDate`.

Acrobat outlines required fields in red. **Note:** this flag alone does
NOT stop our JavaScript submit — Part F6's script does the actual
enforcement. Set both so visuals and behavior agree.

## E6. Tooltips (accessibility — do not skip)
Every field's **General tab** has a **Tooltip** box. Screen readers speak
this text, and Acrobat shows it on hover. Enter a short description for
each field, e.g.:
- `Subject` → *"Subject. Choose T, J, or W. Your choice filters
  the available Invoice Type and Invoice Category options"*
- `State` → *"State. Choose a two-letter state abbreviation"*
- `Total` → *"Total amount. Calculated automatically"*
- `T2_R5_C5` → *"Additional details table, row 5, Expense Category.
  Choose from the list or type a custom category"*
- Buttons too: `SubmitButton` → *"Submit invoice. Sends the completed
  PDF by email to test@test.com"*

## E7. Tab order
Right panel → Fields list → **⋮ (three-dot menu) → Order Tabs by
Structure** (or "by Row"). Then PREVIEW and press Tab repeatedly —
focus should move top-to-bottom, left-to-right, and across page-2 rows
left-to-right then down.

---

# PART F — The JavaScript (the "logic")

This is where the form comes alive. **Do F1 first** — the table scripts
call the function it defines, and will error if it doesn't exist yet.

> **How to paste a script without typos:** always copy the entire gray
> block, including the first and last lines. After pasting, click OK —
> if Acrobat reports a syntax error, you likely missed a brace.

## F1. Document-level script (the page-2 → page-1 roll-up)

**Navigation:** All tools → **Use JavaScript** → **Document JavaScripts**
(older Acrobat: Tools → JavaScript → Document JavaScripts).
1. In "Script Name" type: `t2Summary` → click **Add**.
2. Delete the auto-inserted stub (`function t2Summary() {}`).
3. Paste ALL of this, click OK, then Close:

> **Script code:** copy the current, fully commented script from
> `Form_Logic_Maintenance_Guide.md` → **SCRIPT 1**. The code is kept
> in that ONE place only, so the two guides can never drift apart.

**What it does:** counts how many page-2 rows currently use each expense
category, then writes "label x count" and count × unit price into page-1
item rows 1–3 and locks them. If a category's count drops to zero its
summary row is cleared and unlocked. The `changedRow`/`changedValue`
parameters exist because dropdown validate events fire *before* the new
value is saved into the field — the changing row reports its new value
directly.

## F2. `Subject` — filter the other two dropdowns

Double-click `Subject` → **Validate tab** → select **"Run custom
validation script"** → click **Edit…** → paste → OK → Close:

> **Script code:** copy the current, fully commented script from
> `Form_Logic_Maintenance_Guide.md` → **SCRIPT 2**. The code is kept
> in that ONE place only, so the two guides can never drift apart.

**What it does:** whenever Subject changes, it REPLACES the option lists
of Invoice Type and Invoice Category (`setItems`) with the allowed
subset, and resets both to the placeholder so a choice made under the
previous Subject can never linger. Selecting the placeholder itself
restores the full lists.

**To change the pairings later:** edit `typeMap`/`catMap` here, and keep
D2/D5's full lists in sync.

## F3. `InvoiceType` — auto-select the Invoice Category

Double-click `InvoiceType` → **Validate tab** → "Run custom validation
script" → Edit → paste:

> **Script code:** copy the current, fully commented script from
> `Form_Logic_Maintenance_Guide.md` → **SCRIPT 3**. The code is kept
> in that ONE place only, so the two guides can never drift apart.

**What it does:** looks up the (current Subject, just-picked Invoice
Type) pair in `autoMap`; on a match it sets Invoice Category. Because F2
already narrowed the category list, the value set here is always one of
the legal options. All six combos are mapped, so in practice the
category always self-selects once Subject + Type are chosen.

## F4. Every `T2_R{r}_C5` — auto-fill & lock cost cells

**The same script goes into ALL 210 dropdowns unchanged** — it reads its
own row number out of the field's name. For each `T2_R{r}_C5`:
Properties → **Validate tab** → "Run custom validation script" → Edit →
paste:

> **Script code:** copy the current, fully commented script from
> `Form_Logic_Maintenance_Guide.md` → **SCRIPT 4**. The code is kept
> in that ONE place only, so the two guides can never drift apart.

**What it does, per row:**
- *One-Time Transportation* → Transportation cell (C7) = $100,000, locked.
- *Initial Equipment Package* → Equipment Cost (C6) = $7,500, locked.
- *Quarterly Incentive* → BOTH Equipment Cost (C6) and IT (C8) = $7,500, locked.
- *Anything else* (blank or custom text) → unlock & clear auto-filled cells.
- `clr()` only clears cells that are read-only (i.e., that THIS script
  locked), so costs a user typed manually are never destroyed.
- The last line refreshes the page-1 summary (F1's function).

**Shortcut:** if you configured `T2_R1_C5` fully before copying the row
(step C2 + this script), all 35 copies already carry the script.
Spot-check rows 2, 10, and 35 to confirm.

## F5. `Total` — auto-sum of the items table

Double-click `Total` → **Calculate tab** → choose **"Value is the
sum (+) of:"** → click **Pick…** → tick `Amount1`, `Amount2`, `Amount3`,
`Amount4`, `Amount5` → OK.

(Equivalent custom calculation script, if you prefer:
`AFSimple_Calculate("SUM", new Array("Amount1", "Amount2", "Amount3", "Amount4", "Amount5"));`)

If totals ever update one change "late", fix the order: Prepare Form
right panel → **More → Set Field Calculation Order** → make sure `Total`
is last.

## F6. `SubmitButton` — validate everything, then email the PDF

1. Double-click `SubmitButton`.
2. **Options tab:** Layout = *Label only*; Label = `SUBMIT INVOICE`.
3. **Appearance tab:** Fill Color = dark navy, text color = white,
   font size 11.
4. **Actions tab:** Select Trigger = **Mouse Up**; Select Action =
   **Run a JavaScript** → click **Add…** → paste → OK:

> **Script code:** copy the current, fully commented script from
> `Form_Logic_Maintenance_Guide.md` → **SCRIPT 6**. The code is kept
> in that ONE place only, so the two guides can never drift apart.

**What it does:** walks the `required` list — dropdowns (`"t": "dd"`)
must be off their placeholder, the checkbox (`"cb"`) must be checked
(unchecked = `"Off"`), text fields (`"tx"`) must be non-empty. If
anything is missing it shows ONE alert naming every incomplete field and
stops. Otherwise it opens the user's mail client with the filled PDF
attached, To = `test@test.com`, and a subject/body built live from the
form, e.g. **"T - TX - Acme LLC - Weekly Invoice"**.

**To change the recipient:** edit the `cTo:` value on the last line.
**To add a required field:** add one `{"n": …}` line to the list.

## F7. `LogoButton` — click-to-place logo

1. Double-click `LogoButton`.
2. **Options tab:** Layout = **Icon only**; Behavior = **Push**.
3. **Actions tab:** Trigger **Mouse Up** → **Run a JavaScript** → Add:

```javascript
event.target.buttonImportIcon();
```

**What it does:** at fill time, clicking the (invisible) button opens a
file-picker; the chosen image becomes the button face — i.e., the logo
appears inside the dashed box.

---

# PART G — Final Checks

## G1. Full functional test (use PREVIEW mode)

| # | Do this | Expect this |
|---|---|---|
| 1 | Subject = T | Invoice Type list shrinks to T-Initial + T-Quarterly |
| 2 | Invoice Type = T-Initial | Category self-selects CL 1 |
| 3 | Switch Subject to J | Type & Category reset to placeholders; list = J-Initial/J-Quarterly |
| 4 | Type = J-Quarterly | Category = CL 8 |
| 5 | Page 2 row 1: category = One-Time Transportation | C7 = $100,000 locked; page-1 row 1 = "One-Time Transportation" $100,000; Total = $100,000 |
| 6 | Row 2: category = Quarterly Incentive | C6 AND C8 = $7,500 locked; page-1 row 3 = "Quarterly Incentive (Equipment + Information Technology)" $15,000; Total = $115,000.00 |
| 7 | Row 1: switch to Initial Equipment Package | Row 1's C5 clears/unlocks, C4 = $7,500; page-1 rows recount |
| 8 | Type a custom category in row 3 | No auto-fill; cost cells stay editable |
| 9 | Click SUBMIT with fields empty | One alert listing every missing field |
| 10 | Fill all required, click SUBMIT | Email opens, PDF attached, dynamic subject/body |
| 11 | Try typing in HR Name / Total | Not possible (read-only) |
| 12 | Click the logo box | File picker opens; picked image shows |
| 13 | Bad date in Invoice Date (e.g. "abc") | Acrobat rejects it |
| 14 | Type a long name in a small field | Font shrinks to fit |

## G2. Accessibility check (508)

All tools → **Prepare for accessibility** → **Check for accessibility**
→ Start Checking. Fix what it flags; typical to-dos on a hand-built
form: document Title (File → Properties → Description), language
(Properties → Advanced → Language = English), tags (Prepare for
accessibility → "Automatically tag PDF" + "Autotag form fields"), and
tooltips on any field you missed (E6).

## G3. Save a distribution copy

**File → Save As** a new name for the fill-out copy you send to users.
Keep your editing master separate — future changes are much easier on
the master.

---

# PART H — Troubleshooting (common junior mistakes)

| Symptom | Likely cause / fix |
|---|---|
| Typing in one table cell fills another cell too | Two fields share one name (pasted without renaming). Rename in the Fields panel. |
| Dropdown script only fires after clicking elsewhere | "Commit selected value immediately" not checked (Options tab). |
| Clicking a category does nothing, or console shows `t2UpdateSummary is not defined` | The document-level script (F1) is missing — it must exist before the field scripts run. Redo F1 exactly, name `t2Summary`. |
| `TypeError: this.getField(...) is null` | A script references a field name that doesn't exist — check spelling/case of the named field (e.g., `OperationalDate` not `Operational-Date`). |
| Auto-category never fires | F3's script is on the wrong field (must be on `InvoiceType`, Validate tab), or Subject's value doesn't exactly match `"T"` etc. |
| Page-2 auto-fill errors with `match(...) is null` | The dropdown's field name doesn't match the `T2_R{number}_C5` pattern. Fix the name. |
| Total doesn't update, or lags one change behind | Amounts aren't in the calc: redo F5's Pick list; or fix More → Set Field Calculation Order (Total last). |
| Amounts show `100000` instead of `$100,000` | Format tab not set to Number/2 decimals/$ on that Amount field (E2). |
| Submit shows no alert and no email | The script has a syntax error (Acrobat usually warns on save). Re-paste F6 in full. |
| Email opens but subject/body are empty | The user's default mail handler is webmail — known Acrobat limitation; desktop Outlook/Apple Mail work. |
| Required red outline shows but submit goes through anyway | Expected: the Required flag is visual. Enforcement is F6's `required` list — make sure the field is listed there. |
| Everything works in Acrobat but not in a browser | Browser PDF viewers don't run form JavaScript. Users must open the file in Acrobat/Acrobat Reader. |

---

*Companion files: `Editable_Invoice.pdf` (working reference — open it in
Acrobat and inspect any field's Properties to compare against yours) and
`make_invoice.py` (regenerates the reference PDF from scratch).*
