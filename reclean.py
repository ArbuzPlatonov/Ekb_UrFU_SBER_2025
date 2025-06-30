import os
import shutil
import subprocess

def run_cleaner_script():
    subprocess.run(['python', 'Cleaner.py'])

def create_reversed_folder(source_folder, destination_folder):
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
    files = sorted(os.listdir(source_folder), reverse=True)
    for i, filename in enumerate(files):
        file_path = os.path.join(source_folder, filename)
        if os.path.isfile(file_path):
            new_filename = f"frame_{i}.jpg"
            new_file_path = os.path.join(destination_folder, new_filename)
            shutil.copy(file_path, new_file_path)

def duplicate_folder(source_folder, destination_folder):
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
    for filename in sorted(os.listdir(source_folder)):
        file_path = os.path.join(source_folder, filename)
        if os.path.isfile(file_path):
            new_file_path = os.path.join(destination_folder, filename)
            shutil.copy(file_path, new_file_path)

if __name__ == "__main__":
    run_cleaner_script()
    create_reversed_folder('b2a_foto_analiz', 'b2a')
    duplicate_folder('a2b_foto_analiz', 'a2b')
    print("Процесс завершен.")
