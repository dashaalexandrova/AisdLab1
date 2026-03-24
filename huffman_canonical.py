import os
import struct
from collections import Counter
import heapq


class HuffmanNode:
    def __init__(self, symbol=None, freq=0, left=None, right=None):
        self.symbol = symbol
        self.freq = freq
        self.left = left
        self.right = right

    def __lt__(self, other):
        return self.freq < other.freq

    def is_leaf(self):
        return self.left is None and self.right is None


def build_huffman_tree(frequencies):
    heap = []
    for symbol, freq in frequencies.items():
        heapq.heappush(heap, HuffmanNode(symbol=symbol, freq=freq))

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        parent = HuffmanNode(freq=left.freq + right.freq, left=left, right=right)
        heapq.heappush(heap, parent)

    return heap[0] if heap else None


def generate_codes(node, code="", codes=None):
    if codes is None:
        codes = {}
    if node is None:
        return codes
    if node.is_leaf():
        codes[node.symbol] = code
    else:
        generate_codes(node.left, code + "0", codes)
        generate_codes(node.right, code + "1", codes)
    return codes


def build_canonical_codes(code_lengths):
    """
    Построение канонических кодов Хаффмана по длинам кодов
    code_lengths: dict {symbol: code_length}
    возвращает: dict {symbol: canonical_code}
    """
    # Группируем символы по длине кода
    symbols_by_len = {}
    for symbol, length in code_lengths.items():
        if length not in symbols_by_len:
            symbols_by_len[length] = []
        symbols_by_len[length].append(symbol)

    # Сортируем символы в каждой группе
    for length in symbols_by_len:
        symbols_by_len[length].sort()

    # Генерируем канонические коды
    canonical_codes = {}
    current_code = 0

    for length in sorted(symbols_by_len.keys()):
        for symbol in symbols_by_len[length]:
            code_bits = format(current_code, 'b').zfill(length)
            canonical_codes[symbol] = code_bits
            current_code += 1
        current_code <<= 1

    return canonical_codes


def get_code_lengths(codes):
    """
    Получение длин кодов из словаря кодов
    codes: dict {symbol: code}
    возвращает: dict {symbol: code_length}
    """
    return {symbol: len(code) for symbol, code in codes.items()}


def huffman_encode_canonical(data: bytes, probabilities: dict):
    """
    Кодирование Хаффмана с использованием канонических кодов
    """
    if not data:
        return b'', {}, 0

    # Преобразуем вероятности в частоты
    scale = 1000000
    freq = {}
    for symbol, prob in probabilities.items():
        if prob > 0:
            freq[symbol] = int(prob * scale)

    for symbol in set(data):
        if symbol not in freq:
            freq[symbol] = 1

    # Строим дерево и получаем коды
    tree = build_huffman_tree(freq)
    codes = generate_codes(tree)

    # Получаем длины кодов и строим канонические коды
    code_lengths = get_code_lengths(codes)
    canonical_codes = build_canonical_codes(code_lengths)

    # Кодируем данные каноническими кодами
    result = bytearray()
    buffer = 0
    bit_count = 0

    for byte in data:
        code = canonical_codes[byte]
        for bit in code:
            buffer = (buffer << 1) | int(bit)
            bit_count += 1
            if bit_count == 8:
                result.append(buffer)
                buffer = 0
                bit_count = 0

    if bit_count > 0:
        buffer = buffer << (8 - bit_count)
        result.append(buffer)
        padding = 8 - bit_count
    else:
        padding = 0

    return bytes(result), code_lengths, padding


def huffman_decode_canonical(encoded_data: bytes, code_lengths: dict, padding: int):
    """
    Декодирование канонических кодов Хаффмана
    """
    if not encoded_data:
        return b''

    # Восстанавливаем канонические коды из длин
    canonical_codes = build_canonical_codes(code_lengths)
    reverse_codes = {code: symbol for symbol, code in canonical_codes.items()}

    # Преобразуем байты в битовую строку
    bits = []
    for i, byte in enumerate(encoded_data):
        if i == len(encoded_data) - 1 and padding > 0:
            bits.append(format(byte, '08b')[:8 - padding])
        else:
            bits.append(format(byte, '08b'))

    bits_str = ''.join(bits)

    # Декодируем
    result = bytearray()
    current_code = ''

    for bit in bits_str:
        current_code += bit
        if current_code in reverse_codes:
            result.append(reverse_codes[current_code])
            current_code = ''

    return bytes(result)


def save_code_lengths_to_bytes(code_lengths: dict):
    """
    Сохранение только длин кодов (оптимизированные метаданные)
    Формат: [2 байта: количество символов]
            для каждого символа: [1 байт: символ] [1 байт: длина кода]
    """
    result = bytearray()
    result.extend(struct.pack('>H', len(code_lengths)))

    for symbol, length in code_lengths.items():
        result.append(symbol)
        result.append(length)

    return bytes(result)


def load_code_lengths_from_bytes(data: bytes):
    """
    Загрузка длин кодов из байтовой строки
    """
    code_lengths = {}
    pos = 0
    num_symbols = struct.unpack('>H', data[pos:pos + 2])[0]
    pos += 2

    for _ in range(num_symbols):
        symbol = data[pos]
        length = data[pos + 1]
        pos += 2
        code_lengths[symbol] = length

    return code_lengths


