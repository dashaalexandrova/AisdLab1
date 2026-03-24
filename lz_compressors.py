import os
import struct
import time
from typing import List, Tuple, Dict
from collections import defaultdict


# ==================== LZ77 ====================

def lz77_encode(data: bytes, window_size: int = 4096, lookahead_size: int = 16) -> bytes:
    """
    LZ77 кодирование.

    Формат выходных данных:
    - [2 байта] window_size (размер окна)
    - [2 байта] lookahead_size (размер буфера просмотра)
    - Далее последовательность токенов:
        * [2 байта] offset (смещение)
        * [2 байта] length (длина совпадения)
        * [1 байт] next_char (следующий символ)

    Если совпадение не найдено: offset=0, length=0, next_char=текущий символ
    """
    if not data:
        return b''

    result = bytearray()

    # Сохраняем метаданные для декодирования
    result.extend(struct.pack('>HH', window_size, lookahead_size))

    i = 0
    n = len(data)

    while i < n:
        # Поиск максимального совпадения в окне
        max_match_offset = 0
        max_match_length = 0

        # Определяем границы окна
        window_start = max(0, i - window_size)

        # Ищем совпадения
        for offset in range(1, min(i - window_start + 1, window_size + 1)):
            match_length = 0
            # Сравниваем символы
            while (match_length < lookahead_size and
                   i + match_length < n and
                   data[i - offset + match_length] == data[i + match_length]):
                match_length += 1

            if match_length > max_match_length:
                max_match_length = match_length
                max_match_offset = offset

        # Определяем следующий символ
        if i + max_match_length < n:
            next_char = data[i + max_match_length]
        else:
            next_char = 0
            # Если достигли конца, то длина совпадения не должна включать следующий символ
            if max_match_length > 0:
                max_match_length -= 1

        # Записываем токен
        result.extend(struct.pack('>HHB', max_match_offset, max_match_length, next_char))

        # Перемещаем указатель
        if max_match_length == 0:
            i += 1
        else:
            i += max_match_length
            if next_char != 0:
                i += 1

    return bytes(result)


def lz77_decode(data: bytes) -> bytes:
    """
    LZ77 декодирование.

    Формат входных данных:
    - [2 байта] window_size
    - [2 байта] lookahead_size
    - Далее последовательность токенов
    """
    if not data or len(data) < 4:
        return b''

    result = bytearray()

    # Извлекаем метаданные
    window_size, lookahead_size = struct.unpack('>HH', data[:4])
    pos = 4

    while pos + 5 <= len(data):
        offset, length, next_char = struct.unpack('>HHB', data[pos:pos + 5])
        pos += 5

        if offset > 0 and length > 0:
            # Копируем из уже декодированных данных
            start = len(result) - offset
            for j in range(length):
                if start + j < len(result):
                    result.append(result[start + j])

        if next_char != 0:
            result.append(next_char)

    return bytes(result)


# ==================== LZSS ====================

def lzss_encode(data: bytes, window_size: int = 4096, lookahead_size: int = 16) -> bytes:
    """
    LZSS кодирование (вариация LZ77 с флагами).

    Формат выходных данных:
    - [2 байта] window_size
    - [2 байта] lookahead_size
    - Далее идут блоки по 8 токенов с флагами:
        * [1 байт] flags (бит=1 - ссылка, бит=0 - литерал)
        * Для каждого бита:
            - если 0: [1 байт] литерал
            - если 1: [2 байта] ссылка (смещение 12 бит + длина 4 бита)
                * смещение: 12 бит (0-4095)
                * длина: 4 бита (3-18, так как длина 0-2 не выгодна)
    """
    if not data:
        return b''

    result = bytearray()

    # Сохраняем метаданные
    result.extend(struct.pack('>HH', window_size, lookahead_size))

    i = 0
    n = len(data)

    while i < n:
        flags = 0
        block_data = bytearray()
        tokens_count = 0

        # Обрабатываем до 8 токенов
        for bit in range(8):
            if i >= n:
                break

            # Поиск совпадения
            best_offset = 0
            best_length = 0

            window_start = max(0, i - window_size)

            # Ищем совпадение (минимальная выгодная длина 3)
            for offset in range(1, min(i - window_start + 1, window_size + 1)):
                match_length = 0
                while (match_length < lookahead_size and
                       i + match_length < n and
                       data[i - offset + match_length] == data[i + match_length]):
                    match_length += 1

                # В LZSS выгодно использовать ссылку только если длина >= 3
                if match_length >= 3 and match_length > best_length:
                    best_length = match_length
                    best_offset = offset

                    # Ограничиваем максимальную длину 18 (4 бита: 3-18)
                    if best_length > 18:
                        best_length = 18

            if best_length >= 3:
                # Используем ссылку (бит = 1)
                flags |= (1 << (7 - bit))

                # Кодируем: смещение (12 бит) и длина-3 (4 бита)
                # Упаковываем в 2 байта: [смещение (12 бит)] [длина-3 (4 бита)]
                encoded_ref = ((best_offset & 0xFFF) << 4) | ((best_length - 3) & 0xF)
                block_data.extend(struct.pack('>H', encoded_ref))

                i += best_length
            else:
                # Используем литерал (бит = 0)
                block_data.append(data[i])
                i += 1

            tokens_count += 1

        # Добавляем флаги и данные блока
        result.append(flags)
        result.extend(block_data)

    return bytes(result)


