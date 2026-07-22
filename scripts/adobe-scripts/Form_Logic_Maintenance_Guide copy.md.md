# Invoice Form — Logic Scripts & Maintenance Guide (Junior Edition)

This document contains every JavaScript that powers `Editable_Invoice.pdf`,
**fully commented line-by-line**, plus recipes for the changes you are most
likely to be asked to make (add table pages, change dropdown rules, change
amounts, etc.).

> **Two ways to change this form — pick ONE and stay consistent:**
>
> - **Path A (recommended): edit `make_invoice.py` and re-run it.**
>   Most changes are a one-line edit; the script rebuilds the whole PDF with
>   all scripts, tooltips, and accessibility tags consistent. This guide
>   points to the exact spot for each change.
> - **Path B: edit the PDF directly in Acrobat Pro (Prepare Form).**
>   Fine for small tweaks, but YOU are responsible for updating every place
>   a change touches (this guide lists them). If the team later re-runs
>   `make_invoice.py`, manual Acrobat edits are LOST — so if you go manual,
>   also update the Python script or your changes won't survive a rebuild.
>
> Acrobat JavaScript ignores `//` comments — every block below can be pasted
> into Acrobat exactly as written, comments and all.

---

## THE BIG PICTURE — how the pieces talk to each other

```
Page 1                                  Pages 2-5 (the big table)
┌──────────────────────────┐            ┌─────────────────────────────┐
│ Subject (dropdown)  ─────┼─filters──► │  (not affected)             │
│ InvoiceType (dropdown) ──┼─auto-picks │                             │
│ InvoiceCategory (dropdwn)│◄──┘        │ Each row r:                 │
│                          │            │  T2_R{r}_C3 Expense Categry │
│ ItemDesc1-3 / Amount1-3  │◄─rolls-up──│   → fills/locks C4/C5/C6    │
│   (auto summary rows)    │            │   → calls t2UpdateSummary() │
│ ItemDesc4-5 / Amount4-5  │            └─────────────────────────────┘
│   (manual rows)          │
│ Total = sum(Amount1..5)  │   t2UpdateSummary() lives at DOCUMENT level
│ Acknowledgement (checkbx)│   so every field script can call it.
│ SubmitButton ────────────┼─► validates 17 required fields, then emails
└──────────────────────────┘   the filled PDF via mailDoc()
```

**Field-name contract (do not break):** table cells are named
`T2_R{row}_C{column}` with row numbers continuing across pages
(page 2 = rows 1–35, page 3 = 36–70, page 4 = 71–105, page 5 = 106–140).
Columns: C1 Employee Name, C2 Credential Number, C3 Expense Category,
C4 Equipment Cost, C5 Transportation (One Time), C6 IT.
Script 4 literally parses the field's own name to find its row — a renamed
field breaks silently.

---

## SCRIPT 1 — Document-level: `t2Summary` (the roll-up engine)

**Lives:** Acrobat → All tools → Use JavaScript → **Document JavaScripts**,
entry named `t2Summary`. In `make_invoice.py`: the `doc_js` block (LOGIC 6).

**What it does:** counts how many table rows use each expense category and
writes summary lines into page-1 item rows 1–3. Runs every time any
category dropdown changes (they call it at the end of their own script).

