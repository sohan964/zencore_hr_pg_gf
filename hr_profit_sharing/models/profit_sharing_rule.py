from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProfitSharingRule(models.Model):
    _name = "profit.sharing.rule"
    _description = 'Employee Profit Sharing Rule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
        default=lambda self: self._default_employee(),
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        compute='_compute_company_id',
        store=True,
        readonly=False,
        tracking=True,
    )

    percentage = fields.Float(
        string='Profit Share Percentage',
        required=True,
        digits=(16, 2),
        tracking=True,
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
    )

    salary_attachment_type_id = fields.Many2one(
        'hr.payslip.input.type',
        string='Salary Adjustment Type',
    )

    @api.model
    def _default_employee(self):
        return self.env.context.get('default_employee_id')

    @api.depends('employee_id')
    def _compute_company_id(self):
        for rec in self:
            rec.company_id = rec.employee_id.company_id

    @api.constrains('employee_id', 'active')
    def _check_duplicate_active(self):

        for rec in self:

            existing = self.search([
                ('employee_id', '=', rec.employee_id.id),
                ('active', '=', True),
                ('id', '!=', rec.id),
            ])

            if existing:
                raise ValidationError(
                    'An active Profit Sharing already exists '
                    'for this employee!'
                )