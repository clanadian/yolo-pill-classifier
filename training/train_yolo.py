# -*- coding: utf-8 -*-
"""
train_yolo.py
dataset/(images/labels + data.yaml)를 이용해 YOLOv8 탐지 모델을 학습합니다.

data.yaml의 `path`는 만든 사람 컴퓨터의 절대경로로 박혀 있어 그대로 쓰면
다른 환경에서 어긋날 수 있습니다 (update.md 참고). 이를 피하기 위해
학습 시작 전에 data.yaml을 읽어 `path`를 이 스크립트 기준 실제 경로로
고쳐 임시 yaml로 저장한 뒤, 그 임시 yaml로 학습합니다. 원본 data.yaml은
건드리지 않습니다. data.yaml이 아예 없으면 폴더 구조를 보고 새로 만듭니다.

사용법:
    python training/train_yolo.py
    python training/train_yolo.py --model yolov8s.pt --epochs 100 --imgsz 640 --batch 16
    python training/train_yolo.py --device 0 --export-best

    # Colab (T4 GPU)
    !python training/train_yolo.py --data /content/dataset/data.yaml --workers 2 --export-best

    # 빠른 동작 확인 (2 epoch만)
    python training/train_yolo.py --epochs 2 --name smoke

학습이 끝나면 best.pt 위치를 출력하고, --export-best를 주면 model/best.pt로
복사합니다 (stream/server.py가 이 경로를 기본값으로 읽음).
"""

import argparse
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

import yaml
from ultralytics import YOLO

REPO_ROOT = Path(__file__).resolve().parent.parent

# auto_label.py의 CLASS_MAP, split_and_build.py의 CLASS_NAMES와 순서가 반드시 같아야 함.
# 이 순서가 곧 라벨 .txt의 class_id (0~5).
CLASS_NAMES = [
    "capsule",
    "green_caplet",
    "mint_circle",
    "pink_caplet",
    "white_caplet",
    "yellow_caplet",
]

IMG_EXTS = {".jpg", ".jpeg", ".png"}

# neg_black_*, neg_white_* 등은 알약이 없는 배경만 찍은 네거티브 샘플이라
# 라벨이 비어 있는 게 정상이다 (YOLO 포맷에서 빈 라벨 = 객체 0개).
NEG_PREFIX = "neg_"

# 데이터셋 폴더 이름이 환경마다 다르다.
#   로컬  : dataset/
#   Colab : dataset_yolo/            (train_on_colab.ipynb가 zip을 여기로 품)
#   리사이즈 사본 : dataset_yolo_colab/  (resize_for_colab.py 출력)
# --data를 따로 주지 않으면 아래 순서로 실제 존재하는 폴더를 찾는다.
DATASET_CANDIDATES = ("dataset", "dataset_yolo", "dataset_yolo_colab")


def autodetect_dataset() -> Path:
    """--data 미지정 시 저장소 안에서 데이터셋 폴더를 찾아 data.yaml 경로를 돌려준다."""
    found = [REPO_ROOT / n for n in DATASET_CANDIDATES
             if (REPO_ROOT / n / "images" / "train").is_dir()]
    if not found:
        raise FileNotFoundError(
            "데이터셋 폴더를 찾지 못했습니다. 다음 중 하나가 있어야 합니다:\n"
            + "\n".join(f"  {REPO_ROOT / n}/images/train" for n in DATASET_CANDIDATES)
            + "\n또는 --data 로 data.yaml 경로를 직접 지정하세요."
        )
    if len(found) > 1:
        print(f"[안내] 데이터셋 폴더가 여러 개입니다 {[f.name for f in found]} "
              f"→ '{found[0].name}' 사용 (바꾸려면 --data 지정)")
    print(f"데이터셋: {found[0]}")
    return found[0] / "data.yaml"


def ensure_data_yaml(data_yaml: Path) -> Path:
    """data.yaml이 없으면 폴더 구조를 보고 새로 만든다.

    split_and_build.py가 data.yaml까지 만들어 주지만, 데이터셋만 따로 받거나
    Colab에 압축을 풀어 올린 경우 yaml이 빠져 있는 일이 잦다.
    """
    if data_yaml.exists():
        return data_yaml

    dataset_dir = data_yaml.parent
    if not (dataset_dir / "images" / "train").is_dir():
        raise FileNotFoundError(
            f"data.yaml도 없고 {dataset_dir/'images'/'train'} 도 없습니다.\n"
            f"split_and_build.py를 먼저 실행했는지 확인하세요."
        )

    names_block = "\n".join(f"  {i}: {name}" for i, name in enumerate(CLASS_NAMES))
    data_yaml.write_text(
        f"path: {dataset_dir.resolve()}\n"
        f"train: images/train\n"
        f"val: images/val\n"
        f"names:\n{names_block}\n",
        encoding="utf-8",
    )
    print(f"data.yaml이 없어 새로 만들었습니다: {data_yaml}")
    return data_yaml


