# import json
#
# def remove_status_field(data):
#     for item in data:
#         if item.get('model') == 'orderitem':
#             if 'fields' in item and 'status' in item['fields']:
#                 del item['fields']['status']
#
# # Чтение данных из файла
# with open('fixtures.json', 'r', encoding='utf-8') as file:
#     json_data = json.load(file)
#
# # Удаление поля "status" из объектов "orderitem"
# remove_status_field(json_data)
#
# # Запись обновленных данных обратно в файл
# with open('fixtures.json', 'w', encoding='utf-8') as file:
#     json.dump(json_data, file, ensure_ascii=False, indent=4)
#

# import chardet
#
# # Открываем файл для чтения в бинарном режиме
# with open('store/subcategory_detail.html', 'rb') as file:
#     # Читаем первые несколько байтов из файла для определения кодировки
#     raw_data = file.read(10000)
#
# # Определяем кодировку с помощью модуля chardet
# encoding_result = chardet.detect(raw_data)['encoding']
#
# # Печатаем результат
# print("Результат определения кодировки:", encoding_result)
#
# # Теперь открываем файл для чтения с определенной кодировкой
# with open('store/subcategory_detail.html', 'r', encoding=encoding_result) as file:
#     content = file.read()

# for num in range(1, 26):
#     if num % 2 != 0:  # если не кратно 2, то точно не кратно 4 и 8 тоже
#         continue  # поэтому эту итерацию пропускаем
#     print(f'\nЧисло {num}')
#     print('Кратно 2')
#
#     if num % 4 != 0:
#         continue
#     print('Кратно 4')
#
#     if num % 8 != 0:
#         continue
#     print('Кратно 8')

# У лукоморья дуб зеленый.

# Введите предложение
# s = input()
#
# p = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~№41'
# c = ''
# for i in s:
#     if i not in p:
#         c += i
#
# words = c.lower().split()
# for w in words:
#     print(w[::-1])


# s = 0
# f = False
# for i in range(11):
#     x = int(input())
#     if x <= 0:
#         s += x
#         f = True
# if not f:
#     print('NO')
#
# print(s)

# def common_prefix(words):
#     if not words:
#         return ""
#
#     prefix = words[0]  # Берем первое слово в качестве начального префикса
#
#     # Проходим по остальным словам
#     for word in words[1:]:
#         # Обрезаем префикс до длины общего префикса
#         while not word.startswith(prefix):
#             prefix = prefix[:-1]
#
#     return prefix
#
# # Пример использования
# words = ["flower", "flow", "flight"]
# print("Общий префикс:", common_prefix(words))  # Вывод: "fl"


# def romanToInt(s):
#     # Создаем словарь для соответствия римских цифр и их арабских значений
#     rom_value = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
#     # Инициализируем результат
#     result = 0
#     # Инициализируем предыдущее значение, начинаем с последнего символа
#     prev_value = rom_value[s[-1]]
#     # Проходимся по строке справа налево
#     for i in range(len(s) - 1, -1, -1):
#         # Получаем текущее значение из словаря
#         curr_value = rom_value[s[i]]
#         # Если текущее значение больше или равно предыдущему, добавляем его к результату
#         if curr_value >= prev_value:
#             result += curr_value
#         else:
#             # Иначе, вычитаем его
#             result -= curr_value
#         # Обновляем значение предыдущего символа для следующей итерации
#         prev_value = curr_value
#     # Возвращаем итоговый результат
#     return result
#
# # Пример использования
# print(romanToInt('III'))     # Вывод: 3
# print(romanToInt('IV'))      # Вывод: 4
# print(romanToInt('IX'))      # Вывод: 9
# print(romanToInt('LVIII'))   # Вывод: 58
# print(romanToInt('MCMXCIV')) # Вывод: 1994

# def initials(name):
#     first_n, last_n = name.split()
#     initials = first_n[0].upper() + '.' + last_n[0].upper()
#     print(initials)
#
# initials('Sam Harris')


# class MyClass:
#     def __init__(self, x):
#         self.x = x
#
#     def print_x(self):
#         print(self.x)
#
# obj = MyClass(5)
# obj.print_x()  # Вызывает метод print_x() с экземпляром obj как аргумент self

# import json
#
# # Создаем словарь для хранения данных
# data = {
#     "Россия": "Москва",
#     "США": "Вашингтон",
#     "Китай": "Пекин"
# }
#
# # Добавление данных
# data["Франция"] = "Париж"
#
# # Удаление данных
# del data["Китай"]
#
# # Поиск данных
# country = "Россия"
# capital = data.get(country)
# if capital:
#     print(f"Столица страны {country} - {capital}")
# else:
#     print(f"Данные о стране {country} не найдены")
#
# # Редактирование данных
# data["США"] = "Нью-Йорк"
#
# # Сохранение данных
# with open("data.json", "w") as f:
#     json.dump(data, f)
#
# # Загрузка данных
# with open("data.json", "r") as f:
#     data = json.load(f)
#     print(data)
