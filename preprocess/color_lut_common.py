# -*- coding: utf-8 -*-
"""
color_lut_common.py
COLOR/ 폴더의 원본(" (1).jpg")/보정본(접미사 없음) 쌍으로 휘도·채도 톤 커브를
학습해서, 같은 클래스의 검은 배경 사진에 적용하는 color_fix_*.py의 공용 로직.

B/G/R 채널을 각각 학습하면 배경 화이트밸런스 편향이 색조로 옮겨붙는 버그가 있어서,
휘도(밝기)는 R/G/B에 동일 비율로 곱하고 채도는 HSV S채널에만 적용해 색조를 보존한다.
"""

import glob
import os

import cv2
import numpy as np

N_BINS = 32
MIN_SAMPLES_PER_BIN = 30


def find_pair(color_dir: str, stem: str):
    orig_path = os.path.join(color_dir, f"{stem} (1).jpg")
    edited_path = os.path.join(color_dir, f"{stem}.jpg")
    if not (os.path.exists(orig_path) and os.path.exists(edited_path)):
        raise SystemExit(
            f"[에러] {color_dir}에 '{os.path.basename(orig_path)}' / "
            f"'{os.path.basename(edited_path)}' 쌍이 없음"
        )
    return orig_path, edited_path


def _fit_1d_lut(orig_vals: np.ndarray, edit_vals: np.ndarray, label: str) -> np.ndarray:
    bin_edges = np.linspace(0, 256, N_BINS + 1)
    bin_idx = np.clip(np.digitize(orig_vals, bin_edges) - 1, 0, N_BINS - 1)

    anchor_x, anchor_y = [], []
    for b in range(N_BINS):
        mask = bin_idx == b
        if mask.sum() >= MIN_SAMPLES_PER_BIN:
            anchor_x.append((bin_edges[b] + bin_edges[b + 1]) / 2)
            anchor_y.append(edit_vals[mask].mean())

    if len(anchor_x) < 2:
        raise SystemExit(f"[에러] {label}: 유효 구간이 너무 적음 (샘플 부족)")

    lut = np.interp(np.arange(256), anchor_x, anchor_y)
    return np.clip(lut, 0, 255).astype(np.uint8)


def fit_lut(pairs) -> dict:
    orig_gray_all, edit_gray_all = [], []
    orig_sat_all, edit_sat_all = [], []

    for orig_path, edited_path in pairs:
        o_img = cv2.imread(orig_path)
        e_img = cv2.imread(edited_path)
        orig_gray_all.append(cv2.cvtColor(o_img, cv2.COLOR_BGR2GRAY).ravel())
        edit_gray_all.append(cv2.cvtColor(e_img, cv2.COLOR_BGR2GRAY).ravel())
        orig_sat_all.append(cv2.cvtColor(o_img, cv2.COLOR_BGR2HSV)[:, :, 1].ravel())
        edit_sat_all.append(cv2.cvtColor(e_img, cv2.COLOR_BGR2HSV)[:, :, 1].ravel())

    lum_lut = _fit_1d_lut(np.concatenate(orig_gray_all), np.concatenate(edit_gray_all), "휘도")
    sat_lut = _fit_1d_lut(np.concatenate(orig_sat_all), np.concatenate(edit_sat_all), "채도")
    return {"lum": lum_lut, "sat": sat_lut}


def validate(luts: dict, pairs) -> None:
    errors = []
    for orig_path, edited_path in pairs:
        o_img = cv2.imread(orig_path)
        e_img = cv2.imread(edited_path)
        pred = apply_lut(o_img, luts)
        err = np.abs(pred.astype(np.int16) - e_img.astype(np.int16)).mean()
        errors.append(err)
        print(f"  검증 {os.path.basename(edited_path)}: 평균오차={err:.2f}")
    print(f"  전체 평균오차: {np.mean(errors):.2f}")


def apply_lut(img: np.ndarray, luts: dict) -> np.ndarray:
    lum_lut, sat_lut = luts["lum"], luts["sat"]

    orig_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    target_gray = cv2.LUT(orig_gray.astype(np.uint8), lum_lut).astype(np.float32)

    ratio = np.ones_like(orig_gray)
    nonzero = orig_gray > 1.0
    ratio[nonzero] = target_gray[nonzero] / orig_gray[nonzero]
    ratio = np.clip(ratio, 0.0, 4.0)

    scaled = np.clip(img.astype(np.float32) * ratio[:, :, None], 0, 255).astype(np.uint8)

    hsv = cv2.cvtColor(scaled, cv2.COLOR_BGR2HSV)
    hsv[:, :, 1] = cv2.LUT(hsv[:, :, 1], sat_lut)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def is_black_bg(img: np.ndarray, threshold: float = 80.0) -> bool:
    h, w = img.shape[:2]
    corners = [img[0:20, 0:20], img[0:20, w - 20:w], img[h - 20:h, 0:20], img[h - 20:h, w - 20:w]]
    return float(np.mean([c.mean() for c in corners])) < threshold


def run(class_name: str, color_stem: str, color_dir: str = "../COLOR",
        dataset_dir: str = "../dataset/images", output_dir: str = None,
        bg_threshold: float = 80.0) -> None:
    pair = find_pair(color_dir, color_stem)
    luts = fit_lut([pair])
    print(f"[{class_name}] LUT 학습 완료 ({color_stem}), 검증:")
    validate(luts, [pair])

    output_dir = output_dir or f"../color_fixed/{class_name}"
    os.makedirs(output_dir, exist_ok=True)

    paths = sorted(
        glob.glob(os.path.join(dataset_dir, "train", f"{class_name}_*.jpg"))
        + glob.glob(os.path.join(dataset_dir, "val", f"{class_name}_*.jpg"))
    )

    n_black, n_saved = 0, 0
    for p in paths:
        img = cv2.imread(p)
        if img is None:
            print(f"[경고] 읽기 실패: {p}")
            continue
        if not is_black_bg(img, bg_threshold):
            continue
        n_black += 1
        cv2.imwrite(os.path.join(output_dir, os.path.basename(p)), apply_lut(img, luts))
        n_saved += 1

    print(f"[{class_name}] 검은 배경 판정 {n_black}장, 저장 {n_saved}장 -> {output_dir}")
