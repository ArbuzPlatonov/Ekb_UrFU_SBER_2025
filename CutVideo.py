import cv2
import os

def extract_frames(video_path, output_folder, frame_rate):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    success = True
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(video_fps / frame_rate)
    while success:
        success, frame = cap.read()
        if success and frame_count % frame_interval == 0:
            frame_filename = os.path.join(output_folder, f"frame_{frame_count // frame_interval}.jpg")
            cv2.imwrite(frame_filename, frame)
        frame_count += 1
    cap.release()

video_a2b = 'a2b.mp4'
video_b2a = 'b2a.mp4'
frame_rate = 1

extract_frames(video_a2b, 'a2b_foto', frame_rate)
extract_frames(video_b2a, 'b2a_foto', frame_rate)

print("Кадры успешно извлечены и сохранены в соответствующие папки.")
