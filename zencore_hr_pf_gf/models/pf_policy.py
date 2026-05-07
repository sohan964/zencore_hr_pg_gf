from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PfPolicy(models.Model):
    _name = 'pf.policy'
    _description = 'Provident Fund Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(
        string='Policy Name',
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

    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
    )

    auto_enroll = fields.Boolean(
        string='Auto Enroll',
        default=False,
        help='Automatically create PF account for eligible employees.',
    )

    eligibility_after_months = fields.Integer(
        string='Eligibility After (Months)',
        default=0,
        required=True,
        help='Employee becomes eligible after specified months.',
    )

    employee_type_ids = fields.Many2many(
        'hr.employee.category',
        'pf_policy_employee_category_rel',
        'policy_id',
        'category_id',
        string='Eligible Employee Types',
    )

    employee_contribution_pct = fields.Float(
        string='Employee Contribution (%)',
        required=True,
        tracking=True,
    )

    employer_contribution_pct = fields.Float(
        string='Employer Contribution (%)',
        required=True,
        tracking=True,
    )

    salary_basis = fields.Selection(
        [
            ('basic', 'Basic Salary'),
            ('gross', 'Gross Salary'),
            ('custom', 'Custom Salary Rules'),
        ],
        string='Salary Basis',
        required=True,
        default='basic',
        tracking=True,
    )

    interest_method = fields.Selection(
        [
            ('manual', 'Manual'),
            ('yearly', 'Yearly'),
        ],
        string='Interest Method',
        required=True,
        default='yearly',
        tracking=True,
    )

    interest_rate = fields.Float(
        string='Default Interest Rate (%)',
        tracking=True,
    )

    vesting_enabled = fields.Boolean(
        string='Enable Vesting',
        default=False,
        tracking=True,
    )

    notes = fields.Text(
        string='Internal Notes',
    )

    vesting_ids = fields.One2many(
        'pf.policy.vesting',
        'policy_id',
        string='Vesting Rules',
    )

    _sql_constraints = [
        (
            'name_company_unique',
            'unique(name, company_id)',
            'Policy name must be unique per company.'
        ),
    ]

    @api.constrains(
        'employee_contribution_pct',
        'employer_contribution_pct',
        'interest_rate',
    )
    def _check_percentage_values(self):
        for rec in self:
            for value in [
                rec.employee_contribution_pct,
                rec.employer_contribution_pct,
                rec.interest_rate,
            ]:
                if value < 0 or value > 100:
                    raise ValidationError(
                        _('Percentage values must be between 0 and 100.')
                    )

    @api.constrains('eligibility_after_months')
    def _check_eligibility_after_months(self):
        for rec in self:
            if rec.eligibility_after_months < 0:
                raise ValidationError(
                    _('Eligibility months cannot be negative.')
                )