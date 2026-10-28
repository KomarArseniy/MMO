"""ЛР1, часть 3 (классы и ООП). Вариант 15."""


# ---------- Задание 1. Класс List ----------
class List:
    """Собственная обёртка над списком с набором методов."""

    def __init__(self, items=None):
        self.items = list(items) if items else []

    def add(self, x):                           # добавить в конец
        self.items.append(x)

    def insert_at(self, index, x):              # вставить по индексу
        self.items.insert(index, x)

    def remove_value(self, x):                  # удалить все вхождения значения
        self.items = [i for i in self.items if i != x]

    def reverse(self):                          # развернуть список
        self.items = self.items[::-1]

    def unique(self):                           # убрать дубликаты, сохранив порядок
        seen, result = set(), []
        for i in self.items:
            if i not in seen:
                seen.add(i)
                result.append(i)
        self.items = result

    def max(self):
        return max(self.items) if self.items else None

    def sum(self):
        return sum(self.items)

    def sort(self, descending=False):
        self.items.sort(reverse=descending)

    def __len__(self):
        return len(self.items)

    def __str__(self):
        return f"List({self.items})"


def demo_list():
    lst = List([5, 3, 5, 1, 3])
    print(lst, "длина:", len(lst))
    lst.add(9); lst.insert_at(0, 7)
    print("после add(9), insert_at(0, 7):", lst)
    lst.unique();              print("unique:", lst)
    lst.remove_value(3);       print("remove_value(3):", lst)
    lst.sort(descending=True); print("sort по убыванию:", lst)
    lst.reverse();             print("reverse:", lst)
    print("max =", lst.max(), ", sum =", lst.sum())


# ---------- Задание 2. Транспортные средства ----------
class Vehicle:
    """Базовый класс. speed - км/ч, price_per_km - BYN (бел. руб.) за км."""
    speed = 1
    price_per_km = 1

    def __init__(self, city_from, city_to, distance):
        self.city_from, self.city_to, self.distance = city_from, city_to, distance

    def way_of_moving(self):                    # переопределяется в наследниках
        return "неизвестно"

    def time(self):
        return self.distance / self.speed       # часы

    def cost(self):
        return self.distance * self.price_per_km

    def info(self):
        return (f"{self.__class__.__name__}: {self.city_from} -> {self.city_to}, {self.distance} км, "
                f"способ: {self.way_of_moving()}, время: {self.time():.1f} ч, стоимость: {self.cost():.2f} BYN")


class Plane(Vehicle):
    speed, price_per_km = 800, 0.45
    def way_of_moving(self): return "по воздуху"


class Train(Vehicle):
    speed, price_per_km = 90, 0.15
    def way_of_moving(self): return "по железной дороге"


class Car(Vehicle):
    speed, price_per_km = 70, 0.25
    def way_of_moving(self): return "по автомобильной дороге"


def save_report(trips, filename="trips.txt"):
    """Записывает информацию о поездках в файл."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            for t in trips:
                f.write(t.info() + "\n")
            f.write(f"Самая быстрая: {min(trips, key=Vehicle.time).info()}\n")
            f.write(f"Самая экономичная: {min(trips, key=Vehicle.cost).info()}\n")
    except OSError as e:
        print("Не удалось записать файл:", e)


def demo_vehicles():
    city_from, city_to, distance = "Минск", "Москва", 700
    trips = [Plane(city_from, city_to, distance), Train(city_from, city_to, distance),
             Car(city_from, city_to, distance)]
    for t in trips:
        print(t.info())
    print("Быстрее всего:", min(trips, key=Vehicle.time).__class__.__name__)
    print("Экономичнее всего:", min(trips, key=Vehicle.cost).__class__.__name__)
    save_report(trips)
    print("Отчёт записан в trips.txt")


# ---------- Задание 3. Площадь оклеиваемых стен ----------
def wall_area(length, width, height, windows=(), doors=()):
    """windows/doors - списки пар (ширина, высота). Пол и потолок не считаются."""
    walls = 2 * (length + width) * height
    holes = sum(w * h for w, h in windows) + sum(w * h for w, h in doors)
    if holes > walls:
        raise ValueError("площадь окон и дверей больше площади стен")
    return walls - holes


def demo_wall():
    try:
        l = float(input("Длина комнаты, м: "))
        w = float(input("Ширина комнаты, м: "))
        h = float(input("Высота комнаты, м: "))
        n_win = int(input("Количество окон: "))
        windows = [(float(input(f"  окно {i + 1} ширина: ")), float(input(f"  окно {i + 1} высота: ")))
                   for i in range(n_win)]
        n_door = int(input("Количество дверей: "))
        doors = [(float(input(f"  дверь {i + 1} ширина: ")), float(input(f"  дверь {i + 1} высота: ")))
                 for i in range(n_door)]
        print(f"Площадь для оклейки: {wall_area(l, w, h, windows, doors):.2f} м²")
    except ValueError as e:
        print("Ошибка ввода:", e)


# ---------- Задание 4. Собственный класс: банковский счёт ----------
class BankAccount:
    bank_name = "БеларусБанк"                       # атрибут класса
    accounts_count = 0

    def __init__(self, owner, balance=0):
        self.owner, self.balance = owner, balance
        BankAccount.accounts_count += 1

    # методы экземпляра
    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("сумма должна быть положительной")
        self.balance += amount

    def withdraw(self, amount):
        if amount > self.balance:
            raise ValueError("недостаточно средств")
        self.balance -= amount

    # метод класса: альтернативный конструктор
    @classmethod
    def from_string(cls, text):
        owner, balance = text.split(";")
        return cls(owner, float(balance))

    # статический метод: не использует ни self, ни cls
    @staticmethod
    def is_valid_amount(amount):
        return isinstance(amount, (int, float)) and amount > 0

    def __str__(self):
        return f"{self.bank_name}: {self.owner}, баланс {self.balance}"


def demo_bank():
    acc = BankAccount("Иван", 100)
    acc.deposit(50)
    print(acc)
    acc2 = BankAccount.from_string("Мария;300")
    print(acc2)
    print("Сумма 20 корректна?", BankAccount.is_valid_amount(20), "| -5 корректна?", BankAccount.is_valid_amount(-5))
    try:
        acc.withdraw(1000)
    except ValueError as e:
        print("Ошибка:", e)
    print("Создано счетов:", BankAccount.accounts_count)


if __name__ == "__main__":
    tasks = {"1": demo_list, "2": demo_vehicles, "3": demo_wall, "4": demo_bank}
    while True:
        n = input("\nНомер задания (1-4, 0 - выход): ").strip()
        if n == "0":
            break
        tasks.get(n, lambda: print("Нет такого задания"))()
