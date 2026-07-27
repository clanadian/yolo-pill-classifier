# -*- coding: utf-8 -*-
"""
split_and_build.py
auto_label.py로 라벨(.txt)까지 생성된 클래스별 폴더를,
YOLOv8이 바로 학습할 수 있는 최종 구조로 정리합니다.

규칙:
- 클래스별로 라벨까지 붙은 이미지를 무작위 셔플 후 val_ratio 비율만큼 검증(val)셋으로 분리

사용법:
    python split_and_build.py --input_dir ./dataset_raw --output_dir ./dataset --val_ratio 0.15

출력 구조:
    dataset/
        images/train/*.jpg
        images/val/*.jpg
        labels/train/*.txt
        labels/val/*.txt
        data.yaml
"""

import argparse
import random
import shutil
from pathlib import Path

CLASS_NAMES = [
    "capsule",
    "green_caplet",
    "mint_circle",
    "pink_caplet",
    "white_caplet",
    "yellow_caplet",
]

IMG_EXTS = {".jpg", ".jpeg", ".png"}


def split_one_class(class_dir: Path, val_ratio: float, seed: int):
    images = [p for p in class_dir.iterdir() if p.suffix.lower() in IMG_EXTS]
    labeled = [p for p in images if p.with_suffix(".txt").exists()]
    skipped = len(images) - len(labeled)

    rng = random.Random(seed)
    rng.shuffle(labeled)

    n_val = max(1, round(len(labeled) * val_ratio)) if labeled else 0
    val_set = labeled[:n_val]
    train_set = labeled[n_val:]

    return train_set, val_set, skipped


def copy_pair(img_path: Path, class_name: str, split: str, out_dir: Path):
    # auto_label.py numbers each class's images independently from 000, so filenames
    # collide across classes without this prefix (e.g. capsule/000.jpg vs pink_caplet/000.jpg).
    stem = f"{class_name}_{img_path.stem}"
    shutil.copy2(img_path, out_dir / "images" / split / f"{stem}{img_path.suffix}")
    shutil.copy2(img_path.with_suffix(".txt"), out_dir / "labels" / split / f"{stem}.txt")


def build(input_dir: Path, output_dir: Path, val_ratio: float, seed: int):
    for split in ("train", "val"):
        (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    summary = []
    for class_name in CLASS_NAMES:
        class_dir = input_dir / class_name
        if not class_dir.exists():
            print(f"[경고] 폴더 없음: {class_dir} (스킵)")
            continue

        train_set, val_set, skipped = split_one_class(class_dir, val_ratio, seed)

        for p in train_set:
            copy_pair(p, class_name, "train", output_dir)
        for p in val_set:
            copy_pair(p, class_name, "val", output_dir)

        summary.append((class_name, len(train_set), len(val_set), skipped))

    print(f"{'클래스':15s} {'train':>6s} {'val':>6s} {'라벨없어제외':>10s}")
    for row in summary:
        print(f"{row[0]:15s} {row[1]:6d} {row[2]:6d} {row[3]:10d}")

    yaml_path = output_dir / "data.yaml"
    names_block = "\n".join(f"  {i}: {name}" for i, name in enumerate(CLASS_NAMES))
    # path를 안 쓰면 ultralytics가 이 yaml 파일이 있는 폴더를 기준으로 잡아서
    # 컴퓨터마다 절대경로를 고쳐야 하는 문제가 없어짐 (update.md 참고)
    yaml_content = (
        f"train: images/train\n"
        f"val: images/val\n"
        f"names:\n{names_block}\n"
    )
    yaml_path.write_text(yaml_content, encoding="utf-8")
    print(f"\ndata.yaml 생성 완료: {yaml_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", required=True, help="auto_label.py 실행 후의 클래스별 폴더 루트")
    parser.add_argument("--output_dir", required=True, help="YOLO 학습용 최종 출력 경로 (보통 ./dataset)")
    parser.add_argument("--val_ratio", type=float, default=0.15, help="검증셋 비율 (기본 0.15)")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    build(Path(args.input_dir), Path(args.output_dir), args.val_ratio, args.seed)