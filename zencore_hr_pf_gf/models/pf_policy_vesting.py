from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PfPolicyVesting(models.Model):
    _name = 'pf.policy.vesting'
    _description = 'PF Policy Vesting Rule'
    _order = 'service_year_from asc'

    policy_id = fields.Many2one(
        'pf.policy',
        string='PF Policy',
        required=True,
        ondelete='cascade',
    )

    service_year_from = fields.Float(
        string='Service Year From',
        required=True,
    )

    service_year_to = fields.Float(
        string='Service Year To',
        required=True,
    )

    employer_share_percent = fields.Float(
        string='Employer Share (%)',
        required=True,
        help='Employer contribution eligibility percentage.',
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    # _sql_constraints = [
    #     (
    #         'check_service_year_range',
    #         'CHECK(service_year_to >= service_year_from)',
    #         'Service Year To must be greater than or equal to Service Year From.'
    #     ),
    # ]

    @api.constrains(
        'service_year_from',
        'service_year_to',
        'employer_share_percent',
    )
    def _check_values(self):
        for rec in self:

            if rec.service_year_from < 0:
                raise ValidationError(
                    _('Service Year From cannot be negative.')
                )

            if rec.service_year_to < 0:
                raise ValidationError(
                    _('Service Year To cannot be negative.')
                )

            if (
                rec.employer_share_percent < 0
                or rec.employer_share_percent > 100
            ):
                raise ValidationError(
                    _('Employer Share Percentage must be between 0 and 100.')
                )

    @api.constrains(
        'service_year_from',
        'service_year_to',
        'policy_id',
        'active',
    )
    def _check_overlapping_ranges(self):
        for rec in self:
            domain = [
                ('id', '!=', rec.id),
                ('policy_id', '=', rec.policy_id.id),
                ('active', '=', True),
            ]

            vesting_rules = self.search(domain)

            for rule in vesting_rules:
                overlap = (
                    rec.service_year_from <= rule.service_year_to
                    and rec.service_year_to >= rule.service_year_from
                )

                if overlap:
                    raise ValidationError(
                        _(
                            'Vesting year ranges cannot overlap.\n'
                            'Conflict with range: %s - %s'
                        ) % (
                            rule.service_year_from,
                            rule.service_year_to,
                        )
                    )