def preflight(dataset_dir: Path):
    """학습 전에 데이터셋이 멀쩡한지 검사. 치명적 문제가 있으면 즉시 종료.

    한 번 학습을 시작하면 수십 분이 날아가므로, 몇 초짜리 검사로 먼저 거른다.
    특히 이미지-라벨 짝이 깨지면 ultralytics는 조용히 건너뛰기만 해서
    학습이 '성공'한 것처럼 보이는데 실제로는 데이터가 빠져 있다.
    """
    problems = []
    counts = {}
    neg_counts = {}

    for split in ("train", "val"):
        img_dir = dataset_dir / "images" / split
        lbl_dir = dataset_dir / "labels" / split

        if not img_dir.is_dir() or not lbl_dir.is_dir():
            problems.append(f"폴더 없음: {img_dir if not img_dir.is_dir() else lbl_dir}")
            continue

        images = [p for p in img_dir.iterdir() if p.suffix.lower() in IMG_EXTS]
        if not images:
            problems.append(f"이미지가 한 장도 없음: {img_dir}")
            continue

        per_class = Counter()
        missing, empty, bad, huge = [], [], [], []
        neg_count = 0

        for img_path in images:
            lbl_path = lbl_dir / (img_path.stem + ".txt")
            if not lbl_path.exists():
                missing.append(img_path.name)
                continue

            lines = [l for l in lbl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            if not lines:
                if img_path.name.lower().startswith(NEG_PREFIX):
                    neg_count += 1
                else:
                    empty.append(img_path.name)
                continue

            for line in lines:
                parts = line.split()
                if len(parts) != 5:
                    bad.append(f"{lbl_path.name}(필드 {len(parts)}개)")
                    continue
                cid = int(float(parts[0]))
                if not 0 <= cid < len(CLASS_NAMES):
                    bad.append(f"{lbl_path.name}(class_id={cid})")
                    continue
                per_class[cid] += 1
                # 박스가 화면 절반을 넘으면 auto_label.py가 배경/그림자를 잡았을 가능성이 큼
                if float(parts[3]) * float(parts[4]) > 0.5:
                    huge.append(lbl_path.name)

        counts[split] = per_class
        neg_counts[split] = neg_count

        if missing:
            problems.append(f"[{split}] 라벨 없는 이미지 {len(missing)}장: {missing[:5]}")
        if empty:
            problems.append(f"[{split}] 빈 라벨(네거티브 아님) {len(empty)}개: {empty[:5]}")
        if bad:
            problems.append(f"[{split}] 형식/class_id 이상 {len(bad)}개: {bad[:5]}")
        if huge:
            # 치명적이진 않으므로 경고만 하고 학습은 계속 진행
            print(f"[경고] {split}: 박스가 이미지의 50%를 넘는 라벨 {len(huge)}개 "
                  f"→ {huge[:5]} (auto_label.py --review 로 확인 권장)")

    if problems:
        print("\n=== 데이터셋 문제 발견, 학습을 중단합니다 ===")
        for p in problems:
            print(" -", p)
        sys.exit(1)

    print(f"\n{'클래스':15s} {'train':>7s} {'val':>7s}")
    for cid, name in enumerate(CLASS_NAMES):
        print(f"{name:15s} {counts['train'][cid]:7d} {counts['val'][cid]:7d}")
    print(f"{'합계':15s} {sum(counts['train'].values()):7d} {sum(counts['val'].values()):7d}")
    print(f"{'negative':15s} {neg_counts.get('train', 0):7d} {neg_counts.get('val', 0):7d}")

    if not counts.get("val"):
        print("[경고] val 셋이 비어 있어 검증 지표를 볼 수 없습니다.")


def resolve_data_yaml(data_yaml: Path) -> Path:
    """data.yaml의 path를 이 컴퓨터 기준 절대경로로 고친 임시 yaml을 만들어 반환."""
    content = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    content["path"] = str(data_yaml.parent.resolve())

    # 라벨의 class_id와 yaml의 names가 어긋나면 지표는 멀쩡한데 예측만 틀리는
    # 최악의 버그가 되므로 여기서 잡는다.
    names = content.get("names")
    if isinstance(names, dict):
        names = [names[k] for k in sorted(names)]
    if names and list(names) != CLASS_NAMES:
        print(f"[경고] data.yaml의 names가 CLASS_NAMES와 다릅니다.\n"
              f"  yaml : {list(names)}\n"
              f"  코드 : {CLASS_NAMES}")

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    )
    yaml.safe_dump(content, tmp, allow_unicode=True, sort_keys=False)
    tmp.close()
    return Path(tmp.name)


