# 四格漫画提示词：沙蟹 vs 海葵

## 用途

本提示词用于生成一张 **4 格漫画**，以拟人化的海洋生物视角展示 The Sand Pit 游戏的核心设计与流程。可用于 README 配图、论文插图或项目宣传。

## 角色设定

- **Agent A（追击者）**：一只**沙蟹**（Sand Crab），横向移动迅速，有坚硬的螯，性格执着但有点憨。
- **Agent B（目标）**：一只**海葵**（Sea Anemone），扎根在沙地上，不能移动，但触手有感知范围，性格淡定、略带嘲讽。
- **场景**：海底沙地，50×50 网格，中央有一道竖直的**岩石墙**（x=25），墙上有狭窄的缺口。

## 风格要求

- 海洋科普绘本风格，色彩明亮、线条清晰
- 每格之间用细白边框分隔
- 上方或下方留窄条区域用于简短的中文/英文旁白
- 角色表情夸张、富有情绪，便于读者理解博弈张力

## 四格分镜脚本

### 第 1 格：Phase 1（Pre-wall / 直线接近）

**画面**：沙蟹在左侧沙地上快速横向爬行，身后留下一道沙痕。海葵在右侧远处，只露出一个小小的粉色轮廓。两者中间是宽阔的开放水域，气氛轻松。

**旁白**："Phase 1：沙蟹全力冲刺，海葵还在打盹。"

**情绪**：沙蟹自信满满，海葵悠闲。

---

### 第 2 格：Phase 2（Wall-nav / 绕墙瓶颈）

**画面**：沙蟹猛然刹停在岩石墙前，螯足举起，头顶冒出象征"思考"的泡泡（里面画着迷宫简图）。海葵在墙的另一侧，触手微微摇曳，仿佛在说"你过不来"。墙上有一个窄小的缺口，位置偏上或偏下。

**旁白**："Phase 2：认知瓶颈——沙蟹的 Token 预算决定它能不能‘想通’绕路。"

**情绪**：沙蟹困惑、焦虑（高 Token 时泡泡更多更乱）；海葵略带得意。

---

### 第 3 格：Phase 3（Post-wall / 开放冲刺）

**画面**：沙蟹已经成功穿过缺口，在墙的另一侧扬起沙尘再次冲刺。海葵现在清晰可见，粉色触手因为紧张而微微收缩。两者距离明显拉近。

**旁白**："Phase 3：障碍已越，纯物理冲刺，预算不再重要。"

**情绪**：沙蟹重燃希望，海葵开始紧张。

---

### 第 4 格：Phase 4（Hunt / 奇偶性对决）

**画面**：沙蟹与海葵已经非常接近（画面特写）。沙蟹的螯向前伸出，但画面用半透明的"回合标记"（A / B）悬浮在上方，暗示胜负取决于谁先手。海葵的触手形成一个保护圈。背景可以有一些数据统计样式的漂浮文字（如 "A-first: 88%"、"B-first: 14%"），增加学术趣味。

**旁白**："Phase 4：奇偶性决定论——谁先手，谁主宰命运。"

**情绪**：紧张、决定性的瞬间，略带黑色幽默（即使给了 20K Token，沙蟹也读不懂先后手）。

---

## 英文版 Prompt（可直接用于 Midjourney / DALL-E）

```
A 4-panel comic strip in a bright, marine science-illustration style, telling the story of a grid pursuit game on a sandy seabed.

Characters:
- Agent A: an enthusiastic but slightly goofy Sand Crab (sideways walker, hard claws).
- Agent B: a calm, rooted Sea Anemone (pink tentacles, cannot move, has a smug expression).
- Setting: a 50x50 underwater grid with a tall rock wall running vertically through the middle (x=25), with a small narrow gap.

Panel 1 (Phase 1 - Pre-wall): The Sand Crab scurries quickly across open sand toward the right, leaving a dust trail. The Sea Anemone is a tiny pink blob far in the distance on the other side. Lighthearted, energetic mood. Caption: "Phase 1: Straight commute."

Panel 2 (Phase 2 - Wall-nav): The Sand Crab stops dead at the rock wall, claws raised in confusion, thought bubbles above its head showing maze-like scribbles (more bubbles = higher token budget). The Sea Anemone waves its tentacles mockingly from behind the wall. A small gap is visible in the wall. Caption: "Phase 2: Cognitive bottleneck."

Panel 3 (Phase 3 - Post-wall): The Sand Crab bursts through the gap, kicking up sand, sprinting again. The Sea Anemone now looks nervous, tentacles retracting. The gap is behind the crab. Caption: "Phase 3: Open field."

Panel 4 (Phase 4 - Hunt): Close-up. The Sand Crab's claw reaches toward the Sea Anemone's tentacle ring. Floating translucent turn-order icons ("A" and "B") hover above, showing this is a parity showdown. Small statistical annotations float nearby: "A-first: 88%", "B-first: 14%". Tense, decisive mood. Caption: "Phase 4: Parity determinism."

Style: Clean linework, bright ocean palette (teal, sand-yellow, coral-pink), expressive cartoon faces, white borders between panels, narrative captions below each panel in both Chinese and English.
```

## 建议的图像生成工具

- **Midjourney v6**：使用 `--ar 16:9` 或 `--ar 2:1` 以获得横向漫画排版
- **DALL-E 3**：直接粘贴上述英文 prompt，通常理解分镜较好
- **Stable Diffusion / ComfyUI**：建议配合 ControlNet 的线稿控制，分格生成后拼接

## 备注

如果生成效果不理想，可尝试：
1. 先生成 4 张单格图，再用 Photoshop / Canva 拼接。
2. 将"Sand Crab"替换为"hermit crab"（寄居蟹），AI 对寄居蟹的识别度有时更高。
3. 在 Midjourney 中加入 `--sref` 参考图以保持四格风格一致。
