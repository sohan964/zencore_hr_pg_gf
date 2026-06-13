from odoo import models
from odoo.tools import SQL
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)

class AccountPartnerLedgerReportHandler(models.AbstractModel):
    _inherit = "account.partner.ledger.report.handler"

    def _get_additional_column_aml_values(self):
        additional_columns = super()._get_additional_column_aml_values()

        return SQL(
            """
            %s

            CASE
                WHEN account_move.move_type = 'out_invoice'
                THEN account_move.amount_untaxed
                ELSE NULL
            END AS untaxed_amount,

            CASE
                WHEN account_move.move_type = 'out_invoice'
                THEN account_move.amount_tax
                ELSE NULL
            END AS tax_amount,
            """,
            additional_columns,
        )
    
    def _build_partner_lines(self, report, options, level_shift=0):
        lines = []

        totals_by_column_group = {
            column_group_key: {
                total: 0.0
                for total in [
                    'debit',
                    'credit',
                    'amount',
                    'balance',
                    'untaxed_amount',
                    'tax_amount',
                ]
            }
            for column_group_key in options['column_groups']
        }

        partners_results = self._query_partners(report, options)

        for partner, results in partners_results:
            partner_values = defaultdict(dict)

            for column_group_key in options['column_groups']:
                partner_sum = results.get(column_group_key, {})

                partner_values[column_group_key]['debit'] = partner_sum.get('debit', 0.0)
                partner_values[column_group_key]['credit'] = partner_sum.get('credit', 0.0)
                partner_values[column_group_key]['amount'] = partner_sum.get('amount', 0.0)
                partner_values[column_group_key]['balance'] = partner_sum.get('balance', 0.0)

                partner_values[column_group_key]['untaxed_amount'] = partner_sum.get('untaxed_amount', 0.0)
                partner_values[column_group_key]['tax_amount'] = partner_sum.get('tax_amount', 0.0)

                totals_by_column_group[column_group_key]['debit'] += partner_values[column_group_key]['debit']
                totals_by_column_group[column_group_key]['credit'] += partner_values[column_group_key]['credit']
                totals_by_column_group[column_group_key]['amount'] += partner_values[column_group_key]['amount']
                totals_by_column_group[column_group_key]['balance'] += partner_values[column_group_key]['balance']

                totals_by_column_group[column_group_key]['untaxed_amount'] += partner_values[column_group_key]['untaxed_amount']
                totals_by_column_group[column_group_key]['tax_amount'] += partner_values[column_group_key]['tax_amount']

            lines.append(
                self._get_report_line_partners(
                    options,
                    partner,
                    partner_values,
                    level_shift=level_shift,
                )
            )

        return lines, totals_by_column_group
    

    def _get_query_sums(self, report, options):
        _logger.warning("ZENCORE CUSTOM _get_query_sums CALLED")
        queries = []

        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(column_group_options, 'from_beginning')
            date_from = options['date']['date_from']

            queries.append(SQL(
                """
                (
                    WITH partner_sums AS (
                        SELECT
                            account_move_line.partner_id AS groupby,
                            %(column_group_key)s AS column_group_key,

                            SUM(
                                CASE
                                    WHEN account_move_line.date >= %(date_from)s
                                    THEN %(debit_select)s
                                    ELSE 0
                                END
                            ) AS debit,

                            SUM(
                                CASE
                                    WHEN account_move_line.date >= %(date_from)s
                                    THEN %(credit_select)s
                                    ELSE 0
                                END
                            ) AS credit,

                            SUM(%(balance_select)s) AS amount,
                            SUM(%(balance_select)s) AS balance,

                            SUM(
                                CASE
                                    WHEN account_move.move_type = 'out_invoice'
                                    THEN account_move.amount_untaxed
                                    ELSE 0
                                END
                            ) AS untaxed_amount,

                            SUM(
                                CASE
                                    WHEN account_move.move_type = 'out_invoice'
                                    THEN account_move.amount_tax
                                    ELSE 0
                                END
                            ) AS tax_amount,

                            MAX(account_move_line.date) AS latest_date

                        FROM %(table_references)s

                        JOIN account_move
                            ON account_move.id = account_move_line.move_id

                        %(currency_table_join)s

                        WHERE %(search_condition)s

                        GROUP BY account_move_line.partner_id
                    )

                    SELECT *
                    FROM partner_sums

                    WHERE partner_sums.balance != 0
                    OR partner_sums.latest_date >= %(date_from)s
                )
                """,

                column_group_key=column_group_key,
                date_from=date_from,

                debit_select=report._currency_table_apply_rate(
                    SQL("account_move_line.debit")
                ),

                credit_select=report._currency_table_apply_rate(
                    SQL("account_move_line.credit")
                ),

                balance_select=report._currency_table_apply_rate(
                    SQL("account_move_line.balance")
                ),

                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(column_group_options),
                search_condition=query.where_clause,
            ))

        return SQL(" UNION ALL ").join(queries)
    
    def _query_partners(self, report, options):

        def assign_sum(row):
            fields_to_assign = [
                'balance',
                'debit',
                'credit',
                'amount',
                'untaxed_amount',
                'tax_amount',
            ]

            groupby_partners.setdefault(
                row['groupby'],
                defaultdict(lambda: defaultdict(float))
            )

            for field in fields_to_assign:
                groupby_partners[row['groupby']][row['column_group_key']][field] += row.get(field, 0.0)

        query = self._get_query_sums(report, options)

        groupby_partners = {}

        self.env.cr.execute(query)

        for row in self.env.cr.dictfetchall():
            assign_sum(row)

        if groupby_partners:
            partners = self.env['res.partner'].with_context(
                active_test=False
            ).search([
                ('id', 'in', list(groupby_partners.keys()))
            ])
        else:
            partners = []

        return [
            (
                partner,
                groupby_partners[partner.id]
            )
            for partner in partners
        ]
