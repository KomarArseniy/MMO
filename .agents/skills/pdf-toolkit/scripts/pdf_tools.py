#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_tools.py
Универсальный инструмент для работы с PDF файлами:
- Информация о файле (метаданные, количество страниц, размер)
- Извлечение текста (постранично или целиком)
- Объединение (merge) нескольких PDF в один
- Разделение (split) PDF по диапазонам страниц или постранично
- Поворот страниц (rotate)
- Преобразование изображений (PNG, JPG) в единый PDF
- Наложение штампа / водяного знака
"""

import sys
import os
import argparse
from pathlib import Path
import pypdf
from PIL import Image

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def get_pdf_info(pdf_path: Path):
    """Выводит подробные сведения о PDF файле."""
    if not pdf_path.exists():
        print(f"[ERROR] Файл не найден: {pdf_path}")
        return False
    reader = pypdf.PdfReader(str(pdf_path))
    print("=" * 60)
    print(f"Информация о PDF: {pdf_path.name}")
    print("=" * 60)
    print(f"Полный путь:       {pdf_path.resolve()}")
    print(f"Размер файла:      {pdf_path.stat().st_size:,} байт ({pdf_path.stat().st_size / 1024:.1f} КБ)")
    print(f"Всего страниц:     {len(reader.pages)}")
    print(f"Зашифрован:        {'Да' if reader.is_encrypted else 'Нет'}")

    meta = reader.metadata
    if meta:
        print("\nМетаданные документа:")
        for k, v in meta.items():
            if v:
                print(f"  {k}: {v}")

    # Размеры первой страницы
    if len(reader.pages) > 0:
        box = reader.pages[0].mediabox
        w_pt, h_pt = float(box.width), float(box.height)
        w_mm = w_pt * 25.4 / 72.0
        h_mm = h_pt * 25.4 / 72.0
        print(f"\nРазмер 1-й страницы: {w_mm:.1f} x {h_mm:.1f} мм ({w_pt:.0f} x {h_pt:.0f} pt)")
        if abs(w_mm - 210) < 5 and abs(h_mm - 297) < 5:
            print("Формат: A4 (книжная ориентация)")
        elif abs(w_mm - 297) < 5 and abs(h_mm - 210) < 5:
            print("Формат: A4 (альбомная ориентация)")
    print("=" * 60)
    return True

def extract_text(pdf_path: Path, output_txt: Path = None, pages: str = None):
    """Извлекает текст из PDF документа."""
    reader = pypdf.PdfReader(str(pdf_path))
    total_pages = len(reader.pages)

    target_pages = []
    if pages:
        # Парсим диапазоны страниц, например "1-3,5"
        for part in pages.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-")
                target_pages.extend(range(int(start) - 1, min(int(end), total_pages)))
            else:
                p = int(part) - 1
                if 0 <= p < total_pages:
                    target_pages.append(p)
    else:
        target_pages = list(range(total_pages))

    extracted = []
    for idx in target_pages:
        page_text = reader.pages[idx].extract_text() or ""
        header = f"--- СТРАНИЦА {idx + 1} ---"
        extracted.append(f"{header}\n{page_text}\n")

    full_text = "\n".join(extracted)

    if output_txt:
        output_txt.write_text(full_text, encoding="utf-8")
        print(f"[OK] Текст извлечен в файл: {output_txt} ({len(target_pages)} страниц)")
    else:
        print(full_text)
    return True

def merge_pdfs(output_pdf: Path, input_pdfs: list):
    """Объединяет несколько PDF файлов в один."""
    writer = pypdf.PdfWriter()
    added_count = 0
    total_pages = 0

    for item in input_pdfs:
        p = Path(item)
        if not p.exists():
            print(f"[WARN] Пропуск отсутствующего файла: {p}")
            continue
        reader = pypdf.PdfReader(str(p))
        pages_in_file = len(reader.pages)
        for page in reader.pages:
            writer.add_page(page)
        added_count += 1
        total_pages += pages_in_file
        print(f"  + Добавлен: {p.name} ({pages_in_file} стр.)")

    if added_count == 0:
        print("[ERROR] Нет файлов для объединения!")
        return False

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with open(output_pdf, "wb") as f:
        writer.write(f)

    print(f"[SUCCESS] Объединено {added_count} файлов в {output_pdf} (всего {total_pages} стр.)")
    return True

def split_pdf(pdf_path: Path, output_dir: Path, ranges: str = None):
    """Разделяет PDF на отдельные файлы по страницам или диапазонам."""
    reader = pypdf.PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    output_dir.mkdir(parents=True, exist_ok=True)

    if ranges:
        # Например "1-2, 3-5"
        for idx, part in enumerate(ranges.split(","), start=1):
            part = part.strip()
            writer = pypdf.PdfWriter()
            if "-" in part:
                start, end = part.split("-")
                p_range = range(int(start) - 1, min(int(end), total_pages))
            else:
                p_range = [int(part) - 1]

            for p in p_range:
                if 0 <= p < total_pages:
                    writer.add_page(reader.pages[p])

            out_file = output_dir / f"{pdf_path.stem}_part{idx}.pdf"
            with open(out_file, "wb") as f:
                writer.write(f)
            print(f"[OK] Создана часть {out_file.name} (страницы {part})")
    else:
        # Постраничное разделение
        for i, page in enumerate(reader.pages, start=1):
            writer = pypdf.PdfWriter()
            writer.add_page(page)
            out_file = output_dir / f"{pdf_path.stem}_page{i}.pdf"
            with open(out_file, "wb") as f:
                writer.write(f)
            print(f"[OK] Страница {i}: {out_file.name}")

    print(f"[SUCCESS] Разделение завершено в папку: {output_dir}")
    return True

def rotate_pdf(pdf_path: Path, output_pdf: Path, angle: int, pages: str = None):
    """Поворачивает страницы PDF на 90, 180 или 270 градусов."""
    if angle not in [90, 180, 270]:
        print("[ERROR] Угол поворота должен быть 90, 180 или 270 градусов.")
        return False

    reader = pypdf.PdfReader(str(pdf_path))
    writer = pypdf.PdfWriter()
    total_pages = len(reader.pages)

    rotate_set = set()
    if pages:
        for part in pages.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-")
                rotate_set.update(range(int(start) - 1, min(int(end), total_pages)))
            else:
                rotate_set.add(int(part) - 1)
    else:
        rotate_set = set(range(total_pages))

    for idx, page in enumerate(reader.pages):
        if idx in rotate_set:
            page.rotate(angle)
        writer.add_page(page)

    with open(output_pdf, "wb") as f:
        writer.write(f)

    print(f"[SUCCESS] Файл повернут на {angle}° и сохранен в: {output_pdf}")
    return True

def images_to_pdf(output_pdf: Path, image_paths: list):
    """Преобразует список изображений в единый многостраничный PDF документ."""
    valid_images = []
    for p in image_paths:
        path = Path(p)
        if path.exists():
            img = Image.open(path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            valid_images.append(img)
        else:
            print(f"[WARN] Изображение не найдено: {path}")

    if not valid_images:
        print("[ERROR] Нет доступных изображений для создания PDF.")
        return False

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    first_img = valid_images[0]
    rest_images = valid_images[1:] if len(valid_images) > 1 else []

    first_img.save(str(output_pdf), "PDF", resolution=100.0, save_all=True, append_images=rest_images)
    print(f"[SUCCESS] Создан PDF из {len(valid_images)} изображений: {output_pdf}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Инструмент для работы с PDF (pypdf & PIL)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # info
    p_info = subparsers.add_parser("info", help="Информация о PDF файле")
    p_info.add_argument("pdf", type=str, help="Путь к PDF")

    # extract
    p_ext = subparsers.add_parser("extract", help="Извлечь текст из PDF")
    p_ext.add_argument("pdf", type=str, help="Путь к PDF")
    p_ext.add_argument("-o", "--output", type=str, help="Файл для сохранения текста")
    p_ext.add_argument("-p", "--pages", type=str, help="Страницы для извлечения (например: 1-3,5)")

    # merge
    p_merge = subparsers.add_parser("merge", help="Объединить несколько PDF")
    p_merge.add_argument("-o", "--output", type=str, required=True, help="Выходной PDF")
    p_merge.add_argument("inputs", nargs="+", help="Исходные PDF файлы")

    # split
    p_split = subparsers.add_parser("split", help="Разделить PDF")
    p_split.add_argument("pdf", type=str, help="Путь к PDF")
    p_split.add_argument("-o", "--out-dir", type=str, default="./split_pdf", help="Выходная папка")
    p_split.add_argument("-r", "--ranges", type=str, help="Диапазоны страниц (например: 1-2, 3-5)")

    # rotate
    p_rot = subparsers.add_parser("rotate", help="Повернуть страницы PDF")
    p_rot.add_argument("pdf", type=str, help="Путь к исходному PDF")
    p_rot.add_argument("-o", "--output", type=str, required=True, help="Выходной PDF")
    p_rot.add_argument("-a", "--angle", type=int, choices=[90, 180, 270], required=True, help="Угол поворота")
    p_rot.add_argument("-p", "--pages", type=str, help="Страницы для поворота (например: 1,3-5)")

    # img2pdf
    p_img = subparsers.add_parser("img2pdf", help="Собрать изображения в PDF")
    p_img.add_argument("-o", "--output", type=str, required=True, help="Выходной PDF")
    p_img.add_argument("images", nargs="+", help="Файлы изображений")

    args = parser.parse_args()

    if args.command == "info":
        get_pdf_info(Path(args.pdf))
    elif args.command == "extract":
        extract_text(Path(args.pdf), Path(args.output) if args.output else None, args.pages)
    elif args.command == "merge":
        merge_pdfs(Path(args.output), args.inputs)
    elif args.command == "split":
        split_pdf(Path(args.pdf), Path(args.out_dir), args.ranges)
    elif args.command == "rotate":
        rotate_pdf(Path(args.pdf), Path(args.output), args.angle, args.pages)
    elif args.command == "img2pdf":
        images_to_pdf(Path(args.output), args.images)

if __name__ == "__main__":
    main()