```javascript
// Total number of data rows across ALL table pages.
// ⚠ MUST match reality. 4 pages x 35 rows = 140. If you add a table page,
// this becomes 175, and so on. If this number is too small, selections on
// the extra pages are silently ignored; too big, and the script crashes
// looking for fields that don't exist ("getField(...) is null").
var T2_ROWS = 140;

// Helper: writes ONE summary line on page 1.
//   descName/amtName : page-1 fields to write into (e.g. "ItemDesc1")
//   label            : text shown, e.g. "Transportation (One Time)"
//   count            : how many table rows currently use this category
//   unit             : dollar amount PER ROW
function t2SetSummaryRow(descName, amtName, label, count, unit) {
    var d = this.getField(descName), a = this.getField(amtName);
    if (count > 0) {
        // e.g. "Transportation (One Time) x 3" when count is 3
        d.value = label + (count > 1 ? " x " + count : "");
        a.value = count * unit;              // Amount fields format as $
        d.readonly = true; a.readonly = true; // lock: users can't edit a
                                              // computed summary
    } else if (d.readonly) {
        // count fell to zero AND we had locked it earlier -> clear + unlock.
        // The readonly check means we never wipe a row the user typed into.
        d.value = ""; a.value = ""; d.readonly = false; a.readonly = false;
    }
}

// The main recount. Called by every category dropdown with ITS row number
// and ITS newly picked value. Why pass those in? Because Acrobat fires
// "validate" BEFORE saving the new value into the field — so if we read
// the changing field with getField we'd still see the OLD value.
function t2UpdateSummary(changedRow, changedValue) {
    var trCount = 0, eqCount = 0, qeCount = 0;
    for (var r = 1; r <= T2_ROWS; r++) {
        var v = (r == changedRow) ? changedValue
                                  : this.getField("T2_R" + r + "_C3").value;
        // ⚠ these strings must match the dropdown options EXACTLY
        // (same spelling, same capitalization, same parentheses)
        if (v == "Transportation (One Time)") trCount++;
        else if (v == "Equipment Package (One Time)") eqCount++;
        else if (v == "Quarterly Expense") qeCount++;
    }
    // page-1 summary rows: which row shows which category, at what unit $.
    // Rows 4-5 are intentionally left for manual entry.
    t2SetSummaryRow("ItemDesc1", "Amount1", "Transportation (One Time)", trCount, 100000);
    t2SetSummaryRow("ItemDesc2", "Amount2", "Equipment Package (One Time)", eqCount, 7500);
    t2SetSummaryRow("ItemDesc3", "Amount3", "Quarterly Expense (Equipment + IT)", qeCount, 15000);
}
```

---

## SCRIPT 2 — `Subject` dropdown: filter the other two dropdowns

