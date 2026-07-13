# -*- coding: utf-8 -*-
"""
온라인 커뮤니티 신고·제재 시스템 시뮬레이터

인공지능 과목에서 구현하는 자동 필터링 봇의 제재 처리 로직을
파이썬 기초 과목 단계에서 OOP 기반으로 먼저 프로토타이핑한 모듈.
신고 누적 → 게시물 블라인드 → 작성자 제재로 이어지는 처리 흐름을
사용자 유형(User)과 검토 봇(ModerationBot)의 다형성으로 구현했다.
"""


class User:
    """커뮤니티 사용자. 위반 누적 횟수에 따라 이용 정지 여부가 결정된다."""

    def __init__(self, name):
        self.name = name
        self._violation_count = 0
        self._is_blocked = False
        self.user_type = "일반 사용자"

    def receive_violation(self, threshold=3):
        """위반 1건을 누적시키고, 기준치 초과 시 계정을 정지한다."""
        self._violation_count += 1
        print(f"    ⚠ {self.name}님의 위반 누적 횟수: {self._violation_count}")

        if self._violation_count >= threshold:
            self._is_blocked = True
            print(f"    🚫 {self.name}님은 위반 누적으로 이용이 정지되었습니다.")

    def get_status(self):
        status = "정지됨" if self._is_blocked else "정상"
        return f"[{self.name} | {self.user_type}] 위반횟수:{self._violation_count}  상태:{status}"


class RegularUser(User):
    """일반 사용자. 기본 제재 기준(threshold=3)을 그대로 따른다."""

    def __init__(self, name):
        super().__init__(name)
        self.user_type = "일반 사용자"


class RepeatOffenderUser(User):
    """반복 위반 이력이 있는 사용자. 더 낮은 기준치로 즉시 제재한다."""

    def __init__(self, name):
        super().__init__(name)
        self.user_type = "반복 위반자"

    def receive_violation(self, threshold=1):
        print(f"    (반복 위반자라 더 엄격한 기준이 적용됩니다)")
        super().receive_violation(threshold=threshold)


class Post:
    """게시물. 작성자(User)를 참조하며 신고 누적 상태를 관리한다."""

    def __init__(self, content, author: User):
        self.content = content
        self.author = author
        self.report_count = 0
        self.is_blind = False

    def receive_report(self):
        self.report_count += 1
        print(f"  📢 게시물 신고 접수 (누적 {self.report_count}건) : \"{self.content}\"")


class ModerationBot:
    """게시물 검토 봇의 기본 동작. blind_threshold를 기준으로 블라인드 여부를 판단한다."""

    def __init__(self, bot_name, blind_threshold):
        self.bot_name = bot_name
        self.blind_threshold = blind_threshold

    def review(self, post: Post):
        print(f"  🤖 [{self.bot_name}] 게시물 검토 중... "
              f"(신고 {post.report_count}건 / 기준 {self.blind_threshold}건)")

        if post.report_count >= self.blind_threshold and not post.is_blind:
            post.is_blind = True
            print(f"  ⛔ 게시물이 블라인드 처리되었습니다.")
            post.author.receive_violation()
        else:
            print(f"  ✅ 아직 기준 미달이라 게시물을 유지합니다.")


class StrictBot(ModerationBot):
    """신고 2건 이상이면 즉시 블라인드 처리하는 고강도 검토 봇."""

    def __init__(self):
        super().__init__(bot_name="엄격봇", blind_threshold=2)


class LenientBot(ModerationBot):
    """신고 5건 이상부터 블라인드 처리하는 저강도 검토 봇."""

    def __init__(self):
        super().__init__(bot_name="관대봇", blind_threshold=5)


class CommunityServer:
    """User, Post, ModerationBot을 종합해 신고 처리 흐름을 조율하는 서버."""

    def __init__(self, bot: ModerationBot):
        self.posts = []
        self.bot = bot

    def add_post(self, post: Post):
        self.posts.append(post)

    def simulate_reports(self, post: Post, report_times: int):
        print(f"\n--- '{post.content}' 게시물에 신고 {report_times}회 발생 ---")
        for _ in range(report_times):
            post.receive_report()
            self.bot.review(post)


def main():
    user_a = RegularUser("사용자A")
    user_b = RepeatOffenderUser("사용자B")

    post1 = Post("성별 비하 표현이 담긴 글", author=user_a)
    post2 = Post("특정 성별을 조롱하는 반복적인 글", author=user_b)

    strict_server = CommunityServer(bot=StrictBot())
    strict_server.add_post(post1)
    strict_server.add_post(post2)

    strict_server.simulate_reports(post1, report_times=3)
    strict_server.simulate_reports(post2, report_times=2)

    print("\n===== 최종 결과 =====")
    print(user_a.get_status())
    print(user_b.get_status())
    print(f"post1 블라인드 여부: {post1.is_blind}")
    print(f"post2 블라인드 여부: {post2.is_blind}")

    # 봇 종류에 따른 처리 기준 차이 비교
    print("\n===== 봇 종류에 따른 차이 비교 =====")
    post3_strict = Post("애매한 수위의 글", author=RegularUser("사용자C"))
    post3_lenient = Post("애매한 수위의 글(복제본)", author=RegularUser("사용자D"))

    lenient_server = CommunityServer(bot=LenientBot())

    print("[엄격봇 서버]")
    strict_server.simulate_reports(post3_strict, report_times=2)

    print("\n[관대봇 서버]")
    lenient_server.simulate_reports(post3_lenient, report_times=2)

    print("\n👉 결론: 동일한 신고 2건이라도 봇의 판단 기준(review 메서드)에 따라 "
          "처리 결과가 달라진다. 실제 필터링 봇 설계 시 제재 강도를 유연하게 "
          "조절할 수 있는 구조적 근거가 된다.")


if __name__ == "__main__":
    main()
