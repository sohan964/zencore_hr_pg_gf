from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import date


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
        required = True
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
    
    @api.model_create_multi
    def create(self, vals_list):

        records = super().create(vals_list)

        for rec in records:
            rec._create_profit_sharing_adjustment()

        return records
    
    def _create_profit_sharing_adjustment(self):

        self.ensure_one()

        # ----------------------------------
        # Already Exists?
        # ----------------------------------

        existing = self.env['hr.salary.attachment'].search([
            ('other_input_type_id', '=', self.salary_attachment_type_id.id),
            ('employee_ids', 'in', self.employee_id.id),
        ], limit=1)

        if existing:
            return

        # ----------------------------------
        # First day of current month
        # ----------------------------------

        today = fields.Date.today()

        first_day = today.replace(day=1)

        # ----------------------------------
        # Calculate profit share
        # ----------------------------------

        net_profit = self._get_company_net_profit()

        amount = (
            net_profit *
            self.percentage
        ) / 100

        # ----------------------------------
        # Create Salary Adjustment
        # ----------------------------------

        self.env['hr.salary.attachment'].create({

            'employee_ids': [
                (6, 0, [self.employee_id.id])
            ],

            'company_id': self.company_id.id,

            'other_input_type_id':
                self.salary_attachment_type_id.id,

            'monthly_amount': amount,

            'is_refund': True,

            'duration_type': 'unlimited',

            'date_start': first_day,

            'description':
                f'Profit Sharing {self.percentage}%',

        })
    def _get_company_net_profit(self):

        report = self.env['account.report'].search([
            ('name', '=', 'Profit and Loss')
        ], limit=1)

        if not report:
            return 0.0

        options = report.get_options({})

        lines = report._get_lines(options)

        net_profit = 0.0

        for line in lines:

            if line.get('name') == 'Net Profit':

                columns = line.get('columns', [])

                if columns:
                    net_profit = columns[0].get(
                        'no_format',
                        0.0
                    )

                break

        return net_profit