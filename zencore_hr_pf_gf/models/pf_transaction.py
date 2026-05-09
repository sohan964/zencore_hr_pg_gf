from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PfTransaction(models.Model):
    _name = 'pf.transaction'
    _description = 'PF Transaction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'transaction_date desc, id desc'

    pf_account_id = fields.Many2one(
        'pf.account',
        string='PF Account',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    employee_id = fields.Many2one(
        related='pf_account_id.employee_id',
        store=True,
        string='Employee',
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

    transaction_date = fields.Date(
        string='Transaction Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    transaction_type = fields.Selection(
        [
            ('employee_contribution', 'Employee Contribution'),
            ('employer_contribution', 'Employer Contribution'),
            ('interest', 'Interest'),
            ('opening_balance', 'Opening Balance'),
            ('adjustment', 'Adjustment'),
            ('withdrawal', 'Withdrawal'),
            ('settlement', 'Settlement'),
            ('reversal', 'Reversal'),
        ],
        string='Transaction Type',
        required=True,
        tracking=True,
    )

    payroll_id = fields.Many2one(
        'hr.payslip',
        string='Payroll',
        tracking=True,
    )

    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        copy=False,
        tracking=True,
    )

    amount_employee = fields.Monetary(
        string='Employee Amount',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )

    amount_employer = fields.Monetary(
        string='Employer Amount',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )

    amount_interest = fields.Monetary(
        string='Interest Amount',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )

    total_amount = fields.Monetary(
        string='Total Amount',
        currency_field='currency_id',
        compute='_compute_total_amount',
        store=True,
        tracking=True,
    )

    balance_after = fields.Monetary(
        string='Balance After',
        currency_field='currency_id',
        tracking=True,
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('reversed', 'Reversed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        tracking=True,
    )

    remarks = fields.Text(
        string='Remarks',
    )

    @api.depends(
        'amount_employee',
        'amount_employer',
        'amount_interest',
    )
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = (
                rec.amount_employee
                + rec.amount_employer
                + rec.amount_interest
            )

    @api.constrains(
        'amount_employee',
        'amount_employer',
        'amount_interest',
    )
    def _check_amounts(self):
        for rec in self:

            if rec.amount_employee < 0:
                raise ValidationError(
                    _('Employee amount cannot be negative.')
                )

            if rec.amount_employer < 0:
                raise ValidationError(
                    _('Employer amount cannot be negative.')
                )

            if rec.amount_interest < 0:
                raise ValidationError(
                    _('Interest amount cannot be negative.')
                )

    @api.constrains('payroll_id', 'transaction_type')
    def _check_payroll_required(self):
        for rec in self:

            payroll_required_types = [
                'employee_contribution',
                'employer_contribution',
            ]

            if (
                rec.transaction_type in payroll_required_types
                and not rec.payroll_id
            ):
                raise ValidationError(
                    _('Payroll is required for contribution transactions.')
                )

    def action_post(self):
        for rec in self:

            if rec.state != 'draft':
                continue

            rec.state = 'posted'

    def action_reverse(self):
        for rec in self:

            if rec.state != 'posted':
                continue

            self.create({
                'pf_account_id': rec.pf_account_id.id,
                'transaction_date': fields.Date.today(),
                'transaction_type': 'reversal',
                'amount_employee': rec.amount_employee,
                'amount_employer': rec.amount_employer,
                'amount_interest': rec.amount_interest,
                'remarks': _('Reversal of transaction %s') % rec.id,
                'state': 'posted',
            })

            rec.state = 'reversed'