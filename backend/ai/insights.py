from decimal import Decimal

from sqlalchemy import text


def _to_string(value):
    if isinstance(value, Decimal):
        return str(value)

    return value


def generate_inventory_insights(engine, business_id: int):
    insights = []

    with engine.connect() as conn:
        summary = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (
                        WHERE stock = 0
                    ) AS out_of_stock,

                    COUNT(*) FILTER (
                        WHERE stock > 0
                        AND stock <= reorder_level
                    ) AS low_stock,

                    COUNT(*) FILTER (
                        WHERE expiry_date IS NOT NULL
                        AND expiry_date >= CURRENT_DATE
                        AND expiry_date <= CURRENT_DATE + INTERVAL '7 days'
                    ) AS expiring_soon,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN expiry_date IS NOT NULL
                                AND expiry_date >= CURRENT_DATE
                                AND expiry_date <= CURRENT_DATE + INTERVAL '7 days'
                                THEN stock * cost_price
                                ELSE 0
                            END
                        ),
                        0
                    ) AS expiry_value

                FROM products

                WHERE business_id = :business_id
                  AND archived_at IS NULL
                """
            ),
            {
                "business_id": business_id
            },
        ).mappings().one()

    out_of_stock = summary["out_of_stock"] or 0
    low_stock = summary["low_stock"] or 0
    expiring_soon = summary["expiring_soon"] or 0
    expiry_value = summary["expiry_value"] or Decimal("0")

    if out_of_stock > 0:
        insights.append(
            {
                "type": "stock",
                "severity": "critical",
                "title": "Out of Stock",
                "message": (
                    f"{out_of_stock} product"
                    f"{'s are' if out_of_stock != 1 else ' is'} "
                    "currently out of stock."
                ),
                "affected_products": out_of_stock,
            }
        )

    if low_stock > 0:
        insights.append(
            {
                "type": "stock",
                "severity": "warning",
                "title": "Low Stock",
                "message": (
                    f"{low_stock} product"
                    f"{'s are' if low_stock != 1 else ' is'} "
                    "at or below the reorder level."
                ),
                "affected_products": low_stock,
            }
        )

    if expiring_soon > 0:
        insights.append(
            {
                "type": "expiry",
                "severity": "warning",
                "title": "Expiry Risk",
                "message": (
                    f"{expiring_soon} product"
                    f"{'s expire' if expiring_soon != 1 else ' expires'} "
                    "within the next 7 days."
                ),
                "affected_products": expiring_soon,
                "value_at_risk": _to_string(expiry_value),
            }
        )

    if not insights:
        insights.append(
            {
                "type": "inventory",
                "severity": "normal",
                "title": "Inventory Healthy",
                "message": (
                    "No immediate stock or expiry issues need attention."
                ),
                "affected_products": 0,
            }
        )

    return insights