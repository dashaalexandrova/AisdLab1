import os
import struct
import math
from io import BytesIO


class BitWriter:
    """Запись битов в поток"""

    def __init__(self, output_buffer):
        self.buffer = output_buffer
        self.current_byte = 0
        self.bits_in_current = 0

    def write_bits(self, value, num_bits):
        """Записать значение длиной num_bits бит"""
        if num_bits == 0:
            return

        # Маскируем только нужные биты
        value &= (1 << num_bits) - 1

        # Добавляем биты в текущий байт
        self.current_byte |= (value << self.bits_in_current)
        self.bits_in_current += num_bits

        # Пока есть полные байты, записываем их
        while self.bits_in_current >= 8:
            self.buffer.append(self.current_byte & 0xFF)
            self.current_byte >>= 8
            self.bits_in_current -= 8

    def flush(self):
        """Записать оставшиеся биты"""
        if self.bits_in_current > 0:
            self.buffer.append(self.current_byte & 0xFF)
        self.current_byte = 0
        self.bits_in_current = 0


class BitReader:
    """Чтение битов из потока"""

    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.current_byte = 0
        self.bits_remaining = 0

    def read_bits(self, num_bits):
        """Прочитать num_bits бит"""
        if num_bits == 0:
            return 0

        result = 0
        bits_read = 0

        while bits_read < num_bits:
            # Если в буфере нет бит, читаем новый байт
            if self.bits_remaining == 0:
                if self.pos >= len(self.data):
                    raise EOFError("Неожиданный конец файла")
                self.current_byte = self.data[self.pos]
                self.pos += 1
                self.bits_remaining = 8

            # Сколько бит можем взять из буфера
            bits_to_take = min(num_bits - bits_read, self.bits_remaining)

            # Извлекаем биты
            result |= ((self.current_byte & ((1 << bits_to_take) - 1)) << bits_read)
            self.current_byte >>= bits_to_take
            self.bits_remaining -= bits_to_take
            bits_read += bits_to_take

        return result

    def eof(self):
        """Проверка, достигнут ли конец"""
        return self.pos >= len(self.data) and self.bits_remaining == 0