def lzss_decode(data: bytes) -> bytes:
    """
    LZSS декодирование.

    Формат входных данных:
    - [2 байта] window_size
    - [2 байта] lookahead_size
    - Далее блоки с флагами и данными
    """
    if not data or len(data) < 4:
        return b''

    result = bytearray()

    # Извлекаем метаданные
    window_size, lookahead_size = struct.unpack('>HH', data[:4])
    pos = 4

    while pos < len(data):
        flags = data[pos]
        pos += 1

        # Обрабатываем 8 битов флагов
        for bit in range(8):
            if pos >= len(data):
                break

            if (flags >> (7 - bit)) & 1:
                # Это ссылка
                if pos + 2 > len(data):
                    break

                encoded_ref = struct.unpack('>H', data[pos:pos + 2])[0]
                pos += 2

                # Распаковываем смещение (12 бит) и длину (4 бита)
                offset = (encoded_ref >> 4) & 0xFFF
                length = (encoded_ref & 0xF) + 3

                # Копируем из уже декодированных данных
                start = len(result) - offset
                for j in range(length):
                    if start + j < len(result):
                        result.append(result[start + j])
            else:
                # Это литерал
                result.append(data[pos])
                pos += 1

    return bytes(result)


# ==================== LZ78 ====================

class LZ78Coder:
    """LZ78 кодирование с ограниченным словарем"""

    def __init__(self, max_dict_size: int = 4096):
        self.max_dict_size = max_dict_size

    def encode(self, data: bytes) -> bytes:
        """
        LZ78 кодирование.

        Формат: для каждого токена:
        - [2 байта] индекс в словаре (0-65535)
        - [1 байт] следующий символ
        """
        if not data:
            return b''

        # Инициализируем словарь пустой строкой
        dictionary = {b'': 0}
        result = bytearray()
        current = b''

        for byte in data:
            new_current = current + bytes([byte])

            if new_current in dictionary:
                # Продолжаем наращивать строку
                current = new_current
            else:
                # Выводим пару (индекс префикса, символ)
                prefix_idx = dictionary[current]
                result.extend(prefix_idx.to_bytes(2, 'big'))
                result.append(byte)

                # Добавляем новую строку в словарь, если есть место
                if len(dictionary) < self.max_dict_size:
                    dictionary[new_current] = len(dictionary)

                # Сбрасываем текущую строку
                current = b''

        # Обрабатываем остаток
        if current:
            prefix_idx = dictionary[current]
            result.extend(prefix_idx.to_bytes(2, 'big'))
            result.append(0)  # Нулевой байт как признак конца

        return bytes(result)

    def decode(self, data: bytes) -> bytes:
        """
        LZ78 декодирование.
        """
        if not data:
            return b''

        # Инициализируем словарь
        dictionary = {0: b''}
        result = bytearray()
        i = 0
        n = len(data)

        while i + 3 <= n:
            idx = int.from_bytes(data[i:i + 2], 'big')
            char = data[i + 2]
            i += 3

            if idx in dictionary:
                entry = dictionary[idx] + bytes([char]) if char != 0 else dictionary[idx]
            else:
                entry = b''

            if entry:
                result.extend(entry)

                # Добавляем в словарь, если есть место
                if len(dictionary) < self.max_dict_size:
                    dictionary[len(dictionary)] = entry

        return bytes(result)


# ==================== LZW ====================

