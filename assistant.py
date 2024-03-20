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

t = input()
s = '!'
c = 0
for i in t:
    if i == s:
        c += 1
print(c)