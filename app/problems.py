from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Problem:
    id: int
    title: str
    difficulty: str
    description: str
    input_description: str
    output_description: str
    examples: list[dict[str, str]]
    hints: list[str]
    template: str
    method_name: str
    test_cases: list[dict[str, object]]


PROBLEMS = {
    1: Problem(
        id=1,
        title="两数之和",
        difficulty="简单",
        description="给定一个整数数组 nums 和一个整数目标值 target，请在数组中找出和为目标值的两个整数，并返回它们的数组下标。",
        input_description="方法参数为 nums: List[int] 和 target: int。",
        output_description="返回 List[int]，包含两个下标。每组测试只存在一个有效答案。",
        examples=[
            {
                "input": "nums = [2,7,11,15], target = 9",
                "output": "[0,1]",
                "explanation": "nums[0] + nums[1] = 9",
            },
            {
                "input": "nums = [3,2,4], target = 6",
                "output": "[1,2]",
                "explanation": "nums[1] + nums[2] = 6",
            },
        ],
        hints=[
            "使用哈希表记录已经遍历过的数字和下标。",
            "遍历 num 时检查 target - num 是否已经出现。",
        ],
        template=(
            "from typing import List\n\n\n"
            "class Solution:\n"
            "    def twoSum(self, nums: List[int], target: int) -> List[int]:\n"
            "        # 在这里写你的代码\n"
            "        pass\n"
        ),
        method_name="twoSum",
        test_cases=[
            {"args": [[2, 7, 11, 15], 9], "expected": [0, 1]},
            {"args": [[3, 2, 4], 6], "expected": [1, 2]},
            {"args": [[3, 3], 6], "expected": [0, 1]},
        ],
    ),
    2: Problem(
        id=2,
        title="爬楼梯",
        difficulty="简单",
        description="假设你正在爬楼梯。每次你可以爬 1 或 2 个台阶，给定台阶数 n，请输出到达楼顶的方法数。",
        input_description="方法参数为 n: int。",
        output_description="返回 int，表示不同的爬楼方法数。",
        examples=[
            {
                "input": "2",
                "output": "2",
                "explanation": "可以爬 1 + 1，也可以一次爬 2。",
            },
            {
                "input": "5",
                "output": "8",
                "explanation": "共有 8 种不同方法。",
            },
        ],
        hints=[
            "令 f(n) 表示爬到第 n 阶的方法数。",
            "状态转移为 f(n) = f(n - 1) + f(n - 2)。",
        ],
        template=(
            "class Solution:\n"
            "    def climbStairs(self, n: int) -> int:\n"
            "        # 在这里写你的代码\n"
            "        pass\n"
        ),
        method_name="climbStairs",
        test_cases=[
            {"args": [2], "expected": 2},
            {"args": [3], "expected": 3},
            {"args": [5], "expected": 8},
            {"args": [10], "expected": 89},
        ],
    ),
}


def list_problems() -> list[dict[str, object]]:
    return [
        {
            "id": problem.id,
            "title": problem.title,
            "difficulty": problem.difficulty,
            "method_name": problem.method_name,
        }
        for problem in PROBLEMS.values()
    ]


def get_problem(problem_id: int) -> Problem | None:
    return PROBLEMS.get(problem_id)
