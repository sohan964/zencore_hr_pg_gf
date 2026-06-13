from odoo import models
from odoo.tools import SQL
from collections import defaultdict


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
        """ Executes the queries and performs all the computation.
        :return:        A list of tuple (partner, column_group_values) sorted by the table's model _order:
                        - partner is a res.parter record.
                        - column_group_values is a dict(column_group_key, fetched_values), where
                            - column_group_key is a string identifying a column group, like in options['column_groups']
                            - fetched_values is a dictionary containing:
                                - sum:                              {'debit': float, 'credit': float, 'balance': float}
                                - (optional) initial_balance:       {'debit': float, 'credit': float, 'balance': float}
                                - (optional) lines:                 [line_vals_1, line_vals_2, ...]
        """
        def assign_sum(row):
            fields_to_assign = [
                'balance',
                'debit',
                'credit',
                'amount',
                'untaxed_amount',
                'tax_amount',
            ]
            if any(
                not company_currency.is_zero(row.get(field, 0.0) or 0.0)
                for field in fields_to_assign
            ):
                groupby_partners.setdefault(row['groupby'], defaultdict(lambda: defaultdict(float)))
                for field in fields_to_assign:
                    groupby_partners[row['groupby']][row['column_group_key']][field] += row[field]

        company_currency = self.env.company.currency_id

        # Execute the queries and dispatch the results.
        query = self._get_query_sums(report, options)

        groupby_partners = {}

        self.env.cr.execute(query)
        for res in self.env.cr.dictfetchall():
            assign_sum(res)

        # Correct the sums per partner, for the lines without partner reconciled with a line having a partner
        query = self._get_sums_without_partner(options)

        self.env.cr.execute(query)
        totals = {}
        for total_field in [
            'debit',
            'credit',
            'amount',
            'balance',
            'untaxed_amount',
            'tax_amount',
        ]:
            totals[total_field] = {col_group_key: 0 for col_group_key in options['column_groups']}

        for row in self.env.cr.dictfetchall():
            totals['debit'][row['column_group_key']] += row['debit']
            totals['credit'][row['column_group_key']] += row['credit']
            totals['amount'][row['column_group_key']] += row['amount']
            totals['balance'][row['column_group_key']] += row['balance']
            totals['untaxed_amount'][row['column_group_key']] += row.get('untaxed_amount', 0.0)
            totals['tax_amount'][row['column_group_key']] += row.get('tax_amount', 0.0)

            if row['groupby'] not in groupby_partners:
                continue

            assign_sum(row)

        if None in groupby_partners:
            # Debit/credit are inverted for the unknown partner as the computation is made regarding the balance of the known partner
            for column_group_key in options['column_groups']:
                groupby_partners[None][column_group_key]['debit'] += totals['credit'][column_group_key]
                groupby_partners[None][column_group_key]['credit'] += totals['debit'][column_group_key]
                groupby_partners[None][column_group_key]['amount'] += totals['amount'][column_group_key]
                groupby_partners[None][column_group_key]['balance'] -= totals['balance'][column_group_key]
                groupby_partners[None][column_group_key]['untaxed_amount'] += totals['untaxed_amount'][column_group_key]
                groupby_partners[None][column_group_key]['tax_amount'] += totals['tax_amount'][column_group_key]

        # Retrieve the partners to browse.
        # groupby_partners.keys() contains all account ids affected by:
        # - the amls in the current period.
        # - the amls affecting the initial balance.
        if groupby_partners:
            # Note a search is done instead of a browse to preserve the table ordering.
            partners = self.env['res.partner'].with_context(active_test=False).search_fetch([('id', 'in', list(groupby_partners.keys()))], ["id", "name", "trust", "company_registry", "vat"])
        else:
            partners = []

        # Add 'Partner Unknown' if needed
        if None in groupby_partners.keys():
            partners = [p for p in partners] + [None]

        return [(partner, groupby_partners[partner.id if partner else None]) for partner in partners]
