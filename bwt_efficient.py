import os
import time


def bwt_encode_suffix(data: bytes) -> tuple:
    if not data:
        return b'', 0

    data_with_eof = data + b'\xFF'
    n = len(data_with_eof)

    suffixes = list(range(n))
    suffixes.sort(key=lambda i: data_with_eof[i:])

    last_column = bytearray()
    original_index = 0

    for i, pos in enumerate(suffixes):
        if pos == 0:
            last_char = data_with_eof[-1]
            original_index = i
        else:
            last_char = data_with_eof[pos - 1]
        last_column.append(last_char)

    return bytes(last_column), original_index


def rle_encode(data: bytes) -> bytes:
    if not data:
        return b''

    result = bytearray()
    i = 0
    n = len(data)

    while i < n:
        run_len = 1
        while i + run_len < n and data[i] == data[i + run_len] and run_len < 255:
            run_len += 1

        if run_len > 1:
            result.append(run_len)
            result.append(data[i])
            i += run_len
        else:
            result.append(0)
            result.append(data[i])
            i += 1

    return bytes(result)


def bwt_rle_encode(data: bytes, block_size: int) -> bytes:
    if not data:
        return b''

    result = bytearray()
    n = len(data)

    for start in range(0, n, block_size):
        block = data[start:start + block_size]
        last_col, idx = bwt_encode_suffix(block)
        compressed = rle_encode(last_col)
        # Используем 4 байта для индекса
        result.extend(idx.to_bytes(4, 'big'))
        result.extend(compressed)

    return bytes(result)


if __name__ == "__main__":
    desktop_path = r"C:\Users\Daria\OneDrive\Desktop\аисд"
    file_path = os.path.join(desktop_path, 'Русский текст.txt')

    with open(file_path, 'rb') as f:
        data = f.read()

    print("=" * 70)
    print("ИССЛЕДОВАНИЕ РАЗМЕРА БЛОКА ДЛЯ BWT + RLE")
    print("=" * 70)
    print(f"Файл: русский текст (размер: {len(data):,} байт)")
    print()

    block_sizes = [64 * 1024, 128 * 1024, 256 * 1024, 512 * 1024]

    print(f"{'Блок (КБ)':<15} {'Сжатый (байт)':>15} {'Коэффициент':>12} {'Время (с)':>12}")
    print("-" * 60)

    for bs in block_sizes:
        start_time = time.time()
        enc = bwt_rle_encode(data, block_size=bs)
        elapsed = time.time() - start_time

        ratio = len(enc) / len(data)
        print(f"{bs // 1024:<15} {len(enc):>15,} {ratio:>12.4f} {elapsed:>12.2f}")

    print("\n✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")