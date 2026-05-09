from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PfSettlement(models.Model):
    _name = 'pf.settlement'
    _description = 'PF Settlement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'settlement_date desc, id desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
    )

    pf_account_id = fields.Many2one(
        'pf.account',
        string='PF Account',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    company_id = fields.Many2one(
        related='pf_account_id.company_id',
        store=True,
        string='Company',
    )

    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True,
    )

    separation_date = fields.Date(
        string='Separation Date',
        required=True,
        tracking=True,
    )

    settlement_date = fields.Date(
        string='Settlement Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    employee_share = fields.Monetary(
        string='Employee Share',
        currency_field='currency_id',
        readonly=True,
        tracking=True,
    )

    employer_share = fields.Monetary(
        string='Employer Share',
        currency_field='currency_id',
        readonly=True,
        tracking=True,
    )

    vested_share = fields.Monetary(
        string='Vested Share',
        currency_field='currency_id',
        readonly=True,
        tracking=True,
    )

    interest_amount = fields.Monetary(
        string='Interest Amount',
        currency_field='currency_id',
        readonly=True,
        tracking=True,
    )

    payable_amount = fields.Monetary(
        string='Payable Amount',
        currency_field='currency_id',
        compute='_compute_payable_amount',
        store=True,
        tracking=True,
    )

    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        copy=False,
        tracking=True,
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('calculated', 'Calculated'),
            ('approved', 'Approved'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        tracking=True,
    )

    @api.depends(
        'employee_share',
        'vested_share',
        'interest_amount',
    )
    def _compute_payable_amount(self):
        for rec in self:
            rec.payable_amount = (
                rec.employee_share
                + rec.vested_share
                + rec.interest_amount
            )

    @api.constrains(
        'separation_date',
        'settlement_date',
    )
    def _check_dates(self):
        for rec in self:

            if rec.separation_date > rec.settlement_date:
                raise ValidationError(
                    _(
                        'Settlement Date must be greater than '
                        'or equal to Separation Date.'
                    )
                )

    @api.constrains('employee_id', 'pf_account_id')
    def _check_employee_pf_account(self):
        for rec in self:

            if rec.pf_account_id.employee_id != rec.employee_id:
                raise ValidationError(
                    _('Selected PF Account does not belong to the employee.')
                )

    def action_calculate(self):
        for rec in self:

            account = rec.pf_account_id

            rec.employee_share = account.total_employee_share
            rec.employer_share = account.total_employer_share
            rec.interest_amount = account.total_interest

            vested_percent = 0.0

            if account.policy_id.vesting_enabled:

                joining_date = rec.employee_id.first_contract_date

                if joining_date and rec.separation_date:

                    service_days = (
                        rec.separation_date - joining_date
                    ).days

                    service_years = service_days / 365

                    vesting_rule = self.env[
                        'pf.policy.vesting'
                    ].search([
                        ('policy_id', '=', account.policy_id.id),
                        ('service_year_from', '<=', service_years),
                        ('service_year_to', '>=', service_years),
                        ('active', '=', True),
                    ], limit=1)

                    if vesting_rule:
                        vested_percent = (
                            vesting_rule.employer_share_percent
                        )

            else:
                vested_percent = 100.0

            rec.vested_share = (
                rec.employer_share * vested_percent
            ) / 100

            rec.state = 'calculated'

    def action_approve(self):
        for rec in self:

            if rec.state != 'calculated':
                continue

            rec.state = 'approved'

    def action_mark_paid(self):
        for rec in self:

            if rec.state != 'approved':
                continue

            rec.state = 'paid'

            rec.pf_account_id.state = 'closed'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'