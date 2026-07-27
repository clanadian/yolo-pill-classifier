import cv2
from ultralytics import YOLO

#model = YOLO("best.pt")
#results = model.predict(source="D:\DeepLearning\티처블머신_가위바위보\dataset\class_03", conf=0.25)
#exit()

# 1. YOLOv8 사전 학습 모델 로드
#model = YOLO('yolov8n.pt')
model = YOLO('best.pt')
# 2. 웹캠 열기 (0은 기본 내장/외장 카메라)
cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    
    if success:
        # 3. 프레임 단위로 객체 탐지 수행
        results = model(frame,conf=0.25, iou=0.75)
#        results = model.track(frame, persist=True)
        
        # 4. 프레임에 탐지된 결과를 시각화
        annotated_frame = results[0].plot()
        
        # 5. 결과 화면 출력
        cv2.imshow("YOLOv8 Webcam", annotated_frame)
        
        # 6. 'q' 키를 누르면 종료
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    else:
        break

# 7. 카메라 해제 및 창 닫기
cap.release()
cv2.destroyAllWindows()