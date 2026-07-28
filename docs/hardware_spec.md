# 하드웨어 스펙

## 웹캠

- Device        : USB2.0 PC CAMERA
- Driver        : uvcvideo (UVC)
- Interface     : USB 2.0
- Video Device  : /dev/video0
- Pixel Format  : YUYV (YUYV 4:2:2)

Supported Resolutions
- 640×480 @ 30 FPS / 15 FPS
- 352×288 @ 30 FPS / 15 FPS
- 320×240 @ 30 FPS / 15 FPS
- 176×144 @ 30 FPS / 15 FPS
- 160×120 @ 30 FPS / 15 FPS

확인 명령어:
```bash
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
```

## Jetson Nano

- 모델        : Jetson Nano (t210ref)
- L4T 버전    : R32.6.1 (REVISION: 6.1, GCID: 27863751)
- JetPack 버전 : 4.6 (nvidia-jetpack 4.6-b199)
- CUDA 버전   : 10.2.300
- 커널/아키텍처 : Linux 4.9.253-tegra aarch64

확인 명령어 (Jetson Nano 보드에서 실행):
```bash
cat /etc/nv_tegra_release          # L4T 버전 (예: R32 (release), REVISION: 7.1 → JetPack 4.6.1)
sudo apt-cache show nvidia-jetpack | grep -i version   # JetPack 메타패키지 버전 (설치돼 있는 경우)
dpkg-query --show nvidia-l4t-core  # L4T core 패키지 버전
nvcc --version                     # CUDA 버전 (nvcc 설치돼 있는 경우)
cat /usr/local/cuda/version.txt    # CUDA 버전 (대안)
uname -a                           # 커널/아키텍처
python3 -c "import cv2; print(cv2.__version__)"   # OpenCV 버전
```

`jetson-stats`(`jtop`)가 설치돼 있다면 `jetson_release` 한 줄로 위 항목 대부분을 한 번에 볼 수 있음:
```bash
pip install -U jetson-stats
jetson_release
```
