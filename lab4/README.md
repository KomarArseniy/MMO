# ЛР4. Бинарная классификация (Healthy Meal Plan, цель is_healthy)

Запуск (из папки lab4):

    pip install -r requirements.txt
    python lab4_classification.py

CSV (`healthy_meal_plans.csv`) уже лежит рядом со скриптом. Скрипт печатает очистку данных и таблицу метрик,
сохраняет `results.csv` и 5 графиков в `figures/`.
Модели: логистическая регрессия, SVM (RBF), CART; с учётом дисбаланса классов (class_weight='balanced').
