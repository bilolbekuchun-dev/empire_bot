import aiohttp
import json

async def get_dollar_rate():
    return 12700


async def create_invoice_hamyonlar(shop_key: str, shop_id: str, amount: int):
    url = "https://hamyonlar.uz/api/create_invoice"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "shop_key": shop_key,
        "shop_id": shop_id,
        "amount": str(amount)
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=json.dumps(payload), ssl=False) as response:
            return await response.json()

async def get_payment_status_hamyonlar(invoice_id: str):
    url = f"https://hamyonlar.uz/merchant/{invoice_id}/json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, ssl=False) as response:
            return await response.json()