import cv2
import numpy as np
import os
import time
import tensorflow as tf
from tensorflow.keras.applications import VGG16
from tensorflow.keras.models import Model
from scipy.signal import savgol_filter
from sklearn.metrics.pairwise import cosine_similarity

FRAME_RATE = 1
KALMAN_Q = 0.01
KALMAN_R = 0.1

class SimpleKalmanFilter:
    def __init__(self, process_noise, measurement_noise):
        self.state = 0.0
        self.covariance = 1.0
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
    
    def update(self, measurement):
        predicted_state = self.state
        predicted_covariance = self.covariance + self.process_noise
        kalman_gain = predicted_covariance / (predicted_covariance + self.measurement_noise)
        self.state = predicted_state + kalman_gain * (measurement - predicted_state)
        self.covariance = (1 - kalman_gain) * predicted_covariance
        return self.state

def init_vgg_model():
    base_model = VGG16(weights='imagenet', include_top=False)
    return Model(inputs=base_model.input, outputs=base_model.get_layer('block5_pool').output)

def extract_features(model, image):
    image = cv2.resize(image, (224, 224))
    image = np.expand_dims(image, axis=0)
    image = tf.keras.applications.vgg16.preprocess_input(image)
    features = model.predict(image, verbose=0)
    return features.flatten()

def calculate_optical_flow(prev_frame, current_frame):
    if prev_frame is None or current_frame is None:
        return {'magnitude': 0, 'angle': 0, 'mean_x': 0, 'mean_y': 0, 'std_x': 0, 'std_y': 0}
    gray_prev = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    gray_curr = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    flow = cv2.calcOpticalFlowFarneback(gray_prev, gray_curr, None, pyr_scale=0.5, levels=5, winsize=25, iterations=10, poly_n=7, poly_sigma=1.5, flags=cv2.OPTFLOW_FARNEBACK_GAUSSIAN)
    flow_x = flow[..., 0]
    flow_y = flow[..., 1]
    mean_flow_x = np.mean(flow_x)
    mean_flow_y = np.mean(flow_y)
    std_flow_x = np.std(flow_x)
    std_flow_y = np.std(flow_y)
    magnitude = np.linalg.norm([mean_flow_x, mean_flow_y])
    angle = np.degrees(np.arctan2(mean_flow_y, mean_flow_x))
    return {'magnitude': magnitude, 'angle': angle, 'mean_x': mean_flow_x, 'mean_y': mean_flow_y, 'std_x': std_flow_x, 'std_y': std_flow_y}

def calculate_satellite_velocity_vector(velocity, pitch, yaw):
    vx = velocity * np.cos(np.radians(pitch)) * np.cos(np.radians(yaw))
    vy = velocity * np.cos(np.radians(pitch)) * np.sin(np.radians(yaw))
    vz = velocity * np.sin(np.radians(pitch))
    return (vx, vy, vz)

def calculate_wind_vector(wind_speed, wind_direction):
    wx = wind_speed * np.cos(np.radians(wind_direction))
    wy = wind_speed * np.sin(np.radians(wind_direction))
    wz = 0
    return (wx, wy, wz)

def generate_correction_command(similarity, flow_data, env_data, timestamp, current_frame):
    altitude = env_data['altitude']
    velocity = env_data['velocity']
    wind_speed = env_data['wind_speed']
    wind_direction = env_data['wind_direction']
    pressure = env_data['pressure']
    temperature = env_data['temperature']
    flow_angle = flow_data['angle']
    flow_magnitude = flow_data['magnitude']
    sat_velocity = calculate_satellite_velocity_vector(velocity, env_data['pitch'], env_data['yaw'])
    wind_vector = calculate_wind_vector(wind_speed, wind_direction)
    if similarity > 30:
        status = "Нормальное отклонение"
    elif similarity > 25:
        status = "Умеренное отклонение"
    elif similarity > 20:
        status = "Значительное отклонение"
    else:
        status = "КРИТИЧЕСКОЕ ОТКЛОНЕНИЕ"
    yaw_correction = -flow_angle * (1 - similarity/100)
    yaw_direction = get_direction(flow_angle)
    horizon_angle = detect_horizon_angle(current_frame)
    roll_correction = -horizon_angle * 0.7
    pitch_correction = calculate_pitch_correction(altitude, velocity, temperature)
    wind_correction = wind_speed * 0.3 * np.sin(np.radians(flow_angle))
    recommendation = f"""
=== Анализ траектории (t={timestamp:.1f}s) ===
Статус: {status} (схожесть: {similarity:.2f}%)
Основные параметры:
  Высота: {altitude:.1f} м | Скорость: {velocity:.1f} м/с
  Ветер: {wind_speed:.1f} м/с ({wind_direction:.1f}°) | Давление: {pressure:.1f} hPa | Температура: {temperature:.1f}°C

Рекомендации по коррекции:
1. Рыскание (Yaw): 
   - Угол: {yaw_correction:.2f}°
   - Направление: {yaw_direction}
   - Обоснование: Вектор оптического потока ({flow_angle:.1f}°)

2. Крен (Roll): 
   - Коррекция: {roll_correction:.2f}°
   - Обоснование: Наклон горизонта ({horizon_angle:.1f}°)

3. Тангаж (Pitch): 
   - Коррекция: {pitch_correction:.2f}°
   - Обоснование: Высота/скорость (V={velocity:.1f} м/с, H={altitude:.1f} м)

4. Ветровая коррекция:
   - Смещение: {wind_correction:.2f}°
   - Обоснование: Ветер {wind_speed:.1f} м/с

Дополнительные метрики:
- Магнитуда потока: {flow_magnitude:.4f}
- Стандартное отклонение X: {flow_data['std_x']:.4f}
- Стандартное отклонение Y: {flow_data['std_y']:.4f}
- Вектор скорости БЛА: X={sat_velocity[0]:.2f}, Y={sat_velocity[1]:.2f}, Z={sat_velocity[2]:.2f} м/с
- Вектор ветра: X={wind_vector[0]:.2f}, Y={wind_vector[1]:.2f}, Z={wind_vector[2]:.2f} м/с
"""
    return recommendation

