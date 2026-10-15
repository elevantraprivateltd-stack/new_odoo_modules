# Purchase 3-Way Matching — Odoo 19 Community

This is a custom Community addon that implements a basic PO / receipt / vendor-bill matching workflow. It is not an official Odoo Enterprise module and has not been runtime-tested against your particular Odoo installation.

## Workflow
1. Enable **Purchase → Configuration → Settings → 3-Way Matching**.
2. Confirm purchase orders for a vendor.
3. Create an incoming receipt and choose the vendor.
4. Select the relevant open purchase order(s) in **Purchase Orders**. The remaining quantities on the selected PO lines are loaded into the receipt. Validate the actual quantities received; create a backorder for the remainder when appropriate.
5. On each physical product, open the Purchase tab and set **Control Policy** to **On received quantities**. Create the vendor bill from the purchase order, not as an unrelated manual bill, so PO-line links are retained and standard Odoo received-quantity billing can apply.
6. The bill displays a matching status. Registering payment is blocked if a PO-linked bill quantity exceeds the received quantity or exceeds the ordered quantity.

## Important limitations
- A vendor bill with no PO-linked product lines is labelled **Non-PO Bill (No Matching)** and is not blocked by this addon. This follows the requested separate-accounting-review flow; it is not considered a successful 3-way match.
- This addon blocks payment registration for bills that fail quantity matching. It does not block posting the bill; this is closer to Odoo's standard 3-way-match payment gate.
- Quantity checks do not fully reconcile unit prices, taxes, freight, returns, currency differences, or every complex multi-PO scenario. Test with a staging database before production use.
- This addon is a custom approximation of Enterprise-style workflow, not a claim of feature-for-feature parity with Enterprise.

## Installation
1. Back up the database and addons directory.
2. Extract this folder into a directory included in `addons_path`.
3. Restart Odoo, update the Apps list, and install **Purchase 3-Way Matching**.
4. Test with a disposable database and sample vendor/POs first.
