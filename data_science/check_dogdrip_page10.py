"""
개드립 10페이지(비회원 상태로 새 세션에서)에 접속했을 때
실제로 어떤 내용이 오는지 확인하는 진단 스크립트.

- 로그인 요구 화면인지
- 에러/차단 안내 화면인지
- 정말 빈 목록인지
를 구분하기 위해 <title>, 본문 텍스트, li.webzine 개수를 모두 출력.
"""
from bs4 import BeautifulSoup

from crawler_utils import save_debug_html, logger
from selenium_utils import get_driver, fetch_rendered_html

URL = "https://www.dogdrip.net/dogdrip?sort_index=popular&page=10"


def main():
    driver = get_driver(headless=True)
    try:
        # 예열 없이 바로 10페이지로 (문제 재현용)
        html = fetch_rendered_html(driver, URL, wait_sec=5.0)
    finally:
        driver.quit()

    save_debug_html("dogdrip_page10_check", html)
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("title")
    print(f"<title>: {title_tag.get_text() if title_tag else '없음'}")

    items = soup.select("li.webzine")
    print(f"li.webzine 개수: {len(items)}")

    text = soup.get_text(separator=" ", strip=True)
    print(f"\n페이지 텍스트 앞부분(500자):\n{text[:500]}")

    # 로그인 관련 문구가 있는지 확인
    login_markers = ["로그인이 필요", "로그인 후", "회원만", "비회원"]
    found_markers = [m for m in login_markers if m in text]
    print(f"\n로그인 관련 문구 발견: {found_markers if found_markers else '없음'}")


if __name__ == "__main__":
    main()
