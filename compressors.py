"""
compressors.py - Все компрессоры для лабораторной работы
"""

import os
import struct
import sys

# Добавляем путь к папке с файлами
sys.path.insert(0, r"C:\Users\Daria\OneDrive\Desktop\аисд\lab1")

# Импорты файлов
from rle_compressor import RLE

from bwt import bwt_encode_blocks, bwt_decode_blocks
# MTF функции
try:
    from entropy_mtf import mtf_encode, mtf_decode
except ImportError:
    # Простая реализация если нет
    def mtf_encode(data: bytes) -> bytes:
        dictionary = list(range(256))
        result = []
        for byte in data:
            idx = dictionary.index(byte)
            result.append(idx)
            dictionary.pop(idx)
            dictionary.insert(0, byte)
        return bytes(result)

    def mtf_decode(data: bytes) -> bytes:
        dictionary = list(range(256))
        result = []
        for idx in data:
            byte = dictionary[idx]
            result.append(byte)
            dictionary.pop(idx)
            dictionary.insert(0, byte)
        return bytes(result)

# Хаффман
try:
    from huffman_canonical import (
        build_probabilities_from_data,
        huffman_encode_canonical,
        huffman_decode_canonical
    )
except ImportError:
    try:
        from huffman import (
            build_probabilities_from_data,
            huffman_encode_canonical,
            huffman_decode_canonical
        )
    except:
        print("Ошибка: huffman модуль не найден")
        sys.exit(1)

# LZ функции
try:
    from lz_compressors import (
        lzss_encode, lzss_decode,
        LZWCoder
    )
except ImportError:
    try:
        from lz import (
            lzss_encode, lzss_decode,
            LZWCoder
        )
    except:
        print("Ошибка: lz модуль не найден")
        sys.exit(1)


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def save_code_lengths(code_lengths):
    result = bytearray()
    result.extend(struct.pack('>H', len(code_lengths)))
    for symbol, length in code_lengths.items():
        result.append(symbol)
        result.append(length)
    return bytes(result)


def load_code_lengths(data):
    code_lengths = {}
    pos = 0
    num = struct.unpack('>H', data[pos:pos+2])[0]
    pos += 2
    for _ in range(num):
        symbol = data[pos]
        length = data[pos+1]
        code_lengths[symbol] = length
        pos += 2
    return code_lengths


# ==================== КОМПРЕССОРЫ ====================

class CompressorHA:
    def __init__(self):
        self.name = "HA"

    def compress(self, data):
        probs = build_probabilities_from_data(data)
        encoded, code_lengths, padding = huffman_encode_canonical(data, probs)
        return encoded, (code_lengths, padding), 0

    def decompress(self, encoded, metadata, _):
        code_lengths, padding = metadata
        return huffman_decode_canonical(encoded, code_lengths, padding)


class CompressorRLE:
    def __init__(self, Ms=8, Mc=8):
        self.rle = RLE(Ms, Mc)
        self.name = "RLE"

    def compress(self, data):
        encoded = self.rle.encode(data)
        return encoded, None, 0

    def decompress(self, encoded, _, __):
        return self.rle.decode(encoded)


from bwt import bwt_encode_blocks, bwt_decode_blocks


class CompressorBWT_RLE:
    def __init__(self, block_size=None, Ms=8, Mc=8):
        self.block_size = block_size
        self.rle = RLE(Ms, Mc)
        self.name = "BWT+RLE"

    def compress(self, data):
        # BWT с блоками
        bwt_data, indices, block_sizes, is_bwt = bwt_encode_blocks(data, self.block_size)

        # Сохраняем метаданные
        metadata = {
            'indices': indices,
            'block_sizes': block_sizes,
            'is_bwt': is_bwt,
            'Ms': self.rle.Ms,
            'Mc': self.rle.Mc
        }

        # RLE кодирование
        encoded = self.rle.encode(bwt_data)
        return encoded, metadata, 0

    def decompress(self, encoded, metadata, __):
        # RLE декодирование
        rle = RLE(metadata['Ms'], metadata['Mc'])
        bwt_data = rle.decode(encoded)

        # BWT декодирование с блоками
        return bwt_decode_blocks(
            bwt_data,
            metadata['indices'],
            metadata['block_sizes'],
            metadata['is_bwt']
        )