def huffman_compress_file_canonical(input_path: str, output_path: str, probabilities: dict):
    """
    Сжатие файла с каноническими кодами (оптимизированные метаданные)
    """
    with open(input_path, 'rb') as f:
        data = f.read()

    original_size = len(data)
    encoded_data, code_lengths, padding = huffman_encode_canonical(data, probabilities)

    # Сохраняем только длины кодов (вместо полного словаря)
    code_lengths_data = save_code_lengths_to_bytes(code_lengths)

    with open(output_path, 'wb') as f:
        f.write(bytes([padding]))
        f.write(struct.pack('>I', len(code_lengths_data)))
        f.write(code_lengths_data)
        f.write(encoded_data)

    compressed_size = len(code_lengths_data) + len(encoded_data) + 5
    ratio = compressed_size / original_size if original_size > 0 else 0

    return original_size, compressed_size, ratio, code_lengths, len(code_lengths_data)


def huffman_decompress_file_canonical(input_path: str, output_path: str):
    """
    Распаковка файла с каноническими кодами
    """
    with open(input_path, 'rb') as f:
        padding = f.read(1)[0]
        code_lengths_len = struct.unpack('>I', f.read(4))[0]
        code_lengths_data = f.read(code_lengths_len)
        encoded_data = f.read()

    code_lengths = load_code_lengths_from_bytes(code_lengths_data)
    decoded_data = huffman_decode_canonical(encoded_data, code_lengths, padding)

    with open(output_path, 'wb') as f:
        f.write(decoded_data)

    return len(decoded_data)


def build_probabilities_from_data(data: bytes):
    """Вспомогательная функция для построения модели из данных"""
    freq = Counter(data)
    total = len(data)
    return {symbol: count / total for symbol, count in freq.items()}


def main():
    desktop_path = r"C:\Users\Daria\OneDrive\Desktop\аисд"
    huffman_folder = os.path.join(desktop_path, 'huffman')
    if not os.path.exists(huffman_folder):
        os.makedirs(huffman_folder)

    files_to_test = [
        ('enwik7', os.path.join(desktop_path, 'enwik7')),
        ('russian_text', os.path.join(desktop_path, 'Русский текст.txt')),
        ('binary_file', os.path.join(desktop_path, 'Бинарный файл.exe')),
        ('bw_raw', os.path.join(desktop_path, 'чб', 'bw.raw')),
        ('gray_raw', os.path.join(desktop_path, 'серое', 'gray.raw')),
        ('color_raw', os.path.join(desktop_path, 'цветное', 'color.raw')),
    ]

    print("ХАФФМАН (КАНОНИЧЕСКИЕ КОДЫ)")
    print(f"{'Файл':<25} {'Исходный':>12} {'Сжатый':>12} {'Словарь':>12} {'Коэффициент':>12} {'Статус':>12}")
    print("-" * 120)

    results = []

    for name, path in files_to_test:
        if not os.path.exists(path):
            print(f"{name:<25} {'НЕ НАЙДЕН':<60}")
            continue

        try:
            with open(path, 'rb') as f:
                data = f.read()

            probabilities = build_probabilities_from_data(data)

            original_size, compressed_size, ratio, code_lengths, dict_size = huffman_compress_file_canonical(
                path,
                os.path.join(huffman_folder, f"{name}_huffman_canonical.bin"),
                probabilities
            )

            decoded_size = huffman_decompress_file_canonical(
                os.path.join(huffman_folder, f"{name}_huffman_canonical.bin"),
                os.path.join(huffman_folder, f"{name}_huffman_canonical_decoded")
            )

            with open(path, 'rb') as f1, open(os.path.join(huffman_folder, f"{name}_huffman_canonical_decoded"),
                                              'rb') as f2:
                is_valid = f1.read() == f2.read()

            status = "✓ OK" if is_valid else "✗ ОШИБКА"

            print(
                f"{name:<25} {original_size:>12,} {compressed_size:>12,} {dict_size:>12,} {ratio:>12.4f} {status:>12}")

            results.append({
                'name': name,
                'original': original_size,
                'compressed': compressed_size,
                'dict_size': dict_size,
                'ratio': ratio,
                'num_codes': len(code_lengths)
            })

        except Exception as e:
            print(f"{name:<25} {'ОШИБКА: ' + str(e)[:50]:<60}")

    print("\n\n" + "=" * 120)


    print("\n\n" + "=" * 120)
    print("СРАВНЕНИЕ РАЗМЕРА СЛОВАРЯ: СТАНДАРТНЫЙ vs КАНОНИЧЕСКИЙ")
    print("=" * 120)
    print()
    print("| Файл | Стандартный словарь (байт) | Канонический словарь (байт) | Экономия (байт) | Экономия (%) |")
    print("|------|---------------------------|----------------------------|----------------|--------------|")

    for r in results:
        # Для стандартного словаря: символ(1) + длина(1) + код(переменная)
        std_dict_size = 5
        # Оценка: в среднем код занимает (длина/8) байт
        std_dict_size += r['num_codes'] * (2 + 2)

        canon_dict_size = r['dict_size']
        savings = std_dict_size - canon_dict_size
        savings_percent = (savings / std_dict_size) * 100 if std_dict_size > 0 else 0

        print(
            f"| {r['name']} | {std_dict_size:>25,} | {canon_dict_size:>26,} | {savings:>14,} | {savings_percent:>12.1f}% |")

    print("\n" + "=" * 120)


if __name__ == "__main__":
    main()