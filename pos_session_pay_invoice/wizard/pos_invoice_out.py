# -*- coding: utf-8 -*-
# Copyright (C) 2017 Creu Blanca
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, api, models, _
from odoo.exceptions import UserError


class PosInvoiceOut(models.TransientModel):
    _name = 'pos.invoice.out'
    _inherit = 'cash.box.in'

    def default_company(self):
        active_model = self.env.context.get('active_model', False)
        if active_model:
            active_ids = self.env.context.get('active_ids', False)
            active = self.env[active_model].browse(active_ids)
            if active_model == 'pos.session':
                return active[0].config_id.company_id
            return active[0].company_id
        return None

    def default_journals(self):
        active_model = self.env.context.get('active_model', False)
        if active_model:
            active_ids = self.env.context.get('active_ids', False)
            active = self.env[active_model].browse(active_ids)
            if active_model == 'pos.session':
                return self.env['account.journal'].browse(
                    [r.journal_id.id for r in active.statement_ids])

    def default_currency(self):
        active_model = self.env.context.get('active_model', False)
        if active_model:
            active_ids = self.env.context.get('active_ids', False)
            active = self.env[active_model].browse(active_ids)
            if active_model == 'pos.session':
                return active[0].config_id.company_id.currency_id
            return active[0].company_id.currency_id
        return None

    def default_journal(self):
        journals = self.default_journals()
        if journals:
            return journals[0]

    invoice_id = fields.Many2one(
        'account.invoice',
        string='Invoice',
        required=True
    )
    name = fields.Char(
        related='invoice_id.number'
    )
    company_id = fields.Many2one(
        'res.company',
        default=default_company,
        required=True,
        readonly=True
    )
    journal_ids = fields.Many2many(
        'account.journal',
        default=default_journals,
        required=True,
        readonly=True
    )
    journal_id = fields.Many2one(
        'account.journal',
        required=True,
        default=default_journal
    )
    currency_id = fields.Many2one('res.currency', default=default_currency,
                                  required=True, readonly=True)

    @api.onchange('journal_id')
    def _onchange_journal(self):
        self.currency_id = self.journal_id.currency_id or \
                self.journal_id.company_id.currency_id

    @api.onchange('invoice_id')
    def _onchange_invoice(self):
        self.amount = self.invoice_id.residual

    @api.multi
    def _calculate_values_for_statement_line(self, record):
        res = super(PosInvoiceOut, self)._calculate_values_for_statement_line(
            record
        )
        res['invoice_id'] = self.invoice_id.id
        res['account_id'] = self.invoice_id.account_id.id
        res['ref'] = self.invoice_id.number
        res['partner_id'] = self.invoice_id.partner_id.id
        return res

    @api.multi
    def run(self):
        active_model = self.env.context.get('active_model', False)
        active_ids = self.env.context.get('active_ids', False)
        if active_model == 'pos.session':
            bank_statements = [
                session.statement_ids.filtered(
                    lambda r: r.journal_id.id == self.journal_id.id
                )
                for session in self.env[active_model].browse(active_ids)
            ]
            if not bank_statements:
                raise UserError(_('Bank Statement was not found'))
            return self._run(bank_statements)
        else:
            return super(PosInvoiceOut, self).run()
