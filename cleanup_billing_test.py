#!/usr/bin/env python3
"""Cleanup script for Phase 3 Billing test data"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def cleanup():
    """Delete all quotations, invoices, and counters from test"""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "raybotix_digital")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Delete all quotations
    result = await db.quotations.delete_many({})
    print(f"✅ Deleted {result.deleted_count} quotations")
    
    # Delete all invoices
    result = await db.invoices.delete_many({})
    print(f"✅ Deleted {result.deleted_count} invoices")
    
    # Delete counters for quotations and invoices
    result = await db.counters.delete_many({"_id": {"$regex": "^(quotation_|invoice_)"}})
    print(f"✅ Deleted {result.deleted_count} counter documents")
    
    # Ensure Priya's crm_access is False
    result = await db.users.update_one(
        {"email": "priya@raybotix.com"},
        {"$set": {"crm_access": False}}
    )
    if result.matched_count > 0:
        print(f"✅ Ensured Priya's crm_access is False")
    
    client.close()
    print("\n✅ Cleanup complete!")

if __name__ == "__main__":
    asyncio.run(cleanup())
