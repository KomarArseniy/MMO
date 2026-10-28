---
name: pdf-toolkit
description: >-
  Inspects, extracts text from, merges, splits, rotates, and converts images to PDF documents.
  Use this skill whenever the user asks to read, analyze, extract text from, split, merge, rotate, or manipulate PDF files.
---

# PDF Toolkit

Универсальный инструмент для работы с PDF документами на базе библиотеки `pypdf` и `Pillow`.

---

## 1. Возможности и команды

Все операции выполняются через скрипт `scripts/pdf_tools.py`:

### Получение информации о PDF
Выводит количество страниц, размер в байтах и миллиметрах (определяет формат A4 книжный/альбомный), метаданные и статус шифрования:
```powershell
python <path_to_skill>/scripts/pdf_tools.py info document.pdf
```

### Извлечение текста
Извлечь весь текст документа:
```powershell
python <path_to_skill>/scripts/pdf_tools.py extract document.pdf -o extracted.txt
```
Извлечь только указанные страницы (например, страницы 1, 2, 3 и 5):
```powershell
python <path_to_skill>/scripts/pdf_tools.py extract document.pdf -p "1-3,5" -o extracted.txt
```

### Объединение нескольких PDF в один (Merge)
```powershell
python <path_to_skill>/scripts/pdf_tools.py merge -o combined.pdf part1.pdf part2.pdf part3.pdf
```

### Разделение PDF на части (Split)
Разбить по диапазонам страниц:
```powershell
python <path_to_skill>/scripts/pdf_tools.py split input.pdf -o ./output_folder -r "1-3,4-7,8"
```
Разбить на отдельные страницы (по 1 странице в файл):
```powershell
python <path_to_skill>/scripts/pdf_tools.py split input.pdf -o ./output_folder
```

### Поворот страниц (Rotate)
Повернуть весь документ или отдельные страницы на 90, 180 или 270 градусов:
```powershell
python <path_to_skill>/scripts/pdf_tools.py rotate input.pdf -o rotated.pdf -a 90 -p "2-4"
```

### Конвертация изображений в PDF (img2pdf)
Собрать скриншоты или фотографии в единый многостраничный PDF:
```powershell
python <path_to_skill>/scripts/pdf_tools.py img2pdf -o screenshots.pdf screen1.png screen2.png screen3.jpg
```
