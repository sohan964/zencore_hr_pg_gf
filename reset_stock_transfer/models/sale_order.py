from odoo import models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_reset_sale_to_draft(self):
        self.ensure_one()

        # Process only outbound deliveries
        outbound_pickings = self.picking_ids.filtered(
            lambda p: p.picking_type_id.code == "outgoing"
        )

        for picking in outbound_pickings:

            # If delivery was validated
            if picking.state == "done":
                picking.action_reset_to_draft()

            # Cancel delivery
            if picking.state != "cancel":
                picking.action_cancel()

        # Reset Sale Order
        self.write({
            "state": "draft",
        })

        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }