"""
분류기 정확도 평가 스크립트 (선택, 권장)
------------------------------------------------
- eval_set.csv(UnSmile 데이터셋 valid 스플릿, build_fewshot_examples.py로 생성)의
  정답 라벨과 우리 LLM 분류기의 출력을 비교해 정확도/정밀도/재현율을 계산한다.
- 본 실행 전 classify_discrimination.py와 fewshot_examples.json이 같은 폴더에 있어야 한다.
- PPT에 "분류기 검증 결과"로 넣기 좋은 수치를 출력한다.

주의: eval_set.csv는 UnSmile의 '여성/가족'·'남성'·'clean' 라벨만 가지고 있어
      1차(차별여부)·2차(대상성별) 판별 정확도만 검증 가능하다.
      3차 세부유형(A~G)은 UnSmile에 없는 자체 기준이라 이 스크립트로는 검증하지 않는다.

사전 준비: pip install anthropic pandas
"""

import pandas as pd

from classify_discrimination import classify_batch, BATCH_SIZE

EVAL_PATH = "eval_set.csv"


def evaluate():
    df = pd.read_csv(EVAL_PATH)
    texts = df["text"].astype(str).tolist()

    pred_disc, pred_gender = [], []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        results = classify_batch(batch)
        results_sorted = sorted(results, key=lambda r: r["index"])
        for r in results_sorted:
            pred_disc.append(bool(r["is_discriminatory"]))
            pred_gender.append(r["target_gender"])
        print(f"  평가 진행 {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")

    df["pred_is_discriminatory"] = pred_disc
    df["pred_target_gender"] = pred_gender
    df.to_csv("eval_result_detail.csv", index=False, encoding="utf-8-sig")

    gold_disc = df["gold_is_discriminatory"].astype(bool)

    tp = ((df["pred_is_discriminatory"] == True) & (gold_disc == True)).sum()
    fp = ((df["pred_is_discriminatory"] == True) & (gold_disc == False)).sum()
    fn = ((df["pred_is_discriminatory"] == False) & (gold_disc == True)).sum()
    tn = ((df["pred_is_discriminatory"] == False) & (gold_disc == False)).sum()

    accuracy = (tp + tn) / len(df) if len(df) else 0
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    # 대상 성별 정확도 (1차가 true인 정답 케이스 중, 2차 대상 성별도 일치하는 비율)
    gender_rows = df[gold_disc == True]
    gender_correct = (gender_rows["pred_target_gender"] == gender_rows["gold_target_gender"]).sum()
    gender_acc = gender_correct / len(gender_rows) if len(gender_rows) else 0

    print("\n===== 1차 판별(차별표현 여부) 평가 결과 =====")
    print(f"정확도(Accuracy):  {accuracy:.3f}")
    print(f"정밀도(Precision): {precision:.3f}")
    print(f"재현율(Recall):    {recall:.3f}")
    print(f"F1 Score:          {f1:.3f}")
    print(f"(TP={tp}, FP={fp}, FN={fn}, TN={tn}, 전체={len(df)})")
    print("\n===== 2차 판별(대상 성별) 평가 결과 =====")
    print(f"대상 성별 일치율: {gender_acc:.3f} ({gender_correct}/{len(gender_rows)})")
    print("\n상세 결과는 eval_result_detail.csv 에 저장됨")


if __name__ == "__main__":
    evaluate()
