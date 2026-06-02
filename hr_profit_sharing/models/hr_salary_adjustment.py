from odoo import api, fields, models


class HrSalaryAdjustment(models.Model):
    _inherit = 'hr.salary.attachment'

    def _get_company_net_profit(self):
        print("attachment >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> debug")

        company = self.company_id

        # ------------------------------------------------
        # GET P&L REPORT
        # ------------------------------------------------

        report = self.env['account.report'].search([
            ('name', '=', 'Profit and Loss')
        ], limit=1)

        print("this is report>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>debug point", report)
        if not report:
            return 0.0

        # ------------------------------------------------
        # REPORT OPTIONS
        # ------------------------------------------------

        options = report.get_options({})

        # ------------------------------------------------
        # GET REPORT LINES
        # ------------------------------------------------

        lines = report._get_lines(options)

        # ------------------------------------------------
        # FIND NET PROFIT
        # ------------------------------------------------

        net_profit = 0.0

        for line in lines:

            name = line.get('name')

            if name and 'Net Profit' in name:

                columns = line.get('columns', [])

                if columns:
                    net_profit = columns[0].get('no_format', 0.0)

                break

        return net_profit

    @api.onchange('other_input_type_id')
    def _onchange_profit_sharing(self):

        # print("onChange >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> debug")
        for rec in self:
            print("EMPLOYEE", rec.employee_ids)
            if not rec.employee_ids:
                return

            # ------------------------------------------------
            # GET ACTIVE PROFIT RULE
            # ------------------------------------------------
            # print("EMPLOYEE IDS ID:", rec.employee_ids.ids)
            profit_rule = self.env[
                'profit.sharing.rule'
            ].search([
                ('employee_id', '=', rec.employee_ids.ids),
                ('active', '=', True),
            ], limit=1)
            # print("PROFIT RULE", profit_rule)
            if not profit_rule:
                return
            
            # print("TYPE SELECTED", rec.other_input_type_id)
            # print("RULE TYPE", profit_rule.salary_attachment_type_id)
            
            # ------------------------------------------------
            # TYPE MATCH
            # ------------------------------------------------

            if (
                rec.other_input_type_id
                != profit_rule.salary_attachment_type_id
            ):
                return

            # print("CALLING NET PROFIT")
            # ------------------------------------------------
            # GET NET PROFIT
            # ------------------------------------------------

            net_profit = rec._get_company_net_profit()

            print("NET PROFIT", net_profit)


            # ------------------------------------------------
            # CALCULATE PROFIT SHARE
            # ------------------------------------------------

            amount = (
                net_profit
                * profit_rule.percentage
            ) / 100

            # ------------------------------------------------
            # SET AMOUNT
            # ------------------------------------------------

            rec.monthly_amount = amount