**Lives:** Subject field → Properties → **Validate tab** ("Run custom
validation script"). Options tab must have ☑ *Commit selected value
immediately* (otherwise this fires only when the user clicks away).
In `make_invoice.py`: `TYPE_RULES` / `CAT_RULES` + `cascade_js` (LOGIC 1).

```javascript
// The placeholder shown before anything is selected. Must match the
// first Options-tab entry of InvoiceType and InvoiceCategory EXACTLY.
var PH = "-- Select an option --";

// WHICH Invoice Types each Subject may use.
// Keys = Subject values. To change a pairing, edit these lists.
// ⚠ every string here must also exist in allTypes below (and in the
// InvoiceType field's own Options list).
var typeMap = {"T": ["Initial", "Weekly"],
               "J": ["Monthly", "Quarterly"],
               "W": ["Semi-Annually", "Annually"]};

// WHICH Invoice Categories each Subject may use. Same rules as typeMap.
var catMap = {"T": ["INV001 - Transportation & Equipment (Initial Stipend)", "INV002 - Quarterly Incentive"],
              "J": ["INV003 - Customer Summer Incentive", "INV004 - Customer Quarterly Incentive"],
              "W": ["INV005 - Employee Winter Incentive", "INV006 - Employee Quarterly Incentive"]};

// The FULL lists, used when no Subject is selected (placeholder chosen).
var allTypes = ["Initial", "Weekly", "Monthly", "Quarterly", "Semi-Annually", "Annually"];
var allCats = ["INV001 - Transportation & Equipment (Initial Stipend)", "INV002 - Quarterly Incentive", "INV003 - Customer Summer Incentive", "INV004 - Customer Quarterly Incentive", "INV005 - Employee Winter Incentive", "INV006 - Employee Quarterly Incentive"];

var v = event.value;                          // the Subject just picked
var it = this.getField("InvoiceType");
var ic = this.getField("InvoiceCategory");

// setItems REPLACES a dropdown's entire option list on the fly.
// "typeMap[v] ? typeMap[v] : allTypes" = "if v has a rule use it,
// otherwise fall back to the full list".
it.setItems([PH].concat(typeMap[v] ? typeMap[v] : allTypes));
ic.setItems([PH].concat(catMap[v] ? catMap[v] : allCats));

// Reset both to the placeholder. This is deliberate: switching Subject
// must never leave a choice from the previous Subject sitting there.
it.value = PH;
ic.value = PH;
```

---

## SCRIPT 3 — `InvoiceType` dropdown: auto-pick the Invoice Category

**Lives:** InvoiceType field → Properties → **Validate tab**. Options tab:
☑ *Commit selected value immediately*.
In `make_invoice.py`: `AUTO_CATEGORY` + `type_js` (LOGIC 2).

```javascript
// autoMap[Subject][InvoiceType] = the category to auto-select.
// To add/change a rule, edit this table. A missing combination simply
// means "don't auto-pick" — the user chooses manually from the
// (already filtered) list.
// ⚠ the category strings must be options the Subject script (script 2)
// put into InvoiceCategory — i.e. they must appear in catMap for that
// same Subject, or the assignment will be rejected.
var autoMap = {"T": {"Initial": "INV001 - Transportation & Equipment (Initial Stipend)",
                     "Weekly": "INV002 - Quarterly Incentive"},
               "J": {"Monthly": "INV003 - Customer Summer Incentive",
                     "Quarterly": "INV004 - Customer Quarterly Incentive"},
               "W": {"Semi-Annually": "INV005 - Employee Winter Incentive",
                     "Annually": "INV006 - Employee Quarterly Incentive"}};

var s = this.getField("Subject").value;       // current Subject
var ic = this.getField("InvoiceCategory");
// event.value = the Invoice Type the user just picked
if (autoMap[s] && autoMap[s][event.value]) {  // rule exists for this combo?
    ic.value = autoMap[s][event.value];       // then set the category
}
```

---

## SCRIPT 4 — Expense Category dropdowns (ALL table rows, identical code)

**Lives:** EVERY `T2_R{r}_C3` field → Properties → **Validate tab**.
Options tab on each: ☑ *Allow user to enter custom text* and
☑ *Commit selected value immediately*.
In `make_invoice.py`: the `cat_js` loop (LOGIC 5) — note the Python version
hard-codes each row number instead; both behave identically.

**The key trick:** the script asks Acrobat for its own field name and
extracts the row number from it. That's why ONE unchanged script works in
all 140 dropdowns — and why it works in any NEW rows too, as long as they
follow the `T2_R{number}_C3` naming pattern.

```javascript
// event.target = the field this script is attached to.
// name is e.g. "T2_R57_C3"; the regex captures "57".
// ⚠ if the field name doesn't match the pattern this line throws
// "match(...) is null" — that error always means a misnamed field.
var r = event.target.name.match(/^T2_R(\d+)_C3$/)[1];

// The three cost cells in THIS row:
var eq = this.getField("T2_R" + r + "_C4");   // Equipment Cost
var tr = this.getField("T2_R" + r + "_C5");   // Transportation (One Time)
var it = this.getField("T2_R" + r + "_C6");   // IT

var v = event.value;                          // category just picked/typed

// clr() = "clear this cell ONLY if a script locked it".
// A locked (readonly) cell was auto-filled by us -> safe to clear.
// An unlocked cell may hold the user's own typing -> leave it alone.
function clr(f) { if (f.readonly) { f.value = ""; f.readonly = false; } }

if (v == "Transportation (One Time)") {
    tr.value = "$100,000.00"; tr.readonly = true;   // fill + lock C5
    clr(eq); clr(it);                               // undo other auto-fills
} else if (v == "Equipment Package (One Time)") {
    eq.value = "$7,500.00"; eq.readonly = true;     // fill + lock C4
    clr(tr); clr(it);
} else if (v == "Quarterly Expense") {
    eq.value = "$7,500.00"; eq.readonly = true;     // fills BOTH C4...
    it.value = "$7,500.00"; it.readonly = true;     // ...and C6
    clr(tr);
} else {
    // blank, or a custom typed category: no auto amounts at all
    clr(eq); clr(tr); clr(it);
}

// Tell the document-level engine to recount and refresh page 1.
// Pass OUR row + NEW value because the field itself still holds the old
// value during a validate event (see Script 1's comment).
t2UpdateSummary(r, v);
```

---

## SCRIPT 5 — `Total`: auto-sum of the page-1 items table

**Lives:** Total field → Properties → **Calculate tab** → "Run custom
calculation script" (or equivalently the built-in "Value is the sum of"
picker). General tab: ☑ Read Only.
In `make_invoice.py`: the `total_obj` block (LOGIC 3).

