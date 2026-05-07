
import os
from datetime import datetime

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

def get_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise EnvironmentError(
            "SUPABASE_URL and SUPABASE_KEY must be set in your .env file."
        )
    return create_client(url, key)

def get_settings() -> dict:
    sb = get_client()
    res = sb.table("settings").select("key, value").execute()
    return {row["key"]: row["value"] for row in (res.data or [])}


def save_settings(data: dict) -> None:
    sb = get_client()
    rows = [{"key": k, "value": str(v)} for k, v in data.items()]
    sb.table("settings").upsert(rows, on_conflict="key").execute()


def get_setting(key: str) -> str | None:
    sb = get_client()
    res = sb.table("settings").select("value").eq("key", key).execute()
    return res.data[0]["value"] if res.data else None


def set_setting(key: str, value: str) -> None:
    sb = get_client()
    sb.table("settings").upsert({"key": key, "value": value}, on_conflict="key").execute()

def next_invoice_number() -> str:
    counter = int(get_setting("invoice_counter") or 1000)
    counter += 1
    set_setting("invoice_counter", str(counter))
    year = datetime.now().strftime("%Y")
    return f"INV-{year}-{counter:05d}"

def get_customers() -> list[dict]:
    sb = get_client()
    res = sb.table("customers").select("*").order("name").execute()
    return res.data or []


def add_customer_manual(
    name: str, phone: str, gst: str, address: str, state: str
) -> None:
    sb = get_client()
    sb.table("customers").insert({
        "name": name,
        "phone": phone,
        "gst_number": gst,
        "address": address,
        "state": state,
    }).execute()


def upsert_customers(records: list[dict]) -> tuple[int, int]:
    """
    Bulk upsert customers from an Excel import.
    Matches on gst_number (if provided) or falls back to name.
    Returns (inserted, updated).
    """
    sb = get_client()
    inserted = updated = 0

    for r in records:
        row = {
            "name":       str(r.get("customer name") or r.get("name", "")).strip(),
            "phone":      str(r.get("phone", "")).strip(),
            "gst_number": str(r.get("gst number") or r.get("gst_number", "")).strip(),
            "address":    str(r.get("address", "")).strip(),
            "state":      str(r.get("state", "")).strip(),
        }
        if not row["name"]:
            continue

        # Try to find existing record
        existing_id = None
        if row["gst_number"]:
            res = sb.table("customers").select("id").eq("gst_number", row["gst_number"]).execute()
            if res.data:
                existing_id = res.data[0]["id"]
        if not existing_id:
            res = sb.table("customers").select("id").eq("name", row["name"]).execute()
            if res.data:
                existing_id = res.data[0]["id"]

        if existing_id:
            sb.table("customers").update(row).eq("id", existing_id).execute()
            updated += 1
        else:
            sb.table("customers").insert(row).execute()
            inserted += 1

    return inserted, updated

def get_products() -> list[dict]:
    sb = get_client()
    res = sb.table("products").select("*").order("name").execute()
    return res.data or []


def get_product_by_name(name: str) -> dict | None:
    sb = get_client()
    res = sb.table("products").select("*").eq("name", name).execute()
    return res.data[0] if res.data else None


def check_stock(name: str, qty: float) -> bool:
    product = get_product_by_name(name)
    return bool(product and float(product.get("quantity", 0)) >= qty)


def upsert_products(records: list[dict]) -> tuple[int, int]:
    """
    Bulk upsert products from an Excel import.
    Matches on SKU (if provided) or product name.
    Returns (inserted, updated).
    """
    sb = get_client()
    inserted = updated = 0

    for r in records:
        row = {
            "name":        str(r.get("product name") or r.get("name", "")).strip(),
            "sku":         str(r.get("sku", "")).strip(),
            "quantity":    float(r.get("quantity", 0)),
            "price":       float(r.get("price", 0)),
            "gst_percent": float(r.get("gst%") or r.get("gst_percent", 18)),
        }
        if not row["name"]:
            continue

        existing_id = None
        if row["sku"]:
            res = sb.table("products").select("id").eq("sku", row["sku"]).execute()
            if res.data:
                existing_id = res.data[0]["id"]
        if not existing_id:
            res = sb.table("products").select("id").eq("name", row["name"]).execute()
            if res.data:
                existing_id = res.data[0]["id"]

        if existing_id:
            sb.table("products").update(row).eq("id", existing_id).execute()
            updated += 1
        else:
            sb.table("products").insert(row).execute()
            inserted += 1

    return inserted, updated

def save_invoice(invoice: dict, items: list[dict]) -> int:
    """
    Saves invoice header + line items, and deducts stock.
    Returns the new invoice's ID.
    """
    sb = get_client()

    inv_row = {
        "invoice_number":   invoice["invoice_number"],
        "customer_name":    invoice.get("customer_name"),
        "customer_gst":     invoice.get("customer_gst"),
        "customer_address": invoice.get("customer_address"),
        "customer_state":   invoice.get("customer_state"),
        "business_state":   invoice.get("business_state"),
        "is_interstate":    bool(invoice.get("is_interstate", False)),
        "invoice_date":     invoice.get("invoice_date", datetime.now().strftime("%Y-%m-%d")),
        "subtotal":         invoice.get("subtotal", 0),
        "cgst":             invoice.get("cgst", 0),
        "sgst":             invoice.get("sgst", 0),
        "igst":             invoice.get("igst", 0),
        "total":            invoice.get("total", 0),
    }

    res = sb.table("invoices").insert(inv_row).execute()
    invoice_id = res.data[0]["id"]

    for item in items:
        sb.table("invoice_items").insert({
            "invoice_id":   invoice_id,
            "product_name": item["product_name"],
            "quantity":     item["quantity"],
            "price":        item["price"],
            "gst_percent":  item["gst_percent"],
            "cgst_amount":  item.get("cgst_amount", 0),
            "sgst_amount":  item.get("sgst_amount", 0),
            "igst_amount":  item.get("igst_amount", 0),
            "line_total":   item.get("line_total", 0),
        }).execute()

        # Deduct stock
        product = get_product_by_name(item["product_name"])
        if product:
            new_qty = max(0.0, float(product["quantity"]) - float(item["quantity"]))
            sb.table("products").update({"quantity": new_qty}).eq("id", product["id"]).execute()

    return invoice_id


def get_invoices() -> list[dict]:
    sb = get_client()
    res = sb.table("invoices").select("*").order("created_at", desc=True).execute()
    return res.data or []


def get_invoice_by_id(invoice_id: int) -> dict | None:
    sb = get_client()
    res = sb.table("invoices").select("*").eq("id", invoice_id).execute()
    return res.data[0] if res.data else None


def get_invoice_items(invoice_id: int) -> list[dict]:
    sb = get_client()
    res = sb.table("invoice_items").select("*").eq("invoice_id", invoice_id).execute()
    return res.data or []
