# Copyright 2020 ForgeFlow, S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    pos_control_ending_balance = fields.Boolean(
        'Control ending balance in POS')
