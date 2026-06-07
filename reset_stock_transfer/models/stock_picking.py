from odoo import models
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_reset_to_draft(self):
        self.ensure_one()

        if self.state != "done":
            raise UserError(
                "Only completed transfers can be reset."
            )

        # Reverse stock
        wizard = self.env["stock.return.picking"].with_context(
            active_id=self.id,
            active_ids=self.ids,
            active_model="stock.picking",
        ).create({})

        for line in wizard.product_return_moves:
            line.quantity = line.move_id.quantity

        return_picking = wizard._create_return()
        return_picking.button_validate()

        # Reset picking
        self.write({
            "state": "draft",
        })

        # Reset moves
        self.move_ids.write({
            "state": "draft",
        })

        # Remove completed move lines
        self.move_line_ids.unlink()

        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }