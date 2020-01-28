# Copyright 2020 ForgeFlow, S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class POSBankStatementUpdateClosingBalance(models.TransientModel):
    _name = "pos.update.bank.statement.closing.balance"
    _description = 'POS Update Bank Statement Closing Balance'

    session_id = fields.Many2one(
        comodel_name='pos.session',
    )
    item_ids = fields.One2many(
        comodel_name="pos.update.bank.statement.closing.balance.line",
        inverse_name="wiz_id",
        string="Items",
    )

    @api.model
    def _prepare_item(self, session, statement):
        return {
            "statement_id": statement.id,
            "name": statement.name,
            "journal_id": statement.journal_id.id,
            "balance_start": statement.balance_start,
            "total_entry_encoding": statement.total_entry_encoding,
            "currency_id": statement.currency_id.id,
        }

    @api.model
    def default_get(self, flds):
        res = super().default_get(flds)
        session_obj = self.env["pos.session"]
        active_ids = self.env.context["active_ids"] or []
        active_model = self.env.context["active_model"]

        if not active_ids:
            return res
        assert active_model == "pos.session", \
            "Bad context propagation"

        items = []
        if len(active_ids) > 1:
            raise UserError(_('You cannot start the closing '
                              'balance for multiple POS sessions'))
        session = session_obj.browse(active_ids[0])
        for statement in session.statement_ids:
            if statement.journal_id.type != 'cash' or \
                (statement.journal_id.type == 'cash' and
                 not session.cash_control):
                items.append([0, 0, self._prepare_item(session, statement)])
        res["session_id"] = session.id
        res["item_ids"] = items
        return res

    @api.model
    def _prepare_cash_box_journal(self, item):
        return {
            'amount': abs(item.difference),
            'name': _('Out'),
            "journal_id": item.journal_id.id,
        }

    @api.multi
    def action_confirm(self):
        self.ensure_one()
        for item in self.item_ids:
            if item.difference:
                if item.difference > 0.0:
                    model = "cash.box.journal.in"
                else:
                    model = "cash.box.journal.out"
                wizard = (
                    self.env[model]
                        .with_context(
                        active_model="pos.session",
                        active_ids=self.session_id.ids
                    ).create(self._prepare_cash_box_journal(item))
                )
                wizard.run()
                item.statement_id.balance_end_real = item.balance_end_real
        return True


class BankStatementLineUpdateEndingBalanceLine(models.TransientModel):
    _name = "pos.update.bank.statement.closing.balance.line"
    _description = 'POS Update Bank Statement Closing Balance Line'

    wiz_id = fields.Many2one(
        comodel_name='pos.update.bank.statement.closing.balance',
        required=True,
    )
    statement_id = fields.Many2one(
        comodel_name='account.bank.statement',
    )
    name = fields.Char(
        related='statement_id.name'
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        related='statement_id.journal_id',
    )
    balance_start = fields.Monetary(
        related='statement_id.balance_start',
    )
    total_entry_encoding = fields.Monetary(
        related='statement_id.total_entry_encoding',
    )
    balance_end = fields.Monetary(compute='_compute_balance_end')
    balance_end_real = fields.Monetary(default=0.0)
    difference = fields.Monetary(compute='_compute_balance_end')
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='statement_id.currency_id'
    )

    def _compute_balance_end(self):
        for rec in self:
            rec.balance_end = rec.balance_start + rec.total_entry_encoding
            rec.difference = rec.balance_end_real - rec.balance_end
