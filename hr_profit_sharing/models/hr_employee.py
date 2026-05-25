from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    active_profit_sharing_id = fields.Many2one(
        'profit.sharing.rule',
        compute='_compute_profit_sharing_data',
    )

    profit_sharing_count = fields.Integer(
        compute='_compute_profit_sharing_data',
    )

    profit_sharing_percentage = fields.Float(
        related='active_profit_sharing_id.percentage',
        readonly=True,
    )

    profit_sharing_company_id = fields.Many2one(
        related='active_profit_sharing_id.company_id',
        readonly=True,
    )

    profit_sharing_input_type_id = fields.Many2one(
        related='active_profit_sharing_id.salary_attachment_type_id',
        readonly=True,
    )

    profit_sharing_active = fields.Boolean(
        related='active_profit_sharing_id.active',
        readonly=True,
    )

    @api.depends()
    def _compute_profit_sharing_data(self):

        for rec in self:

            rule = self.env['profit.sharing.rule'].search([
                ('employee_id', '=', rec.id),
                # ('active', '=', True),
            ], limit=1, order='create_date desc')

            rec.active_profit_sharing_id = rule

            rec.profit_sharing_count = self.env[
                'profit.sharing.rule'
            ].search_count([
                ('employee_id', '=', rec.id),
            ])

    def action_generate_profit_sharing(self):

        self.ensure_one()

        existing = self.env['profit.sharing.rule'].search([
            ('employee_id', '=', self.id),
            ('active', '=', True),
        ], limit=1)

        if existing:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Profit Sharing',
                'res_model': 'profit.sharing.rule',
                'res_id': existing.id,
                'view_mode': 'form',
                'target': 'current',
            }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Profit Sharing',
            'res_model': 'profit.sharing.rule',
            'view_mode': 'form',
            'target': 'current',

            'context': {
                'default_employee_id': self.id,
            }
        }

    def action_open_profit_sharing(self):

        self.ensure_one()

        if not self.active_profit_sharing_id:
            return

        return {
            'type': 'ir.actions.act_window',
            'name': 'Profit Sharing',
            'res_model': 'profit.sharing.rule',
            'res_id': self.active_profit_sharing_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_profit_sharing(self):

        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Profit Sharing History',
            'res_model': 'profit.sharing.rule',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'target': 'current',
        }