class CompressorBWT_MTF_HA:
    def __init__(self, block_size=None):
        self.block_size = block_size
        self.name = "BWT+MTF+HA"

    def compress(self, data):
        # BWT с блоками
        bwt_data, indices, block_sizes, is_bwt = bwt_encode_blocks(data, self.block_size)

        # Упаковываем метаданные BWT в байты
        indices_data = struct.pack(f'>{len(indices)}I', *indices)
        block_sizes_data = struct.pack(f'>{len(block_sizes)}I', *block_sizes)
        is_bwt_data = bytes([1 if flag else 0 for flag in is_bwt])

        # Объединяем: [индексы][размеры_блоков][флаги_bwt][bwt_данные]
        full_bwt = indices_data + block_sizes_data + is_bwt_data + bwt_data

        # MTF
        mtf_data = mtf_encode(full_bwt)

        # Хаффман
        probs = build_probabilities_from_data(mtf_data)
        encoded, code_lengths, padding = huffman_encode_canonical(mtf_data, probs)

        # Сохраняем метаданные для декодирования
        metadata = {
            'indices': indices,
            'block_sizes': block_sizes,
            'is_bwt': is_bwt,
            'code_lengths': code_lengths,
            'padding': padding
        }

        return encoded, metadata, 0

    def decompress(self, encoded, metadata, __):
        # Хаффман декодирование
        mtf_data = huffman_decode_canonical(encoded, metadata['code_lengths'], metadata['padding'])

        # MTF декодирование
        full_bwt = mtf_decode(mtf_data)

        # Извлекаем метаданные BWT
        n_blocks = len(metadata['indices'])
        indices_size = n_blocks * 4
        block_sizes_size = n_blocks * 4

        indices_data = full_bwt[:indices_size]
        block_sizes_data = full_bwt[indices_size:indices_size + block_sizes_size]
        is_bwt_data = full_bwt[indices_size + block_sizes_size:indices_size + block_sizes_size + n_blocks]
        bwt_data = full_bwt[indices_size + block_sizes_size + n_blocks:]

        # Восстанавливаем списки
        indices = list(struct.unpack(f'>{n_blocks}I', indices_data))
        block_sizes = list(struct.unpack(f'>{n_blocks}I', block_sizes_data))
        is_bwt = [bool(b) for b in is_bwt_data]

        # BWT декодирование с блоками
        return bwt_decode_blocks(bwt_data, indices, block_sizes, is_bwt)


class CompressorBWT_MTF_RLE_HA:
    def __init__(self, block_size=None, Ms=8, Mc=8):
        self.block_size = block_size
        self.rle = RLE(Ms, Mc)
        self.name = "BWT+MTF+RLE+HA"

    def compress(self, data):
        # BWT с блоками
        bwt_data, indices, block_sizes, is_bwt = bwt_encode_blocks(data, self.block_size)

        # Упаковываем метаданные BWT в байты
        indices_data = struct.pack(f'>{len(indices)}I', *indices)
        block_sizes_data = struct.pack(f'>{len(block_sizes)}I', *block_sizes)
        is_bwt_data = bytes([1 if flag else 0 for flag in is_bwt])

        # Объединяем: [индексы][размеры_блоков][флаги_bwt][bwt_данные]
        full_bwt = indices_data + block_sizes_data + is_bwt_data + bwt_data

        # MTF
        mtf_data = mtf_encode(full_bwt)

        # RLE
        rle_data = self.rle.encode(mtf_data)

        # Хаффман
        probs = build_probabilities_from_data(rle_data)
        encoded, code_lengths, padding = huffman_encode_canonical(rle_data, probs)

        # Сохраняем метаданные
        metadata = {
            'indices': indices,
            'block_sizes': block_sizes,
            'is_bwt': is_bwt,
            'code_lengths': code_lengths,
            'padding': padding,
            'Ms': self.rle.Ms,
            'Mc': self.rle.Mc
        }

        return encoded, metadata, 0

    def decompress(self, encoded, metadata, __):
        # Хаффман декодирование
        rle_data = huffman_decode_canonical(encoded, metadata['code_lengths'], metadata['padding'])

        # RLE декодирование
        rle = RLE(metadata['Ms'], metadata['Mc'])
        mtf_data = rle.decode(rle_data)

        # MTF декодирование
        full_bwt = mtf_decode(mtf_data)

        # Извлекаем метаданные BWT
        n_blocks = len(metadata['indices'])
        indices_size = n_blocks * 4
        block_sizes_size = n_blocks * 4

        indices_data = full_bwt[:indices_size]
        block_sizes_data = full_bwt[indices_size:indices_size + block_sizes_size]
        is_bwt_data = full_bwt[indices_size + block_sizes_size:indices_size + block_sizes_size + n_blocks]
        bwt_data = full_bwt[indices_size + block_sizes_size + n_blocks:]

        # Восстанавливаем списки
        indices = list(struct.unpack(f'>{n_blocks}I', indices_data))
        block_sizes = list(struct.unpack(f'>{n_blocks}I', block_sizes_data))
        is_bwt = [bool(b) for b in is_bwt_data]

        # BWT декодирование с блоками
        return bwt_decode_blocks(bwt_data, indices, block_sizes, is_bwt)


class CompressorLZSS:
    def __init__(self, window_size=4096):
        self.window_size = window_size
        self.name = "LZSS"

    def compress(self, data):
        encoded = lzss_encode(data, self.window_size)
        return encoded, self.window_size, 0

    def decompress(self, encoded, window_size, __):
        return lzss_decode(encoded)


