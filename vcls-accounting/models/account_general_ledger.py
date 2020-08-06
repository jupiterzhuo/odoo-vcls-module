# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.tools.misc import format_date


class ReportAccountGeneralLedger(models.AbstractModel):
    _inherit = "account.general.ledger"

    def _get_columns_name(self, options):
        column_names = super(ReportAccountGeneralLedger, self)._get_columns_name(options)
        column_names.insert(1, {'name': _("Journal")})
        return column_names

    @api.model
    def _get_lines(self, options, line_id=None):
        """Overwrite the native method to add the Journal on each line"""
        offset = int(options.get('lines_offset', 0))
        lines = []
        context = self.env.context
        company_id = self.env.user.company_id
        used_currency = company_id.currency_id
        dt_from = options['date'].get('date_from')
        line_id = line_id and int(line_id.split('_')[1]) or None
        aml_lines = []
        # Aml go back to the beginning of the user chosen range but the amount on the account line should go back to either the beginning of the fy or the beginning of times depending on the account
        grouped_accounts = self.with_context(date_from_aml=dt_from, date_from=dt_from and company_id.compute_fiscalyear_dates(fields.Date.from_string(dt_from))['date_from'] or None)._group_by_account_id(options, line_id)
        sorted_accounts = sorted(grouped_accounts, key=lambda a: a.code)
        unfold_all = context.get('print_mode') and len(options.get('unfolded_lines')) == 0
        sum_debit = sum_credit = sum_balance = 0
        for account in sorted_accounts:
            display_name = account.code + " " + account.name
            if options.get('filter_accounts'):
                #skip all accounts where both the code and the name don't start with the given filtering string
                if not any([display_name_part.lower().startswith(options['filter_accounts'].lower()) for display_name_part in display_name.split(' ')]):
                    continue
            debit = grouped_accounts[account]['debit']
            credit = grouped_accounts[account]['credit']
            balance = grouped_accounts[account]['balance']
            sum_debit += debit
            sum_credit += credit
            sum_balance += balance
            amount_currency = '' if not account.currency_id else self.with_context(no_format=False).format_value(grouped_accounts[account]['amount_currency'], currency=account.currency_id)
            # don't add header for `load more`
            if offset == 0:
                lines.append({
                    'id': 'account_%s' % (account.id,),
                    'name': len(display_name) > 40 and not context.get('print_mode') and display_name[:40]+'...' or display_name,
                    'title_hover': display_name,
                    'columns': [{'name': v} for v in [amount_currency, self.format_value(debit), self.format_value(credit), self.format_value(balance)]],
                    'level': 2,
                    'unfoldable': True,
                    'unfolded': 'account_%s' % (account.id,) in options.get('unfolded_lines') or unfold_all,
                    'colspan': 4,
                })
            if 'account_%s' % (account.id,) in options.get('unfolded_lines') or unfold_all:
                initial_debit = grouped_accounts[account]['initial_bal']['debit']
                initial_credit = grouped_accounts[account]['initial_bal']['credit']
                initial_balance = grouped_accounts[account]['initial_bal']['balance']
                initial_currency = '' if not account.currency_id else self.with_context(no_format=False).format_value(grouped_accounts[account]['initial_bal']['amount_currency'], currency=account.currency_id)

                domain_lines = []
                if offset == 0:
                    domain_lines.append({
                        'id': 'initial_%s' % (account.id,),
                        'class': 'o_account_reports_initial_balance',
                        'name': _('Initial Balance'),
                        'parent_id': 'account_%s' % (account.id,),
                        'columns': [{'name': v} for v in ['', '', '', initial_currency, self.format_value(initial_debit), self.format_value(initial_credit), self.format_value(initial_balance)]],
                    })
                    progress = initial_balance
                else:
                    # for load more:
                    progress = float(options.get('lines_progress', initial_balance))

                amls = grouped_accounts[account]['lines']

                remaining_lines = 0
                if not context.get('print_mode'):
                    remaining_lines = grouped_accounts[account]['total_lines'] - offset - len(amls)


                for line in amls:
                    if options.get('cash_basis'):
                        line_debit = line.debit_cash_basis
                        line_credit = line.credit_cash_basis
                    else:
                        line_debit = line.debit
                        line_credit = line.credit
                    date = amls.env.context.get('date') or fields.Date.today()
                    line_debit = line.company_id.currency_id._convert(line_debit, used_currency, company_id, date)
                    line_credit = line.company_id.currency_id._convert(line_credit, used_currency, company_id, date)
                    progress = progress + line_debit - line_credit
                    currency = "" if not line.currency_id else self.with_context(no_format=False).format_value(line.amount_currency, currency=line.currency_id)

                    name = line.name and line.name or ''
                    if line.ref:
                        name = name and name + ' - ' + line.ref or line.ref
                    name_title = name
                    # Don't split the name when printing
                    if len(name) > 35 and not self.env.context.get('no_format') and not self.env.context.get('print_mode'):
                        name = name[:32] + "..."
                    partner_name = line.partner_id.name
                    partner_name_title = partner_name
                    if partner_name and len(partner_name) > 35  and not self.env.context.get('no_format') and not self.env.context.get('print_mode'):
                        partner_name = partner_name[:32] + "..."
                    caret_type = 'account.move'
                    action_context = {}
                    if line.invoice_id:
                        caret_type = 'account.invoice.in' if line.invoice_id.type in ('in_refund', 'in_invoice') else 'account.invoice.out'
                        action_context = {
                            'default_type': line.invoice_id.type,
                            'type': line.invoice_id.type,
                            'journal_type': line.invoice_id.journal_id.type,
                        }
                    elif line.payment_id:
                        caret_type = 'account.payment'
                    columns = [{'name': v} for v in [line.journal_id.name, format_date(self.env, line.date),
                                                     name, partner_name, currency,
                                                     line_debit != 0 and self.format_value(line_debit) or '',
                                                     line_credit != 0 and self.format_value(line_credit) or '',
                                                     self.format_value(progress)]]
                    columns[2]['class'] = 'whitespace_print'
                    columns[3]['class'] = 'whitespace_print'
                    columns[2]['title'] = name_title
                    columns[3]['title'] = partner_name_title
                    line_value = {
                        'id': line.id,
                        'action_context': action_context,
                        'caret_options': caret_type,
                        'class': 'top-vertical-align',
                        'parent_id': 'account_%s' % (account.id,),
                        'name': line.move_id.name if line.move_id.name else '/',
                        'columns': columns,
                        'level': 4,
                    }
                    aml_lines.append(line.id)
                    domain_lines.append(line_value)

                # load more
                if remaining_lines > 0:
                    domain_lines.append({
                        'id': 'loadmore_%s' % account.id,
                        # if MAX_LINES is None, there will be no remaining lines
                        # so this should not cause a problem
                        'offset': offset + self.MAX_LINES,
                        'progress': progress,
                        'class': 'o_account_reports_load_more text-center',
                        'parent_id': 'account_%s' % (account.id,),
                        'name': _('Load more... (%s remaining)') % remaining_lines,
                        'colspan': 7,
                        'columns': [{}],
                    })
                # don't add total line for `load more`
                if offset == 0:
                    domain_lines.append({
                        'id': 'total_' + str(account.id),
                        'class': 'o_account_reports_domain_total',
                        'parent_id': 'account_%s' % (account.id,),
                        'name': _('Total '),
                        'columns': [{'name': v} for v in ['', '', '', amount_currency, self.format_value(debit), self.format_value(credit), self.format_value(balance)]],
                    })

                lines += domain_lines

        if not line_id:

            lines.append({
                'id': 'general_ledger_total_%s' % company_id.id,
                'name': _('Total'),
                'class': 'total',
                'level': 1,
                'columns': [{'name': v} for v in ['', '', '', '', self.format_value(sum_debit), self.format_value(sum_credit), self.format_value(sum_balance)]],
            })

        journals = [j for j in options.get('journals') if j.get('selected')]
        if len(journals) == 1 and journals[0].get('type') in ['sale', 'purchase'] and not line_id:
            lines.append({
                'id': 0,
                'name': _('Tax Declaration'),
                'columns': [{'name': v} for v in ['', '', '', '', '', '', '']],
                'level': 1,
                'unfoldable': False,
                'unfolded': False,
            })
            lines.append({
                'id': 0,
                'name': _('Name'),
                'columns': [{'name': v} for v in ['', '', '', '', _('Base Amount'), _('Tax Amount'), '']],
                'level': 2,
                'unfoldable': False,
                'unfolded': False,
            })
            journal_currency = self.env['account.journal'].browse(journals[0]['id']).company_id.currency_id
            for tax, values in self._get_taxes(journals[0]).items():
                base_amount = journal_currency._convert(values['base_amount'], used_currency, company_id, options['date']['date_to'])
                tax_amount = journal_currency._convert(values['tax_amount'], used_currency, company_id, options['date']['date_to'])
                lines.append({
                    'id': '%s_tax' % (tax.id,),
                    'name': tax.name + ' (' + str(tax.amount) + ')',
                    'caret_options': 'account.tax',
                    'unfoldable': False,
                    'columns': [{'name': v} for v in [self.format_value(base_amount), self.format_value(tax_amount), '']],
                    'colspan': 5,
                    'level': 4,
                })

        if self.env.context.get('aml_only', False):
            return aml_lines
        return lines
