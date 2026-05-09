from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PfInterestRate(models.Model):
    _name = 'pf.interest.rate'
    _description = 'PF Interest Rate'
    _order = 'year desc'

    policy_id = fields.Many2one(
        'pf.policy',
        string='PF Policy',
        required=True,
        ondelete='cascade',
    )

    year = fields.Integer(
        string='Year',
        required=True,
    )

    rate = fields.Float(
        string='Interest Rate (%)',
        required=True,
    )

    effective_from = fields.Date(
        string='Effective From',
        required=True,
    )

    effective_to = fields.Date(
        string='Effective To',
        required=True,
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    _sql_constraints = [
        (
            'policy_year_unique',
            'unique(policy_id, year)',
            'Interest rate already exists for this policy and year.'
        ),
    ]

    @api.constrains('rate')
    def _check_rate(self):
        for rec in self:
            if rec.rate < 0 or rec.rate > 100:
                raise ValidationError(
                    _('Interest rate must be between 0 and 100.')
                )

    @api.constrains(
        'effective_from',
        'effective_to',
    )
    def _check_effective_dates(self):
        for rec in self:
            if rec.effective_from > rec.effective_to:
                raise ValidationError(
                    _('Effective To date must be greater than Effective From date.')
                )

    @api.constrains('year')
    def _check_year(self):
        current_year = fields.Date.today().year

        for rec in self:
            if rec.year < 2000 or rec.year > current_year + 20:
                raise ValidationError(
                    _('Please enter a valid year.')
                )