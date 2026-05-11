from odoo import models


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

            self.env['pf.transaction'].create({
                'pf_account_id': pf_account.id,
                'transaction_date': slip.date_to,
                'transaction_type': 'contribution',
                'move_id':slip.move_id.id,
                'payroll_id': slip.id,
                'amount_employee': employee_amount,
                'amount_employer': employer_amount,
                'state': 'posted',
                'remarks': f'PF generated from payroll {slip.name}',
            })

        return res