def report(metrics, model):
    """클래스별 성능 표. 색이 비슷한 알약끼리 섞이는지 여기서 드러난다."""
    print("\n=== 클래스별 성능 ===")
    try:
        names = model.names
        print(f"{'클래스':15s} {'mAP50':>8s} {'mAP50-95':>10s}")
        for i, cid in enumerate(list(metrics.box.ap_class_index)):
            print(f"{names[cid]:15s} {metrics.box.ap50[i]:8.3f} {metrics.box.maps[cid]:10.3f}")
        print(f"{'전체':15s} {metrics.box.map50:8.3f} {metrics.box.map:10.3f}")
    except Exception as e:  # ultralytics 버전에 따라 속성명이 다를 수 있음
        print(f"(클래스별 표 생성 실패: {e})")


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 알약 탐지 학습")
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="data.yaml 경로 (기본: dataset/ → dataset_yolo/ → dataset_yolo_colab/ 순으로 자동 탐지, "
             "yaml이 없으면 자동 생성)",
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
    parser.add_argument("--workers", type=int, default=8,
                        help="Colab은 CPU가 2코어뿐이라 --workers 2 권장")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--device",
        default=None,
        help="예: 0 / 0,1 / cpu / mps (기본: ultralytics 자동 선택)",
    )
    parser.add_argument("--project", default=str(REPO_ROOT / "runs"))
    parser.add_argument("--name", default="pill_yolo")
    parser.add_argument("--resume", action="store_true", help="가장 최근 학습 이어하기")
    parser.add_argument("--skip-check", action="store_true", help="데이터셋 사전 검사 건너뛰기")
    parser.add_argument(
        "--export-best",
        action="store_true",
        help="학습 후 best.pt를 model/ 폴더로 복사 (stream/server.py 기본 경로)",
    )
    args = parser.parse_args()

    data_yaml = ensure_data_yaml(args.data if args.data else autodetect_dataset())
    if not args.skip_check:
        preflight(data_yaml.parent)

    tmp_data_yaml = resolve_data_yaml(data_yaml)
    try:
        model = YOLO(args.model)
        results = model.train(
            data=str(tmp_data_yaml),
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            patience=args.patience,
            workers=args.workers,
            seed=args.seed,
            device=args.device,
            project=args.project,
            name=args.name,
            resume=args.resume,
            plots=True,

            # --- 색 증강: 알약 6종 중 4종이 '색'으로만 구분되므로 색조(hue)는 건드리지 않는다.
            #     대신 밝기/채도는 어느 정도 흔들어 준다. 학습 사진은 폰 촬영인데
            #     실제 데모는 웹캠이라 조명 조건이 다르기 때문.
            hsv_h=0.0,
            hsv_s=0.3,
            hsv_v=0.4,

            # --- 기하 증강: 알약은 정해진 방향이 없어 마음껏 돌리고 뒤집어도 된다.
            degrees=180.0,
            translate=0.2,
            scale=0.5,
            fliplr=0.5,
            flipud=0.5,

            # --- mosaic: 데이터셋이 전부 '한 장에 알약 1개'인데 웹캠에서는 여러 개가 잡힌다.
            #     mosaic이 유일하게 다중 객체 장면을 만들어 주므로 켜 두고,
            #     마지막 10 epoch만 꺼서 실제 분포에 맞춰 마무리한다.
            mosaic=1.0,
            close_mosaic=10,
        )

        # model.train()이 마지막에 이미 best.pt로 검증을 돌리므로 그 결과를 그대로 쓴다.
        # 여기서 model.val()을 또 부르면 같은 계산을 반복하고 runs/detect/val 폴더까지 새로 생긴다.
        report(results, model)

        best_pt = Path(results.save_dir) / "weights" / "best.pt"
        print(f"\n학습 완료. best.pt: {best_pt}")

        if args.export_best:
            if best_pt.exists():
                dest = REPO_ROOT / "model" / "best.pt"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(best_pt, dest)
                print(f"best.pt를 model/ 폴더로 복사했습니다: {dest}")
            else:
                print(f"[경고] best.pt를 찾을 수 없어 복사하지 못했습니다: {best_pt}")
    finally:
        tmp_data_yaml.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
