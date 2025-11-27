"""
Простой тест Gemini Live API (WebSockets)
"""
import asyncio
import os
import traceback
from google import genai
from google.genai import types

# ---------------------------------------------------------
# КЛЮЧИ (из .env)
API_KEYS = [
    "AIzaSyCalj1ugvpU1thqDtROGCEgIGdXDFBIOJM",  # Ключ 1
    "AIzaSyDDsvjPVcTzJoGgz7XWmhB7ZEVMCrg6P0c",  # Ключ 2
    "AIzaSyD18h8QwDeSl8U5pFMM1HtoB3VaUksXy-g",  # Ключ 3 (новый)
]
# ---------------------------------------------------------

MODEL_ID = "gemini-2.0-flash-exp"  # Техническое имя для Live API
API_VERSION = "v1alpha"            # Обязательно для BidiStreaming


async def test_live_connection(api_key, key_num):
    print(f"\n{'='*60}")
    print(f"🔌 Тест ключа #{key_num}")
    print(f"🔌 Подключение к {MODEL_ID} (API: {API_VERSION})...")
    
    # 1. Инициализация клиента с правильной версией
    client = genai.Client(
        api_key=api_key,
        http_options={'api_version': API_VERSION}
    )
    
    # 2. Конфигурация: только ТЕКСТ (чтобы было быстро)
    config = types.LiveConnectConfig(
        response_modalities=["TEXT"]
    )
    
    try:
        # 3. Открываем WebSocket соединение
        async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
            print("✅ Соединение установлено! (WebSockets работают)")
            
            # 4. Отправляем сообщение
            message = "Привет! Просто ответь одним словом: 'Работает'."
            print(f"📤 Отправляю: {message}")
            await session.send(message, end_of_turn=True)
            
            # 5. Читаем поток ответов
            print("📥 Жду ответ...")
            full_response = ""
            
            async for response in session.receive():
                # Ответы приходят чанками (кусочками)
                if response.server_content and response.server_content.model_turn:
                    for part in response.server_content.model_turn.parts:
                        if part.text:
                            print(f"🟢 Получен чанк: {part.text}")
                            full_response += part.text
                
                # Если модель закончила фразу
                if response.server_content and response.server_content.turn_complete:
                    print("🏁 Ответ завершен.")
                    break
            
            print(f"\n✅ УСПЕХ! Ключ #{key_num} работает!")
            print(f"Полный ответ: {full_response}")
            return True
            
    except Exception as e:
        print(f"\n❌ ОШИБКА на ключе #{key_num}:")
        error_msg = str(e)
        
        if "quota" in error_msg.lower() or "exceeded" in error_msg.lower():
            print(f"   Квота исчерпана")
        elif "404" in error_msg or "not found" in error_msg.lower():
            print(f"   Модель не найдена (проверь MODEL_ID)")
        elif "403" in error_msg:
            print(f"   Проблема с ключом (неверный или нет доступа)")
        elif "1008" in error_msg:
            print(f"   Policy violation (регион или доступ)")
        else:
            print(f"   {error_msg}")
        
        return False


async def main():
    print("="*60)
    print("🧪 Тест Gemini Live API (WebSockets)")
    print("="*60)
    
    success_count = 0
    
    for i, api_key in enumerate(API_KEYS, 1):
        result = await test_live_connection(api_key, i)
        if result:
            success_count += 1
            print(f"\n🎉 Ключ #{i} работает! Можно использовать.")
            break  # Нашли рабочий ключ
        else:
            print(f"\n⚠️ Ключ #{i} не работает, пробуем следующий...")
    
    print(f"\n{'='*60}")
    if success_count > 0:
        print(f"✅ Найдено рабочих ключей: {success_count}/3")
        print(f"✅ Live API работает! Unlimited лимиты доступны!")
    else:
        print(f"❌ Все ключи исчерпаны или недоступны")
        print(f"💡 Подожди до завтра или добавь платёжку в Google AI Studio")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
