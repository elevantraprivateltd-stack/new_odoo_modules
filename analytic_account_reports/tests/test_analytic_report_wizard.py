# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAnalyticReportWizard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Test Plan',
        })
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Test Analytic Account',
            'plan_id': cls.analytic_plan.id,
            'company_id': cls.env.company.id,
        })
        cls.general_account = cls.env['account.account'].search(
            [('company_ids', 'in', cls.env.company.id)], limit=1
        )
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})

        cls.env['account.analytic.line'].create({
            'name': 'Test analytic line',
            'account_id': cls.analytic_account.id,
            'date': '2026-01-15',
            'amount': 500.0,
            'unit_amount': 1.0,
            'partner_id': cls.partner.id,
            'company_id': cls.env.company.id,
        })

    def test_wizard_defaults(self):
        wizard = self.env['analytic.report.wizard'].create({})
        self.assertTrue(wizard.date_from)
        self.assertTrue(wizard.date_to)
        self.assertEqual(wizard.company_id, self.env.company)

    def test_get_report_data_returns_grouped_lines(self):
        wizard = self.env['analytic.report.wizard'].create({
            'date_from': '2026-01-01',
            'date_to': '2026-12-31',
            'target_move': 'all',
            'analytic_account_ids': [(6, 0, self.analytic_account.ids)],
        })
        data = wizard._get_report_data()
        self.assertTrue(data, 'Expected at least one grouped result')
        self.assertEqual(data[0]['account'], self.analytic_account)
        self.assertEqual(len(data[0]['lines']), 1)
        self.assertAlmostEqual(data[0]['total_amount'], 500.0)

    def test_no_data_raises_user_error(self):
        wizard = self.env['analytic.report.wizard'].create({
            'date_from': '2000-01-01',
            'date_to': '2000-01-02',
            'target_move': 'all',
        })
        with self.assertRaises(UserError):
            wizard.action_print_pdf()
        with self.assertRaises(UserError):
            wizard.action_export_xlsx()

    def test_export_xlsx_creates_attachment(self):
        wizard = self.env['analytic.report.wizard'].create({
            'date_from': '2026-01-01',
            'date_to': '2026-12-31',
            'target_move': 'all',
            'analytic_account_ids': [(6, 0, self.analytic_account.ids)],
        })
        action = wizard.action_export_xlsx()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'analytic.report.wizard'),
            ('res_id', '=', wizard.id),
        ])
        self.assertTrue(attachment, 'Expected an XLSX attachment to be created')

    def test_direct_account_report_data(self):
        data = self.analytic_account._get_analytic_report_data()
        self.assertEqual(data['count'], 1)
        self.assertAlmostEqual(data['total_amount'], 500.0)
        self.assertIn('pl_summary', data)
        self.assertIn('budget_items', data)
