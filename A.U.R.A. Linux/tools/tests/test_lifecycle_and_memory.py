# -*- coding: utf-8 -*-
# ==============================================================================
# Adaptive Underworld Recon Array (A.U.R.A.)
# Copyright (C) 2026 JeffTheNerdDev96
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ==============================================================================
"""
Automated unit & integration tests for:
- Thread & process shutdown verification
- Neural hardware coprocessor thread start/stop/unload
- Immediate stop generation and abort handling
- Memory purge & standby state restoration
- Complete lifecycle shutdown
"""

import os
import sys
import time

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_TESTS_DIR)
_APP_ROOT = os.path.dirname(_TOOLS_DIR)
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from bootstrap import configure_qt_paths
configure_qt_paths()

from PyQt6.QtWidgets import QApplication
from core.lifecycle import shutdown_application
from hardware.detector import HardwareDetector
from subsystems.ai.engine import UnifiedInferenceEngine, NeuralHardwareCoProcessor
from ui import MainWindow


def test_coprocessor_lifecycle():
    print("[TEST] NeuralHardwareCoProcessor thread lifecycle & unload...")
    detector = HardwareDetector()
    coproc = NeuralHardwareCoProcessor(detector)
    
    # 1. Start stream mesh (if supported mode)
    stop_event = coproc.start_stream_mesh("CPU")
    if stop_event is not None:
        assert len(coproc.active_threads) > 0, "Expected active worker threads"
        time.sleep(0.05)
        # 2. Stop workers
        coproc.stop_all_workers()
        assert len(coproc.active_threads) == 0, "Expected all coprocessor threads to be joined and cleared"
        assert coproc.active_stop_event is None
    
    # 3. Test unload coprocessor
    coproc.unload_coprocessor()
    assert len(coproc.compiled_models) == 0
    assert coproc.core is None
    assert coproc.base_model is None
    assert coproc._dml_session is None
    print(" -> NeuralHardwareCoProcessor passed!")


def test_engine_abort_and_unload():
    print("[TEST] UnifiedInferenceEngine request_abort and unload_model...")
    engine = UnifiedInferenceEngine(eager_load=False)
    assert not engine.is_loaded
    assert engine.llm is None

    # Test request_abort flag
    engine.request_abort()
    assert engine._abort_requested is True
    engine.clear_abort()
    assert engine._abort_requested is False

    # Test unload_model on uninitialized or initialized engine
    engine.unload_model()
    assert engine.llm is None
    assert not engine.is_loaded
    assert engine.coprocessor.active_stop_event is None
    print(" -> UnifiedInferenceEngine abort & unload passed!")


def test_ui_stop_and_purge_lifecycle():
    print("[TEST] MainWindow stop generation, memory purge, and shutdown...")
    app = QApplication.instance()
    if not app:
        app = QApplication(["A.U.R.A_LifecycleTest", "-platform", "offscreen"])

    window = MainWindow()
    assert window is not None

    # Initial state should be Standby
    assert window.engine.llm is None
    assert "Standby" in window._get_idle_badge_text() or "Online" in window._get_idle_badge_text()

    # 1. Test Stop Generation mechanism
    window._execute_tactical_prompt("What is a warp scrambler?", "Test User")
    assert window.worker is not None
    # Trigger stop generation immediately
    window._stop_generation()
    assert not window.send_btn.isHidden()
    assert window.send_btn.isEnabled()
    assert window.stop_btn.isHidden()
    assert window.progress_container.isHidden()
    print(" -> Stop generation UI & worker teardown passed!")

    # 2. Test Memory Purge & Standby state
    # Add dummy context
    window.chat_history.append({"role": "user", "content": "Sample prompt"})
    window.chat_history.append({"role": "assistant", "content": "Sample response"})
    window._reset_memory()
    
    assert len(window.chat_history) == 0, "Chat history should be empty after purge"
    assert len(window.attachments) == 0, "Attachments should be cleared after purge"
    assert len(window.current_assistant_tokens) == 0
    assert window.engine.llm is None, "Engine LLM should be None after purge"
    assert "Standby" in window._get_idle_badge_text(), f"Expected Standby in badge text, got {window._get_idle_badge_text()}"
    print(" -> Memory purge & standby state restoration passed!")

    # 3. Test Full Lifecycle Shutdown
    shutdown_application(window)
    assert getattr(window, "_shutdown_done", False) is True
    assert window.idle_timer.isActive() is False
    assert window.chat_monitor.running is False
    print(" -> Full lifecycle shutdown passed!")

    window.close()
    return True


if __name__ == "__main__":
    test_coprocessor_lifecycle()
    test_engine_abort_and_unload()
    test_ui_stop_and_purge_lifecycle()
    print("\n[SUCCESS] ALL LIFECYCLE, STOP GENERATION & PURGE TESTS PASSED!")
