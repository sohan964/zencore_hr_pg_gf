from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'


    pf_payable_account_id = fields.Many2one(
        'account.account',
        string='PF Payable Account',
    )

    pf_bank_account_id = fields.Many2one(
        'account.account',
        string='PF Bank Account',
    )