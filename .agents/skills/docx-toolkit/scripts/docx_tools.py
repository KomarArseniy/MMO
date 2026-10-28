#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docx_tools.py
Инструмент для работы с файлами Microsoft Word (.docx):
- Получение сведений о структуре и свойствах документа
- Извлечение текста и таблиц
- Создание отчетов по стандарту БГУИР СТП 01-2017 / 01-2024 в формате DOCX
- Конвертация Markdown в оформленный DOCX
"""

import sys
import os
import re
import argparse
from pathlib import Path
import docx
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def get_docx_info(docx_path: Path):
    """Выводит информацию о документе docx."""
    if not docx_path.exists():
        print(f"[ERROR] Файл не найден: {docx_path}")
        return False
    doc = docx.Document(str(docx_path))
    num_paragraphs = len(doc.paragraphs)
    num_tables = len(doc.tables)

    total_words = 0
    for p in doc.paragraphs:
        total_words += len(p.text.split())
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                total_words += len(cell.text.split())

    print("=" * 60)
    print(f"Информация о DOCX: {docx_path.name}")
    print("=" * 60)
    print(f"Размер файла:      {docx_path.stat().st_size:,} байт ({docx_path.stat().st_size / 1024:.1f} КБ)")
    print(f"Параграфов:        {num_paragraphs}")
    print(f"Таблиц:            {num_tables}")
    print(f"Примерно слов:     {total_words}")

    # Размеры полей первой секции
    sec = doc.sections[0]
    print(f"Поля:")
    print(f"  Левое:   {sec.left_margin.cm:.1f} см")
    print(f"  Правое:  {sec.right_margin.cm:.1f} см")
    print(f"  Верхнее: {sec.top_margin.cm:.1f} см")
    print(f"  Нижнее:  {sec.bottom_margin.cm:.1f} см")
    print("=" * 60)
    return True

def extract_text(docx_path: Path, output_txt: Path = None):
    """Извлекает текст из документа docx, включая таблицы."""
    doc = docx.Document(str(docx_path))
    lines = []

    for p in doc.paragraphs:
        if p.text.strip():
            lines.append(p.text)

    if doc.tables:
        lines.append("\n--- ТАБЛИЦЫ ---")
        for idx, t in enumerate(doc.tables, start=1):
            lines.append(f"\n[Таблица {idx}]")
            for row in t.rows:
                row_text = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                lines.append(" | ".join(row_text))

    full_text = "\n".join(lines)
    if output_txt:
        output_txt.write_text(full_text, encoding="utf-8")
        print(f"[OK] Текст извлечен в файл: {output_txt}")
    else:
        print(full_text)
    return True

def apply_stp_section_settings(section):
    """Применяет поля формата А4 по стандарту БГУИР СТП 01-2017/2024."""
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3.0)    # 30 мм
    section.right_margin = Cm(1.5)   # 15 мм
    section.top_margin = Cm(2.0)     # 20 мм
    section.bottom_margin = Cm(2.0)  # 20 мм
    section.footer_distance = Cm(1.0) # 10 мм от нижнего края

def add_stp_paragraph(doc, text="", bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True, space_after=0):
    """Добавляет абзац по правилам СТП (Times New Roman 14pt, интервал 1.0, отступ 1.25 см)."""
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)

    if indent:
        p.paragraph_format.first_line_indent = Cm(1.25)
    else:
        p.paragraph_format.first_line_indent = Cm(0)

    if text:
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(14)
        run.bold = bold
        run.italic = italic
        # Обеспечение кириллического шрифта в схеме XML
        rPr = run._r.get_or_add_rPr()
        rFonts = parse_xml(r'<w:rFonts %s w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>' % nsdecls('w'))
        rPr.append(rFonts)

    return p

def add_stp_heading(doc, text, is_numbered=True):
    """Добавляет заголовок раздела по СТП."""
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(18)

    if is_numbered:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(1.25)
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)

    run = p.add_run(text.upper() if is_numbered else text.upper())
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)
    run.bold = True
    rPr = run._r.get_or_add_rPr()
    rFonts = parse_xml(r'<w:rFonts %s w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>' % nsdecls('w'))
    rPr.append(rFonts)
    return p

def create_stp_report(output_docx: Path, config: dict):
    """Создает полноценный отчет по лабораторной работе в DOCX по стандарту БГУИР СТП 01-2017/2024."""
    doc = docx.Document()
    sec = doc.sections[0]
    apply_stp_section_settings(sec)

    # 1. ТИТУЛЬНЫЙ ЛИСТ
    tp = config.get("title_page", {})
    faculty = tp.get("faculty", "Факультет компьютерных систем и сетей")
    dept = tp.get("department", "Кафедра программного обеспечения информационных технологий")
    subject = tp.get("subject", "Основы алгоритмизации и программирования")
    lab_num = tp.get("lab_number", 1)
    lab_topic = tp.get("lab_topic", "Разработка разветвляющихся и циклических алгоритмов")
    variant = tp.get("variant", 1)
    student = tp.get("student", "Иванов И. И.")
    group = tp.get("group", "150501")
    teacher_role = tp.get("teacher_role", "старший преподаватель")
    teacher = tp.get("teacher", "Петров П. П.")
    city = tp.get("city", "Минск")
    year = tp.get("year", 2026)

    # Шапка титульного листа
    p = add_stp_paragraph(doc, "МИНИСТЕРСТВО ОБРАЗОВАНИЯ РЕСПУБЛИКИ БЕЛАРУСЬ", bold=False, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    p.runs[0].font.size = Pt(12)
    p = add_stp_paragraph(doc, "УЧРЕЖДЕНИЕ ОБРАЗОВАНИЯ", bold=False, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    p.runs[0].font.size = Pt(12)
    p = add_stp_paragraph(doc, "«БЕЛОРУССКИЙ ГОСУДАРСТВЕННЫЙ УНИВЕРСИТЕТ ИНФОРМАТИКИ И РАДИОЭЛЕКТРОНИКИ»", bold=False, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    p.runs[0].font.size = Pt(12)
    p = add_stp_paragraph(doc, faculty, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    p.runs[0].font.size = Pt(12)
    p = add_stp_paragraph(doc, dept, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    p.runs[0].font.size = Pt(12)

    for _ in range(3):
        add_stp_paragraph(doc, "", indent=False)

    # Название работы
    add_stp_paragraph(doc, "ОТЧЕТ", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_stp_paragraph(doc, f"по лабораторной работе № {lab_num}", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_stp_paragraph(doc, f"по дисциплине «{subject}»", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_stp_paragraph(doc, f"на тему: «{lab_topic}»", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_stp_paragraph(doc, f"Вариант № {variant}", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)

    for _ in range(3):
        add_stp_paragraph(doc, "", indent=False)

    # Блок исполнителя и преподавателя (справа)
    p_sign = add_stp_paragraph(doc, indent=False, align=WD_ALIGN_PARAGRAPH.RIGHT)
    r1 = p_sign.add_run("Выполнил(а):\n")
    r1.bold = True
    p_sign.add_run(f"студент(ка) гр. {group}\n{student}\n\n")
    r2 = p_sign.add_run("Проверил:\n")
    r2.bold = True
    p_sign.add_run(f"{teacher_role}\n{teacher}")
    for run in p_sign.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(14)

    for _ in range(4):
        add_stp_paragraph(doc, "", indent=False)

    add_stp_paragraph(doc, f"{city} {year}", align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)

    # Разрыв раздела (титульный лист без номера, далее со 2-й страницы)
    new_sec = doc.add_section()
    apply_stp_section_settings(new_sec)

    # 2. ЦЕЛЬ РАБОТЫ
    add_stp_heading(doc, "1 ЦЕЛЬ РАБОТЫ")
    goal = config.get("goal", "Изучение теоретических основ и приобретение практических навыков реализации заданного алгоритма.")
    add_stp_paragraph(doc, goal)

    # 3. ТЕОРИЯ (не более 4 страниц!)
    add_stp_heading(doc, "2 КРАТКИЕ ТЕОРЕТИЧЕСКИЕ СВЕДЕНИЯ")
    theory = config.get("theory", "")
    theory_file = config.get("theory_file")
    if theory_file and Path(theory_file).exists():
        theory = Path(theory_file).read_text(encoding="utf-8")
    for para in theory.split("\n\n"):
        p_clean = para.strip().replace("\n", " ")
        if p_clean:
            add_stp_paragraph(doc, p_clean)

    # 4. ИНДИВИДУАЛЬНОЕ ЗАДАНИЕ
    add_stp_heading(doc, "3 ФОРМУЛИРОВКА ИНДИВИДУАЛЬНОГО ЗАДАНИЯ")
    add_stp_paragraph(doc, f"В соответствии с вариантом № {variant} поставлена следующая задача:")
    task = config.get("task", f"Разработать алгоритм и программу для варианта № {variant}.")
    task_file = config.get("task_file")
    if task_file and Path(task_file).exists():
        task = Path(task_file).read_text(encoding="utf-8")
    for para in task.split("\n\n"):
        p_clean = para.strip().replace("\n", " ")
        if p_clean:
            add_stp_paragraph(doc, p_clean)

    # 5. КОД РЕШЕНИЯ
    add_stp_heading(doc, "4 КОД РЕШЕНИЯ ИНДИВИДУАЛЬНОГО ЗАДАНИЯ")
    add_stp_paragraph(doc, "Ниже приведен полный исходный код разработанной программы решения индивидуального задания.")

    code_items = config.get("code_files", [])
    for c in code_items:
        c_path = Path(c.get("path", ""))
        caption = c.get("caption", f"Исходный код программы ({c_path.name})")
        add_stp_paragraph(doc, caption, bold=True, indent=True, space_after=6)

        code_text = ""
        if c_path.exists():
            code_text = c_path.read_text(encoding="utf-8")
        elif "code" in c:
            code_text = c["code"]

        if code_text:
            for line in code_text.splitlines():
                p_code = doc.add_paragraph()
                p_code.paragraph_format.line_spacing = 1.0
                p_code.paragraph_format.space_before = Pt(0)
                p_code.paragraph_format.space_after = Pt(0)
                p_code.paragraph_format.first_line_indent = Cm(0)
                p_code.alignment = WD_ALIGN_PARAGRAPH.LEFT

                r_text = p_code.add_run(line if line else " ")
                r_text.font.name = "Courier New"
                r_text.font.size = Pt(13)
                r_text.font.color.rgb = RGBColor(0, 0, 0)
                rPr = r_text._r.get_or_add_rPr()
                rFonts = parse_xml(r'<w:rFonts %s w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New"/>' % nsdecls('w'))
                rPr.append(rFonts)

            add_stp_paragraph(doc, "", indent=False)


    # 6. СКРИНШОТЫ
    add_stp_heading(doc, "5 РЕЗУЛЬТАТЫ ВЫПОЛНЕНИЯ ИНДИВИДУАЛЬНОГО ЗАДАНИЯ")
    add_stp_paragraph(doc, "Работоспособность алгоритма и правильность выполнения программы подтверждаются результатами тестирования на контрольных наборах данных.")

    screenshots = config.get("screenshots", [])
    for idx, s in enumerate(screenshots, start=1):
        s_path = Path(s.get("path", ""))
        caption = s.get("caption", f"Результаты выполнения программы (тест {idx})").strip().rstrip('.')

        add_stp_paragraph(doc, f"На рисунке {idx} представлен результат выполнения программы при тестировании.")

        if s_path.exists():
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.first_line_indent = Cm(0)
            p_img.paragraph_format.space_before = Pt(12)
            p_img.paragraph_format.space_after = Pt(6)
            run_img = p_img.add_run()
            run_img.add_picture(str(s_path), width=Cm(15.0))

        # Подпись по СТП: Рисунок 1 – Подпись (по центру, без точки)
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.first_line_indent = Cm(0)
        p_cap.paragraph_format.space_after = Pt(18)
        run_cap = p_cap.add_run(f"Рисунок {idx} – {caption}")
        run_cap.font.name = "Times New Roman"
        run_cap.font.size = Pt(14)

    # 7. ВЫВОДЫ
    add_stp_heading(doc, "6 ВЫВОДЫ")
    conclusions = config.get("conclusions", [])
    if isinstance(conclusions, list):
        for idx, item in enumerate(conclusions, start=1):
            add_stp_paragraph(doc, f"{idx}. {item}")
    else:
        add_stp_paragraph(doc, str(conclusions))

    output_docx.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_docx))
    print(f"[SUCCESS] Документ DOCX по СТП успешно создан: {output_docx}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Инструмент для работы с DOCX (python-docx)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # info
    p_info = subparsers.add_parser("info", help="Информация о документе DOCX")
    p_info.add_argument("docx", type=str, help="Путь к файлу docx")

    # extract
    p_ext = subparsers.add_parser("extract", help="Извлечь текст из DOCX")
    p_ext.add_argument("docx", type=str, help="Путь к файлу docx")
    p_ext.add_argument("-o", "--output", type=str, help="Файл для сохранения текста")

    # create-stp
    p_stp = subparsers.add_parser("create-stp", help="Создать отчет по СТП в DOCX")
    p_stp.add_argument("-c", "--config", type=str, required=True, help="Путь к YAML/JSON конфигу отчета")
    p_stp.add_argument("-o", "--output", type=str, required=True, help="Выходной docx файл")

    args = parser.parse_args()

    if args.command == "info":
        get_docx_info(Path(args.docx))
    elif args.command == "extract":
        extract_text(Path(args.docx), Path(args.output) if args.output else None)
    elif args.command == "create-stp":
        cfg_path = Path(args.config)
        import yaml
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        create_stp_report(Path(args.output), cfg)

if __name__ == "__main__":
    main()