```javascript
// AFSimple_Calculate is built into Acrobat: recalculates whenever ANY
// field changes. To include more fields in the total, add their names.
AFSimple_Calculate("SUM", new Array("Amount1", "Amount2", "Amount3", "Amount4", "Amount5"));
```

---

## SCRIPT 6 — `SubmitButton`: validate everything, then email the PDF

**Lives:** SubmitButton → Properties → **Actions tab** → Mouse Up →
Run a JavaScript. In `make_invoice.py`: `REQUIRED` + `submit_js` (LOGIC 4).

```javascript
// ONE list drives all required-field checking. Each entry:
//   n  = field name        (must match the field exactly)
//   t  = type of check:  "dd" dropdown  -> fails while on its placeholder
//                        "cb" checkbox  -> fails while unchecked ("Off")
//                        "tx" text      -> fails while empty
//   ph = the placeholder to compare against (dropdowns only)
//   lb = human-readable label shown in the error alert
// TO ADD a required field: add one line here (and tick "Required" on the
// field's General tab so it gets the red outline too).
// TO REMOVE one: delete its line.
var required = [
    {"n": "Subject", "t": "dd", "ph": "-- Select an option --", "lb": "Subject"},
    {"n": "InvoiceType", "t": "dd", "ph": "-- Select an option --", "lb": "Invoice Type"},
    {"n": "BankingVerified", "t": "dd", "ph": "-- Select an option --", "lb": "Verified Banking Information in SAM.gov"},
    {"n": "RegistrationActive", "t": "cb", "ph": "", "lb": "SAM Registration Active"},
    {"n": "ServiceProviderName", "t": "tx", "ph": "", "lb": "Service Provider Name"},
    {"n": "StreetAddress", "t": "tx", "ph": "", "lb": "Street Address"},
    {"n": "City", "t": "tx", "ph": "", "lb": "City"},
    {"n": "State", "t": "dd", "ph": "-- Select State --", "lb": "State"},
    {"n": "ZipCode", "t": "tx", "ph": "", "lb": "Zip Code"},
    {"n": "POCName", "t": "tx", "ph": "", "lb": "POC Name"},
    {"n": "POCEmail", "t": "tx", "ph": "", "lb": "POC Email"},
    {"n": "RegistrationNo", "t": "tx", "ph": "", "lb": "Registration No. (EI)"},
    {"n": "OperationalDate", "t": "tx", "ph": "", "lb": "Operational Date"},
    {"n": "InvoiceStartDate", "t": "tx", "ph": "", "lb": "Invoice Start Date"},
    {"n": "InvoiceEndDate", "t": "tx", "ph": "", "lb": "Invoice End Date"},
    {"n": "InvoiceDate", "t": "tx", "ph": "", "lb": "Invoice Date"},
    {"n": "Acknowledgement", "t": "cb", "ph": "", "lb": "Acknowledgement of accuracy"}
];

// Walk the list and collect the labels of everything still incomplete.
var missing = [];
for (var i = 0; i < required.length; i++) {
    var r = required[i];
    var v = this.getField(r.n).value;
    if (r.t == "dd" && v == r.ph) missing.push(r.lb);
    else if (r.t == "cb" && v == "Off") missing.push(r.lb);    // "Off" = unchecked
    else if (r.t == "tx" && (v == null || String(v) == "")) missing.push(r.lb);
}

if (missing.length > 0) {
    // ONE alert naming every incomplete field. No email is sent.
    app.alert("Please complete the following required fields before submitting:\n\n- "
              + missing.join("\n- "), 1);
} else {
    // Email subject built from live values, e.g.
    //   "T - TX - Acme Services LLC - Weekly Invoice"
    // Add more fields to the subject by concatenating more getField calls.
    var ref = this.getField("Subject").value + " - "
            + this.getField("State").value + " - "
            + this.getField("ServiceProviderName").value + " - "
            + this.getField("InvoiceType").value + " Invoice";
    var msg = "Hello,\n\nAttached is the " + ref + "\n\n";   // email body
    // mailDoc: opens the user's mail client with THIS filled PDF attached.
    // cTo = recipient — CHANGE THE EMAIL ADDRESS HERE.
    // (bUI:true shows the compose window instead of sending silently.)
    this.mailDoc({bUI: true, cTo: "test@test.com", cSubject: ref, cMsg: msg});
}
```

