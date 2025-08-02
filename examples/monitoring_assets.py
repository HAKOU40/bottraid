import time
import asyncio
import logging
from pyquotex.config import credentials
from pyquotex.stable_api import Quotex
from pyquotex.utils.processor import process_candles, get_color

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(message)s'
)
logging.disable()


async def get_candle(client, asset, period, lock):
    async with lock:
        candles_color = []
        offset = 3600  # آخر ساعة
        end_from_time = time.time()

        # جلب الشموع
        candles = await client.get_candles(asset, end_from_time, offset, period)
        candles_data = candles

        if len(candles_data) > 0:
            if not candles_data[0].get("open"):
                candles = process_candles(candles_data, period)
                candles_data = candles

            print(f"\n{asset} ({period}s):")
            for candle in candles_data:
                color = get_color(candle)
                candles_color.append(color)
                print(candle)

        else:
            print(f"{asset} ({period}s) - No candles.")

        print(f"\r{asset} ({period}s) - {time.strftime('%H:%M:%S')}", end="")


async def process_all_assets(client, assets, periods):
    lock = asyncio.Lock()
    tasks = []

    for period in periods:
        for asset in assets:
            tasks.append(asyncio.create_task(get_candle(client, asset, period, lock)))

    await asyncio.gather(*tasks)


async def main():
    email, password = credentials()
    client = Quotex(
        email=email,
        password=password,
        lang="pt",
    )
    check_connect, message = await client.connect()
    if check_connect:
        codes_asset = await client.get_all_assets()
        assets = list(codes_asset.keys())[:30]  # اختيار أول 30 أصل فقط
        periods = [10, 15, 20, 25, 30]  # الفترات المطلوبة
        start_time = time.time()

        await process_all_assets(client, assets, periods)

        end_time = time.time()
        print(f"\nTotal time: {end_time - start_time:.2f} seconds")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())

