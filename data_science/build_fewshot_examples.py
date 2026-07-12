"""
UnSmile 데이터셋 기반 few-shot 예시 / 평가셋 생성 스크립트
------------------------------------------------------------
출처: Korean UnSmile Dataset (Smilegate AI, 2022)
      https://github.com/smilegate-ai/korean_unsmile_dataset
라이선스: CC-BY-NC-ND 4.0 (비상업적 이용, 출처 표기 필요)
      -> 본 프로젝트(고교 AI·SW 챌린지, 비상업 교육 목적)는 라이선스 범위 내 사용

역할
- train 스플릿에서 여성/남성 혐오 예시 + clean(중립) 예시를 뽑아 fewshot_examples.json 생성
  -> classify_discrimination.py의 프롬프트에 삽입되어 LLM 판별 기준을 보정(precision 향상)
- valid 스플릿에서 별도로 eval_set.csv(정답 라벨 포함 평가셋) 생성
  -> evaluate_classifier.py에서 우리 분류기의 정확도를 검증하는 데 사용
  (few-shot과 평가셋은 서로 다른 스플릿에서 뽑아 데이터 누수를 방지함)

사전 준비: pip install pandas requests
"""

import json
import re
from pathlib import Path

import pandas as pd
import requests

OUT_DIR = Path(".")
BASE_URL = "https://raw.githubusercontent.com/smilegate-ai/korean_unsmile_dataset/main/"
TRAIN_FILE = "unsmile_train_v1.0.tsv"
VALID_FILE = "unsmile_valid_v1.0.tsv"

EXCLUDE_KEYWORDS = ["일베", "무슬림", "이슬람", "국짐", "민주당", "조선", "틀딱",
                    "박근혜", "박근헤", "세월호", "대법원", "부정선거"]


def download(filename: str) -> pd.DataFrame:
    local = OUT_DIR / filename
    if not local.exists():
        resp = requests.get(BASE_URL + filename, timeout=30)
        resp.raise_for_status()
        local.write_bytes(resp.content)
    return pd.read_csv(local, sep="\t")


def is_clean_text_ok(text: str) -> bool:
    """clean(중립) 예시로 쓰기에 너무 노이즈가 많거나 정치·종교색이 강한 문장 제외"""
    if re.search(r"[ㅋㅎㅠㅜ]{3,}", text):
        return False
    if len(re.findall(r"[가-힣]", text)) < 10:
        return False
    if any(kw in text for kw in EXCLUDE_KEYWORDS):
        return False
    return True


def build_fewshot(train_df: pd.DataFrame, n_per_class: int = 4, seed: int = 42):
    train_df = train_df.copy()
    train_df["len"] = train_df["문장"].str.len()

    female_cand = train_df[(train_df["여성/가족"] == 1) & train_df["len"].between(15, 50)]
    male_cand = train_df[(train_df["남성"] == 1) & train_df["len"].between(15, 50)]
    clean_cand = train_df[(train_df["clean"] == 1) & train_df["len"].between(15, 45)]
    clean_cand = clean_cand[clean_cand["문장"].apply(is_clean_text_ok)]

    female_ex = female_cand.sample(n=n_per_class, random_state=seed)["문장"].tolist()
    male_ex = male_cand.sample(n=n_per_class, random_state=seed)["문장"].tolist()
    clean_ex = clean_cand.sample(n=max(3, n_per_class - 1), random_state=seed)["문장"].tolist()

    fewshot = []
    for t in female_ex:
        fewshot.append({"text": t, "is_discriminatory": True, "target_gender": "여성"})
    for t in male_ex:
        fewshot.append({"text": t, "is_discriminatory": True, "target_gender": "남성"})
    for t in clean_ex:
        fewshot.append({"text": t, "is_discriminatory": False, "target_gender": None})

    # 대상 성별 혼동(tie-break) 사례: 문장에 양쪽 성별 단어가 섞여 있을 때
    # 실제 조롱 대상이 누구인지 판단하는 기준을 보여주는 실제 사례 (train에서 수동 확인)
    fewshot.append({
        "text": "여윽시 맘충년들 저런년들이랑 결혼한남자는 대체 얼마나 병신일까?",
        "is_discriminatory": True, "target_gender": "여성",
        "note": "여성 멸칭(맘충년)과 남자 언급이 같이 나오지만, 실제 조롱 대상은 여성 쪽이다",
    })
    fewshot.append({
        "text": "김치녀 김여사 아무렇지도 않게 쓴다고 지도 얘기하면서 한남은 답답하대 역시 자지는 머리가 너무 나쁘노",
        "is_discriminatory": True, "target_gender": "남성",
        "note": "여성 멸칭(김치녀)이 인용되지만, 실제 조롱 대상(지적 능력 비하)은 남성 쪽이다",
    })
    # 노골적 멸칭 없는 은근한 혐오 사례 (재현율 보강용)
    fewshot.append({
        "text": "으따 좋은 직업은 유리천장이 있고 노가다 택배상하차는 유리천장이 없당께~~~",
        "is_discriminatory": True, "target_gender": "여성",
        "note": "멸칭 없이 냉소적 비유로 여성의 차별 주장을 조롱함",
    })
    fewshot.append({
        "text": "여기 댓글 남자얘기 없고 고위직얘기뿐임. 그리고 남자성욕은 본능이다",
        "is_discriminatory": True, "target_gender": "남성",
        "note": "멸칭 없이 본질주의적 고정관념으로 남성을 일반화함",
    })
    return fewshot


def build_eval_set(valid_df: pd.DataFrame, n_per_class: int = 50, seed: int = 1):
    valid_df = valid_df.copy()
    valid_df["len"] = valid_df["문장"].str.len()

    f = valid_df[(valid_df["여성/가족"] == 1) & valid_df["len"].between(10, 80)].sample(
        n=n_per_class, random_state=seed)
    m = valid_df[(valid_df["남성"] == 1) & valid_df["len"].between(10, 80)].sample(
        n=n_per_class, random_state=seed)
    c = valid_df[(valid_df["clean"] == 1) & valid_df["len"].between(10, 80)].sample(
        n=n_per_class, random_state=seed)

    rows = []
    for _, r in f.iterrows():
        rows.append({"text": r["문장"], "gold_is_discriminatory": True, "gold_target_gender": "여성"})
    for _, r in m.iterrows():
        rows.append({"text": r["문장"], "gold_is_discriminatory": True, "gold_target_gender": "남성"})
    for _, r in c.iterrows():
        rows.append({"text": r["문장"], "gold_is_discriminatory": False, "gold_target_gender": ""})

    return pd.DataFrame(rows).sample(frac=1, random_state=99).reset_index(drop=True)


if __name__ == "__main__":
    print("UnSmile 데이터셋 다운로드 중...")
    train_df = download(TRAIN_FILE)
    valid_df = download(VALID_FILE)

    fewshot = build_fewshot(train_df)
    with open(OUT_DIR / "fewshot_examples.json", "w", encoding="utf-8") as f:
        json.dump(fewshot, f, ensure_ascii=False, indent=2)
    print(f"fewshot_examples.json 생성 완료 ({len(fewshot)}건)")

    eval_df = build_eval_set(valid_df)
    eval_df.to_csv(OUT_DIR / "eval_set.csv", index=False, encoding="utf-8-sig")
    print(f"eval_set.csv 생성 완료 ({len(eval_df)}건)")
