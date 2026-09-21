"""海龟汤游戏服务。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import ai_client
import config
import judge_client
import puzzle_bank

EXIT_WORDS = ("退出", "不想玩了", "想要答案", "公布答案", "不猜了")
MAX_WRONG_ANSWERS = 3


@dataclass
class Qa:
    question: str
    answer: str


@dataclass
class GameState:
    room_id: int
    surface: str = ""
    truth: str = ""
    ended: bool = False
    question_count: int = 0
    wrong_answers: int = 0
    history: list = field(default_factory=list)

    def record_qa(self, question: str, answer: str) -> None:
        self.history.append(Qa(question, answer))

    def build_state_text(self) -> str:
        parts = [
            "海龟汤谜题主持。",
            f"汤面（公开）：{self.surface}",
            f"汤底（仅主持人可见的真相）：{self.truth}",
        ]
        if self.history:
            parts.append("已进行的问答：")
            for qa in self.history:
                parts.append(f"Q: {qa.question} A: {qa.answer}")
        return "\n".join(parts)


_game_store: dict[int, GameState] = {}


def _end_game(state: GameState, prefix: str) -> str:
    state.ended = True
    return f"{prefix}游戏已结束。\n汤底：{state.truth}"


def _intro(surface: str, lead: str) -> str:
    return (
        f"{lead}\n汤面：{surface}"
        + "\n\n你可以不断提问，我只回答「是」「否」或「与此无关」。"
        + "若已还原真相，请在下方「提交答案」框中直接写出你的推断。"
    )


def start_game(room_id: int, puzzle_index: Optional[int] = None, tag: Optional[str] = None) -> str:
    if puzzle_index is not None:
        puzzle = puzzle_bank.get_at(puzzle_index)
        lead = "游戏开始！"
    else:
        puzzle = puzzle_bank.random(tag=tag)
        lead = "游戏开始！" if not tag else f"已从「{tag}」中为你盛上一碗！"
    state = GameState(room_id=room_id, surface=puzzle["surface"], truth=puzzle["truth"])
    _game_store[room_id] = state
    return _intro(puzzle["surface"], lead)


def next_puzzle(room_id: int, tag: Optional[str] = None) -> str:
    state = _game_store.get(room_id)
    if state is None:
        raise RuntimeError("请先开始游戏")
    if state.ended:
        raise RuntimeError("游戏已结束，请重新「开始」")
    puzzle = puzzle_bank.random(tag=tag)
    state.surface = puzzle["surface"]
    state.truth = puzzle["truth"]
    state.question_count = 0
    state.wrong_answers = 0
    state.history.clear()
    return _intro(puzzle["surface"], "换了一碗新汤。")


def do_chat(room_id: int, message: str) -> str:
    if message == "开始":
        return start_game(room_id)

    state = _game_store.get(room_id)
    if state is None:
        raise RuntimeError("请先开始游戏")
    if state.ended:
        return "游戏已结束，请重新「开始」"

    if any(word in message for word in EXIT_WORDS):
        return _end_game(state, "你选择了退出。")

    judgment = judge_client.judge(state.build_state_text(), message)
    verdict = judge_client.verdict_text(judgment["verdict"])
    state.record_qa(message, verdict)
    state.question_count += 1

    if judgment["closeness"] >= config.CLOSENESS_THRESHOLD:
        return _end_game(state, "你已经逼近了真相！")

    return f"{verdict}。"


async def submit_answer(room_id: int, answer: str) -> str:
    state = _game_store.get(room_id)
    if state is None:
        raise RuntimeError("请先开始游戏")
    if state.ended:
        return "游戏已结束，请重新「开始」"

    if config.gateway_ready():
        # 优先语义判定；失败则回退结构化判决
        try:
            correct = await ai_client.check_answer(state.truth, answer)
        except Exception as e:
            print(f"答案判定回退：{e}")
            p = judge_client.judge_answer(state.build_state_text(), answer)
            correct = p >= 0.5
    else:
        raise RuntimeError("服务未配置：请设置 AI_GATEWAY_API_KEY")

    if correct:
        state.record_qa(answer, "提交答案：正确")
        return _end_game(state, "恭喜你还原了真相！")

    state.wrong_answers += 1
    state.record_qa(answer, f"提交答案：错误（第 {state.wrong_answers} 次）")

    if state.wrong_answers >= MAX_WRONG_ANSWERS:
        return _end_game(
            state,
            f"你已经答错 {MAX_WRONG_ANSWERS} 次，汤底揭晓。",
        )

    return (
        f"你的答案与真相还有距离。（第 {state.wrong_answers} 次答错，"
        f"共 {MAX_WRONG_ANSWERS} 次机会）请继续提问。"
    )


def list_rooms() -> list:
    result = []
    for room_id, state in _game_store.items():
        messages = []
        if state.surface:
            messages.append({"role": "assistant", "content": f"汤面：{state.surface}"})
        for qa in state.history:
            messages.append({"role": "user", "content": qa.question})
            messages.append({"role": "assistant", "content": qa.answer})
        result.append({"roomId": room_id, "chatMessageList": messages})
    return result
