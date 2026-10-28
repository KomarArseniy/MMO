"""ЛР1, часть 1 (встроенные типы данных). Вариант 15."""
import re


# ---------- Задание 1. Секунды -> дни:часы:минуты:секунды ----------
def task1():
    total = int(input("Введите количество секунд: "))
    days, rest = divmod(total, 24 * 3600)      # divmod возвращает (частное, остаток)
    hours, rest = divmod(rest, 3600)
    minutes, seconds = divmod(rest, 60)
    print(f"{days}:{hours:02d}:{minutes:02d}:{seconds:02d}")


# ---------- Задание 2. Все числа из строки ----------
def task2():
    text = input("Введите строку: ")
    numbers = re.findall(r"\d+", text)          # \d+ = одна или больше цифр подряд
    print("Числа в строке:", [int(n) for n in numbers] if numbers else "чисел нет")


# ---------- Задание 3. Гласные и согласные в словах списка ----------
def task3():
    data = ['Python', 15442, 32, 'QweRty', 34, 19, 'love']
    vowels = set("aeiou")
    for item in data:
        if isinstance(item, str):               # числа пропускаем
            low = item.lower()
            v = sum(1 for ch in low if ch in vowels)
            c = sum(1 for ch in low if ch.isalpha() and ch not in vowels)
            print(f"{item}: гласных {v}, согласных {c}")


# ---------- Задание 4. Слияние нескольких словарей ----------
def merge_dicts(*dicts):
    result = {}
    for d in dicts:
        result.update(d)                        # при одинаковых ключах побеждает поздний
    return result


def task4():
    d1 = {'a': 1, 'b': 2}
    d2 = {'b': 20, 'c': 3}
    d3 = {'d': 4}
    print("Слияние:", merge_dicts(d1, d2, d3))
    print("То же через {**d1, **d2, **d3}:", {**d1, **d2, **d3})


# ---------- Задание 5. Ювелирный магазин ----------
# название -> [состав, цена за 1 шт., количество на складе]
shop = {
    "кольцо":   ["золото 585", 350.0, 10],
    "серьги":   ["серебро 925", 120.0, 15],
    "цепочка":  ["золото 585", 480.0, 6],
    "браслет":  ["серебро 925", 200.0, 8],
}


def show_info(name):
    """Печатает описание, цену и количество одного изделия."""
    comp, price, qty = shop[name]
    print(f"{name}: состав - {comp}, цена - {price} BYN, в наличии - {qty} шт.")


def buy():
    total = 0.0
    while True:
        name = input("Название изделия (n - выход): ").strip().lower()
        if name == "n":
            break
        if name not in shop:
            print("Такого изделия нет.")
            continue
        try:
            count = int(input("Количество: "))
        except ValueError:
            print("Количество должно быть целым числом.")
            continue
        if count <= 0 or count > shop[name][2]:
            print(f"Недостаточно на складе (есть {shop[name][2]} шт.).")
            continue
        shop[name][2] -= count                  # уменьшаем остаток
        total += count * shop[name][1]
        print(f"Добавлено: {name} x{count}")
    print(f"Итого к оплате: {total} BYN")
    print("Осталось на складе:")
    for n, (_, _, q) in shop.items():
        print(f"  {n}: {q} шт.")


def task5():
    while True:
        print("\n1 - описание  2 - цена  3 - количество  4 - вся информация  5 - покупка  6 - до свидания")
        choice = input("Пункт меню: ").strip()
        if choice == "1":
            for n, v in shop.items():
                print(f"{n} - {v[0]}")
        elif choice == "2":
            for n, v in shop.items():
                print(f"{n} - {v[1]} BYN")
        elif choice == "3":
            for n, v in shop.items():
                print(f"{n} - {v[2]} шт.")
        elif choice == "4":
            for n in shop:
                show_info(n)
        elif choice == "5":
            buy()
        elif choice == "6":
            print("До свидания!")
            break
        else:
            print("Нет такого пункта.")


# ---------- Задание 6. Сумма элементов кортежа до первого отрицательного ----------
def task6():
    t = (5, 3, 8, -2, 7, 1)
    total = 0
    for x in t:
        if x < 0:
            break
        total += x
    print("Кортеж:", t, "-> сумма до первого отрицательного:", total)

if __name__ == "__main__":
    tasks = {"1": task1, "2": task2, "3": task3, "4": task4, "5": task5, "6": task6}
    while True:
        n = input("\nНомер задания (1-6, 0 - выход): ").strip()
        if n == "0":
            break
        tasks.get(n, lambda: print("Нет такого задания"))()
