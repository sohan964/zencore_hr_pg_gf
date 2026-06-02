this code need to add when salary rules create inside the 
PF rules amount type will be Python Code.
then need to paste this code over their

result = 0.0
pf_account = payslip.env['pf.account'].search([
    ('employee_id', '=', employee.id),
    ('state', '=', 'active'),
], limit=1)

if pf_account:

    result = -(
        employee.wage
        * pf_account.policy_id.employee_contribution_pct
    ) / 100