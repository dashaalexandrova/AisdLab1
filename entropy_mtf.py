import os
import math
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.family'] = 'DejaVu Sans'


def calculate_entropy(data: bytes, symbol_bytes: int = 1) -> float:
    if not data:
        return 0.0

    step = symbol_bytes
    n = len(data) // step

    if n == 0:
        return 0.0

    symbols = []
    for i in range(0, len(data) - len(data) % step, step):
        symbols.append(data[i:i + step])

    counter = Counter(symbols)

    entropy = 0.0
    for count in counter.values():
        p = count / n
        entropy -= p * math.log2(p)

    return entropy


def mtf_encode(data: bytes) -> bytes:
    dictionary = list(range(256))
    result = []

    for byte in data:
        index = dictionary.index(byte)
        result.append(index)
        dictionary.pop(index)
        dictionary.insert(0, byte)

    return bytes(result)


def mtf_decode(data: bytes) -> bytes:
    dictionary = list(range(256))
    result = []

    for index in data:
        byte = dictionary[index]
        result.append(byte)
        dictionary.pop(index)
        dictionary.insert(0, byte)

    return bytes(result)


def filter_ascii_only(text: str) -> str:
    return ''.join(ch for ch in text if ord(ch) <= 127)


def analyze_entropy_english(desktop_path):
    enwik7_path = os.path.join(desktop_path, 'enwik7')

    if not os.path.exists(enwik7_path):
        print(f"Файл не найден: {enwik7_path}")
        return None, None

    with open(enwik7_path, 'rb') as f:
        raw_bytes = f.read()

    try:
        text = raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        text = raw_bytes.decode('latin-1')

    filtered_text = filter_ascii_only(text)
    filtered_bytes = filtered_text.encode('ascii')

    symbol_sizes = [1, 2, 3, 4]
    entropies = []

    for size in symbol_sizes:
        entropy = calculate_entropy(filtered_bytes, size)
        entropies.append(entropy)

    plt.figure(figsize=(10, 6))
    plt.plot(symbol_sizes, entropies, marker='o', linewidth=2, markersize=8, color='darkblue')
    plt.xlabel('Длина кода символа (байт)', fontsize=12)
    plt.ylabel('Энтропия (бит/символ)', fontsize=12)
    plt.title('Зависимость энтропии от длины кода символа', fontsize=14)
    plt.xticks([1, 2, 3, 4])
    plt.grid(True, alpha=0.3)

    for x, y in zip(symbol_sizes, entropies):
        plt.annotate(f'{y:.2f}', (x, y), textcoords="offset points", xytext=(0, 10), ha='center')

    plt.savefig('entropy_vs_symbol_length.png', dpi=150, bbox_inches='tight')
    plt.show()

    return entropies, filtered_bytes


def analyze_mtf_impact(desktop_path, filtered_english_bytes):
    test_files = [
        ('enwik7 (ASCII только)', filtered_english_bytes),
        ('enwik7 (оригинал)', os.path.join(desktop_path, 'enwik7')),
        ('Русский текст', os.path.join(desktop_path, 'Русский текст.txt')),
        ('Бинарный файл', os.path.join(desktop_path, 'Бинарный файл.exe')),
        ('ЧБ изображение RAW', os.path.join(desktop_path, 'чб', 'bw.raw')),
        ('Grayscale RAW', os.path.join(desktop_path, 'серое', 'gray.raw')),
        ('Цветной RAW', os.path.join(desktop_path, 'цветное', 'color.raw')),
    ]

    results = []

    for name, path in test_files:
        if name == 'enwik7 (ASCII только)':
            if filtered_english_bytes is None:
                continue
            data = filtered_english_bytes
        else:
            if not os.path.exists(path):
                continue
            with open(path, 'rb') as f:
                data = f.read()

        entropy_before = calculate_entropy(data, 1)
        mtf_data = mtf_encode(data)
        entropy_after = calculate_entropy(mtf_data, 1)
        change = entropy_after - entropy_before

        results.append({
            'name': name,
            'size': len(data),
            'entropy_before': entropy_before,
            'entropy_after': entropy_after,
            'change': change
        })

    return results


def print_summary_tables(entropies, mtf_results):

    print("Влияние MTF на энтропию")
    print()
    print("| Файл | Размер (байт) | Энтропия до MTF | Энтропия после MTF | Δ |")
    print("|------|---------------|-----------------|--------------------|---|")

    for r in mtf_results:
        print(
            f"| {r['name']:<30} | {r['size']:>11,} | {r['entropy_before']:>15.4f} | {r['entropy_after']:>18.4f} | {r['change']:>+8.4f} |")


def main():
    desktop_path = r"C:\Users\Daria\OneDrive\Desktop\аисд"

    entropies, filtered_english = analyze_entropy_english(desktop_path)

    if entropies is None:
        return

    mtf_results = analyze_mtf_impact(desktop_path, filtered_english)

    print_summary_tables(entropies, mtf_results)


if __name__ == "__main__":
    main()