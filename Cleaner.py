import os
import cv2
import numpy as np
import subprocess

def run_cut_video_script():
    subprocess.run(['python', 'CutVideo.py'])

def is_noisy_image(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    std_dev = image.std()
    mean_brightness = image.mean()
    hist = cv2.calcHist([image], [0], None, [256], [0, 256])
    hist_range = np.ptp(hist)
    is_noisy = (std_dev < 15) or (mean_brightness < 50 or mean_brightness > 200) or (hist_range < 50)
    return is_noisy

def filter_images(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    for filename in os.listdir(input_folder):
        file_path = os.path.join(input_folder, filename)
        if os.path.isfile(file_path) and not is_noisy_image(file_path):
            output_path = os.path.join(output_folder, filename)
            cv2.imwrite(output_path, cv2.imread(file_path))

def process_folders():
    folders = ['a2b_foto', 'b2a_foto']
    for folder in folders:
        input_folder = folder
        output_folder = f"{folder}_analiz"
        filter_images(input_folder, output_folder)

if __name__ == "__main__":
    run_cut_video_script()
    process_folders()
    print("Фильтрация завершена. Кадры без помех сохранены в соответствующие папки.")
