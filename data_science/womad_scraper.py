"""
워마드(womad.life) 크롤러 - 월간베스트

Cloudflare 챌린지 때문에 undetected-chromedriver 사용.
구조 확인 완료 (2026-07-08, 실제 HTML 샘플 기반).

행 구조:
  <tr>
    <td class="number">글번호</td>
    <td class="repository">게시판명</td>
    <td class="title"><a href="/l/{id}?...">
        <span class="category-text">카테고리</span> 제목 <span class="comments-count">댓글수</span>
    </a></td>
    <td>작성자</td>
    <td>작성일</td>
    <td>조회수</td>
    <td><span class="votes-score-{id}">추천수</span></td>
  </tr>

주의: 원본 게시글의 카테고리명/제목에 성적·혐오 표현이 그대로 포함될 수 있음.
연구 목적상 원본 그대로 수집하는 것이 맞으므로 별도로 필터링하지 않음
(필터링/분류는 다음 단계인 LLM 기반 전처리에서 수행).
"""
import re
import time
from urllib.parse import urljoin

import undetected_chromedriver as uc
from bs4 import BeautifulSoup

from crawler_utils import logger, polite_sleep

BASE_URL = "https://womad.life/best/monthlybest"
DOMAIN = "https://womad.life"


def get_uc_driver():
    options = uc.ChromeOptions()
    return uc.Chrome(options=options, version_main=149)  # 설치된 Chrome 버전에 맞춰야 함


def parse_list_page(html: str):
    soup = BeautifulSoup(html, "lxml")
    posts = []

    for row in soup.select("tr"):
        number_td = row.select_one("td.number")
        title_td = row.select_one("td.title")
        if not number_td or not title_td:
            continue  # 헤더 행 등은 건너뜀

        post_id = number_td.get_text(strip=True)

        title_link = title_td.find("a", href=True)
        if not title_link:
            continue

        url = urljoin(DOMAIN, title_link["href"])

        category_tag = title_link.select_one("span.category-text")
        category = category_tag.get_text(strip=True) if category_tag else ""

        comment_tag = title_link.select_one("span.comments-count")
        comment_count = 0
        if comment_tag:
            m = re.search(r"\d+", comment_tag.get_text())
            if m:
                comment_count = int(m.group())

        # 제목: 링크 전체 텍스트에서 카테고리/댓글수 부분 제외
        title = title_link.get_text(" ", strip=True)
        if category_tag:
            title = title.replace(category_tag.get_text(strip=True), "", 1)
        if comment_tag:
            title = title.replace(comment_tag.get_text(strip=True), "", 1)
        title = title.strip()

        other_tds = row.find_all("td")
        repository = other_tds[1].get_text(strip=True) if len(other_tds) > 1 else ""
        author = other_tds[3].get_text(strip=True) if len(other_tds) > 3 else ""
        date_text = other_tds[4].get_text(strip=True) if len(other_tds) > 4 else ""
        views = other_tds[5].get_text(strip=True) if len(other_tds) > 5 else ""

        recommend = 0
        recommend_span = row.select_one("span[class*='votes-score-']")
        if recommend_span:
            m = re.search(r"\d+", recommend_span.get_text())
            if m:
                recommend = int(m.group())

        posts.append({
            "site": "워마드",
            "post_id": post_id,
            "repository": repository,
            "category": category,
            "title": title,
            "url": url,
            "author": author,
            "date": date_text,
            "views": views,
            "recommend": recommend,
            "comment_count": comment_count,
        })

    return posts


def crawl(max_pages: int = 10):
    driver = get_uc_driver()
    all_posts = []

    try:
        for page in range(1, max_pages + 1):
            url = f"{BASE_URL}/{page}"
            logger.info(f"[워마드] {page}페이지 요청 중...")
            driver.get(url)
            time.sleep(5)  # 챌린지 재확인 대비 여유 대기

            html = driver.page_source
            posts = parse_list_page(html)

            if not posts:
                logger.warning(f"{page}페이지에서 게시글을 찾지 못함, 중단")
                break

            all_posts.extend(posts)
            logger.info(f"{page}페이지: {len(posts)}개 수집 (누적 {len(all_posts)}개)")
            polite_sleep()
    finally:
        driver.quit()

    return all_posts


if __name__ == "__main__":
    posts = crawl(max_pages=3)
    print(f"\n총 {len(posts)}개 게시글 수집")
    for p in posts[:5]:
        print(p)
