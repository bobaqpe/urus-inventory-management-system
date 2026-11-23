from decimal import Decimal
from datetime import date, datetime, timedelta
from uuid import UUID
from sqlalchemy import text


def _serialize(value):
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()
    
    if isinstance(value, UUID):
        return str(value)
    
    return value


def _serialize_row(row):
    return {
        key: _serialize(value)
        for key, value in dict(row).items()
    }
def get_inventory_summary(engine, business_id: int):
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total_products,

                    COUNT(*) FILTER (
                        WHERE stock = 0
                    ) AS out_of_stock,

                    COUNT(*) FILTER (
                        WHERE stock > 0
                        AND stock <= reorder_level
                    ) AS low_stock,

                    COALESCE(
                        SUM(stock * cost_price),
                        0
                    ) AS inventory_value

                FROM products

                WHERE business_id = :business_id
                  AND archived_at IS NULL
                """
            ),
            {
                "business_id": business_id
            },
        ).mappings().one()

    return _serialize_row(row)

def search_products(
    engine,
    business_id: int,
    query: str,
    limit: int = 20,
):
    query = query.strip()

    if not query:
        return []

    limit = max(1, min(limit, 20))

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    p.id,
                    p.name,
                    p.sku,
                    c.name AS category,
                    s.name AS supplier,
                    p.stock,
                    p.unit,
                    p.reorder_level,
                    p.cost_price,
                    p.expiry_date
                FROM products p
                LEFT JOIN categories c
                    ON c.id = p.category_id
                   AND c.business_id = p.business_id
                LEFT JOIN suppliers s
                    ON s.id = p.supplier_id
                   AND s.business_id = p.business_id
                WHERE p.business_id = :business_id
                  AND p.archived_at IS NULL
                  AND (
                      LOWER(p.name) LIKE LOWER(:search)
                      OR LOWER(p.sku) LIKE LOWER(:search)
                  )
                ORDER BY p.name
                LIMIT :limit
                """
            ),
            {
                "business_id": business_id,
                "search": f"%{query}%",
                "limit": limit,
            },
        ).mappings().all()

    return [_serialize_row(row) for row in rows]

def get_low_stock_products(
    engine,
    business_id: int,
    limit: int = 20,
):
    limit = max(1, min(limit, 50))

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    p.id,
                    p.name,
                    p.sku,
                    p.stock,
                    p.unit,
                    p.reorder_level,
                    c.name AS category
                FROM products p
                LEFT JOIN categories c
                    ON c.id = p.category_id
                   AND c.business_id = p.business_id
                WHERE p.business_id = :business_id
                  AND p.archived_at IS NULL
                  AND p.stock > 0
                  AND p.stock <= p.reorder_level
                ORDER BY
                    (p.reorder_level - p.stock) DESC,
                    p.name
                LIMIT :limit
                """
            ),
            {
                "business_id": business_id,
                "limit": limit,
            },
        ).mappings().all()

    return [_serialize_row(row) for row in rows]


def get_out_of_stock_products(
    engine,
    business_id: int,
    limit: int = 20,
):
    limit = max(1, min(limit, 50))

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    p.id,
                    p.name,
                    p.sku,
                    p.unit,
                    c.name AS category
                FROM products p
                LEFT JOIN categories c
                    ON c.id = p.category_id
                   AND c.business_id = p.business_id
                WHERE p.business_id = :business_id
                  AND p.archived_at IS NULL
                  AND p.stock = 0
                ORDER BY p.name
                LIMIT :limit
                """
            ),
            {
                "business_id": business_id,
                "limit": limit,
            },
        ).mappings().all()

    return [_serialize_row(row) for row in rows]

def get_expiring_products(
    engine,
    business_id: int,
    days: int = 7,
    limit: int = 20,
):
    days = max(1, min(days, 90))
    limit = max(1, min(limit, 50))

    with engine.connect() as conn:
        today = date.today()
        cutoff = today + timedelta(days=days)

        rows = conn.execute(
            text(
                """
                SELECT
                    p.id,
                    p.name,
                    p.sku,
                    p.stock,
                    p.unit,
                    p.cost_price,
                    p.expiry_date,
                    c.name AS category
                FROM products p
                LEFT JOIN categories c
                    ON c.id = p.category_id
                   AND c.business_id = p.business_id
                WHERE p.business_id = :business_id
                  AND p.archived_at IS NULL
                  AND p.expiry_date IS NOT NULL
                  AND p.expiry_date >= :today
                  AND p.expiry_date <= :cutoff
                ORDER BY
                    p.expiry_date ASC,
                    p.name ASC
                LIMIT :limit
                """
            ),
            {
                "business_id": business_id,
                "today": today,
                "cutoff": cutoff,
                "limit": limit,
            },
        ).mappings().all()

    return [_serialize_row(row) for row in rows]

def get_recent_inventory_activity(
    engine,
    business_id: int,
    limit: int = 20,
):
    limit = max(1, min(limit, 50))

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    m.id,
                    m.product_id,
                    p.name AS product,
                    m.quantity_delta,
                    m.reason,
                    m.created_at
                FROM stock_movements m
                JOIN products p
                    ON p.id = m.product_id
                   AND p.business_id = m.business_id
                WHERE m.business_id = :business_id
                ORDER BY m.created_at DESC
                LIMIT :limit
                """
            ),
            {
                "business_id": business_id,
                "limit": limit,
            },
        ).mappings().all()

    return [_serialize_row(row) for row in rows]

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_inventory_summary",
            "description": (
                "Get the current inventory summary including total products, "
                "low-stock products, out-of-stock products, and inventory value."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": (
                "Search for products using a product name or SKU."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Product name or SKU to search for.",
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_low_stock_products",
            "description": (
                "Get products that are currently at or below their reorder level."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_out_of_stock_products",
            "description": (
                "Get products whose current stock quantity is zero."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_expiring_products",
            "description": (
                "Get products that will expire within a given number of days."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 90,
                        "description": (
                            "Number of days from today to check for expiry."
                        ),
                    }
                },
                "required": ["days"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_inventory_activity",
            "description": (
                "Get recent inventory stock movements and activity."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
]

def execute_tool(
    name: str,
    arguments: dict,
    *,
    engine,
    business_id: int,
):
    handlers = {
        "get_inventory_summary": get_inventory_summary,
        "search_products": search_products,
        "get_low_stock_products": get_low_stock_products,
        "get_out_of_stock_products": get_out_of_stock_products,
        "get_expiring_products": get_expiring_products,
        "get_recent_inventory_activity": get_recent_inventory_activity,
    }

    handler = handlers.get(name)

    if handler is None:
        raise ValueError(f"Unsupported AI tool: {name}")

    return handler(
        engine,
        business_id,
        **arguments,
    )