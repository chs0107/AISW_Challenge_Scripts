# -*- coding: utf-8 -*-
"""
남녀차별 커뮤니티 분석 스크립트
- 개드립(남초) vs 워마드(여초) 비교 분석
- 유형(A~G) 분포 분석
- 타겟 성별 x 유형 교차분석
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import koreanize_matplotlib
from scipy.stats import chi2_contingency
import os

OUT_DIR = "Analysis"   # 로컬에서 쓸 경우 원하는 경로로 변경
os.makedirs(OUT_DIR, exist_ok=True)

TYPE_NAMES = {
    'A': 'A: 낙인/비하 표현',
    'B': 'B: 외모/신체 비하',
    'C': 'C: 능력/지적 비하',
    'D': 'D: 성적 대상화',
    'E': 'E: 경제적 착취 프레임',
    'F': 'F: 폭력 조장',
    'G': 'G: 기여/희생 폄훼',
}
TYPE_ORDER = list(TYPE_NAMES.keys())

# -----------------------------
# 1. 데이터 로드 (인코딩 자동 감지)
# -----------------------------
def read_csv_auto(path):
    for enc in ["utf-8", "utf-8-sig", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"인코딩을 찾을 수 없음: {path}")

dog = read_csv_auto(r"classification_results\dogdrip_classification.csv")
wom = read_csv_auto(r"classification_results\womad_classification.csv")

dog["community"] = "개드립(남초)"
wom["community"] = "워마드(여초)"
df = pd.concat([dog, wom], ignore_index=True)

# -----------------------------
# 2. 커뮤니티별 차별 발언 비율 + 카이제곱 검정
# -----------------------------
summary = df.groupby("community")["is_discriminatory"].agg(["sum", "count"])
summary["ratio"] = summary["sum"] / summary["count"] * 100
print("=== 커뮤니티별 차별 발언 비율 ===")
print(summary)

contingency = pd.crosstab(df["community"], df["is_discriminatory"])
chi2, p, dof, expected = chi2_contingency(contingency)
print(f"\n=== 카이제곱 검정 ===\nchi2={chi2:.2f}, p-value={p:.6f}, dof={dof}")
sig_text = "통계적으로 유의미한 차이 (p<0.001)" if p < 0.001 else f"p={p:.4f}"
print(sig_text)

# 시각화 1: 커뮤니티별 차별 발언 비율 막대그래프
fig, ax = plt.subplots(figsize=(6, 5))
colors = ["#4C72B0", "#DD8452"]
bars = ax.bar(summary.index, summary["ratio"], color=colors, width=0.5)
for bar, val in zip(bars, summary["ratio"]):
    ax.text(bar.get_x() + bar.get_width()/2, val + 0.8, f"{val:.1f}%",
            ha="center", fontsize=13, fontweight="bold")
ax.set_ylabel("차별 발언 비율 (%)", fontsize=12)
ax.set_title("커뮤니티별 차별성 발언 비율\n(카이제곱검정 p<0.001)", fontsize=14, fontweight="bold")
ax.set_ylim(0, max(summary["ratio"]) * 1.25)
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/1_community_discriminatory_ratio.png", dpi=150)
plt.close()

# -----------------------------
# 3. 유형(A~G) 개별 빈도 분석 (콤마 split)
# -----------------------------
def explode_types(sub_df):
    rows = []
    for _, row in sub_df.dropna(subset=["types"]).iterrows():
        for t in str(row["types"]).split(","):
            t = t.strip()
            if t in TYPE_NAMES:
                rows.append({"community": row["community"], "type": t})
    return pd.DataFrame(rows)

type_df = explode_types(df)
type_counts = type_df.groupby(["community", "type"]).size().unstack(fill_value=0)
type_counts = type_counts.reindex(columns=TYPE_ORDER, fill_value=0)
print("\n=== 커뮤니티별 유형 개별 빈도 ===")
print(type_counts)

# 시각화 2: 그룹 막대그래프 (유형별 x 커뮤니티, 절대 빈도)
fig, ax = plt.subplots(figsize=(11, 6))
x = np.arange(len(TYPE_ORDER))
width = 0.35
ax.bar(x - width/2, type_counts.loc["개드립(남초)"], width, label="개드립(남초)", color="#4C72B0")
ax.bar(x + width/2, type_counts.loc["워마드(여초)"], width, label="워마드(여초)", color="#DD8452")
ax.set_xticks(x)
ax.set_xticklabels([TYPE_NAMES[t] for t in TYPE_ORDER], rotation=30, ha="right", fontsize=10)
ax.set_ylabel("등장 빈도 (건)", fontsize=12)
ax.set_title("커뮤니티별 차별 유형(A~G) 분포", fontsize=14, fontweight="bold")
ax.legend()
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/2_type_distribution_by_community.png", dpi=150)
plt.close()

# 시각화 2-2: 커뮤니티 내 비율(%)로 정규화 -> "구성비" 비교 (절대량 차이 배제)
type_pct_within = type_counts.div(type_counts.sum(axis=1), axis=0) * 100
fig, ax = plt.subplots(figsize=(11, 6))
ax.bar(x - width/2, type_pct_within.loc["개드립(남초)"], width, label="개드립(남초)", color="#4C72B0")
ax.bar(x + width/2, type_pct_within.loc["워마드(여초)"], width, label="워마드(여초)", color="#DD8452")
ax.set_xticks(x)
ax.set_xticklabels([TYPE_NAMES[t] for t in TYPE_ORDER], rotation=30, ha="right", fontsize=10)
ax.set_ylabel("커뮤니티 내 유형 구성비 (%)", fontsize=12)
ax.set_title("커뮤니티별 차별 유형 '구성비' 비교\n(각 커뮤니티의 차별 발언 내 비중, 절대량 차이 배제)", fontsize=13, fontweight="bold")
ax.legend()
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/2b_type_pct_within_community.png", dpi=150)
plt.close()
print("\n=== 커뮤니티 내 유형 구성비(%) ===")
print(type_pct_within.round(1))

# -----------------------------
# 4. 타겟 성별 x 유형 교차분석 (100% 누적 막대)
# -----------------------------
gender_type_df = []
for _, row in df.dropna(subset=["types", "target_gender"]).iterrows():
    for t in str(row["types"]).split(","):
        t = t.strip()
        if t in TYPE_NAMES:
            gender_type_df.append({"target_gender": row["target_gender"], "type": t})
gender_type_df = pd.DataFrame(gender_type_df)

gt_counts = gender_type_df.groupby(["type", "target_gender"]).size().unstack(fill_value=0)
gt_counts = gt_counts.reindex(TYPE_ORDER, fill_value=0)
gt_pct = gt_counts.div(gt_counts.sum(axis=1), axis=0) * 100
print("\n=== 타겟 성별별 유형 비중(%) ===")
print(gt_pct)

fig, ax = plt.subplots(figsize=(10, 6))
bottom = np.zeros(len(gt_pct))
colors_gender = {"여성": "#E07A9E", "남성": "#5B8FD8"}
for gender in gt_pct.columns:
    ax.bar([TYPE_NAMES[t] for t in gt_pct.index], gt_pct[gender], bottom=bottom,
           label=f"{gender} 타겟", color=colors_gender.get(gender, "#999999"))
    bottom += gt_pct[gender].values
ax.set_ylabel("비중 (%)", fontsize=12)
ax.set_title("타겟 성별에 따른 차별 유형(A~G) 비중", fontsize=14, fontweight="bold")
ax.legend()
plt.xticks(rotation=30, ha="right", fontsize=10)
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/3_gender_type_stacked.png", dpi=150)
plt.close()

# -----------------------------
# 5. 히트맵 (커뮤니티 x 유형)
# -----------------------------
fig, ax = plt.subplots(figsize=(9, 4))
im = ax.imshow(type_counts.values, cmap="Oranges", aspect="auto")
ax.set_xticks(np.arange(len(TYPE_ORDER)))
ax.set_xticklabels([f"{t}" for t in TYPE_ORDER])
ax.set_yticks(np.arange(len(type_counts.index)))
ax.set_yticklabels(type_counts.index)
for i in range(len(type_counts.index)):
    for j in range(len(TYPE_ORDER)):
        val = type_counts.values[i, j]
        ax.text(j, i, str(val), ha="center", va="center",
                color="white" if val > type_counts.values.max()*0.5 else "black", fontsize=10)
ax.set_title("커뮤니티 x 유형 히트맵", fontsize=14, fontweight="bold")
plt.colorbar(im, ax=ax, label="빈도(건)")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/4_heatmap_community_type.png", dpi=150)
plt.close()

# -----------------------------
# 6. 요약 결과 저장 (CSV)
# -----------------------------
summary.to_csv(f"{OUT_DIR}/summary_ratio.csv", encoding="utf-8-sig")
type_counts.to_csv(f"{OUT_DIR}/summary_type_counts.csv", encoding="utf-8-sig")
gt_pct.round(1).to_csv(f"{OUT_DIR}/summary_gender_type_pct.csv", encoding="utf-8-sig")

print("\n분석 완료. 이미지 5개 + 요약 CSV 3개가 outputs 폴더에 저장됨.")