"""
Исследование зависимости энтропии от размера блока BWT+MTF
"""

import os
import sys
import math
from collections import Counter
import matplotlib.pyplot as plt

sys.path.insert(0, r"C:\Users\Daria\OneDrive\Desktop\аисд\lab1")
from bwt import bwt_encode_blocks


def calculate_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counter = Counter(data)
    n = len(data)
    entropy = 0.0
    for count in counter.values():
        p = count / n
        entropy -= p * math.log2(p)
    return entropy


def mtf_encode(data: bytes) -> bytes:
    dictionary = list(range(256))
    result = []
    for byte in data:
        idx = dictionary.index(byte)
        result.append(idx)
        dictionary.pop(idx)
        dictionary.insert(0, byte)
    return bytes(result)


def main():
    base_path = r"C:\Users\Daria\OneDrive\Desktop\аисд"
    file_path = os.path.join(base_path, "Русский текст.txt")

    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return

    with open(file_path, 'rb') as f:
        data = f.read()

    block_sizes = [256, 512, 1024, 2048, 4096, 8192, 16384]

    print("="*70)
    print("ИССЛЕДОВАНИЕ ЭНТРОПИИ ПОСЛЕ BWT+MTF")
    print("Русский текст")
    print("="*70)
    print(f"Размер файла: {len(data):,} байт")
    print()

    # Исходная энтропия
    original_entropy = calculate_entropy(data)
    print(f"Исходная энтропия: {original_entropy:.4f} бит/символ")
    print()

    # Таблица
    print(f"{'Размер блока (байт)':<20} {'Энтропия после BWT+MTF':>25} {'Изменение':>12}")
    print("-"*60)

    results = []

    for bs in block_sizes:
        if bs > len(data):
            continue

        # BWT с блоками
        bwt_data, indices, block_sizes_list, is_bwt = bwt_encode_blocks(data, bs)

        # MTF
        mtf_data = mtf_encode(bwt_data)

        # Энтропия
        entropy = calculate_entropy(mtf_data)
        change = entropy - original_entropy

        print(f"{bs:<20} {entropy:>25.4f} {change:>+12.4f}")

        results.append({
            'block_size': bs,
            'entropy': entropy,
            'change': change
        })

    print("-"*60)

    # Оптимальный блок
    best = min(results, key=lambda x: x['entropy'])
    print(f"\n✅ Оптимальный размер блока: {best['block_size']} байт")
    print(f"   Энтропия: {best['entropy']:.4f} бит/символ")
    print(f"   Улучшение: {original_entropy - best['entropy']:.4f} бит/символ")

    # График
    plt.figure(figsize=(10, 6))
    block_sizes_plot = [r['block_size'] for r in results]
    entropies_plot = [r['entropy'] for r in results]

    plt.plot(block_sizes_plot, entropies_plot, marker='o', linewidth=2, markersize=8, color='blue')
    plt.axhline(y=original_entropy, color='red', linestyle='--', label=f'Исходная энтропия: {original_entropy:.4f}')

    plt.xlabel('Размер блока (байт)', fontsize=12)
    plt.ylabel('Энтропия (бит/символ)', fontsize=12)
    plt.title('Зависимость энтропии от размера блока BWT+MTF\n(русский текст)', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.xscale('log')
    plt.legend()
    plt.tight_layout()
    plt.savefig('bwt_mtf_entropy_russian.png', dpi=150)
    plt.show()

    print("\n📊 График сохранен: bwt_mtf_entropy_russian.png")


if __name__ == "__main__":
    main()