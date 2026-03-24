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


def huffman_encode(data: bytes, probabilities: dict):
    """
    Кодирование Хаффмана

    Входные данные:
        data - байтовая строка для кодирования
        probabilities - вероятностная модель {symbol: probability}
                        probability от 0 до 1, сумма = 1
    Выходные данные:
        encoded_data - закодированная байтовая строка
        codes - словарь кодов {symbol: code}
        padding - количество добавленных битов
    """
    if not data:
        return b'', {}, 0

    # Преобразуем вероятности в частоты для построения дерева
    scale = 1000000
    freq = {}
    for symbol, prob in probabilities.items():
        if prob > 0:
            freq[symbol] = int(prob * scale)

    # Добавляем символы из данных, которых нет в модели
    for symbol in set(data):
        if symbol not in freq:
            freq[symbol] = 1

    tree = build_huffman_tree(freq)
    codes = generate_codes(tree)

    result = bytearray()
    buffer = 0
    bit_count = 0

    for byte in data:
        code = codes[byte]
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

    return bytes(result), codes, padding


def huffman_decode(encoded_data: bytes, codes: dict, padding: int):
    if not encoded_data:
        return b''

    reverse_codes = {code: symbol for symbol, code in codes.items()}

    bits = []
    for i, byte in enumerate(encoded_data):
        if i == len(encoded_data) - 1 and padding > 0:
            bits.append(format(byte, '08b')[:8 - padding])
        else:
            bits.append(format(byte, '08b'))

    bits_str = ''.join(bits)

    result = bytearray()
    current_code = ''

    for bit in bits_str:
        current_code += bit
        if current_code in reverse_codes:
            result.append(reverse_codes[current_code])
            current_code = ''

    return bytes(result)


def save_codes_to_bytes(codes: dict):
    result = bytearray()
    result.extend(struct.pack('>H', len(codes)))

    for symbol, code in codes.items():
        result.append(symbol)
        code_len = len(code)
        result.append(code_len)
        code_value = int(code, 2)
        code_bytes = code_value.to_bytes((code_len + 7) // 8, 'big')
        result.extend(code_bytes)

    return bytes(result)


def load_codes_from_bytes(data: bytes):
    codes = {}
    pos = 0
    num_symbols = struct.unpack('>H', data[pos:pos + 2])[0]
    pos += 2

    for _ in range(num_symbols):
        symbol = data[pos]
        code_len = data[pos + 1]
        pos += 2
        code_bytes_len = (code_len + 7) // 8
        code_bytes = data[pos:pos + code_bytes_len]
        code_value = int.from_bytes(code_bytes, 'big')
        code_bits = bin(code_value)[2:].zfill(code_len)
        codes[symbol] = code_bits
        pos += code_bytes_len

    return codes


def huffman_compress_file(input_path: str, output_path: str, probabilities: dict):
    with open(input_path, 'rb') as f:
        data = f.read()

    original_size = len(data)
    encoded_data, codes, padding = huffman_encode(data, probabilities)

    codes_data = save_codes_to_bytes(codes)

    with open(output_path, 'wb') as f:
        f.write(bytes([padding]))
        f.write(struct.pack('>I', len(codes_data)))
        f.write(codes_data)
        f.write(encoded_data)

    compressed_size = len(codes_data) + len(encoded_data) + 5
    ratio = compressed_size / original_size if original_size > 0 else 0

    return original_size, compressed_size, ratio, codes, len(codes_data)


def huffman_decompress_file(input_path: str, output_path: str):
    with open(input_path, 'rb') as f:
        padding = f.read(1)[0]
        codes_len = struct.unpack('>I', f.read(4))[0]
        codes_data = f.read(codes_len)
        encoded_data = f.read()

    codes = load_codes_from_bytes(codes_data)
    decoded_data = huffman_decode(encoded_data, codes, padding)

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

    print("ХАФФМАН")
    print(f"{'Файл':<25} {'Исходный':>12} {'Сжатый':>12} {'Словарь':>12} {'Коэффициент':>12} {'Статус':>12}")
    print("-" * 120)

    results = []

    for name, path in files_to_test:
        if not os.path.exists(path):
            print(f"{name:<25} {'НЕ НАЙДЕН':<60}")
            continue

        try:
            # Сначала читаем данные для построения модели
            with open(path, 'rb') as f:
                data = f.read()

            # Строим вероятностную модель из данных
            probabilities = build_probabilities_from_data(data)

            original_size, compressed_size, ratio, codes, dict_size = huffman_compress_file(
                path,
                os.path.join(huffman_folder, f"{name}_huffman.bin"),
                probabilities
            )

            decoded_size = huffman_decompress_file(
                os.path.join(huffman_folder, f"{name}_huffman.bin"),
                os.path.join(huffman_folder, f"{name}_huffman_decoded")
            )

            with open(path, 'rb') as f1, open(os.path.join(huffman_folder, f"{name}_huffman_decoded"), 'rb') as f2:
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
                'num_codes': len(codes)
            })

        except Exception as e:
            print(f"{name:<25} {'ОШИБКА: ' + str(e)[:50]:<60}")






if __name__ == "__main__":
    main()