def detect_horizon_angle(image):
    if image is None or image.size == 0:
        return 0.0
    try:
        small_img = cv2.resize(image, (640, 480))
        gray = cv2.cvtColor(small_img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10)
        if lines is None:
            return 0.0
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(x2 - x1) < 20:
                continue
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(angle) < 30:
                angles.append(angle)
        if not angles:
            return 0.0
        return np.median(angles)
    except Exception as e:
        print(f"Ошибка детекции горизонта: {str(e)}")
        return 0.0

def calculate_pitch_correction(altitude, velocity, temperature):
    base_correction = (altitude - 100) * 0.01 + (velocity - 15) * 0.05
    temp_factor = (temperature - 20) * 0.002
    return np.clip(base_correction + temp_factor, -10, 10)

def get_direction(angle):
    if angle < 0:
        angle += 360
    directions = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
    index = int((angle + 22.5) / 45) % 8
    return directions[index]

def get_environment_data(timestamp):
    return {
        'altitude': 100 + 5 * np.sin(timestamp/10),
        'velocity': 20 + 2 * np.cos(timestamp/5),
        'wind_speed': 8 + 3 * np.sin(timestamp/7),
        'wind_direction': 45 + 30 * np.sin(timestamp/12),
        'pressure': 1013 - 10 * np.cos(timestamp/8),
        'temperature': 25 + 10 * np.sin(timestamp/9),
        'pitch': 5 * np.sin(timestamp/11),
        'yaw': 10 * np.sin(timestamp/13)
    }

def process_videos(video_a2b, video_b2a, output_file):
    vgg_model = init_vgg_model()
    kalman_angle = SimpleKalmanFilter(KALMAN_Q, KALMAN_R)
    kalman_magnitude = SimpleKalmanFilter(KALMAN_Q, KALMAN_R)
    cap_a2b = cv2.VideoCapture(video_a2b)
    cap_b2a = cv2.VideoCapture(video_b2a)
    if not cap_a2b.isOpened() or not cap_b2a.isOpened():
        print("Ошибка открытия видеофайлов!")
        return []
    fps_a2b = cap_a2b.get(cv2.CAP_PROP_FPS)
    frame_interval = int(fps_a2b / FRAME_RATE)
    frame_count = 0
    prev_frame = None
    results = []
    with open(output_file, 'w') as f:
        f.write("ДЕТАЛИЗИРОВАННЫЕ РЕКОМЕНДАЦИИ ПО КОРРЕКЦИИ ТРАЕКТОРИИ\n")
        f.write("=" * 80 + "\n\n")
    while True:
        success_a2b, frame_a2b = cap_a2b.read()
        success_b2a, frame_b2a = cap_b2a.read()
        if not (success_a2b and success_b2a):
            break
        if frame_count % frame_interval != 0:
            frame_count += 1
            continue
        frame_b2a = cv2.rotate(frame_b2a, cv2.ROTATE_180)
        start_time = time.time()
        try:
            features_a2b = extract_features(vgg_model, frame_a2b)
            features_b2a = extract_features(vgg_model, frame_b2a)
            similarity = cosine_similarity([features_a2b], [features_b2a])[0][0] * 100
            flow_data = calculate_optical_flow(prev_frame, frame_a2b)
            if prev_frame is not None:
                filtered_angle = kalman_angle.update(flow_data['angle'])
                filtered_magnitude = kalman_magnitude.update(flow_data['magnitude'])
                flow_data['angle'] = filtered_angle
                flow_data['magnitude'] = filtered_magnitude
            timestamp_val = frame_count / fps_a2b
            env_data = get_environment_data(timestamp_val)
            command = generate_correction_command(similarity, flow_data, env_data, timestamp_val, frame_a2b)
            results.append((timestamp_val, similarity, command))
            with open(output_file, 'a') as f:
                f.write(command)
                f.write("\n" + "=" * 80 + "\n\n")
            print(f"Обработана секунда {timestamp_val:.1f}: схожесть={similarity:.2f}%")
            prev_frame = frame_a2b.copy()
        except Exception as e:
            print(f"Ошибка обработки кадра {frame_count}: {str(e)}")
        frame_count += 1
    cap_a2b.release()
    cap_b2a.release()
    return results

if __name__ == "__main__":
    print("Начало обработки видео...")
    start_time = time.time()
    results = process_videos("a2b.mp4", "b2a.mp4", "dp1140.txt")
    total_time = time.time() - start_time
    print(f"Обработка завершена за {total_time:.2f} секунд")
    print(f"Детализированные рекомендации сохранены в dp1140.txt")

