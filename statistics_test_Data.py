
from os.path import join
from os import listdir
import pandas as pd
from collections import Counter
import matplotlib.pyplot as plt

test_dir = '/home/brayz/Desktop/TEST_DATA_US'


match_xls = join(test_dir, 'all_files_information.csv')
df = pd.read_csv(match_xls, header=None)
new_header = df.iloc[0]
df = df[1:]
df.columns = new_header

mylist = list(df['file'])

cnt = Counter(mylist)
double_list = [k for k, v in cnt.items() if v > 1]
birads_dist = []
acr_dist = []
birthyear_dist = []
for file in listdir(test_dir):
    if file.endswith('.png'):
        file_name = file[:-4]
        file_name += '.dcm'
        if file_name in double_list:
            print(file_name)
        else:
            row = df.loc[lambda df: df['file'] == file_name, :]
            birads_dist.append(int(row['birads']))
            acr_dist.append(df.loc[lambda df: df['file'] == file_name, 'acr'].values[0])

            #print(df['acr'].where(df['file'] == file_name))
            birthyear_dist.append(int(row['birth_year']))

birads_dist += [2, 5, 4, 3, 2, 4, 4,2]
acr_dist += ['b', 'c', 'c', 'd', 'c', 'd']
birthyear_dist += [1949, 1946, 1969, 1958, 1950, 1965, 1973, 1967]



counter=Counter(birads_dist)
print(counter)


counter=Counter(birthyear_dist)
print(counter)
plt.bar(counter.keys(), counter.values())
plt.show()


labels = ['A', 'B', 'C', 'D', 'unknown']
values = [13, 35, 51, 21, 32]
plt.bar(labels, values, color=["C0","C0","C0","C0", "grey"])
plt.xlabel('Breast Density ACR Score')
plt.ylabel('Occurence')
plt.show()


