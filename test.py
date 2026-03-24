import os

desktop_path = r"C:\Users\Daria\OneDrive\Desktop\аисд"

files = [
    ('enwik7', os.path.join(desktop_path, 'enwik7')),
    ('binary_file', os.path.join(desktop_path, 'Бинарный файл.exe')),
    ('russian_text', os.path.join(desktop_path, 'Русский текст.txt')),
    ('bw_raw', os.path.join(desktop_path, 'чб', 'bw.raw')),
    ('gray_raw', os.path.join(desktop_path, 'серое', 'gray.raw')),
    ('color_raw', os.path.join(desktop_path, 'цветное', 'color.raw')),
]

print("Имена файлов:")
for name, path in files:
    exists = "есть" if os.path.exists(path) else "нет"
    print(f"  '{name}' -> {exists}")