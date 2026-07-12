"""
구간별로 나눠서 수집한 여러 엑셀 파일(예: 개드립_p1-9.xlsx, 개드립_p10-19.xlsx, ...)을
하나로 합치는 스크립트.

- post_id가 겹치는 경우(같은 게시글이 두 구간에 중복 수집된 경우) 중복 제거
- id 컬럼은 합친 후 1부터 다시 순서대로 부여

사용법:
  python merge_excels.py output/개드립_p1-9.xlsx output/개드립_p10-19.xlsx output/개드립_p20-29.xlsx --out output/개드립_최종.xlsx
"""
import argparse

import pandas as pd

from crawler_utils import logger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", help="합칠 엑셀 파일 경로들")
    parser.add_argument("--out", required=True, help="최종 저장 경로")
    args = parser.parse_args()

    dfs = []
    for f in args.files:
        df = pd.read_excel(f)
        logger.info(f"{f}: {len(df)}행 로드")
        dfs.append(df)

    merged = pd.concat(dfs, ignore_index=True)
    before = len(merged)

    # post_id + type + text 조합으로 완전 중복된 행만 제거 (구간이 겹쳐서 같은 게시글이 두 번 들어간 경우 대비)
    merged = merged.drop_duplicates(subset=["post_id", "type", "text"], keep="first")
    after = len(merged)
    if before != after:
        logger.info(f"중복 제거: {before}행 -> {after}행")

    # id 컬럼 재부여
    merged = merged.reset_index(drop=True)
    merged["id"] = merged.index + 1

    merged.to_excel(args.out, index=False)
    logger.info(f"저장 완료: {args.out} (총 {len(merged)}행, 게시글 기준 {merged[merged['type'] == 'title'].shape[0]}개)")


if __name__ == "__main__":
    main()
