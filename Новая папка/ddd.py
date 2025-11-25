

import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Путь к файлу
folder = r'C:\Users\kanske\Desktop\PLMControl-master (work)\Новая папка'
filename = '20000101_012608.csv'
filepath = os.path.join(folder, filename)

# Чтение CSV-файла, пропуская первые 9 строк
df = pd.read_csv(filepath, skiprows=9, header=None)

# Проверим первые строки
print(df.head())

# Извлекаем третий столбец (нумерация с нуля: 0, 1, 2)
signal = df[2].values  # 2-й индекс = 3-й столбец

# Построение временной оси
dt = 0.01000e-6  # 0.01000 мкс = 10 нс
time = np.arange(0, len(signal)) * dt

# График
plt.figure(figsize=(10, 5))
plt.plot(time * 1e6, signal, label='CH2', color='darkorange')  # умножаем на 1e6 для микросекунд
plt.xlabel('Время (мкс)')
plt.ylabel('Сигнал')
plt.title('Сигнал с магнитного зонда (CH2)')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
