import aiohttp


async def check_internet_connection():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://www.google.com', timeout=5) as response:
                return response.status < 400
    except:
        return False
