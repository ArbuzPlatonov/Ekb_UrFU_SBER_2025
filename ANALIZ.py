import os
import cv2
import numpy as np
from keras.applications import VGG16
from keras.applications.vgg16 import preprocess_input
from keras.models import Model
from sklearn.metrics.pairwise import cosine_similarity
import subprocess
import time

base_model = VGG16(weights='imagenet', include_top=False)
model = Model(inputs=base_model.input, outputs=base_model.get_layer('block5_pool').output)

def extract_features(image_path):
    image = cv2.imread(image_path)
    image = cv2.resize(image, (224, 224))
    image = np.expand_dims(image, axis=0)
    image = preprocess_input(image)
    features = model.predict(image)
    return features.flatten()

def compare_images(image1_path, image2_path):
    features1 = extract_features(image1_path)
    features2 = extract_features(image2_path)
    similarity = cosine_similarity([features1], [features2])
    similarity_percentage = similarity[0][0] * 100
    return similarity_percentage

def run_reclean_script():
    subprocess.run(['python', 'reclean.py'])

def compare_folders(folder_a2b, folder_b2a, result_file):
    files_a2b = sorted(os.listdir(folder_a2b))
    files_b2a = sorted(os.listdir(folder_b2a))
    with open(result_file, 'w') as f:
        for i, (file_a2b, file_b2a) in enumerate(zip(files_a2b, files_b2a)):
            image1_path = os.path.join(folder_a2b, file_a2b)
            image2_path = os.path.join(folder_b2a, file_b2a)
            if os.path.isfile(image1_path) and os.path.isfile(image2_path):
                start_time = time.time()
                similarity_score = compare_images(image1_path, image2_path)
                end_time = time.time()
                processing_time = end_time - start_time
                f.write(f"Пара {i+1} - Схожесть: {similarity_score:.2f}% - Время обработки: {processing_time:.2f} секунд\n")
            else:
                break

if __name__ == "__main__":
    run_reclean_script()
    compare_folders('a2b', 'b2a', 'result.txt')
    print("Сравнение завершено. Результаты сохранены в result.txt.")
