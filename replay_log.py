#!/usr/bin/env python3
"""
The Sand Pit - Log Replay Tool
Replay game sessions from JSONL log files with a PyQt6 GUI.
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QSlider, QTextEdit,
                             QFileDialog, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont


class LogParser:
    """Parse JSONL log files into replayable state sequences."""

    @staticmethod
    def parse_log(log_file: str) -> List[Dict[str, Any]]:
        """Parse a log file and return a list of events."""
        events = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    @staticmethod
    def extract_config(events: List[Dict]) -> Dict[str, Any]:
        """Extract configuration from the experiment_start event."""
        for event in events:
            if event.get('event_type') == 'experiment_start':
                return event.get('config', {})
        return {}

    @staticmethod
    def extract_game_states(events: List[Dict]) -> List[Dict]:
        """Extract a sequence of game states from events."""
        states = []
        current_round = 0
        agent_a_pos = None
        agent_b_pos = None
        agent_a_reasoning = ""
        agent_b_reasoning = ""

        for event in events:
            event_type = event.get('event_type')

            if event_type == 'round_start':
                current_round = event.get('round', 0)
                game_state = event.get('game_state', {})
                if game_state:
                    agent_a_data = game_state.get('agent_a', {})
                    agent_b_data = game_state.get('agent_b', {})
                    if agent_a_data:
                        agent_a_pos = tuple(agent_a_data.get('position', [0, 0]))
                    if agent_b_data:
                        agent_b_pos = tuple(agent_b_data.get('position', [0, 0]))

                states.append({
                    'round': current_round,
                    'event': 'round_start',
                    'agent_a': agent_a_pos,
                    'agent_b': agent_b_pos,
                    'reasoning_a': agent_a_reasoning,
                    'reasoning_b': agent_b_reasoning,
                    'event_data': event
                })

            elif event_type == 'api_response':
                agent_name = event.get('agent', '')
                response = event.get('response', {})
                parsed = response.get('parsed_content', {}) or {}

                fallback_reasoning = ""
                if not parsed:
                    raw_content = response.get('raw_content', '')
                    if raw_content:
                        try:
                            if '```json' in raw_content:
                                json_str = raw_content.split('```json')[1].split('```')[0].strip()
                            elif '```' in raw_content:
                                json_str = raw_content.split('```')[1].split('```')[0].strip()
                            else:
                                json_str = raw_content.strip()
                            parsed = json.loads(json_str)
                        except (json.JSONDecodeError, IndexError):
                            parsed = {}
                            if 'thought_process' in raw_content:
                                try:
                                    start_marker = '"thought_process"'
                                    start_idx = raw_content.find(start_marker)
                                    if start_idx != -1:
                                        content_start = raw_content.find(':', start_idx) + 1
                                        content = raw_content[content_start:].strip()
                                        if content.startswith('"'):
                                            content = content[1:]
                                        last_period = content.rfind('. ')
                                        if last_period != -1:
                                            content = content[:last_period + 1]
                                        fallback_reasoning = content + "\n\n[Content truncated - Token Limit]"
                                except Exception:
                                    fallback_reasoning = ""

                reasoning = response.get('reasoning_content') or parsed.get('reasoning', '') or parsed.get('thought_process', '') or fallback_reasoning

                if 'Agent_A' in agent_name:
                    agent_a_reasoning = reasoning
                    if parsed:
                        agent_a_pos = (parsed.get('x'), parsed.get('y'))
                elif 'Agent_B' in agent_name:
                    agent_b_reasoning = reasoning
                    if parsed:
                        agent_b_pos = (parsed.get('x'), parsed.get('y'))

            elif event_type == 'turn_end':
                agent_name = event.get('agent', '')
                pos_after = event.get('position_after')
                if pos_after:
                    if 'Agent_A' in agent_name:
                        agent_a_pos = tuple(pos_after)
                    elif 'Agent_B' in agent_name:
                        agent_b_pos = tuple(pos_after)

                states.append({
                    'round': current_round,
                    'event': 'turn',
                    'agent': agent_name,
                    'agent_a': agent_a_pos,
                    'agent_b': agent_b_pos,
                    'reasoning_a': agent_a_reasoning,
                    'reasoning_b': agent_b_reasoning,
                    'event_data': event
                })

            elif event_type == 'game_end':
                states.append({
                    'round': current_round,
                    'event': 'end',
                    'agent_a': agent_a_pos,
                    'agent_b': agent_b_pos,
                    'reasoning_a': agent_a_reasoning,
                    'reasoning_b': agent_b_reasoning,
                    'winner': event.get('winner'),
                    'win_reason': event.get('win_reason'),
                    'event_data': event
                })

        return states


class ReplayCanvas(QWidget):
    """Replay canvas widget."""

    def __init__(self, map_size: int = 50, cell_size: int = 12, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.map_size = map_size
        self.cell_size = cell_size
        self.agent_a_pos = None
        self.agent_b_pos = None
        self.config = config or {}

        physics_config = config.get('physics', {}) if config else {}
        self.perception_radius = physics_config.get('perception_radius', 12.0)
        self.capture_radius = physics_config.get('capture_radius', 2.0)
        self.agent_b_capture_radius = physics_config.get('agent_b_capture_radius', 3.0)
        self.move_step = physics_config.get('move_step', 4.0)

        self.walls = self.config.get('walls', []) if self.config else []
        self.trail_a: List[tuple] = []

        self.setFixedSize(map_size * cell_size + 40, map_size * cell_size + 40)
        self.setStyleSheet("background-color: #1a1a2e;")

    def set_positions(self, agent_a, agent_b):
        self.agent_a_pos = agent_a
        self.agent_b_pos = agent_b
        self.update()

    def set_trail_a(self, trail: List[tuple]):
        self.trail_a = trail
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        self._draw_grid(painter)
        self._draw_walls(painter)

        if self.agent_a_pos:
            self._draw_perception_circle(painter, self.agent_a_pos, QColor(0, 255, 0, 20))
        if self.agent_b_pos:
            self._draw_perception_circle(painter, self.agent_b_pos, QColor(255, 0, 0, 20))

        if self.agent_a_pos:
            self._draw_movement_circle(painter, self.agent_a_pos, QColor(0, 150, 255, 60))

        if self.agent_a_pos:
            self._draw_capture_circle(painter, self.agent_a_pos, QColor(255, 215, 0, 100), is_agent_b=False)
        if self.agent_b_pos:
            self._draw_capture_circle(painter, self.agent_b_pos, QColor(255, 215, 0, 100), is_agent_b=True)

        if len(self.trail_a) > 1:
            self._draw_trail_a(painter)

        if self.agent_a_pos:
            self._draw_agent(painter, self.agent_a_pos, QColor(0, 255, 100), "A")
        if self.agent_b_pos:
            self._draw_agent(painter, self.agent_b_pos, QColor(255, 50, 50), "B")

        painter.end()

    def _draw_grid(self, painter: QPainter):
        pen = QPen(QColor(255, 255, 255, 30))
        pen.setWidth(1)
        painter.setPen(pen)

        offset_x = 20
        offset_y = 20

        for i in range(self.map_size + 1):
            x = offset_x + i * self.cell_size
            painter.drawLine(x, offset_y, x, offset_y + self.map_size * self.cell_size)

        for i in range(self.map_size + 1):
            y = offset_y + i * self.cell_size
            painter.drawLine(offset_x, y, offset_x + self.map_size * self.cell_size, y)

    def _draw_walls(self, painter: QPainter):
        """Draw walls with enhanced visual effects."""
        if not self.walls:
            return

        offset_x = 20
        offset_y = 20

        wall_color = QColor(220, 80, 40)
        wall_inner_color = QColor(255, 120, 60)
        wall_border = QColor(180, 50, 20)
        wall_glow = QColor(255, 100, 50, 80)
        wall_pattern = QColor(255, 200, 150, 100)

        for wall in self.walls:
            x1 = offset_x + int(wall['x1'] * self.cell_size)
            y1 = offset_y + int(wall['y1'] * self.cell_size)
            x2 = offset_x + int(wall['x2'] * self.cell_size)
            y2 = offset_y + int(wall['y2'] * self.cell_size)

            rect_left = min(x1, x2)
            rect_top = min(y1, y2)
            rect_right = max(x1, x2)
            rect_bottom = max(y1, y2)

            if rect_right - rect_left < 4:
                rect_right = rect_left + 4
            if rect_bottom - rect_top < 4:
                rect_bottom = rect_top + 4

            rect_width = rect_right - rect_left
            rect_height = rect_bottom - rect_top

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(wall_glow)
            glow_margin = 4
            painter.drawRect(
                rect_left - glow_margin,
                rect_top - glow_margin,
                rect_width + 2 * glow_margin,
                rect_height + 2 * glow_margin
            )

            pen = QPen(wall_border)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(wall_color)
            painter.drawRect(rect_left, rect_top, rect_width, rect_height)

            painter.setPen(QPen(wall_pattern, 1))
            step = 6
            for i in range(-rect_height, rect_width, step):
                line_start_x = rect_left + max(0, i)
                line_start_y = rect_top + max(0, -i)
                line_end_x = rect_left + min(rect_width, i + rect_height)
                line_end_y = rect_top + min(rect_height, -i + rect_width)
                if line_end_x > line_start_x and line_end_y > line_start_y:
                    painter.drawLine(line_start_x, line_start_y, line_end_x, line_end_y)

            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", 10, QFont.Weight.Bold)
            painter.setFont(font)
            text = "WALL"
            text_rect = painter.fontMetrics().boundingRect(text)
            text_x = rect_left + (rect_width - text_rect.width()) // 2
            text_y = rect_top + (rect_height + text_rect.height()) // 2
            painter.drawText(text_x, text_y, text)

            painter.setBrush(QColor(255, 255, 100))
            marker_size = 4
            corners = [
                (rect_left, rect_top),
                (rect_right, rect_top),
                (rect_left, rect_bottom),
                (rect_right, rect_bottom)
            ]
            for cx, cy in corners:
                painter.drawRect(cx - marker_size//2, cy - marker_size//2, marker_size, marker_size)

    def _draw_perception_circle(self, painter: QPainter, pos, color: QColor):
        offset_x = 20
        offset_y = 20
        cx = offset_x + float(pos[0]) * self.cell_size
        cy = offset_y + float(pos[1]) * self.cell_size
        radius = self.perception_radius * self.cell_size

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - radius), int(cy - radius),
                           int(radius * 2), int(radius * 2))

    def _draw_movement_circle(self, painter: QPainter, pos, color: QColor):
        """Draw movement range circle indicating max distance Agent A can move."""
        offset_x = 20
        offset_y = 20
        cx = offset_x + float(pos[0]) * self.cell_size
        cy = offset_y + float(pos[1]) * self.cell_size
        radius = self.move_step * self.cell_size

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - radius), int(cy - radius),
                           int(radius * 2), int(radius * 2))

        painter.setPen(QPen(QColor(0, 150, 255, 150), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(int(cx - radius), int(cy - radius),
                           int(radius * 2), int(radius * 2))

    def _draw_capture_circle(self, painter: QPainter, pos, color: QColor, is_agent_b: bool = False):
        """Draw capture range circle indicating distance needed to capture opponent."""
        offset_x = 20
        offset_y = 20
        cx = offset_x + float(pos[0]) * self.cell_size
        cy = offset_y + float(pos[1]) * self.cell_size
        capture_radius = self.agent_b_capture_radius if is_agent_b else self.capture_radius
        radius = capture_radius * self.cell_size

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - radius), int(cy - radius),
                           int(radius * 2), int(radius * 2))

        painter.setPen(QPen(QColor(255, 215, 0, 200), 2, Qt.PenStyle.SolidLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(int(cx - radius), int(cy - radius),
                           int(radius * 2), int(radius * 2))

    def _draw_trail_a(self, painter: QPainter):
        """Draw Agent A movement trail: connected lines + historical points, older = fainter."""
        offset_x = 20
        offset_y = 20
        total = len(self.trail_a)

        for i in range(1, total):
            alpha = int(30 + 180 * i / (total - 1))
            pen = QPen(QColor(0, 255, 100, alpha))
            pen.setWidth(2)
            painter.setPen(pen)
            prev = self.trail_a[i - 1]
            curr = self.trail_a[i]
            x1 = int(offset_x + float(prev[0]) * self.cell_size)
            y1 = int(offset_y + float(prev[1]) * self.cell_size)
            x2 = int(offset_x + float(curr[0]) * self.cell_size)
            y2 = int(offset_y + float(curr[1]) * self.cell_size)
            painter.drawLine(x1, y1, x2, y2)

        painter.setPen(Qt.PenStyle.NoPen)
        for i, pos in enumerate(self.trail_a[:-1]):
            alpha = int(20 + 120 * (i + 1) / total)
            painter.setBrush(QColor(0, 200, 80, alpha))
            cx = int(offset_x + float(pos[0]) * self.cell_size)
            cy = int(offset_y + float(pos[1]) * self.cell_size)
            painter.drawEllipse(cx - 2, cy - 2, 4, 4)

    def _draw_agent(self, painter: QPainter, pos, color: QColor, label: str):
        offset_x = 20
        offset_y = 20
        cx = offset_x + int(float(pos[0]) * self.cell_size)
        cy = offset_y + int(float(pos[1]) * self.cell_size)
        radius = max(4, self.cell_size // 2)

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(cx - 4, cy + 4, label)


class LogReplayWindow(QMainWindow):
    """Main log replay window."""

    def __init__(self, log_file: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("The Sand Pit - Log Replay")
        self.setStyleSheet("background-color: #16213e; color: #ffffff;")
        self.resize(900, 700)

        self.events = []
        self.states = []
        self.current_index = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._next_frame)
        self.is_playing = False

        self._setup_ui()

        if log_file:
            self._load_log(log_file)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setSpacing(10)

        # Left panel: canvas
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self.canvas = ReplayCanvas(map_size=50, cell_size=12, config={})
        left_layout.addWidget(self.canvas)

        controls = QHBoxLayout()

        self.btn_load = QPushButton("Load Log")
        self.btn_load.clicked.connect(self._load_log_dialog)
        controls.addWidget(self.btn_load)

        self.btn_play = QPushButton("Play")
        self.btn_play.clicked.connect(self._toggle_play)
        controls.addWidget(self.btn_play)

        self.btn_prev = QPushButton("<<")
        self.btn_prev.clicked.connect(self._prev_frame)
        controls.addWidget(self.btn_prev)

        self.btn_next = QPushButton(">>")
        self.btn_next.clicked.connect(self._next_frame)
        controls.addWidget(self.btn_next)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.valueChanged.connect(self._slider_changed)
        controls.addWidget(self.slider)

        left_layout.addLayout(controls)

        self.lbl_status = QLabel("No log loaded")
        self.lbl_status.setStyleSheet("color: #aaa;")
        left_layout.addWidget(self.lbl_status)

        layout.addWidget(left_panel)

        # Right panel: detail panel
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #0f3460; border-radius: 5px;")
        right_layout = QVBoxLayout(right_panel)
        right_panel.setFixedWidth(350)

        self.lbl_round = QLabel("Round: -")
        self.lbl_round.setStyleSheet("font-size: 16px; font-weight: bold; color: #e94560;")
        right_layout.addWidget(self.lbl_round)

        lbl_a = QLabel("Agent A (Pursuer - Green)")
        lbl_a.setStyleSheet("color: #00ff64; font-weight: bold;")
        right_layout.addWidget(lbl_a)

        self.lbl_pos_a = QLabel("Position: -")
        right_layout.addWidget(self.lbl_pos_a)

        lbl_thought_a = QLabel("Thought Process:")
        lbl_thought_a.setStyleSheet("color: #00aa64; font-size: 10px;")
        right_layout.addWidget(lbl_thought_a)

        self.txt_reasoning_a = QTextEdit()
        self.txt_reasoning_a.setReadOnly(True)
        self.txt_reasoning_a.setStyleSheet("background-color: #1a1a2e; color: #00ff64;")
        self.txt_reasoning_a.setMaximumHeight(150)
        right_layout.addWidget(self.txt_reasoning_a)

        lbl_b = QLabel("Agent B (Evader - Red) - STATIONARY")
        lbl_b.setStyleSheet("color: #ff3232; font-weight: bold;")
        right_layout.addWidget(lbl_b)

        self.lbl_pos_b = QLabel("Position: -")
        right_layout.addWidget(self.lbl_pos_b)

        lbl_thought_b = QLabel("Thought Process:")
        lbl_thought_b.setStyleSheet("color: #aa6464; font-size: 10px;")
        right_layout.addWidget(lbl_thought_b)

        self.txt_reasoning_b = QTextEdit()
        self.txt_reasoning_b.setReadOnly(True)
        self.txt_reasoning_b.setStyleSheet("background-color: #1a1a2e; color: #ff6464;")
        self.txt_reasoning_b.setMaximumHeight(150)
        right_layout.addWidget(self.txt_reasoning_b)

        self.legend = QFrame()
        self.legend.setStyleSheet("background-color: #1a1a2e; border-radius: 3px; padding: 5px;")
        self.legend_layout = QVBoxLayout(self.legend)

        self.lbl_legend = QLabel("Visual Legend")
        self.lbl_legend.setStyleSheet("font-weight: bold; color: #ffffff;")
        self.legend_layout.addWidget(self.lbl_legend)

        self.legend_labels = []
        legend_items = [
            ("Perception Range (loading...)", "Light green/red area"),
            ("Movement Range (loading...) - Agent A only", "Dashed blue circle"),
            ("Capture Range (loading...)", "Solid gold circle"),
            ("WALL - IMPENETRABLE", "Orange-red barrier, cannot cross"),
            ("Agent B - STATIONARY", "No movement"),
        ]

        for name, desc in legend_items:
            lbl = QLabel(f"{name}")
            lbl.setStyleSheet("color: #cccccc; font-size: 11px;")
            self.legend_labels.append(lbl)
            self.legend_layout.addWidget(lbl)

        right_layout.addWidget(self.legend)
        right_layout.addStretch()
        layout.addWidget(right_panel)

    def _load_log_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Log File", "logs",
            "JSONL Files (*.jsonl);;All Files (*.*)"
        )
        if file_path:
            self._load_log(file_path)

    def _load_log(self, log_file: str):
        try:
            self.events = LogParser.parse_log(log_file)
            self.states = LogParser.extract_game_states(self.events)

            if not self.states:
                self.lbl_status.setText("No game states found in log")
                return

            config = LogParser.extract_config(self.events)
            if config:
                physics_config = config.get('physics', {})
                self.canvas.perception_radius = physics_config.get('perception_radius', 12.0)
                self.canvas.capture_radius = physics_config.get('capture_radius', 2.0)
                self.canvas.agent_b_capture_radius = physics_config.get('agent_b_capture_radius', 3.0)
                self.canvas.move_step = physics_config.get('move_step', 4.0)
                self.canvas.walls = config.get('walls', [])
                self._update_legend_labels(config)

            self.slider.setMaximum(len(self.states) - 1)
            self.slider.setValue(0)
            self.current_index = 0
            self._update_display()

            self.lbl_status.setText(f"Loaded: {Path(log_file).name} ({len(self.states)} frames)")

        except Exception as e:
            self.lbl_status.setText(f"Error loading log: {e}")

    def _update_legend_labels(self, config: Dict[str, Any]):
        """Update legend labels based on configuration."""
        physics = config.get('physics', {})
        perception = physics.get('perception_radius', 12.0)
        move_step = physics.get('move_step', 4.0)
        capture_a = physics.get('capture_radius', 2.0)
        capture_b = physics.get('agent_b_capture_radius', 3.0)

        if len(self.legend_labels) >= 4:
            self.legend_labels[0].setText(f"Perception Range ({perception})")
            self.legend_labels[1].setText(f"Movement Range ({move_step}) - Agent A only")
            self.legend_labels[2].setText(f"Capture Range A({capture_a}) B({capture_b})")

    def _update_display(self):
        if not self.states or self.current_index >= len(self.states):
            return

        state = self.states[self.current_index]
        event_type = state.get('event', '')

        round_text = f"Round: {state['round']}"
        if event_type == 'round_start':
            round_text += " - Start"
        elif event_type == 'turn':
            agent = state.get('agent', '')
            round_text += f" - {agent} Moved"
        elif event_type == 'end':
            winner = state.get('winner', 'None')
            round_text += f" - Game Over! Winner: {winner}"
        self.lbl_round.setText(round_text)

        pos_a = state['agent_a']
        pos_b = state['agent_b']

        self.lbl_pos_a.setText(f"Position: ({pos_a[0]:.2f}, {pos_a[1]:.2f})" if pos_a else "Position: -")
        self.lbl_pos_b.setText(f"Position: ({pos_b[0]:.2f}, {pos_b[1]:.2f})" if pos_b else "Position: -")

        self.txt_reasoning_a.setText(state.get('reasoning_a', '') or "No reasoning recorded")
        self.txt_reasoning_b.setText(state.get('reasoning_b', '') or "No reasoning recorded")

        trail_a = []
        for s in self.states[:self.current_index + 1]:
            p = s.get('agent_a')
            if p and p[0] is not None and p[1] is not None:
                if not trail_a or (float(trail_a[-1][0]) != float(p[0]) or
                                   float(trail_a[-1][1]) != float(p[1])):
                    trail_a.append(p)
        self.canvas.set_trail_a(trail_a)

        self.canvas.set_positions(pos_a, pos_b)

        self.slider.blockSignals(True)
        self.slider.setValue(self.current_index)
        self.slider.blockSignals(False)

    def _toggle_play(self):
        if self.is_playing:
            self.timer.stop()
            self.btn_play.setText("Play")
            self.is_playing = False
        else:
            self.timer.start(500)
            self.btn_play.setText("Pause")
            self.is_playing = True

    def _next_frame(self):
        if self.current_index < len(self.states) - 1:
            self.current_index += 1
            self._update_display()
        else:
            if self.is_playing:
                self._toggle_play()

    def _prev_frame(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._update_display()

    def _slider_changed(self, value):
        self.current_index = value
        self._update_display()


def main():
    log_file = sys.argv[1] if len(sys.argv) > 1 else None

    app = QApplication(sys.argv)
    window = LogReplayWindow(log_file)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
