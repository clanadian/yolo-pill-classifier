# -*- coding: utf-8 -*-
"""
train_yolo.py
dataset_yolo/(images/labels + data.yaml)를 이용해 YOLOv8 탐지 모델을 학습합니다.

data.yaml의 `path`는 만든 사람 컴퓨터의 절대경로로 박혀 있어 그대로 쓰면
다른 환경에서 어긋날 수 있습니다 (update.md 참고). 이를 피하기 위해
학습 시작 전에 data.yaml을 읽어 `path`를 이 스크립트 기준 실제 경로로
고쳐 임시 yaml로 저장한 뒤, 그 임시 yaml로 학습합니다. 원본 data.yaml은
건드리지 않습니다.

사용법:
    python train_yolo.py
    python train_yolo.py --model yolov8s.pt --epochs 100 --imgsz 640 --batch 16
    python train_yolo.py --device 0

학습이 끝나면 best.pt 위치를 출력하고, --export-best를 주면 저장소 루트에
best.pt로 복사합니다 (yolov8_cam.py가 루트의 best.pt를 그대로 읽음).
"""

import argparse
import shutil
import tempfile
from pathlib import Path

import yaml
from ultralytics import YOLO

REPO_ROOT = Path(__file__).resolve().parent.parent


def resolve_data_yaml(data_yaml: Path) -> Path:
    """data.yaml의 path를 이 컴퓨터 기준 절대경로로 고친 임시 yaml을 만들어 반환."""
    content = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    content["path"] = str(data_yaml.parent.resolve())

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    )
    yaml.safe_dump(content, tmp, allow_unicode=True, sort_keys=False)
    tmp.close()
    return Path(tmp.name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        type=Path,
        default=REPO_ROOT / "dataset_yolo" / "data.yaml",
        help="data.yaml 경로 (기본: dataset_yolo/data.yaml)",
    )
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="시작 가중치 (사전학습 pt 이름 또는 이어할 pt 경로, 기본 yolov8n.pt)",
    )
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--patience", type=int, default=30, help="조기 종료 patience")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--device",
        default=None,
        help="예: 0 / 0,1 / cpu / mps (기본: ultralytics 자동 선택)",
    )
    parser.add_argument("--project", default=str(REPO_ROOT / "runs"))
    parser.add_argument("--name", default="pill_yolo")
    parser.add_argument("--resume", action="store_true", help="가장 최근 학습 이어하기")
    parser.add_argument(
        "--export-best",
        action="store_true",
        help="학습 후 best.pt를 저장소 루트로 복사 (yolov8_cam.py용)",
    )
    args = parser.parse_args()

    if not args.data.exists():
        raise FileNotFoundError(f"data.yaml을 찾을 수 없습니다: {args.data}")

    tmp_data_yaml = resolve_data_yaml(args.data)
    try:
        model = YOLO(args.model)
        results = model.train(
            data=str(tmp_data_yaml),
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            patience=args.patience,
            workers=args.workers,
            device=args.device,
            project=args.project,
            name=args.name,
            resume=args.resume,
        )

        best_pt = Path(results.save_dir) / "weights" / "best.pt"
        print(f"\n학습 완료. best.pt: {best_pt}")

        if args.export_best:
            if best_pt.exists():
                dest = REPO_ROOT / "best.pt"
                shutil.copy2(best_pt, dest)
                print(f"best.pt를 저장소 루트로 복사했습니다: {dest}")
            else:
                print(f"[경고] best.pt를 찾을 수 없어 복사하지 못했습니다: {best_pt}")
    finally:
        tmp_data_yaml.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
