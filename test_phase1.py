# -*- coding: utf-8 -*-
"""
Phase 1 Test Suite for chatGPT.py
Tests: transcribe_audio_file, chat_with_gpt, reset_chat

Compatible with Python 2.7 and Python 3.
Stubs out naoqi/myPepper (Pepper hardware SDK) so OpenAI calls
can be tested standalone without the robot.
"""

from __future__ import print_function
import sys
import os
import wave
import struct
import types

# ── Stub hardware-dependent modules BEFORE importing chatGPT ─────────────────
# Works on Python 2.7 and 3 without any mock library.

def _make_stub(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod

class _AnyCall(object):
    """A stub object where any attribute access returns another stub."""
    def __init__(self, *a, **kw):
        pass
    def __call__(self, *a, **kw):
        return self
    def __getattr__(self, name):
        return _AnyCall()

naoqi_stub = _make_stub('naoqi')
naoqi_stub.ALProxy = _AnyCall

myPepper_stub = _make_stub('myPepper')
myPepper_stub.myPepper = _AnyCall

# ── Change to project directory so .env and sharedVars.py are found ──────────
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import chatGPT as cg  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────

def create_silence_wav(path, duration_seconds=1, sample_rate=16000):
    """Write a minimal mono 16-bit silence WAV file (Python 2/3 compatible)."""
    n_frames = duration_seconds * sample_rate
    f = wave.open(path, 'w')
    try:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(struct.pack('<' + 'h' * n_frames, *([0] * n_frames)))
    finally:
        f.close()


def safe_print(text):
    """Print that survives Python 2 charmap codec errors."""
    try:
        print(text)
    except (UnicodeEncodeError, UnicodeDecodeError):
        if isinstance(text, bytes):
            print(text.decode('utf-8', errors='replace'))
        else:
            print(text.encode('utf-8', errors='replace').decode('ascii', errors='replace'))


def run_tests():
    passed = 0
    failed = 0

    print("=" * 55)
    print("  Phase 1 Test Suite -- chatGPT.py")
    print("  Python " + sys.version.split()[0])
    print("=" * 55)

    # ── Environment sanity check ──────────────────────────────────────────────
    print("\n[ENV CHECK]")
    print("  API KEY loaded : " + str(bool(cg.API_KEY)))
    print("  CHAT URL       : " + str(cg.CHATURL))
    print("  TRANSCRIBE URL : " + str(cg.TRANSCRIPTIONURL))
    print("  PREPROMPT set  : " + str(bool(cg.PREPROMPT)))

    if not cg.API_KEY:
        print("\nFATAL: CHATGPT_KEY not loaded from .env -- aborting tests.")
        return

    interact = cg.chatGPTInteract(APIKEY=cg.API_KEY)

    # ── Test 2: chat_with_gpt ─────────────────────────────────────────────────
    print("\n[TEST 2: chat_with_gpt]")
    try:
        before = len(interact.conversation)
        reply = interact.chat_with_gpt("Hello, introduce yourself in one sentence.")
        after = len(interact.conversation)

        if not reply:
            print("  FAIL: reply is empty")
            failed += 1
        elif after != before + 2:
            print("  FAIL: conversation length wrong (before={}, after={}, expected {})".format(
                before, after, before + 2))
            failed += 1
        else:
            print("  PASS: got reply ({} chars), conversation grew {} -> {}".format(
                len(reply), before, after))
            safe_print("  Reply: " + reply[:120])
            passed += 1
    except Exception as e:
        print("  FAIL: exception -- " + str(e))
        failed += 1

    # ── Test 3: reset_chat ────────────────────────────────────────────────────
    print("\n[TEST 3: reset_chat]")
    try:
        interact.chat_with_gpt("Tell me a quick fun fact.")
        before = len(interact.conversation)
        print("  Before reset: {} messages".format(before))

        interact.reset_chat()
        after = len(interact.conversation)
        print("  After reset : {} messages".format(after))

        if after != 1:
            print("  FAIL: expected 1 message after reset, got {}".format(after))
            failed += 1
        elif interact.conversation[0]["role"] != "system":
            print("  FAIL: first message role is '{}', expected 'system'".format(
                interact.conversation[0]["role"]))
            failed += 1
        elif interact.conversation[0]["content"] != cg.ALLPREPROMPT:
            print("  FAIL: system prompt content does not match ALLPREPROMPT")
            failed += 1
        else:
            print("  PASS: conversation reset to exactly 1 system message")
            passed += 1
    except Exception as e:
        print("  FAIL: exception -- " + str(e))
        failed += 1

    # ── Test 1: transcribe_audio_file ─────────────────────────────────────────
    print("\n[TEST 1: transcribe_audio_file]")
    wav_path = "test_silence.wav"
    try:
        create_silence_wav(wav_path)
        print("  Created silence WAV: " + wav_path)

        result = interact.transcribe_audio_file(wav_path)

        if result is None:
            print("  FAIL: returned None -- check API key and network")
            failed += 1
        elif not hasattr(result, 'text'):
            print("  FAIL: result has no .text attribute")
            failed += 1
        else:
            print("  PASS: .text attribute present (value: '{}')".format(result.text))
            passed += 1
    except Exception as e:
        print("  FAIL: exception -- " + str(e))
        failed += 1
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)
            print("  Cleaned up test WAV.")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("  Results: {}/{} tests passed".format(passed, passed + failed))
    if failed == 0:
        print("  All Phase 1 checks PASSED. Ready for Phase 2.")
    else:
        print("  {} test(s) FAILED. See output above.".format(failed))
    print("=" * 55)


if __name__ == "__main__":
    run_tests()
