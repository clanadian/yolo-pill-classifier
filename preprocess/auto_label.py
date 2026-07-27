# -*- coding: utf-8 -*-
"""
auto_label.py
알약 사진에서 바운딩 박스를 자동으로 뽑아 YOLO 포맷 라벨(.txt)을 생성합니다.

전제조건 (지금까지 촬영 규칙 그대로면 자동으로 만족됨):
- 프레임당 알약 1개
- 배경과 알약의 명암 대비가 있음 (흰/검 배경)
- 손이나 다른 물체가 크게 안 걸림

사용법:
    python auto_label.py --input_dir ./dataset_raw

입력 폴더 구조 (클래스별 폴더, 폴더 이름이 곧 클래스명):
    dataset_raw/
        capsule/          *.jpg
        green_caplet/     *.jpg
        mint_circle/      *.jpg
        pink_caplet/      *.jpg
        white_caplet/     *.jpg
        yellow_caplet/    *.jpg

출력:
    각 이미지 옆에 같은 이름의 .txt 라벨 파일 생성 (YOLO 포맷)
    실패한(=박스를 못 찾은) 이미지 목록 콘솔에 출력
    --review 옵션 주면 박스 그려진 미리보기 이미지를 _review 폴더에 저장 (육안 검수용)
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

# dataset/ 폴더 이름과 반드시 동일해야 함 (split_and_build.py의 CLASS_NAMES와도 순서 일치 필수)
CLASS_MAP = {
    "capsule": 0,
    "green_caplet": 1,
    "mint_circle": 2,
    "pink_caplet": 3,
    "white_caplet": 4,
    "yellow_caplet": 5,
}

IMG_EXTS = {".jpg", ".jpeg", ".png"}


def is_background_dark(img, border=15):
    """네 모서리 평균 밝기로 배경이 어두운지 판단 (알약은 항상 중앙 근처에 있다고 가정)."""
    h, w = img.shape[:2]
    b = min(border, h // 4, w // 4)
    corners = np.concatenate([
        img[:b, :b].reshape(-1, 3),
        img[:b, -b:].reshape(-1, 3),
        img[-b:, :b].reshape(-1, 3),
        img[-b:, -b:].reshape(-1, 3),
    ])
    return corners.mean() < 127


def find_pill_bbox(img):
    """이미지에서 가장 큰 전경 덩어리(=알약)의 바운딩 박스를 찾음. 실패 시 None."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    dark_bg = is_background_dark(img)
    if dark_bg:
        # 배경이 어두우니 밝은 영역 = 전경
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        # 배경이 밝으니 어두운 영역 = 전경
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel = np.ones((7, 7), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    h_img, w_img = img.shape[:2]
    img_area = h_img * w_img

    c = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(c)

    # 너무 작으면(노이즈) 실패 처리
    if area < img_area * 0.005:
        return None

    x, y, w, h = cv2.boundingRect(c)
    bbox_area = w * h

    # 라벨에 실제로 쓰는 건 boundingRect이므로 이 면적도 90% 기준으로 체크해야 함
    # (컨투어 면적만 체크하면, 배경 노이즈로 가늘고 길게 퍼진 컨투어의 외접 사각형이
    #  이미지 전체를 덮어도 통과해버림)
    if bbox_area > img_area * 0.9:
        return None

    # 채움비(컨투어 면적 / 외접 사각형 면적)가 너무 낮으면 알약 덩어리가 아니라
    # 흩어진 노이즈/그림자일 가능성이 높음
    extent = area / bbox_area if bbox_area > 0 else 0
    if extent < 0.35:
        return None

    return x, y, w, h


def to_yolo_line(class_id, x, y, w, h, img_w, img_h):
    cx = (x + w / 2) / img_w
    cy = (y + h / 2) / img_h
    nw = w / img_w
    nh = h / img_h
    return f"{class_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}\n"


def process(input_dir: Path, review: bool):
    review_dir = input_dir / "_review"
    if review:
        review_dir.mkdir(exist_ok=True)

    total, ok, failed = 0, 0, []

    for class_name, class_id in CLASS_MAP.items():
        class_dir = input_dir / class_name
        if not class_dir.exists():
            print(f"[경고] 폴더 없음: {class_dir} (스킵)")
            continue

        images = [p for p in class_dir.iterdir() if p.suffix.lower() in IMG_EXTS]
        for img_path in images:
            total += 1
            img = cv2.imread(str(img_path))
            if img is None:
                failed.append(str(img_path))
                continue

            bbox = find_pill_bbox(img)
            if bbox is None:
                failed.append(str(img_path))
                continue

            x, y, w, h = bbox
            h_img, w_img = img.shape[:2]
            line = to_yolo_line(class_id, x, y, w, h, w_img, h_img)

            label_path = img_path.with_suffix(".txt")
            label_path.write_text(line, encoding="utf-8")
            ok += 1

            if review:
                preview = img.copy()
                cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 0, 255), 3)
                cv2.imwrite(str(review_dir / f"{class_name}_{img_path.name}"), preview)

        print(f"{class_name:15s}: {len(images):4d}장 중 성공 {sum(1 for i in images if i.with_suffix('.txt').exists())}")

    print("\n=== 요약 ===")
    print(f"전체 {total}장 / 성공 {ok}장 / 실패 {len(failed)}장")
    if failed:
        print("\n실패한 이미지 (수동 확인 필요):")
        for f in failed:
            print(" -", f)
    if review:
        print(f"\n박스 미리보기가 {review_dir} 에 저장됐습니다. 훑어보면서 이상한 것만 골라내세요.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", required=True, help="클래스별 폴더가 들어있는 루트 경로")
    parser.add_argument("--review", action="store_true", help="박스 그려진 미리보기 이미지 저장")
    args = parser.parse_args()

    process(Path(args.input_dir), args.review)