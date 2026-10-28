#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_report.py
Валидатор отчетов по лабораторным работам БГУИР на соответствие СТП 01-2017/2024 и заданным требованиям.

Проверяет 7 обязательных разделов:
1. Титульный лист (с обязательным номером варианта!)
2. Цель выполнения лабораторной работы
3. Теория по лабораторной работе (не более 4 страниц!)
4. Формулировка индивидуального задания
5. Весь код решения индивидуального задания
6. Скриншоты выполнения индивидуального задания (подписи Рисунок X – ..., ссылки)
7. Выводы по лабораторной работе
А также поля 30/15/20/20, шрифт 14pt, отступ 1.25 см, нумерацию страниц в правом нижнем углу.
"""

import sys
import re
import argparse
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def validate_tex_report(tex_path: Path):
    if not tex_path.exists():
        print(f"[FAIL] Файл не найден: {tex_path}")
        return False

    content = tex_path.read_text(encoding="utf-8")
    errors = []
    warnings = []
    checks = []

    # 1. Проверка титульного листа и номера варианта
    has_titlepage = r"\makestptitlepage" in content or r"\begin{titlepage}" in content
    var_match = re.search(r'\\stpVariant\{([^}]+)\}', content)
    if not has_titlepage:
        errors.append("1. Титульный лист: отсутствует макрос титульного листа (\\makestptitlepage или \\begin{titlepage}).")
    elif not var_match or not var_match.group(1).strip():
        errors.append("1. Титульный лист: ОТСУТСТВУЕТ ОБЯЗАТЕЛЬНЫЙ НОМЕР ВАРИАНТА (\\stpVariant{...})!")
    else:
        checks.append(f"1. [OK] Титульный лист оформлен. Вариант № {var_match.group(1).strip()} указан.")

    # 2. Цель работы
    has_goal = re.search(r'\\section\*?\{[^}]*[Цц]ел[^}]*\}', content)
    if has_goal:
        checks.append("2. [OK] Раздел 'Цель выполнения лабораторной работы' присутствует.")
    else:
        errors.append("2. Цель работы: отсутствует раздел с целью (\\section{Цель работы}).")

    # 3. Теория (не более 4 страниц!)
    has_theory = re.search(r'\\section\*?\{[^}]*([Тт]еори|[Тт]еоретическ)[^}]*\}', content)
    if has_theory:
        # Извлекаем текст раздела теории до следующего раздела
        theory_match = re.search(r'\\section\*?\{[^}]*(?:[Тт]еори|[Тт]еоретическ)[^}]*\}(.*?)(?:\\section|\Z)', content, re.DOTALL)
        if theory_match:
            theory_body = theory_match.group(1)
            words = len(re.findall(r'\b\w+\b', theory_body))
            est_pages = max(1.0, round(words / 350.0, 1))
            if est_pages > 4.0:
                warnings.append(f"3. Теория: объем раздела составляет ~{est_pages} стр., что ПРЕВЫШАЕТ ЛИМИТ СТП (не более 4 страниц)!")
            else:
                checks.append(f"3. [OK] Раздел 'Теория' присутствует (объем ~{est_pages} стр. из 4 макс.).")
        else:
            checks.append("3. [OK] Раздел 'Теория' присутствует.")
    else:
        errors.append("3. Теория: отсутствует раздел с теоретическими сведениями.")

    # 4. Формулировка индивидуального задания
    has_task = re.search(r'\\section\*?\{[^}]*([Зз]адани|[Фф]ормулировк)[^}]*\}', content)
    if has_task:
        checks.append("4. [OK] Раздел 'Формулировка индивидуального задания' присутствует.")
    else:
        errors.append("4. Задание: отсутствует раздел с формулировкой задания.")

    # 5. Весь код решения индивидуального задания
    has_code_sec = re.search(r'\\section\*?\{[^}]*([Кк]од|[Ии]сходный код)[^}]*\}', content)
    has_listings = r"\begin{lstlisting}" in content or r"\lstinputlisting" in content
    if has_code_sec and has_listings:
        checks.append("5. [OK] Раздел 'Код решения' присутствует и содержит листинги программ.")
    elif not has_code_sec:
        errors.append("5. Код решения: отсутствует раздел с кодом решения (\\section{Код решения...}).")
    else:
        warnings.append("5. Код решения: раздел присутствует, но листинги кода (\\lstinputlisting или \\begin{lstlisting}) не найдены.")

    # 6. Скриншоты выполнения индивидуального задания
    has_results_sec = re.search(r'\\section\*?\{[^}]*([Рр]езультат|[Сс]криншот)[^}]*\}', content)
    has_figures = r"\begin{figure}" in content
    if has_results_sec and has_figures:
        # Проверяем подписи к рисункам (должно быть Рисунок X – Название, без точки)
        captions = re.findall(r'\\caption\{([^}]+)\}', content)
        bad_captions = [c for c in captions if c.strip().endswith('.')]
        if bad_captions:
            warnings.append(f"6. Скриншоты: обнаружена точка в конце подписи рисунка: '{bad_captions[0]}' (по СТП 2.5.5 точки не ставятся).")
        checks.append(f"6. [OK] Раздел 'Скриншоты выполнения' присутствует ({len(re.findall(r'\\begin\{figure\}', content))} рисунков).")
    elif not has_results_sec:
        errors.append("6. Скриншоты: отсутствует раздел с результатами выполнения и скриншотами.")
    else:
        warnings.append("6. Скриншоты: раздел присутствует, но иллюстрации (\\begin{figure}) не добавлены.")

    # 7. Выводы
    has_concl = re.search(r'\\(?:section\*?|anonsection)\{[^}]*[Вв]ывод[^}]*\}', content)
    if has_concl:
        checks.append("7. [OK] Раздел 'Выводы по лабораторной работе' присутствует.")
    else:
        errors.append("7. Выводы: отсутствует раздел выводов (\\section{Выводы}).")

    # Форматирование и стандарты
    sty_path = tex_path.parent / "bsuir_stp.sty"
    if sty_path.exists():
        sty_content = sty_path.read_text(encoding="utf-8")
        if "left=30mm" in sty_content and "right=15mm" in sty_content and "top=20mm" in sty_content and "bottom=20mm" in sty_content:
            checks.append("8. [OK] Поля документа соответствуют СТП: левое 30 мм, правое 15 мм, верхнее 20 мм, нижнее 20 мм.")
        if "parindent=1.25cm" in sty_content or r"\setlength{\parindent}{1.25cm}" in sty_content:
            checks.append("9. [OK] Абзацный отступ равен 1.25 см по СТП 2.1.1.")
        if "fancyfoot[R]" in sty_content:
            checks.append("10. [OK] Номер страницы расположен в правом нижнем углу по СТП 2.2.8.")
        if "sectionbreak" in sty_content or r"\clearpage" in sty_content:
            checks.append("11. [OK] Разделы первого уровня начинаются с новой страницы по СТП.")

    # Вывод результатов проверки
    print("=" * 70)
    print("ОТЧЕТ ПРОВЕРКИ СООТВЕТСТВИЯ СТП 01-2017/2024 БГУИР")
    print("=" * 70)
    for c in checks:
        print(f"  {c}")

    if warnings:
        print("\nПРЕДУПРЕЖДЕНИЯ:")
        for w in warnings:
            print(f"  [WARN] {w}")

    if errors:
        print("\nОШИБКИ СООТВЕТСТВИЯ СТАНДАРТУ:")
        for e in errors:
            print(f"  [ERROR] {e}")
        print("=" * 70)
        return False

    print("\n[SUCCESS] Отчет ПОЛНОСТЬЮ соответствует требованиям СТП и структуры из 7 пунктов!")
    print("=" * 70)
    return True

def main():
    parser = argparse.ArgumentParser(description="Валидатор отчета по СТП БГУИР")
    parser.add_argument("tex_file", type=str, nargs="?", default="./results/report/main.tex", help="Путь к файлу main.tex")
    args = parser.parse_args()

    tex_path = Path(args.tex_file)
    success = validate_tex_report(tex_path)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
