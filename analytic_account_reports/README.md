# Analytic Account Reports (PDF & XLSX)

Print and export **Analytic Account** reports in Odoo, as PDF or XLSX.

## Features

- Reporting wizard with filters:
  - Date From / Date To
  - Analytic Plans / Segments
  - One or more Analytic Accounts
  - Company
  - Posted Entries or All Entries
- Export as PDF (Qweb report) or XLSX (via `xlsxwriter`)
- Per-account "Print PDF Report" / "Export Excel Report" buttons directly on the
  Analytic Account form, showing a full statement including a Profit & Loss
  summary and linked Budget Items (if the Budget Management feature is
  installed)

## Installation

1. Copy this module into your Odoo `addons` path.
2. Update the Apps list and install **Analytic Account Reports (PDF & XLSX)**.
3. No external dependency is required beyond `xlsxwriter`, which ships with
   Odoo by default. If your server is missing it: `pip install xlsxwriter`.

## Usage

- **Accounting ▸ Reporting ▸ Analytic Account Report** opens the filter
  wizard.
- On any **Analytic Account** record, use the **Print PDF Report** /
  **Export Excel Report** buttons in the header for a complete statement of
  that account.

## Dependencies

- `base`
- `analytic`
- `account`

## License

LGPL-3

## Author

Elevantra Private Limited
