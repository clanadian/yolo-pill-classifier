# -*- coding: utf-8 -*-
"""Jetson에서 YOLO .pt를 Ultralytics 호환 TensorRT engine으로 빌드한다."""

import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from ultralytics import YOLO, __version__


TRTEXEC_CANDIDATES = (
    Path("/usr/src/tensorrt/bin/trtexec"),
    Path("/usr/src/tensorrt/samples/trtexec"),
)


def find_trtexec(explicit=None):
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return path
        raise FileNotFoundError("trtexec를 찾을 수 없습니다: {}".format(path))

    command = shutil.which("trtexec")
    if command:
        return Path(command)
    for path in TRTEXEC_CANDIDATES:
        if path.is_file():
            return path
    raise FileNotFoundError("TensorRT trtexec를 찾을 수 없습니다")


def add_ultralytics_metadata(raw_engine, output, model, imgsz, precision):
    """trtexec 바이너리 앞에 Ultralytics가 기대하는 JSON 헤더를 붙인다."""
    metadata = {
        "description": "YOLOv8 pill detector, TensorRT {} for Jetson".format(
            precision.upper()
        ),
        "author": "yolo-pill-classifier",
        "date": datetime.now().isoformat(),
        "version": __version__,
        "license": "AGPL-3.0 License (https://ultralytics.com/license)",
        "docs": "https://docs.ultralytics.com",
        "stride": int(max(model.model.stride)),
        "task": "detect",
        "batch": 1,
        "imgsz": [imgsz, imgsz],
        "names": model.names,
    }
    payload = json.dumps(metadata)
    with output.open("wb") as dst, raw_engine.open("rb") as src:
        dst.write(len(payload).to_bytes(4, byteorder="little", signed=True))
        dst.write(payload.encode())
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def build(args):
    weights = args.weights.resolve()
    model = YOLO(str(weights), task="detect")
    onnx_path = Path(
        model.export(
            format="onnx",
            imgsz=args.imgsz,
            opset=args.opset,
            simplify=False,
            dynamic=False,
        )
    )

    output = args.output or weights.with_name(
        "{}_{}.engine".format(weights.stem, args.precision)
    )
    output = output.resolve()
    raw_engine = output.with_name(output.stem + ".raw.engine")
    command = [
        str(find_trtexec(args.trtexec)),
        "--onnx={}".format(onnx_path.resolve()),
        "--saveEngine={}".format(raw_engine),
        "--workspace={}".format(args.workspace),
    ]
    if args.precision == "fp16":
        command.append("--fp16")

    print("[TensorRT] 실행:", " ".join(command))
    subprocess.run(command, check=True)
    add_ultralytics_metadata(raw_engine, output, model, args.imgsz, args.precision)
    raw_engine.unlink()
    print("[TensorRT] Ultralytics 호환 엔진:", output)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, default=Path("model/best.pt"))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--precision", choices=("fp16", "fp32"), default="fp16")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--opset", type=int, default=12)
    parser.add_argument("--workspace", type=int, default=512, help="MiB")
    parser.add_argument("--trtexec", default=None)
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
