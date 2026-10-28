"""ЛР1, часть 2 (функции и исключения). Вариант 15."""
import ast


# ---------- Задание 1. n-е простое число ----------
def prime(n):
    """Возвращает n-е простое число (prime(1) == 2)."""
    try:
        if not isinstance(n, int) or n < 1:
            raise ValueError("номер должен быть натуральным числом")
        found = []                              # уже найденные простые
        candidate = 2
        while len(found) < n:
            # достаточно делить на найденные простые не больше sqrt(candidate)
            if all(candidate % p for p in found if p * p <= candidate):
                found.append(candidate)
            candidate += 1
        return found[-1]
    except ValueError as e:
        print("Ошибка:", e)
    finally:
        pass                                    # здесь можно освобождать ресурсы


# ---------- Задание 2. Функция, зависящая от типа аргумента ----------
def universal(arg):
    try:
        if isinstance(arg, bool):
            raise TypeError("bool не поддерживается")
        if isinstance(arg, list):
            evens = sum(1 for x in arg if x % 2 == 0)
            print("Чётных чисел:", evens)
            print("Максимум:", max(arg))
            return [x for x in arg if x >= 0]   # без отрицательных
        if isinstance(arg, dict):
            return dict(sorted(arg.items(), key=lambda kv: kv[1], reverse=True))
        if isinstance(arg, int):
            sign = "-" if arg < 0 else ""
            return int(sign + str(abs(arg))[::-1])
        if isinstance(arg, str):
            counts = {}
            for ch in arg:
                counts[ch] = counts.get(ch, 0) + 1
            return counts
        raise TypeError(f"тип {type(arg).__name__} не поддерживается")
    except (TypeError, ValueError) as e:
        print("Ошибка:", e)
    finally:
        print("--- вызов universal завершён ---")


# ---------- Задание 3. Первый полностью отрицательный столбец ----------
def first_negative_column(matrix):
    try:
        cols = len(matrix[0])
        for j in range(cols):
            column = [row[j] for row in matrix]
            if all(x < 0 for x in column):
                return j, sum(column) / len(column)
        return None
    except (IndexError, TypeError) as e:
        print("Ошибка в матрице:", e)
    finally:
        print("--- поиск столбца завершён ---")


def read_matrix():
    n, m = int(input("Строк: ")), int(input("Столбцов: "))
    return [[float(x) for x in input(f"Строка {i + 1} ({m} чисел через пробел): ").split()]
            for i in range(n)]


# ---------- Задание 4. Демонстрация try/except/else/finally ----------
def demo_try():
    for a, b in [(10, 2), (5, 0), ("x", 3)]:
        try:
            print(f"Делим {a} на {b}")
            result = a / b
        except ZeroDivisionError:
            print("  Нельзя делить на ноль")
        except TypeError as e:
            print("  Неверный тип:", e)
        else:                                   # выполняется, если исключения не было
            print("  Результат:", result)
        finally:                                # выполняется всегда
            print("  finally: итерация закончена")
    try:
        open("no_such_file.txt")
    except FileNotFoundError as e:
        print("Файл не найден:", e.filename)


# ---------- Запуск заданий с вводом (меню, как в части 1) ----------
def run1():
    raw = input("Номер простого числа n: ").strip()
    try:
        n = int(raw)
    except ValueError:
        n = raw                                 # prime сама сообщит об ошибке
    print("prime(n) =", prime(n))


def run2():
    print("Введите значение: список [3, -4, 8], словарь {'a': 3, 'b': 10},")
    print("целое число 12345 или строку в кавычках 'hello' (можно и 3.5 - проверка ошибки)")
    try:
        value = ast.literal_eval(input("> ").strip())
    except (ValueError, SyntaxError):
        print("Не удалось разобрать ввод (строки пишите в кавычках)")
        return
    print("Результат:", universal(value))


def run3():
    if input("Ввести свою матрицу? (y/n, n - пример): ").strip().lower() == "y":
        try:
            matrix = read_matrix()
        except ValueError:
            print("Нужно вводить числа.")
            return
    else:
        matrix = [[1, -2, -3], [4, -5, 6], [-7, -8, -9]]
        print("Матрица:", matrix)
    print("Результат (номер столбца, среднее):", first_negative_column(matrix))


if __name__ == "__main__":
    tasks = {"1": run1, "2": run2, "3": run3, "4": demo_try}
    while True:
        n = input("\nНомер задания (1-4, 0 - выход): ").strip()
        if n == "0":
            break
        tasks.get(n, lambda: print("Нет такого задания"))()