class RLE:
    def __init__(self, Ms=8, Mc=8):
        """
        Ms - длина символа в битах
        Mc - длина управляющего кода в битах
        """
        self.Ms = Ms
        self.Mc = Mc

        # Вычисляем параметры
        self.symbol_bytes = math.ceil(Ms / 8)
        self.control_bytes = math.ceil(Mc / 8)

        # Для работы с битами
        self.flag_bit = 1 << (Mc - 1) if Mc > 0 else 0
        self.max_len = self.flag_bit - 1 if self.flag_bit > 0 else 255

        # Для хранения при чтении/записи
        self.symbol_mask = (1 << Ms) - 1 if Ms > 0 else 0
        self.control_mask = (1 << Mc) - 1 if Mc > 0 else 0

    def _bytes_to_symbols(self, data: bytes) -> list:
        """
        Преобразование байтов в символы заданной битовой длины
        """
        if self.Ms == 0:
            return []

        symbols = []
        buffer = 0
        bits_in_buffer = 0

        for byte in data:
            # Добавляем 8 бит от байта в буфер
            buffer |= (byte << bits_in_buffer)
            bits_in_buffer += 8

            # Пока в буфере достаточно бит для символа
            while bits_in_buffer >= self.Ms:
                symbol = buffer & self.symbol_mask
                symbols.append(symbol)
                buffer >>= self.Ms
                bits_in_buffer -= self.Ms

        # Если остались биты, добавляем последний символ (дополненный нулями)
        if bits_in_buffer > 0:
            symbols.append(buffer & self.symbol_mask)

        return symbols

    def _symbols_to_bytes(self, symbols: list, original_size: int = None) -> bytes:
        """
        Преобразование символов обратно в байты
        """
        if self.Ms == 0:
            return b''

        result = bytearray()
        buffer = 0
        bits_in_buffer = 0

        for symbol in symbols:
            buffer |= (symbol << bits_in_buffer)
            bits_in_buffer += self.Ms

            while bits_in_buffer >= 8:
                result.append(buffer & 0xFF)
                buffer >>= 8
                bits_in_buffer -= 8

        # Если остались биты, добавляем последний байт
        if bits_in_buffer > 0:
            result.append(buffer & 0xFF)

        # Обрезаем до оригинального размера, если указан
        if original_size is not None:
            result = result[:original_size]

        return bytes(result)

    def encode(self, data: bytes) -> bytes:
        """
        Кодирование данных с битовой упаковкой
        """
        if not data:
            return b''

        # Преобразуем байты в символы
        symbols = self._bytes_to_symbols(data)

        if not symbols:
            return b''

        # Кодируем последовательность символов
        output_buffer = bytearray()
        writer = BitWriter(output_buffer)

        i = 0
        n = len(symbols)

        while i < n:
            current = symbols[i]

            # ========== ПОИСК ПОВТОРЯЮЩЕЙСЯ ПОСЛЕДОВАТЕЛЬНОСТИ ==========
            run_len = 1
            while (i + run_len < n and
                   symbols[i + run_len] == current and
                   run_len < self.max_len):
                run_len += 1

            if run_len > 1:
                # Режим повтора (старший бит = 0)
                writer.write_bits(run_len, self.Mc)
                writer.write_bits(current, self.Ms)
                i += run_len

            else:
                # ========== ПОИСК УНИКАЛЬНОЙ ПОСЛЕДОВАТЕЛЬНОСТИ ==========
                seq_len = 1
                start_pos = i

                while i + seq_len < n:
                    # Проверяем, не начинается ли повтор с текущей позиции
                    if symbols[start_pos + seq_len - 1] == symbols[start_pos + seq_len]:
                        break
                    seq_len += 1
                    if seq_len >= self.max_len:
                        break

                # Если нашли только один символ и он уникальный
                if seq_len == 0:
                    seq_len = 1

                # Режим уникальных (старший бит = 1)
                control = seq_len | self.flag_bit
                writer.write_bits(control, self.Mc)

                # Записываем все символы последовательности
                for j in range(seq_len):
                    writer.write_bits(symbols[start_pos + j], self.Ms)

                i += seq_len

        writer.flush()
        return bytes(output_buffer)

    def decode(self, data: bytes, original_size: int = None) -> bytes:
        """
        Декодирование данных из битового потока
        """
        if not data:
            return b''

        reader = BitReader(data)
        symbols = []

        try:
            while not reader.eof():
                # Читаем управляющий код
                try:
                    control = reader.read_bits(self.Mc)
                except EOFError:
                    break

                is_unique = (control & self.flag_bit) != 0

                if is_unique:
                    # Режим уникальных: читаем последовательность символов
                    length = control & (~self.flag_bit)

                    for _ in range(length):
                        try:
                            symbol = reader.read_bits(self.Ms)
                            symbols.append(symbol)
                        except EOFError:
                            break
                else:
                    # Режим повтора: читаем один символ и повторяем
                    count = control
                    try:
                        symbol = reader.read_bits(self.Ms)
                        symbols.extend([symbol] * count)
                    except EOFError:
                        break

        except Exception:
            pass

        # Преобразуем символы обратно в байты
        return self._symbols_to_bytes(symbols, original_size)

    def compress_file(self, input_path: str, output_path: str = None):
        """
        Сжатие файла с сохранением метаданных
        """
        with open(input_path, 'rb') as f:
            data = f.read()

        original_size = len(data)
        encoded = self.encode(data)

        # Формируем метаданные: Ms (2 байта), Mc (2 байта), оригинальный размер (4 байта)
        metadata = struct.pack('>HHI', self.Ms, self.Mc, original_size)
        full_data = metadata + encoded

        if output_path:
            with open(output_path, 'wb') as f:
                f.write(full_data)

        ratio = len(full_data) / original_size if original_size > 0 else 0
        return original_size, len(full_data), ratio

    def decompress_file(self, input_path: str, output_path: str):
        """
        Распаковка файла с чтением метаданных
        """
        with open(input_path, 'rb') as f:
            full_data = f.read()

        if len(full_data) < 8:
            raise ValueError("Файл поврежден: недостаточно метаданных")

        # Читаем метаданные
        Ms, Mc, original_size = struct.unpack('>HHI', full_data[:8])
        encoded = full_data[8:]

        # Создаем декодер с правильными параметрами
        rle = RLE(Ms=Ms, Mc=Mc)
        decoded = rle.decode(encoded, original_size)

        with open(output_path, 'wb') as f:
            f.write(decoded)

        return len(decoded)


