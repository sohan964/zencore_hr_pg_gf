from odoo import models, fields


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):

        res = super().action_payslip_done()

        for slip in self:

            pf_account = self.env['pf.account'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('state', '=', 'active'),
            ], limit=1)

            if not pf_account:
                continue

            policy = pf_account.policy_id

            employee_amount = (
                slip.employee_id.wage
                * policy.employee_contribution_pct
            ) / 100

            employer_amount = (
                slip.employee_id.wage
                * policy.employer_contribution_pct
            ) / 100

            print("this is slip>>>>>>>>>>>>>>>>>>>>>",slip.move_id.id)
            current_date = fields.Date.today()
            pf_interest_rate = self.env['pf.interest.rate'].search([
                ('policy_id', '=', policy.id),
                ('active', '=', True),
                ('effective_from', '<=', current_date),
                ('effective_to', '>=', current_date),
            ], limit=1)

            interest_amount = 0
            if pf_interest_rate:
                 interest_amount = (
                     pf_account.total_balance * pf_interest_rate.rate
                 )/100
            else: 
                interest_amount = (
                    pf_account.total_balance * policy.interest_rate
                )/100

            after_balance = pf_account.total_balance + interest_amount + employee_amount + employer_amount

            self.env['pf.transaction'].create({
                'pf_account_id': pf_account.id,
                'transaction_date': slip.date_to,
                'transaction_type': 'contribution',
                'move_id':slip.move_id.id,
                'payroll_id': slip.id,
                'amount_employee': employee_amount,
                'amount_employer': employer_amount,
                'amount_interest': interest_amount,
                'balance_after': after_balance,
                'state': 'posted',
                'remarks': f'PF generated from payroll {slip.name}',
            })

        return res