class LZWCoder:
    """LZW кодирование с ограниченным словарем"""

    def __init__(self, max_dict_size: int = 4096):
        self.max_dict_size = max_dict_size

    def encode(self, data: bytes) -> bytes:
        """
        LZW кодирование.

        Формат: последовательность 2-байтовых кодов
        """
        if not data:
            return b''

        # Инициализируем словарь всеми возможными байтами
        dictionary = {bytes([i]): i for i in range(256)}
        result = bytearray()
        current = b''

        for byte in data:
            new_current = current + bytes([byte])

            if new_current in dictionary:
                current = new_current
            else:
                # Выводим код текущей строки
                code = dictionary[current]
                result.extend(code.to_bytes(2, 'big'))

                # Добавляем новую строку в словарь, если есть место
                if len(dictionary) < self.max_dict_size:
                    dictionary[new_current] = len(dictionary)

                # Начинаем новую строку с текущего символа
                current = bytes([byte])

        # Выводим последнюю строку
        if current:
            code = dictionary[current]
            result.extend(code.to_bytes(2, 'big'))

        return bytes(result)

    def decode(self, data: bytes) -> bytes:
        """
        LZW декодирование.
        """
        if not data or len(data) < 2:
            return b''

        # Инициализируем словарь
        dictionary = {i: bytes([i]) for i in range(256)}
        result = bytearray()
        i = 0
        n = len(data)

        # Читаем первый код
        prev_code = int.from_bytes(data[i:i + 2], 'big')
        i += 2
        result.extend(dictionary[prev_code])

        while i + 2 <= n:
            code = int.from_bytes(data[i:i + 2], 'big')
            i += 2

            if code in dictionary:
                entry = dictionary[code]
            elif code == len(dictionary):
                # Специальный случай для кода, равного текущему размеру словаря
                entry = dictionary[prev_code] + bytes([dictionary[prev_code][0]])
            else:
                # Некорректный код
                break

            result.extend(entry)

            # Добавляем новую строку в словарь
            if len(dictionary) < self.max_dict_size:
                new_entry = dictionary[prev_code] + bytes([entry[0]])
                dictionary[len(dictionary)] = new_entry

            prev_code = code

        return bytes(result)


# ==================== ТЕСТИРОВАНИЕ ====================

def test_algorithm(name: str, encode_func, decode_func, data: bytes, *args, **kwargs):
    """Тестирование алгоритма сжатия"""
    try:
        start_time = time.time()

        if isinstance(encode_func, type):
            # Для классов
            coder = encode_func(*args, **kwargs)
            encoded = coder.encode(data)
            decoded = coder.decode(encoded)
        else:
            # Для функций
            encoded = encode_func(data, *args, **kwargs)
            decoded = decode_func(encoded)

        elapsed_time = time.time() - start_time

        ratio = len(encoded) / len(data) if len(data) > 0 else 1.0
        is_valid = (decoded == data)

        return {
            'name': name,
            'original_size': len(data),
            'compressed_size': len(encoded),
            'ratio': ratio,
            'time': elapsed_time,
            'valid': is_valid
        }
    except Exception as e:
        return {
            'name': name,
            'original_size': len(data),
            'compressed_size': 0,
            'ratio': 0,
            'time': 0,
            'valid': False,
            'error': str(e)
        }


