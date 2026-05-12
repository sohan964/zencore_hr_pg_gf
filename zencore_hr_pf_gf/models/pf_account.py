from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date

class PfAccount(models.Model):
    _name = 'pf.account'
    _description = 'Provident Fund Account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'account_number'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
    )

    policy_id = fields.Many2one(
        'pf.policy',
        string='PF Policy',
        required=True,
        tracking=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
    )

    enrollment_date = fields.Date(
        string='Enrollment Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    eligible_date = fields.Date(
        string='Eligible Date',
        # compute='_compute_eligible_date',
        store=True,
        tracking=True,
    )

    account_number = fields.Char(
        string='Account Number',
        required=True,
        copy=False,
        tracking=True,
    )

    opening_balance_imported = fields.Boolean(
        string='Opening Balance Imported',
        default=False,
        tracking=True,
    )

    opening_balance_date = fields.Date(
        string='Opening Balance Date',
        tracking=True,
    )

    transaction_ids = fields.One2many(
        'pf.transaction',
        'pf_account_id',
        string='Transactions',
    )

    settlement_ids = fields.One2many(
        'pf.settlement',
        'pf_account_id',
        string='Settlements',
    )

    total_employee_share = fields.Monetary(
        string='Employee Share',
        currency_field='currency_id',
        compute='_compute_balances',
        store=True,
    )

    total_employer_share = fields.Monetary(
        string='Employer Share',
        currency_field='currency_id',
        compute='_compute_balances',
        store=True,
    )

    total_interest = fields.Monetary(
        string='Interest Amount',
        currency_field='currency_id',
        compute='_compute_balances',
        store=True,
    )

    total_balance = fields.Monetary(
        string='Total Balance',
        currency_field='currency_id',
        compute='_compute_balances',
        store=True,
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('waiting_eligibility', 'Waiting Eligibility'),
            ('active', 'Active'),
            ('suspended', 'Suspended'),
            ('settled', 'Settled'),
            ('closed', 'Closed'),
        ],
        string='Status',
        default='draft',
        tracking=True,
    )

    is_eligible = fields.Boolean(
        compute='_compute_is_eligible',
    )

    is_waiting_eligibility = fields.Boolean(
        compute='_compute_is_eligible',
    )

    def action_waiting_eligibility(self):
        for rec in self:
            rec.state = 'waiting_eligibility'


    def action_activate(self):
        for rec in self:
            rec.state = 'active'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    @api.depends('eligible_date')
    def _compute_is_eligible(self):

        today = fields.Date.today()

        for rec in self:

            rec.is_eligible = False
            rec.is_waiting_eligibility = False

            if rec.eligible_date:

                if rec.eligible_date <= today:
                    rec.is_eligible = True
                else:
                    rec.is_waiting_eligibility = True

    @api.onchange('employee_id', 'policy_id')
    def _onchange_eligible_date(self):

        self.eligible_date = False

        if (
            self.employee_id.contract_date_start
            and self.policy_id
        ):

            self.eligible_date = (
                self.employee_id.contract_date_start
                + relativedelta(
                    months=self.policy_id.eligibility_after_months
                )
            )

    _sql_constraints = [
        (
            'employee_policy_unique',
            'unique(employee_id, policy_id)',
            'Employee already has a PF account for this policy.'
        ),
    ]

    @api.depends(
        'transaction_ids.amount_employee',
        'transaction_ids.amount_employer',
        'transaction_ids.amount_interest',
        'transaction_ids.state',
    )
    def _compute_balances(self):
        for rec in self:

            transactions = rec.transaction_ids.filtered(
                lambda t: t.state == 'posted'
            )

            rec.total_employee_share = sum(
                transactions.mapped('amount_employee')
            )

            rec.total_employer_share = sum(
                transactions.mapped('amount_employer')
            )

            rec.total_interest = sum(
                transactions.mapped('amount_interest')
            )

            rec.total_balance = (
                rec.total_employee_share
                + rec.total_employer_share
                + rec.total_interest
            )

    @api.constrains('opening_balance_date')
    def _check_opening_balance_date(self):
        for rec in self:
            if (
                rec.opening_balance_imported
                and not rec.opening_balance_date
            ):
                raise ValidationError(
                    _('Opening Balance Date is required.')
                )


    #opening balance imported
    # @api.

    # @api.model_create_multi
    # def create(self, vals_list):

    #     for vals in vals_list:

    #         if vals.get('account_number', _('New')) == _('New'):
    #             vals['account_number'] = self.env[
    #                 'ir.sequence'
    #             ].next_by_code('pf.account') or _('New')

    #     return super().create(vals_list)