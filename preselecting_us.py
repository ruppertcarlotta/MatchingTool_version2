from os import makedirs, listdir
from os.path import join, exists

import numpy as np
import pandas as pd
import random
from sklearn.utils import shuffle
import shutil


if __name__ == '__main__':
    random.seed(0)
    matched_dir = '/home/brayz/Desktop/2021_acr_birads_matched'
    img_per_class = 250

    selected_dir = join(matched_dir, 'preselected')

    if not exists(selected_dir):
        makedirs(selected_dir)

    match_xls = join(matched_dir, 'matching.xlsx')
    df = pd.read_excel(match_xls, header=None)
    new_header = df.iloc[0]
    df = df[1:]
    df.columns = new_header



    selected_files = {'2': [], '3': [], '4': [], '5': []}
    pre_selected = {'file': [], 'birads': [], 'acr': [], 'birth_year': [], 'session_nb': []}
    all_files = []
    for i in [2, 3, 4, 5]:
        img_names = df.query(f'birads=={str(i)}')['file']

        if i == 4 or i == 5:
            nb = img_per_class//2
        else:
            nb = img_per_class
        selected_files[str(i)] = random.sample(list(img_names), nb)
        all_files += selected_files[str(i)]


    for i, file in enumerate(all_files):
        pre_selected['file'].append(file)
        print(file)
        pre_selected['birads'].append(df.loc[df['file'] == file]['birads'].item())
        pre_selected['acr'].append(df.loc[df['file'] == file]['acr'].item())
        pre_selected['birth_year'].append(df.loc[df['file'] == file]['birth_year'].item())
        pre_selected['session_nb'].append(i)


    df_selected = pd.DataFrame.from_dict(pre_selected)
    df_selected = shuffle(df_selected)


    df_selected['session_nb'] = np.arange(len(all_files))

    for file in df_selected['file']:
        original = join(matched_dir, file)
        target = join(selected_dir, file)

        shutil.copyfile(original, target)

    df_selected.to_csv(join(selected_dir, 'matching.csv'), index=False)
    df_selected.to_excel(join(selected_dir, 'matching.xlsx'), index=False)

