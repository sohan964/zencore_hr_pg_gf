from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    intercompany_picking_id = fields.Many2one(
        "stock.picking",
        string="Related Picking",
        check_company=False,
        copy=False,
    )

    is_intercompany_generated = fields.Boolean(
        default=False,
        copy=False,
    )

    def action_confirm(self):
        res = super().action_confirm()

        for picking in self:
            if (
                picking.partner_id
                and not picking.intercompany_picking_id
                and not picking.is_intercompany_generated
            ):
                picking._create_intercompany_picking()

        return res

    def _create_intercompany_picking(self):
        self.ensure_one()

        # Find company from partner
        target_company = self.env["res.company"].sudo().search(
            [("partner_id", "=", self.partner_id.id)],
            limit=1,
        )

        if not target_company:
            return

        # Avoid creating transfer to same company
        if target_company == self.company_id:
            return

        # Only handle Receipts and Deliveries
        if self.picking_type_id.code == "outgoing":
            target_code = "incoming"

        elif self.picking_type_id.code == "incoming":
            target_code = "outgoing"

        else:
            return

        target_picking_type = self.env["stock.picking.type"].sudo().search(
            [
                ("company_id", "=", target_company.id),
                ("code", "=", target_code),
            ],
            limit=1,
        )

        if not target_picking_type:
            return

        if self.intercompany_picking_id:
            return

        source_location = target_picking_type.default_location_src_id.id
        dest_location = target_picking_type.default_location_dest_id.id

        counterpart = (
            self.env["stock.picking"]
            .sudo()
            .with_company(target_company)
            .create(
                {
                    "company_id": target_company.id,
                    "picking_type_id": target_picking_type.id,
                    "origin": self.name,
                    # partner of source company
                    "partner_id": self.company_id.partner_id.id,
                    "is_intercompany_generated": True,
                }
            )
        )

        move_obj = self.env["stock.move"].sudo().with_company(target_company)

        for move in self.move_ids:
            move_obj.create(
                {
                    "product_id": move.product_id.id,
                    "product_uom_qty": move.product_uom_qty,
                    "product_uom": move.product_uom.id,
                    "picking_id": counterpart.id,
                    "company_id": target_company.id,
                    "location_id": source_location,
                    "location_dest_id": dest_location,
                }
            )

        counterpart.action_confirm()

        self.intercompany_picking_id = counterpart.id
        counterpart.intercompany_picking_id = self.id