from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    report_header_icon = fields.Binary(string="Report Header Icon", attachment=True)

    engagement_letter_html = fields.Html(
        string='Engagement Letter Content',
        translate=True,
        default="""
                <p><strong>To,</strong></p>
                <p>The Management,</p>
                <br/>
                <p>We are pleased to confirm our acceptance of this engagement...</p>
            """
    )

    # Header button click hone par report trigger karne ka function
    def action_print_engagement_letter(self):
        return self.env.ref('sales_order_template_manager.action_report_engagement_letter').report_action(self)

    is_proposal_report = fields.Boolean(
        string="Include Proposal Template?",
        default=False
    )

    def action_load_proposal_terms(self):
        """Toggle action: Styled HTML text load karega ya clear karega"""
        terms_text = """
<div style="font-family: Arial, sans-serif; color: #4A4A4A; line-height: 1.6;">

    <h3 style="color: #7C93A8; font-size: 21px; margin-top: 15px; margin-bottom: 8px;">Introduction of Firm</h3>
    <p style="margin-bottom: 12px;">Adeel Khan &amp; Co. is a firm of Chartered Management Accountants providing accountancy, taxation, 
    regulatory compliance, audit support, and business advisory services. Our firm focuses
     on accuracy, confidentiality, and timely compliance while helping clients minimize risk and maintaining proper
      financial discipline.</p> 
      <br/>
    <p>We serve individuals, SMEs, corporate entities, and non-profit organizations with a commitment to professional ethics and
long-term client relationships.</p>

    <h3 style="color: #7C93A8; font-size: 21px; margin-top: 15px; margin-bottom: 8px;">Scope of Work for this engagement</h3>
    <ul style="margin-top: 5px; margin-bottom: 15px; padding-left: 20px;">
        <li>Collection and review of financial data</li>
        <br/>
        <li>Working out opening trial balance of 2024</li>
        <br/>
        <li>Updating fixed assets schedule in coordination with hospital staff and calculation of depreciation</li>
        <br/>
        <li>Extending help in updating Ledgers to arrive at final balances of all accounts</li>
        <br/>
        <li>Updating closing trial balances of 2024, 2025 and 2026</li>
        <br/>
        <li>Preparation of financial statements of hospital for 3 financial years</li>
    </ul>
    <br/>

    <h3 style="color: #7C93A8; font-size: 21px; margin-top: 15px; margin-bottom: 8px;">Data Requirements</h3>
    <p><b>To perform the above services, the following documents/information may be required:</b></p>
    <ul style="margin-top: 5px; margin-bottom: 15px; padding-left: 20px;">
        <li>Financial data ledgers</li>
        <br/>
        <li>Revenue ledgers of all revenue centres including OPD, OT, Pharmacy, Canteen, Labs, Admission Wards, Emergency, etc. plus Govt. Grants year wise</li>
        <br/>
        <li>Costs associated with all revenue centres detailed above</li>
        <br/>
        <li>Administrative expenses ledgers including payroll, maintenance, utilities, etc. year wise</li>
        <br/>
        <li>Stock details/ movements opening, purchases and selling detail yearwise</li>
        <br/>
        <li>Fixed Assets register including purchases and selling detail yearwise</li>
        <br/>
        <li>Accounts receivable &amp; Payables if any on closing dates year wise</li>
        <br/>
        <li>Cash Book updated for the relevant period</li>
        <br/>
        <li>Bank Statements for the relevant period</li>
        <br/>
        <li>Details of any securities, advances, prepayments etc. year wise</li>
        <br/>
        <li>Prepaid insurances etc. if any</li>
        <br/>
        <li>Detail of financial leases if any along with lease schedules</li>
        <br/>
        <li>Financial / operational policies, regulations, SOPs etc.</li>
        <br/>
        <li>Minutes of meetings, agreements with vendors etc.</li>
        <br/>
        <li>Detail of any litigations etc. requiring disclosures, etc.</li>
        <br/>
        <li>Detail of Taxes withheld, deposited, outstandings etc. if any</li>
        <br/>
        <li>Detail of Staff loans and advances etc. with or without interest, etc.</li>
        <br/>
        <li>Any other data required</li>
    </ul>
     <h3 style="color: #7C93A8; font-size: 21px; margin-top: 15px; margin-bottom: 8px;">Professional Fee</h3>
        <p><b>Payment Terms:</b>50% advance, before deputing staff</p>

    <h3 style="color: #7C93A8; font-size: 21px; margin-top: 15px; margin-bottom: 8px;">Timeline</h3>
    <p style="margin-bottom: 12px;">Service completion within <b>20 working days</b> subject to provision of data &amp; information as &amp; when required.</p>

    <h3 style="color: #7C93A8; font-size: 21px; margin-top: 15px; margin-bottom: 8px;">Client Responsibilities</h3>
    <p>The client shall:</p>
    <ul style="margin-top: 5px; margin-bottom: 15px; padding-left: 20px;">

        <li>Provide <b>accurate financial records</b></li>
         <br/>
        <li>Provide required documents <b>on time</b></li>
         <br/>
        <li><b>Disclose all</b> relevant transactions</li>
         <br/>
        <li><b>Respond promptly</b> to queries</li>
    </ul>

    <h3 style="color: #7C93A8; font-size: 21px; margin-top: 15px; margin-bottom: 8px;">Terms &amp; Conditions</h3>
   
    <ol style="margin-top: 5px; margin-bottom: 15px; padding-left: 20px;">
        <li><b>Scope of Work:</b> This quotation is based strictly on the scope of services mentioned herein.</li>
         <br/>
        <li><b>Validity:</b> This quotation is valid for <b>7 days</b> from the date of issuance.</li>
         <br/>
        <li><b>Payment Terms:</b> <b>50% payment in advance</b> is required. Work will commence only after receipt of
            advance payment. Fees are exclusive of government levies, taxes, duties.</li>
         <br/>
        <li><b>Boarding &amp; Lodging:</b> expenses of two staff members will be borne by the hopital over and above
        to quoted fee, including living and food expenses for the whole period until completion and delivery of assignment.</li>
         <br/>
        <li><b>TimeLine:</b> Delivery of Service timelines will start after receipt of advance payment and complete required data from
        the client step wise. Delays due to incomplete or late data shall not be the responsibility of <b> Adeel Khan & Co.</b> Timeline
        may vary due to regulatory or system delays beyond our control.</li>
         <br/>
        <li><b>Client Responsibilities:</b>The client shall provide accurate and complete information, data, and approvals. The firm shall
        not be liable for errors arising from incorrect or incomplete information provided by the client.</li>
         <br/>
        <li><b>Conﬁdentiality & Liability:</b> All client information will be kept conﬁdential. The consultant shall not be liable for any
indirect or consequential losses, including loss of business or profit.</li>
 <br/>

        <li><b>Acceptance & Governing Law:</b> Acceptance of this quotation (signature, stamp, or payment) shall constitute
acceptance of these terms. Disputes, if any, shall be resolved amicably through mutual discussion.</li>

    </ol>

</div>
"""
        for record in self:
            if record.note and "Introduction of Firm" in record.note:
                record.note = False
                record.is_proposal_report = False
            else:
                record.note = terms_text
                record.is_proposal_report = True
        return True