def main():
    """Главная функция тестирования"""

    # Пути к тестовым файлам
    desktop_path = r"C:\Users\Daria\OneDrive\Desktop\аисд"

    test_files = [
        ('enwik7', os.path.join(desktop_path, 'enwik7'), 'Текстовый файл (enwik7)'),
        ('russian_text', os.path.join(desktop_path, 'Русский текст.txt'), 'Русский текст'),
        ('binary_file', os.path.join(desktop_path, 'Бинарный файл.exe'), 'Бинарный файл'),
        ('bw_raw', os.path.join(desktop_path, 'чб', 'bw.raw'), 'ЧБ изображение'),
        ('gray_raw', os.path.join(desktop_path, 'серое', 'gray.raw'), 'Серое изображение'),
        ('color_raw', os.path.join(desktop_path, 'цветное', 'color.raw'), 'Цветное изображение'),
    ]

    # Загружаем данные
    test_data = {}
    for name, path, desc in test_files:
        if os.path.exists(path):
            with open(path, 'rb') as f:
                test_data[name] = {'data': f.read(), 'desc': desc, 'path': path}
            print(f"Загружен: {desc} ({len(test_data[name]['data']):,} байт)")
        else:
            print(f"Файл не найден: {desc} ({path})")

    if not test_data:
        print("\n❌ Нет доступных тестовых файлов!")
        return

    print("\n" + "=" * 100)
    print("ТЕСТИРОВАНИЕ АЛГОРИТМОВ LZ77, LZSS, LZ78, LZW")
    print("=" * 100)

    # 1. Тестирование LZ77 с разными параметрами
    print("\n" + "=" * 100)
    print("1. LZ77 (исследование размера окна)")
    print("=" * 100)

    window_sizes = [256, 512, 1024, 2048, 4096]
    lookahead_size = 16

    for file_name, file_info in test_data.items():
        data = file_info['data']
        if len(data) > 10 * 1024 * 1024:  # Пропускаем слишком большие файлы
            print(f"\n{file_info['desc']}: {len(data):,} байт (пропущен - слишком большой)")
            continue

        print(f"\n{file_info['desc']} (размер: {len(data):,} байт)")
        print(f"{'Окно':<10} {'Сжатый размер':>15} {'Коэффициент':>12} {'Время (с)':>12} {'Статус':>10}")
        print("-" * 65)

        for ws in window_sizes:
            result = test_algorithm(f"LZ77-{ws}", lz77_encode, lz77_decode, data, ws, lookahead_size)
            if result['valid']:
                print(
                    f"{ws:<10} {result['compressed_size']:>15,} {result['ratio']:>12.4f} {result['time']:>12.4f} {'✓':>10}")
            else:
                print(f"{ws:<10} {'ОШИБКА':>15} {'-':>12} {'-':>12} {'✗':>10}")
                if 'error' in result:
                    print(f"  Ошибка: {result['error']}")

    # 2. Тестирование LZSS с разными параметрами
    print("\n" + "=" * 100)
    print("2. LZSS (исследование размера окна)")
    print("=" * 100)

    for file_name, file_info in test_data.items():
        data = file_info['data']
        if len(data) > 10 * 1024 * 1024:
            print(f"\n{file_info['desc']}: {len(data):,} байт (пропущен - слишком большой)")
            continue

        print(f"\n{file_info['desc']} (размер: {len(data):,} байт)")
        print(f"{'Окно':<10} {'Сжатый размер':>15} {'Коэффициент':>12} {'Время (с)':>12} {'Статус':>10}")
        print("-" * 65)

        for ws in window_sizes:
            result = test_algorithm(f"LZSS-{ws}", lzss_encode, lzss_decode, data, ws, lookahead_size)
            if result['valid']:
                print(
                    f"{ws:<10} {result['compressed_size']:>15,} {result['ratio']:>12.4f} {result['time']:>12.4f} {'✓':>10}")
            else:
                print(f"{ws:<10} {'ОШИБКА':>15} {'-':>12} {'-':>12} {'✗':>10}")

    # 3. Тестирование LZ78 с разными размерами словаря
    print("\n" + "=" * 100)
    print("3. LZ78 (исследование размера словаря)")
    print("=" * 100)

    dict_sizes = [256, 512, 1024, 2048, 4096, 8192]

    for file_name, file_info in test_data.items():
        data = file_info['data']
        if len(data) > 10 * 1024 * 1024:
            print(f"\n{file_info['desc']}: {len(data):,} байт (пропущен - слишком большой)")
            continue

        print(f"\n{file_info['desc']} (размер: {len(data):,} байт)")
        print(f"{'Словарь':<10} {'Сжатый размер':>15} {'Коэффициент':>12} {'Время (с)':>12} {'Статус':>10}")
        print("-" * 65)

        for ds in dict_sizes:
            result = test_algorithm(f"LZ78-{ds}", LZ78Coder, None, data, ds)
            if result['valid']:
                print(
                    f"{ds:<10} {result['compressed_size']:>15,} {result['ratio']:>12.4f} {result['time']:>12.4f} {'✓':>10}")
            else:
                print(f"{ds:<10} {'ОШИБКА':>15} {'-':>12} {'-':>12} {'✗':>10}")

    # 4. Тестирование LZW с разными размерами словаря
    print("\n" + "=" * 100)
    print("4. LZW (исследование размера словаря)")
    print("=" * 100)

    for file_name, file_info in test_data.items():
        data = file_info['data']
        if len(data) > 10 * 1024 * 1024:
            print(f"\n{file_info['desc']}: {len(data):,} байт (пропущен - слишком большой)")
            continue

        print(f"\n{file_info['desc']} (размер: {len(data):,} байт)")
        print(f"{'Словарь':<10} {'Сжатый размер':>15} {'Коэффициент':>12} {'Время (с)':>12} {'Статус':>10}")
        print("-" * 65)

        for ds in dict_sizes:
            result = test_algorithm(f"LZW-{ds}", LZWCoder, None, data, ds)
            if result['valid']:
                print(
                    f"{ds:<10} {result['compressed_size']:>15,} {result['ratio']:>12.4f} {result['time']:>12.4f} {'✓':>10}")
            else:
                print(f"{ds:<10} {'ОШИБКА':>15} {'-':>12} {'-':>12} {'✗':>10}")

    # 5. Сравнительный анализ лучших параметров
    print("\n" + "=" * 100)
    print("5. СРАВНИТЕЛЬНЫЙ АНАЛИЗ (лучшие параметры)")
    print("=" * 100)

    best_params = {
        'LZ77': 4096,
        'LZSS': 4096,
        'LZ78': 4096,
        'LZW': 4096
    }

    print(
        f"\n{'Алгоритм':<12} {'Файл':<20} {'Исходный':>12} {'Сжатый':>12} {'Коэффициент':>12} {'Время (с)':>12} {'Статус':>10}")
    print("-" * 95)

    for file_name, file_info in test_data.items():
        data = file_info['data']
        if len(data) > 10 * 1024 * 1024:
            continue

        # LZ77
        result = test_algorithm("LZ77", lz77_encode, lz77_decode, data, best_params['LZ77'], lookahead_size)
        if result['valid']:
            print(
                f"{'LZ77':<12} {file_info['desc']:<20} {result['original_size']:>12,} {result['compressed_size']:>12,} {result['ratio']:>12.4f} {result['time']:>12.4f} {'✓':>10}")

        # LZSS
        result = test_algorithm("LZSS", lzss_encode, lzss_decode, data, best_params['LZSS'], lookahead_size)
        if result['valid']:
            print(
                f"{'LZSS':<12} {file_info['desc']:<20} {result['original_size']:>12,} {result['compressed_size']:>12,} {result['ratio']:>12.4f} {result['time']:>12.4f} {'✓':>10}")

        # LZ78
        result = test_algorithm("LZ78", LZ78Coder, None, data, best_params['LZ78'])
        if result['valid']:
            print(
                f"{'LZ78':<12} {file_info['desc']:<20} {result['original_size']:>12,} {result['compressed_size']:>12,} {result['ratio']:>12.4f} {result['time']:>12.4f} {'✓':>10}")

        # LZW
        result = test_algorithm("LZW", LZWCoder, None, data, best_params['LZW'])
        if result['valid']:
            print(
                f"{'LZW':<12} {file_info['desc']:<20} {result['original_size']:>12,} {result['compressed_size']:>12,} {result['ratio']:>12.4f} {result['time']:>12.4f} {'✓':>10}")

        print("-" * 95)

    # 6. Анализ эффективности для разных типов данных
    print("\n" + "=" * 100)
    print("6. АНАЛИЗ ЭФФЕКТИВНОСТИ ПО ТИПАМ ДАННЫХ")
    print("=" * 100)

    data_types = {}
    for file_name, file_info in test_data.items():
        data_type = file_info['desc'].split()[0] if ' ' in file_info['desc'] else file_info['desc']
        if data_type not in data_types:
            data_types[data_type] = []
        data_types[data_type].append((file_info['desc'], file_info['data']))

    for data_type, files in data_types.items():
        print(f"\n{data_type}:")
        print(f"{'Алгоритм':<12} {'Файл':<20} {'Коэфф. сжатия':>15}")
        print("-" * 50)

        for file_desc, data in files:
            if len(data) > 10 * 1024 * 1024:
                continue

            for algo_name, algo_func, decode_func, params in [
                ('LZ77', lz77_encode, lz77_decode, (4096, 16)),
                ('LZSS', lzss_encode, lzss_decode, (4096, 16)),
                ('LZ78', LZ78Coder, None, (4096,)),
                ('LZW', LZWCoder, None, (4096,))
            ]:
                if isinstance(algo_func, type):
                    coder = algo_func(*params)
                    encoded = coder.encode(data)
                else:
                    encoded = algo_func(data, *params)
                ratio = len(encoded) / len(data)
                print(f"{algo_name:<12} {file_desc:<20} {ratio:>15.4f}")

        print()

    print("\n" + "=" * 100)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 100)


if __name__ == "__main__":
    main()