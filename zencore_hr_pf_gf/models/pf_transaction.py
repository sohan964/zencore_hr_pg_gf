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
            ('contribution', 'Contribution'),
            ('opening_balance', 'Opening Balance'),
            ('adjustment', 'Adjustment'),
            ('withdrawal', 'Withdrawal'),
            ('settlement', 'Settlement'),
            # ('reversal', 'Reversal'),
        ],
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
            # ('reversed', 'Reversed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        tracking=True,
    )

    remarks = fields.Text(
        string='Remarks',
    )

    #this is for the Badge
    payment_status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('paid', 'Paid'),
        ],
        compute='_compute_payment_status',
        store=True,
    )
    #it will show the status badge based on the journal entry
    @api.depends('move_id.state')
    def _compute_payment_status(self):

        for rec in self:

            if rec.move_id and rec.move_id.state == 'posted':
                rec.payment_status = 'paid'
            else:
                rec.payment_status = 'pending'

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



    #handle opening balance
    @api.model_create_multi
    def create(self, vals_list):

        records = super().create(vals_list)

        for rec in records:

            if rec.transaction_type == 'opening_balance':

                rec.pf_account_id.write({
                    'opening_balance_imported': True,
                    'opening_balance_date': fields.Date.today(),
                })

        return records
    
    #duplicate opening balance
    @api.constrains('pf_account_id', 'transaction_type')
    def _check_duplicate_opening_balance(self):

        for rec in self:

            if rec.transaction_type != 'opening_balance':
                continue

            domain = [
                ('id', '!=', rec.id),
                ('pf_account_id', '=', rec.pf_account_id.id),
                ('transaction_type', '=', 'opening_balance'),
            ]

            if self.search_count(domain):

                raise ValidationError(
                    _("Opening balance already submitted for this employee.")
            )
    #prevent duplicate monthly fees
    @api.constrains(
        'pf_account_id',
        'payroll_id',
        'transaction_type',
    )
    def _check_duplicate_payroll_contribution(self):

        for rec in self:

            if rec.transaction_type != 'contribution':
                continue

            domain = [
                ('id', '!=', rec.id),
                ('pf_account_id', '=', rec.pf_account_id.id),
                ('payroll_id', '=', rec.payroll_id.id),
                ('transaction_type', '=', 'contribution'),
            ]

            if self.search_count(domain):

                raise ValidationError(
                    _(
                        "PF contribution already exists "
                        "for this payroll."
                    )
                )