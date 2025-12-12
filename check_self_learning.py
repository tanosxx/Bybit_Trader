"""
Проверка системы самообучения (Self-Learning)
"""
import sys
sys.path.insert(0, '/app')

import pickle
import os
from datetime import datetime

def check_self_learning():
    print("=" * 80)
    print("🧠 ПРОВЕРКА СИСТЕМЫ САМООБУЧЕНИЯ (SELF-LEARNING)")
    print("=" * 80)
    
    model_path = 'ml_data/self_learner.pkl'
    
    # 1. Проверка файла
    print("\n📁 Проверка файла модели:")
    if os.path.exists(model_path):
        size = os.path.getsize(model_path)
        print(f"   ✅ Файл существует: {model_path}")
        print(f"   Размер: {size:,} bytes ({size/1024:.1f} KB)")
        
        # Проверяем время модификации
        mtime = os.path.getmtime(model_path)
        mod_time = datetime.fromtimestamp(mtime)
        print(f"   Последнее обновление: {mod_time}")
    else:
        print(f"   ❌ Файл не найден: {model_path}")
        return
    
    # 2. Загрузка модели
    print("\n📊 Загрузка модели:")
    try:
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
        
        print(f"   ✅ Модель загружена успешно")
        
        # Проверяем структуру
        print(f"\n   Структура данных:")
        for key in data.keys():
            print(f"      - {key}: {type(data[key]).__name__}")
        
        # 3. Статистика обучения
        print(f"\n📈 Статистика обучения:")
        learning_count = data.get('learning_count', 0)
        predictions_count = data.get('predictions_count', 0)
        wins = data.get('wins', 0)
        losses = data.get('losses', 0)
        
        print(f"   Обучено на сделках: {learning_count}")
        print(f"   Предсказаний сделано: {predictions_count}")
        print(f"   Wins: {wins}")
        print(f"   Losses: {losses}")
        
        if learning_count > 0:
            win_rate = (wins / learning_count) * 100
            print(f"   Win Rate: {win_rate:.1f}%")
        
        # 4. Информация о модели
        print(f"\n🤖 Информация о модели:")
        model = data.get('model')
        if model:
            print(f"   Тип модели: {type(model).__name__}")
            print(f"   Модуль: {type(model).__module__}")
            
            # Проверяем атрибуты модели River
            if hasattr(model, 'n_models'):
                print(f"   Количество деревьев: {model.n_models}")
            if hasattr(model, 'max_features'):
                print(f"   Max features: {model.max_features}")
        
        # 5. Метрики
        print(f"\n📊 Метрики:")
        metric = data.get('metric')
        if metric:
            print(f"   Тип метрики: {type(metric).__name__}")
            if hasattr(metric, 'get'):
                accuracy = metric.get()
                print(f"   Accuracy: {accuracy:.2%}")
        
        # 6. Последнее обновление
        updated_at = data.get('updated_at')
        if updated_at:
            print(f"\n⏰ Последнее обновление модели:")
            print(f"   {updated_at}")
        
        # 7. Проверка работоспособности
        print(f"\n🔧 Проверка работоспособности:")
        
        # Пробуем импортировать модуль
        try:
            from core.self_learning import get_self_learner
            print(f"   ✅ Модуль self_learning импортируется")
            
            # Пробуем создать экземпляр
            learner = get_self_learner()
            print(f"   ✅ SelfLearner инициализирован")
            
            # Получаем статистику
            stats = learner.get_stats()
            print(f"\n   Статистика из модуля:")
            print(f"      Enabled: {stats['enabled']}")
            print(f"      Learned samples: {stats['learned_samples']}")
            print(f"      Predictions: {stats['predictions']}")
            print(f"      Win rate: {stats['win_rate']:.1f}%")
            print(f"      Model Accuracy: {stats['model_accuracy']:.2%}")
            print(f"      Ready: {stats['ready']}")
            
            # Проверяем минимальный порог
            if stats['learned_samples'] >= 50:
                print(f"   ✅ Модель обучена достаточно (>= 50 samples)")
            else:
                print(f"   ⚠️  Модель нуждается в дообучении (< 50 samples)")
            
        except Exception as e:
            print(f"   ❌ Ошибка при инициализации: {e}")
            import traceback
            traceback.print_exc()
    
    except Exception as e:
        print(f"   ❌ Ошибка загрузки модели: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✅ ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 80)

if __name__ == "__main__":
    check_self_learning()