class CompressorLZSS_HA:
    def __init__(self, window_size=4096):
        self.window_size = window_size
        self.name = "LZSS+HA"

    def compress(self, data):
        lzss_data = lzss_encode(data, self.window_size)
        probs = build_probabilities_from_data(lzss_data)
        encoded, code_lengths, padding = huffman_encode_canonical(lzss_data, probs)
        return encoded, (self.window_size, code_lengths, padding), 0

    def decompress(self, encoded, metadata, __):
        window_size, code_lengths, padding = metadata
        lzss_data = huffman_decode_canonical(encoded, code_lengths, padding)
        return lzss_decode(lzss_data)


class CompressorLZW:
    def __init__(self, max_dict_size=4096):
        self.coder = LZWCoder(max_dict_size)
        self.max_dict_size = max_dict_size
        self.name = "LZW"

    def compress(self, data):
        encoded = self.coder.encode(data)
        return encoded, self.max_dict_size, 0

    def decompress(self, encoded, dict_size, __):
        coder = LZWCoder(dict_size)
        return coder.decode(encoded)


class CompressorLZW_HA:
    def __init__(self, max_dict_size=4096):
        self.max_dict_size = max_dict_size
        self.name = "LZW+HA"

    def compress(self, data):
        coder = LZWCoder(self.max_dict_size)
        lzw_data = coder.encode(data)
        probs = build_probabilities_from_data(lzw_data)
        encoded, code_lengths, padding = huffman_encode_canonical(lzw_data, probs)
        return encoded, (self.max_dict_size, code_lengths, padding), 0

    def decompress(self, encoded, metadata, __):
        dict_size, code_lengths, padding = metadata
        lzw_data = huffman_decode_canonical(encoded, code_lengths, padding)
        coder = LZWCoder(dict_size)
        return coder.decode(lzw_data)


# ==================== ТЕСТИРОВАНИЕ ====================

def test_compressors():
    """Тестирование всех компрессоров на тестовых файлах"""

    base_path = r"C:\Users\Daria\OneDrive\Desktop\аисд"

    test_files = [
        ("enwik7", os.path.join(base_path, "enwik7")),
        ("russian_text", os.path.join(base_path, "Русский текст.txt")),
        ("binary_file", os.path.join(base_path, "Бинарный файл.exe")),
        ("bw_image", os.path.join(base_path, "чб", "bw.raw")),
        ("gray_image", os.path.join(base_path, "серое", "gray.raw")),
        ("color_image", os.path.join(base_path, "цветное", "color.raw")),
    ]

    compressors = [
        CompressorHA(),
        CompressorRLE(),
        CompressorBWT_RLE(),
        CompressorBWT_MTF_HA(),
        CompressorBWT_MTF_RLE_HA(),
        CompressorLZSS(),
        CompressorLZSS_HA(),
        CompressorLZW(),
        CompressorLZW_HA(),
    ]

    print("=" * 130)
    print("ТЕСТИРОВАНИЕ КОМПРЕССОРОВ")
    print("=" * 130)

    all_results = []

    for file_name, file_path in test_files:
        if not os.path.exists(file_path):
            print(f"\n❌ Файл не найден: {file_path}")
            continue

        print(f"\n📁 {file_name} ({os.path.getsize(file_path):,} байт)")
        print("-" * 110)

        with open(file_path, 'rb') as f:
            data = f.read()

        original_size = len(data)

        print(f"{'Компрессор':<25} {'Сжатый':>12} {'Коэфф.':>10} {'Статус':>8}")
        print("-" * 110)

        for comp in compressors:
            try:
                import time
                start = time.time()

                encoded, metadata, _ = comp.compress(data)
                compressed_size = len(encoded)

                decoded = comp.decompress(encoded, metadata, 0)

                elapsed = time.time() - start
                ratio = compressed_size / original_size if original_size > 0 else 0
                is_valid = decoded == data
                status = "✓" if is_valid else "✗"

                print(f"{comp.name:<25} {compressed_size:>12,} {ratio:>10.4f} {elapsed:>7.3f}s {status:>8}")

                all_results.append({
                    'file': file_name,
                    'compressor': comp.name,
                    'original': original_size,
                    'compressed': compressed_size,
                    'ratio': ratio,
                    'time': elapsed,
                    'status': status
                })

            except Exception as e:
                print(f"{comp.name:<25} {'ОШИБКА':>12} {'':>10} {str(e)[:30]:>8}")

        print("-" * 110)

    # Сводная таблица
    print("\n" + "=" * 130)
    print("СВОДНАЯ ТАБЛИЦА")
    print("=" * 130)
    print(f"{'Файл':<20} {'Компрессор':<20} {'Исходный':>12} {'Сжатый':>12} {'Коэфф.':>10} {'Время':>10}")
    print("-" * 130)

    for r in all_results:
        print(f"{r['file']:<20} {r['compressor']:<20} {r['original']:>12,} {r['compressed']:>12,} {r['ratio']:>10.4f} {r['time']:>9.3f}s")

    print("=" * 130)

    return all_results


if __name__ == "__main__":
    test_compressors()