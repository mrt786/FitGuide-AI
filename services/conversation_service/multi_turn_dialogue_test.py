"""
Multi-turn dialogue test script for Conversation Service.

This validates:
- streaming chat works for multiple turns
- compressed memory is stored
- benchmark metrics are generated

Usage:
  python multi_turn_dialogue_test.py
"""

import asyncio
import json
import time

import aiohttp

BASE_URL = "http://localhost:8002"
TEST_SESSION_ID = "test-multiturn-session"

TEST_TURNS = [
    "I am 22 years old, 70 kg, and a beginner. I want to build muscle.",
    "I can train only 3 days per week for 45 minutes.",
    "I have mild knee discomfort when doing deep squats.",
    "Can you give me a concise plan for tomorrow?",
]


async def chat_turn(http_session: aiohttp.ClientSession, session_id: str, message: str) -> str:
    payload = {"session_id": session_id, "message": message}
    output = ""

    async with http_session.post(f"{BASE_URL}/chat", json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Chat failed: {resp.status} - {await resp.text()}")

        async for line in resp.content:
            if not line:
                continue
            data = json.loads(line.decode("utf-8"))
            if "token" in data:
                output += data["token"]
            if data.get("done"):
                break

    return output.strip()


async def run_test():
    start = time.perf_counter()

    async with aiohttp.ClientSession() as http_session:
        # Cleanup any previous state.
        await http_session.delete(f"{BASE_URL}/session/{TEST_SESSION_ID}")

        print("Running multi-turn test...")
        for i, message in enumerate(TEST_TURNS, start=1):
            response = await chat_turn(http_session, TEST_SESSION_ID, message)
            print(f"Turn {i} response chars: {len(response)}")
            if not response:
                raise AssertionError(f"Empty response at turn {i}")

        # Allow async summarization tasks to complete and poll for persisted state.
        session_info = {}
        benchmark_info = {}
        for _ in range(8):
            await asyncio.sleep(1.0)

            async with http_session.get(f"{BASE_URL}/session/{TEST_SESSION_ID}") as resp:
                if resp.status == 200:
                    session_info = await resp.json()

            async with http_session.get(f"{BASE_URL}/benchmarks/{TEST_SESSION_ID}") as resp:
                if resp.status == 200:
                    benchmark_info = await resp.json()

            if session_info and benchmark_info:
                break

        if not session_info:
            raise AssertionError("Session state was not persisted")
        if not benchmark_info:
            raise AssertionError("Benchmark data was not persisted")

        memory_count = session_info.get("memory_count", 0)
        turns = benchmark_info.get("turns", 0)
        profile = session_info.get("profile", {})

        assert memory_count >= 2, f"Expected compressed memory, got {memory_count}"
        assert turns >= len(TEST_TURNS), f"Expected >= {len(TEST_TURNS)} turns, got {turns}"
        assert profile.get("goal") == "build muscle", f"Expected goal to persist, got {profile.get('goal')}"
        assert profile.get("age") == "22", f"Expected age to persist, got {profile.get('age')}"
        assert profile.get("weight") is not None, "Expected weight to persist"
        assert profile.get("injury") == "none", f"Expected injury to persist as none, got {profile.get('injury')}"

        duration = (time.perf_counter() - start) * 1000.0
        print("Test passed")
        print(f"Recent history count: {session_info.get('recent_history_count')}")
        print(f"Profile: {profile}")
        print(f"Memory count: {memory_count}")
        print(f"Avg TTFT ms: {benchmark_info.get('avg_ttft_ms')}")
        print(f"Avg total latency ms: {benchmark_info.get('avg_total_latency_ms')}")
        print(f"Script duration ms: {duration:.2f}")


if __name__ == "__main__":
    asyncio.run(run_test())