def main():
    desktop_path = r"C:\Users\Daria\OneDrive\Desktop\аисд"
    rle_folder = os.path.join(desktop_path, "RLE")
    if not os.path.exists(rle_folder):
        os.makedirs(rle_folder)

    # Список файлов с путями
    test_files = [
        {
            'name': 'enwik7',
            'path': os.path.join(desktop_path, 'enwik7'),
        },
        {
            'name': 'russian_text',
            'path': os.path.join(desktop_path, 'Русский текст.txt'),
        },
        {
            'name': 'binary_file',
            'path': os.path.join(desktop_path, 'Бинарный файл.exe'),
        },
        {
            'name': 'bw_image_raw',
            'path': os.path.join(desktop_path, 'чб', 'bw.raw'),
        },
        {
            'name': 'gray_image_raw',
            'path': os.path.join(desktop_path, 'серое', 'gray.raw'),
        },
        {
            'name': 'color_image_raw',
            'path': os.path.join(desktop_path, 'цветное', 'color.raw'),
        },
    ]


    print("RLE (Ms=8, Mc=8)")
    print(f"{'Файл':<25} {'Исходный':>12} {'Сжатый':>12} {'Коэфф.':>10} {'Статус':>8}")
    print("-" * 100)

    results = []

    for file_info in test_files:
        file_path = file_info['path']
        file_name = file_info['name']

        if not os.path.exists(file_path):
            print(f"{file_name:<25} {'НЕ НАЙДЕН':<40}")
            continue

        # Для всех файлов используем Ms=8, Mc=8
        Ms = 8
        Mc = 8

        try:
            rle = RLE(Ms=Ms, Mc=Mc)

            encoded_path = os.path.join(rle_folder, f"{file_name}_rle_encoded.bin")
            decoded_path = os.path.join(rle_folder, f"{file_name}_rle_decoded")

            original_size, compressed_size, ratio = rle.compress_file(file_path, encoded_path)
            decoded_size = rle.decompress_file(encoded_path, decoded_path)

            # Проверка корректности
            with open(file_path, 'rb') as f1, open(decoded_path, 'rb') as f2:
                is_valid = f1.read() == f2.read()

            status = "✓" if is_valid else "✗"

            print(
                f"{file_name:<25} {original_size:>12,} {compressed_size:>12,} "
                f"{ratio:>10.4f} {status:>8}")

            results.append({
                'file': file_name,
                'original': original_size,
                'compressed': compressed_size,
                'ratio': ratio,
                'path': file_path
            })

        except Exception as e:
            print(f"{file_name:<25} {'ОШИБКА: ' + str(e):<40}")

    print("-" * 100)

    # Оптимизация для цветного изображения (подбор Ms)


    color_path = os.path.join(desktop_path, 'цветное', 'color.raw')
    if os.path.exists(color_path):
        with open(color_path, 'rb') as f:
            color_data = f.read()

        original_size = len(color_data)
        print(f"\nЦветное изображение: {original_size:,} байт")

        best_ratio = 1.0
        best_Ms = 8

        for Ms in [8, 16, 24, 32]:
            rle = RLE(Ms=Ms, Mc=8)
            encoded = rle.encode(color_data)
            total_size = len(encoded) + 8  # +8 байт метаданных
            ratio = total_size / original_size

            if ratio < best_ratio:
                best_ratio = ratio
                best_Ms = Ms

            print(f"  Ms={Ms:2d} бит ({math.ceil(Ms / 8)} байт/символ): "
                  f"сжатый = {total_size:>10,} байт, коэффициент = {ratio:.4f}")




if __name__ == "__main__":
    main()