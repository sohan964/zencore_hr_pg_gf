from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PfSettlement(models.Model):
    _name = 'pf.settlement'
    _description = 'PF Settlement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'settlement_date desc, id desc'



    pf_account_id = fields.Many2one(
        'pf.account',
        string='PF Account',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
    )
    @api.onchange('pf_account_id')
    def _onchange_pf_account_id(self):

        for rec in self:

            rec.employee_id = rec.pf_account_id.employee_id

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

    include_interest = fields.Boolean(
        string='Include Interest',
        default=True,
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
        'employee_share',
        'vested_share',
        'interest_amount',
        'include_interest',
    )
    def _compute_payable_amount(self):

        for rec in self:

            payable = (
                rec.employee_share
                + rec.vested_share
            )

            if rec.include_interest:
                payable += rec.interest_amount

            rec.payable_amount = payable

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
    
    @api.constrains('pf_account_id', 'state')
    def _check_duplicate_settlement(self):

        for rec in self:

            if rec.state == 'cancelled':
                continue

            domain = [
                ('id', '!=', rec.id),
                ('pf_account_id', '=', rec.pf_account_id.id),
                ('state', '!=', 'cancelled'),
            ]

            if self.search_count(domain):

                raise ValidationError(
                    _('This PF account is already in settlement.')
                )

    def action_calculate(self):
        for rec in self:

            account = rec.pf_account_id

            rec.employee_share = account.total_employee_share
            rec.employer_share = account.total_employer_share
            rec.interest_amount = account.total_interest

            vested_percent = 0.0

            if account.policy_id.vesting_enabled:

                joining_date = rec.employee_id.contract_date_start

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
                vested_percent = account.policy_id.vesting_rate

            rec.vested_share = (
                rec.employer_share * vested_percent
            ) / 100

            rec.state = 'calculated'

    def action_approve(self):

        for rec in self:

            if rec.state != 'calculated':
                continue

            journal = rec.pf_account_id.policy_id.pf_journal_id

            if not journal:
                raise ValidationError(
                    _('Please configure PF Journal in PF Policy.')
                )

            liability_account = (
                rec.pf_account_id.policy_id.pf_liability_account_id
            )

            bank_account = (
                rec.pf_account_id.policy_id.pf_bank_account_id
            )

            if not liability_account:
                raise ValidationError(
                    _('Please configure PF Liability Account.')
                )

            if not bank_account:
                raise ValidationError(
                    _('Please configure PF Bank Account.')
                )

            move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': journal.id,
                'date': fields.Date.today(),
                'ref': f'PF Settlement - {rec.employee_id.name}',
                'line_ids': [

                    (0, 0, {
                        'name': 'PF Settlement Liability',
                        'account_id': liability_account.id,
                        'debit': rec.payable_amount,
                    }),

                    (0, 0, {
                        'name': 'PF Settlement Bank Payment',
                        'account_id': bank_account.id,
                        'credit': rec.payable_amount,
                    }),
                ]
            })

            rec.move_id = move.id
            rec.pf_account_id.state = 'settled'
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