"""
크롤링 공통 유틸리티

- 요청 세션 (실제 브라우저처럼 보이는 헤더 포함)
- 요청 간 랜덤 딜레이 (서버 부담/차단 방지)
- 봇 차단(Cloudflare, 캡차 등) 페이지인지 대략 판별
- 구조 분석용 HTML 저장 (raw_html/ 폴더)

이 파일은 건드릴 필요 없음. 사이트별 스크립트에서 import해서 사용.
"""
import time
import random
import logging
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("crawler")

# 커뮤니티 사이트들은 User-Agent로 '브라우저인지 스크립트인지'를 구분하는 경우가 많음
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

RAW_HTML_DIR = Path(__file__).parent / "raw_html"
RAW_HTML_DIR.mkdir(exist_ok=True)


def get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    return s


def polite_sleep(min_sec: float = 1.0, max_sec: float = 2.5):
    """요청 사이 랜덤 딜레이. 너무 빠르게 요청하면 차단당하기 쉬움."""
    time.sleep(random.uniform(min_sec, max_sec))


def fetch(session: requests.Session, url: str, timeout: int = 10):
    """단순 GET 요청. 실패하면 None 반환."""
    try:
        res = session.get(url, timeout=timeout)
        res.raise_for_status()
        res.encoding = res.apparent_encoding
        return res.text
    except requests.RequestException as e:
        logger.warning(f"요청 실패: {url} ({e})")
        return None


# 봇 차단/캡차 페이지에 자주 등장하는 문구들 (완벽하진 않지만 1차 필터로 충분)
BOT_BLOCK_MARKERS = [
    "cf-browser-verification",
    "잠시만 기다려",
    "access denied",
    "captcha",
    "cloudflare",
    "checking your browser",
    "성인인증",
    "로그인이 필요",
]


def looks_blocked(html: str) -> bool:
    """받아온 HTML이 정상 게시판이 아니라 차단/로그인 페이지인지 대략 판별"""
    if not html or len(html) < 1000:
        return True
    lowered = html.lower()
    return any(marker.lower() in lowered for marker in BOT_BLOCK_MARKERS)


def save_debug_html(site_key: str, html: str) -> Path:
    """구조 분석용으로 raw_html/ 폴더에 저장. VS Code에서 열어서 직접 확인."""
    path = RAW_HTML_DIR / f"{site_key}.html"
    path.write_text(html or "", encoding="utf-8")
    logger.info(f"저장됨: {path}")
    return path


def save_rows_to_excel(rows, columns, path: str):
    """
    rows(딕셔너리 리스트)를 지정된 컬럼 순서로 엑셀에 저장.
    중간 저장/최종 저장 공용으로 사용 (덮어쓰기 방식).
    """
    import os
    import pandas as pd

    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    df = pd.DataFrame(rows, columns=columns)
    df.to_excel(path, index=False)
    logger.info(f"엑셀 저장 완료: {path} (총 {len(df)}행)")