---

## SCRIPT 7 — `LogoButton`: click to place the organization logo

**Lives:** LogoButton → Actions tab → Mouse Up → Run a JavaScript.
Options tab: Layout = **Icon only**.

```javascript
// Opens a file picker; the chosen image becomes the button's face,
// i.e. the logo appears inside the dashed box.
event.target.buttonImportIcon();
```

---
---

# MAINTENANCE RECIPES

## RECIPE 1 — Add table pages (page 6, 7, 8 …)

Each table page holds 35 rows. Adding pages = extending the row range and
keeping `T2_ROWS` in sync.

### Path A — via `make_invoice.py` (two numbers, done)
1. Open `make_invoice.py`, find `N_TABLE_PAGES = 4` → set to 5 (or 6, 7…).
2. Find `TOTAL_PAGES = 5` → set to N_TABLE_PAGES + 1 (footer "Page X of Y").
3. Run `python3 make_invoice.py`.
That's everything: new pages, correctly numbered fields (rows 141–175 for
page 6), scripts on every new dropdown, `T2_ROWS` updated automatically
(it's derived from the row counter), tooltips, tab order, and tagging.

### Path B — manually in Acrobat Pro
1. **Duplicate a table page:** Organize Pages → right-click page 5 →
   Copy, then Paste after it. ⚠ Acrobat duplicates the FIELDS too, and
   duplicated fields share names with the originals (same-name fields
   mirror each other's values!). You must rename every field on the new
   page.
2. **Rename the 210 new fields** in Prepare Form's Fields panel, following
   the pattern exactly: page 6 = rows 141–175, so its first-row cells are
   `T2_R141_C1` … `T2_R141_C6`, and its last row is `T2_R175_C6`.
3. **Verify the dropdowns kept their settings** (spot-check a few):
   Options list (blank + 3 categories), ☑ Allow custom text, ☑ Commit
   immediately, and the Script 4 validate script. Because Script 4 derives
   its row from the field name, the copied script works unchanged once the
   field is renamed correctly.
4. **Update the counter:** Document JavaScripts → `t2Summary` → change
   `var T2_ROWS = 140;` to `175`. (This is the step people forget —
   symptoms: selections on the new page don't appear in the page-1 totals.)
5. **Fix the footers:** the copied page still says "Page 5 of 5" — edit
   the text with Edit PDF on every page ("Page 6 of 6" etc.).
6. Re-run the accessibility checker (new pages need tagging: Prepare for
   accessibility → Autotag).
7. Test: pick a category in the LAST row of the NEW page → page-1 summary
   and Total must update.

## RECIPE 2 — Change which Invoice Types / Categories a Subject shows
1. Edit `typeMap` / `catMap` in **Script 2** (Subject → Validate tab).
2. If you added a brand-new Type or Category string, ALSO add it to:
   - `allTypes` / `allCats` in the same script,
   - the field's own Options-tab list (that's what shows before any
     Subject is picked),
   - `autoMap` in **Script 3** if the new combo should auto-pick.
3. Path A equivalents: `TYPE_RULES`, `CAT_RULES`, `INVOICE_TYPES`,
   `CATEGORIES`, `AUTO_CATEGORY` in `make_invoice.py`.
⚠ Strings must match EXACTLY everywhere (copy-paste them, don't retype).

## RECIPE 3 — Add a new Subject (e.g. "X")
1. Add "X" to the Subject field's Options list (after the placeholder).
2. Add a `"X": [...]` entry to `typeMap` AND `catMap` in Script 2.
3. Optionally add `"X": {...}` rules to `autoMap` in Script 3.
4. Path A: `SUBJECTS`, `TYPE_RULES`, `CAT_RULES`, `AUTO_CATEGORY`.

## RECIPE 4 — Change the auto-fill dollar amounts
The amounts exist in TWO places that must stay in sync:
1. **Script 4** (every category dropdown): the display strings
   `"$100,000.00"` / `"$7,500.00"`. Changing them here changes what
   appears in the table cells. (Path B pain: that's 140 fields to re-paste
   — strong argument for Path A.)
2. **Script 1** (`t2Summary`): the numeric `100000` / `7500` / `15000`
   in the three `t2SetSummaryRow` calls — these drive the page-1 summary
   math. Remember Quarterly Expense's unit is the SUM of its two cells.
Path A: the same two spots in `make_invoice.py` (LOGIC 5 and LOGIC 6).

## RECIPE 5 — Add a new Expense Category with its own auto-fill
1. Add the option string to every category dropdown's Options list
   (Path A: `EXPENSE_CATEGORIES`).
2. In **Script 4**, add an `else if (v == "New Category") { ... }` branch
   filling/locking whichever cost cells apply (copy an existing branch).
3. In **Script 1**, add a counter (`else if (v == "New Category") xxCount++;`)
   and a `t2SetSummaryRow("ItemDesc4", "Amount4", "New Category", xxCount, UNIT);`
   line if it should roll up to page 1 — note that consumes manual row 4.
4. Path A: `EXPENSE_CATEGORIES` + the `cat_js` and `doc_js` blocks.

## RECIPE 6 — Change the submit email address, subject, or body
All in **Script 6**: `cTo` for the recipient; the `ref` line builds the
subject; `msg` is the body. Path A: `SUBMIT_EMAIL` constant and the
`submit_js` block.

## RECIPE 7 — Make another field required / not required
1. Script 6: add or remove its line in the `required` list.
2. The field's General tab: tick/untick **Required** (the red outline).
3. The label's red asterisk is static page text — Edit PDF (Path B) or the
   `required=True` argument on the label in `make_invoice.py` (Path A).

---

# DEBUGGING CHEAT SHEET

Open Acrobat's JavaScript console with **Ctrl+J** (Windows) / **Cmd+J**
(Mac) — errors from any script appear there. You can also test snippets:
type `this.getField("T2_R141_C3").value` and press Ctrl+Enter.

| Symptom | Cause |
|---|---|
| `t2UpdateSummary is not defined` | Document JavaScript (Script 1) missing or renamed |
| `this.getField(...) is null` | A script references a field name that doesn't exist — typo or renamed field |
| `match(...) is null` in a table dropdown | Field name doesn't follow `T2_R{n}_C3` |
| New page's selections don't reach page-1 totals | `T2_ROWS` not updated (Recipe 1 step 4) |
| Two cells always show the same text | Duplicate field names (paste without rename) |
| Dropdown logic fires only after clicking elsewhere | "Commit selected value immediately" unchecked |
| Category auto-pick silently does nothing | String mismatch between `autoMap` and the actual option text |
| Summary shows stale counts after switching categories rapidly | Almost always a string mismatch in Script 1's comparisons |
| Everything dead in a web browser | Browsers don't run PDF JavaScript — must use Acrobat/Reader |

---
*Companion files: `make_invoice.py` (rebuilds the PDF — the commented
"LOGIC 1–6" sections mirror the scripts above), `Acrobat_Form_Setup_Guide.md`
(click-by-click field creation), `Editable_Invoice.pdf` (working reference).*
