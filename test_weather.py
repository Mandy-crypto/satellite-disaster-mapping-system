import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    from app.services.weather_service import get_weather_service
    service = get_weather_service()
    api_key = os.getenv("OPENWEATHER_API_KEY")
    print(f'🔑 API Key loaded: {api_key[:10] if api_key else "NOT FOUND"}...')
    print('🌤️ Fetching weather for Bhopal...')
    result = await service.fetch_current_weather(23.181, 79.951)
    print(f'✅ Temperature: {result.temperature_c}°C')
    print(f'✅ Rainfall: {result.rainfall_mm}mm')
    print(f'✅ Humidity: {result.humidity}%')
    print(f'✅ Wind Speed: {result.wind_speed_mps} m/s')
    print(f'✅ Risk Level: {result.risk_level}')
    print(f'✅ Weather Condition: {result.weather_condition}')

asyncio.run(test())