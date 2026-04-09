# Automated Capacity -- UI Design Document

## 1. Design Philosophy

Automated Capacity generalizes Karpathy's autoresearch concept: an AI agent that autonomously finds or builds simulated environments, then runs experiments to solve problems. The UI must serve two fundamentally different modes of interaction:

- **Active supervision** -- the user is watching, steering, and learning from the agent in real time.
- **Passive review** -- the user was asleep / away and returns to examine what happened.

The design language should communicate *quiet competence*. The system is doing complex work autonomously; the interface should feel like a mission control room -- dense with information but visually calm, with attention drawn only where it matters. Think Bloomberg Terminal meets a well-designed observability dashboard, not a flashy marketing page.

**Color system**: A dark background (not pure black -- something like `#0a0e17`) with a muted palette. The primary accent is a green (`#22c55e`) for positive signals (kept experiments, improving metrics). A warm amber (`#f59e0b`) for caution/neutral. A soft red (`#ef4444`) for failures/regressions. Agent "thinking" activity uses a cool blue (`#3b82f6`). Simulation domains each get a distinct but muted hue for visual identification.

**Typography**: Monospace for metrics, code, and logs. A clean sans-serif (Inter or similar) for labels and prose. Numbers should be tabular-aligned everywhere.

**Motion**: Subtle. Real-time data streams in smoothly. State transitions use 200ms eases. No gratuitous animation -- the data itself is the show.

---

## 2. Information Architecture

```
Automated Capacity
|
+-- Dashboard (home)
|   +-- Active Campaigns overview
|   +-- Global metrics ribbon
|   +-- Agent fleet status
|   +-- Recent activity feed
|
+-- Campaign (a single problem the agent is working on)
|   +-- Problem Definition
|   +-- Environment(s) in use
|   +-- Experiment Timeline
|   +-- Live Monitor (when running)
|   +-- Results & Analysis
|
+-- Environment Browser
|   +-- Domain categories (ML, Systems, Physics, etc.)
|   +-- Environment library (pre-built + user-created)
|   +-- Environment builder/editor
|
+-- Agent Configuration
|   +-- Strategy profiles
|   +-- Resource constraints
|   +-- Behavioral parameters
|
+-- History & Search
    +-- Full experiment archive
    +-- Cross-campaign comparison
    +-- Saved analyses
```

A **Campaign** is the central organizing concept. It corresponds to one problem statement. A campaign contains one or more environments and many experiments. This is the generalization of autoresearch's "branch" -- but now the agent might use multiple simulation environments within a single campaign (e.g., testing a control algorithm first in a simplified physics sim, then graduating to a higher-fidelity one).

---

## 3. Dashboard / Overview

### 3.1 Layout

The dashboard is a single scrollable page divided into horizontal bands:

```
+-----------------------------------------------------------------------+
|  [Logo/Name]    Campaign: ___________  [+ New Campaign]    [Settings] |
+-----------------------------------------------------------------------+
|                     GLOBAL METRICS RIBBON                             |
|  Experiments Today: 47  |  Keep Rate: 23%  |  Best Improvement: -2.1% |
|  Active Agents: 3       |  Total Compute: 14.2 GPU-hrs               |
+-----------------------------------------------------------------------+
|                                                                       |
|   ACTIVE CAMPAIGNS (cards)                                            |
|   +-------------------+  +-------------------+  +------------------+  |
|   | ML Training       |  | Robotics Control  |  | Portfolio Opt    |  |
|   | Campaign Alpha    |  | Quadcopter Hover  |  | Sharpe Max       |  |
|   |                   |  |                   |  |                  |  |
|   | [sparkline chart] |  | [sparkline chart] |  | [sparkline]      |  |
|   | val_bpb: 0.977    |  | reward: 847.2     |  | sharpe: 2.14     |  |
|   | Exp #83 running   |  | Exp #41 running   |  | Paused (idle)    |  |
|   | 15/83 kept        |  | 12/41 kept        |  | 8/22 kept        |  |
|   +-------------------+  +-------------------+  +------------------+  |
|                                                                       |
+-----------------------------------------------------------------------+
|                                                                       |
|   ACTIVITY FEED (chronological)                                       |
|   10:42  [ML Training]  Exp #84 KEPT -- "RoPE base freq 1e5->2e5"    |
|          val_bpb 0.977 -> 0.976 (-0.001)                             |
|   10:36  [ML Training]  Exp #83 DISCARDED -- "GeLU -> SwiGLU"        |
|   10:31  [Robotics]     Exp #42 KEPT -- "increase PD gain by 20%"    |
|   10:24  [ML Training]  Exp #82 CRASH -- OOM at 48GB                 |
|   ...                                                                 |
|                                                                       |
+-----------------------------------------------------------------------+
|                                                                       |
|   AGENT STATUS (fleet view)                                           |
|   Agent-1: [|||||||----] Running Exp #84 (ML Training) -- 3:22/5:00  |
|   Agent-2: [||||||||||] Evaluating Exp #42 (Robotics) -- finalizing   |
|   Agent-3: [--idle----] Waiting for assignment                        |
|                                                                       |
+-----------------------------------------------------------------------+
```

### 3.2 Component Details

**Global Metrics Ribbon**: A thin, always-visible bar at the top of the dashboard showing aggregate statistics. Numbers use countup animation when they change. Clicking any metric drills down to a filtered view of the relevant experiments.

**Active Campaign Cards**: Each card is a compact summary of one campaign. Contains:
- Campaign name and domain tag (with domain color pip)
- A sparkline showing the "running best" metric over experiment number (exactly like the autoresearch progress.png chart, but miniaturized)
- Current best metric value, bolded
- Experiment count and keep rate (e.g., "15/83 kept")
- Status indicator: running (pulsing dot), paused, completed, error
- Clicking a card navigates to the full Campaign view

**Activity Feed**: A reverse-chronological stream of experiment outcomes. Each entry shows:
- Timestamp
- Campaign name (color-coded by domain)
- Experiment number
- Outcome: KEPT (green), DISCARDED (gray), CRASH (red)
- One-line description of what was tried
- Delta from previous best (for kept experiments)

The feed supports filtering by campaign, outcome, and time range. It uses virtual scrolling for performance.

**Agent Status**: Shows each agent instance as a horizontal bar. The bar fills to show progress through the current experiment's time budget. Color indicates state: blue for running, green for evaluating, amber for idle, red for error. Clicking an agent opens the live monitor for its current experiment.

### 3.3 Interactions

- **Campaign cards** are draggable to reorder by priority.
- **Double-clicking** the sparkline on a campaign card opens the full progress chart.
- The **"+ New Campaign"** button opens the Problem Input flow (Section 4).
- **Keyboard shortcut** `Cmd+K` / `Ctrl+K` opens a command palette for quick navigation to any campaign, environment, or experiment by name/number.

---

## 4. Problem Input

### 4.1 Flow

The Problem Input is a multi-step wizard presented as a slide-over panel from the right side of the screen (not a full page navigation -- the dashboard remains visible underneath, dimmed). Steps:

```
Step 1: DESCRIBE THE PROBLEM
+-----------------------------------------------------------------------+
|                                                                       |
|  What problem should the agent solve?                                 |
|                                                                       |
|  +---------------------------------------------------------------+   |
|  | I want to pretrain a small language model on FineWeb-Edu and  |   |
|  | achieve the lowest possible validation bits-per-byte within   |   |
|  | a 5-minute training budget on a single H100. The agent should |   |
|  | explore architecture, optimizer, and hyperparameter changes.   |   |
|  +---------------------------------------------------------------+   |
|                                                                       |
|  Domain: [ML Training v]  (auto-detected, user can override)         |
|                                                                       |
|  Objective metric: ____________  Direction: [Minimize v]              |
|  Secondary metrics (optional): ____________                           |
|  Constraints: ____________                                            |
|                                                                       |
|                                           [Next ->]                   |
+-----------------------------------------------------------------------+

Step 2: ENVIRONMENT SELECTION
+-----------------------------------------------------------------------+
|                                                                       |
|  The agent analyzed your problem and suggests:                        |
|                                                                       |
|  RECOMMENDED                                                          |
|  +-----------------------------------+                                |
|  | [*] Single-GPU LLM Pretraining   |  98% match                    |
|  |     PyTorch, nanochat-based       |                                |
|  |     5-min time-budget, val_bpb    |                                |
|  +-----------------------------------+                                |
|                                                                       |
|  ALSO COMPATIBLE                                                      |
|  +-----------------------------------+                                |
|  | [ ] Multi-GPU Distributed Train  |  72% match                    |
|  +-----------------------------------+                                |
|  +-----------------------------------+                                |
|  | [ ] Custom Environment (new)     |  --                            |
|  +-----------------------------------+                                |
|                                                                       |
|                                  [<- Back]  [Next ->]                 |
+-----------------------------------------------------------------------+

Step 3: AGENT STRATEGY
+-----------------------------------------------------------------------+
|                                                                       |
|  How should the agent approach this?                                  |
|                                                                       |
|  Strategy preset: [Balanced v]                                        |
|                                                                       |
|     Exploration <===|=====> Exploitation                              |
|     Risk tolerance  <==|======> (conservative ... aggressive)         |
|     Simplicity bias <=======|==> (prefer simple ... allow complex)    |
|                                                                       |
|  Time budget per experiment: [5 min]                                  |
|  Max concurrent experiments: [1]                                      |
|  Auto-stop after: [Never v] / N experiments / N hours / target metric |
|                                                                       |
|  Mutable files: [train.py]  (add/remove)                             |
|  Read-only context: [prepare.py, README.md]  (add/remove)            |
|                                                                       |
|                                  [<- Back]  [Launch Campaign ->]      |
+-----------------------------------------------------------------------+
```

### 4.2 Component Details

**Problem Description**: A large, multi-line text area with a generous minimum height. The text area supports markdown. Below it, the system shows an auto-detected domain classification with a dropdown to override. This is not just cosmetic -- the domain determines which environments are suggested and which metric types are available.

**Objective Metric**: A text field for the metric name (e.g., `val_bpb`, `reward`, `sharpe_ratio`). The direction dropdown selects minimize or maximize. Secondary metrics are optional and used for constraint-checking / display but not for keep/discard decisions. Constraints are expressed as key-value pairs (e.g., `peak_vram_mb < 50000`, `latency_ms < 100`).

**Environment Selection**: Shows a ranked list of compatible environments from the library. Each environment card shows:
- Name and brief description
- Compatibility score (how well it matches the problem description)
- Tags: domain, language/framework, resource requirements
- A "preview" button that expands to show the environment's file structure and README

The user can select one or more environments. If selecting multiple, the agent will start with the highest-ranked and may graduate to others.

**Agent Strategy**: Sliders with labeled endpoints. The presets (Conservative, Balanced, Aggressive, Exploratory) set the sliders to predefined positions but the user can adjust individual sliders afterward. The "mutable files" and "read-only context" lists use a tag-input component where files can be added/removed.

### 4.3 Interactions

- The wizard remembers state -- closing and reopening returns to where you left off.
- Each step has inline validation. The "Next" button is disabled until required fields are filled.
- The problem description field has an "Enhance with AI" button that expands a terse description into a detailed one with suggested metrics and constraints.
- After launching, the user is taken directly to the Campaign view for the new campaign.

---

## 5. Environment Browser

### 5.1 Layout

A two-pane layout: domain/category sidebar on the left, environment grid on the right.

```
+-------------------+-------------------------------------------------------+
| DOMAINS           |  ENVIRONMENTS                           [+ Create]    |
|                   |  Search: [________________________] [Filters v]       |
| > All (47)        |                                                       |
|   ML Training (8) |  +------------------+ +------------------+            |
|   Systems (6)     |  | nanochat-single  | | distributed-llm  |            |
|   Robotics (5)    |  | GPU              | | multi-node       |            |
|   Physics (4)     |  | PyTorch, H100    | | PyTorch, NCCL    |            |
|   Chemistry (3)   |  | 5-min budget     | | configurable     |            |
|   Economics (4)   |  | 12 campaigns     | | 3 campaigns      |            |
|   Game/Strategy(5)|  +------------------+ +------------------+            |
|   Social (3)      |  +------------------+ +------------------+            |
|   Environment (4) |  | rl-gymnasium     | | custom-physics   |            |
|   Math/Opt (5)    |  | OpenAI Gym envs  | | MuJoCo-based     |            |
|                   |  | CPU or GPU       | | GPU recommended  |            |
|   [User Created]  |  | 7 campaigns      | | 2 campaigns      |            |
|                   |  +------------------+ +------------------+            |
|                   |                                                       |
+-------------------+-------------------------------------------------------+
```

### 5.2 Environment Detail View

Clicking an environment card opens a detail panel (slide-over from right):

```
+-----------------------------------------------------------------------+
|  NANOCHAT SINGLE-GPU PRETRAINING                                      |
|  Domain: ML Training    Created by: System    Used in: 12 campaigns   |
+-----------------------------------------------------------------------+
|                                                                       |
|  DESCRIPTION                                                          |
|  Single-file GPT pretraining on a single GPU. Based on Karpathy's    |
|  nanochat. Fixed 5-minute time budget, val_bpb metric.               |
|                                                                       |
|  FILES                                                                |
|  +-- train.py         (mutable)     26KB   GPT model + training loop |
|  +-- prepare.py       (read-only)   15KB   Data prep + evaluation    |
|  +-- pyproject.toml   (read-only)   543B   Dependencies             |
|                                                                       |
|  METRICS                                                              |
|  Primary: val_bpb (minimize)                                          |
|  Secondary: peak_vram_mb, mfu_percent, total_tokens_M, num_steps     |
|                                                                       |
|  REQUIREMENTS                                                         |
|  - Single NVIDIA GPU (H100 recommended)                               |
|  - Python 3.10+, uv                                                   |
|  - ~50GB VRAM                                                         |
|                                                                       |
|  HISTORICAL PERFORMANCE                                               |
|  [Chart: best val_bpb achieved across all campaigns using this env]   |
|                                                                       |
|  [Use in New Campaign]  [Clone & Modify]  [View Source]               |
+-----------------------------------------------------------------------+
```

### 5.3 Environment Builder

For creating new environments, a form-based editor:

- **Name and description** (text fields)
- **Domain classification** (dropdown)
- **File editor**: An embedded code editor (Monaco) for each file in the environment. Files are tagged as mutable or read-only. The user can add/remove files.
- **Metric configuration**: Define the primary metric name, direction, and how it's extracted from output (regex pattern or structured output format).
- **Resource requirements**: GPU, memory, disk, estimated time per experiment.
- **Validation**: A "dry run" button that executes the environment once to verify it works, captures the output, and confirms metric extraction.

---

## 6. Campaign View (Experiment Timeline + Live Monitor)

This is the most important and most visited screen. It combines the experiment history and live monitoring into a single view.

### 6.1 Layout

```
+-----------------------------------------------------------------------+
|  [<- Dashboard]  CAMPAIGN: ML Training Alpha          [Pause] [Stop]  |
|  Problem: Minimize val_bpb for single-GPU LLM pretraining            |
|  Environment: nanochat-single-gpu    Agent: Agent-1                   |
+-----------------------------------------------------------------------+
|                                                                       |
|  PROGRESS CHART                                                       |
|  (Full-width reproduction of the autoresearch progress.png style)     |
|                                                                       |
|    1.000 |  o  baseline                                               |
|          |  \                                                          |
|    0.990 |   o--o  halve batch / warmdown                             |
|          |       \                                                     |
|    0.980 |        o---o---o  depth 9 / LR tune / window pattern       |
|          |                 \                                           |
|    0.977 |                  o---*  <-- current best (pulsing)          |
|          +----+----+----+----+----+----+----+----+                    |
|          0   10   20   30   40   50   60   70   80                    |
|                        Experiment #                                    |
|                                                                       |
|  [x] Show discarded  [x] Show labels  [ ] Log scale  [Time axis v]   |
+-----------------------------------------------------------------------+
|                                                                       |
|  EXPERIMENT TABLE                          LIVE MONITOR               |
|  +------------------------------------+  +-------------------------+  |
|  | #  | Status | val_bpb | Desc       |  | EXPERIMENT #84          |  |
|  |----|--------|---------|------------|  | Status: RUNNING         |  |
|  | 84 | [run]  | --      | SwiGLU act |  | Elapsed: 3:22 / 5:00   |  |
|  | 83 | [keep] | 0.977   | RoPE freq  |  | [=========>----] 67%    |  |
|  | 82 | [crash]| --      | double wid |  |                         |  |
|  | 81 | [disc] | 0.979   | dropout 0.1|  | LIVE TRAINING LOSS      |  |
|  | 80 | [disc] | 0.978   | new sched  |  | [real-time line chart]  |  |
|  | 79 | [keep] | 0.978   | embed LR   |  |                         |  |
|  | .. |        |         |            |  | AGENT REASONING         |  |
|  +------------------------------------+  | "Trying SwiGLU because  |  |
|                                          |  GeLU variants showed   |  |
|  Showing 84 experiments                  |  promise in exp #71     |  |
|  15 kept, 62 discarded, 7 crashed        |  but SiLU didn't help.  |  |
|  Keep rate: 18%                          |  SwiGLU adds a gate     |  |
|                                          |  projection..."         |  |
|                                          |                         |  |
|                                          | CURRENT METRICS         |  |
|                                          | Step: 612/~950          |  |
|                                          | Train loss: 3.421       |  |
|                                          | VRAM: 44.2 GB           |  |
|                                          | MFU: 39.1%              |  |
|                                          | Tokens: 312M            |  |
|                                          +-------------------------+  |
+-----------------------------------------------------------------------+
```

### 6.2 Progress Chart

This is the hero visualization of the entire application. It directly extends the style shown in autoresearch's `progress.png`:

- **X-axis**: Experiment number (or optionally wall-clock time)
- **Y-axis**: Primary metric (auto-scaled, direction-aware -- "lower is better" for val_bpb, "higher is better" for reward)
- **Kept experiments**: Large filled circles in green, connected by a "running best" step line
- **Discarded experiments**: Small gray dots, unfilled
- **Crashed experiments**: Small red X marks
- **Labels**: Each kept experiment has a tooltip showing the description. When zoomed in or when "show labels" is on, descriptions appear as angled text annotations (exactly like the autoresearch chart)
- **Current experiment**: If running, shown as a pulsing/animated dot at the right edge. Its Y position updates in real time as interim metrics come in.
- **Hover**: Hovering over any point shows a tooltip with full experiment details
- **Click**: Clicking a point selects it and scrolls the experiment table to that row
- **Zoom**: Mouse wheel zooms the X-axis. Pinch-zoom on trackpad. A minimap below the chart shows the full range with the current viewport highlighted.
- **Toggle controls** below the chart: show/hide discarded, show/hide labels, log scale, switch X-axis between experiment number and wall clock time.

### 6.3 Experiment Table

A sortable, filterable table with the following columns:

| Column | Content |
|--------|---------|
| # | Experiment number |
| Status | Icon + color: green circle (keep), gray circle (discard), red X (crash), blue spinner (running) |
| Primary Metric | The objective metric value, bold if it's a new best |
| Delta | Change from previous best. Green negative for minimize, green positive for maximize |
| VRAM | Peak memory usage |
| Duration | Wall-clock time |
| Description | One-line summary of what was tried |
| Timestamp | When the experiment completed |

**Interactions**:
- Clicking a row expands it inline to show:
  - Full agent reasoning (why it tried this)
  - Code diff (what changed in the mutable files)
  - Full metric output block
  - Stdout/stderr log (collapsible, scrollable)
- Multi-select rows (checkboxes) to compare them in the Results & Analysis view
- Right-click context menu: "Revert to this experiment", "Branch from this experiment", "View diff from baseline"
- Column sorting and text filtering on description

### 6.4 Live Monitor Panel

The right panel during an active experiment. Contains:

**Progress Bar**: Shows elapsed time vs. time budget. Uses the environment's configured time budget. The bar color transitions from blue to green as it approaches completion.

**Live Training Metrics Chart**: A real-time streaming line chart showing training loss (and optionally other metrics) as the experiment runs. Updates every few seconds. The chart auto-scrolls but can be paused by hovering. A faint horizontal line shows the previous best metric for reference.

**Agent Reasoning**: A scrolling text area showing the agent's thought process. This is the agent's internal reasoning about why it chose this experiment, what it expects, and any mid-experiment observations. Formatted as markdown. This is crucial for the user to understand the agent's strategy -- it transforms the system from a black box into a transparent research partner.

**Current Metrics**: A small key-value table showing live stats: current training step, train loss, VRAM usage, MFU, tokens processed. These update in real time.

**Log Tail**: A collapsible section at the bottom showing the last ~20 lines of raw stdout/stderr. Monospace, with ANSI color support. Can be expanded to full screen.

### 6.5 Campaign Controls

- **Pause**: Stops the agent after the current experiment finishes. The campaign remains in a paused state and can be resumed.
- **Stop**: Terminates the campaign. The agent finishes the current experiment, logs results, and halts.
- **Abort** (in dropdown): Kills the current experiment immediately. Use with caution.
- **Branch**: Creates a new campaign branching from the current best state. Useful for exploring a different strategy from a known-good starting point.

---

## 7. Results & Analysis

### 7.1 Access

The Results & Analysis view is accessible from within a campaign (via a tab) or as a standalone page for cross-campaign comparison.

### 7.2 Single-Campaign Analysis

```
+-----------------------------------------------------------------------+
|  ANALYSIS: ML Training Alpha                                          |
+-----------------------------------------------------------------------+
|                                                                       |
|  METRIC TRAJECTORY (extended version of progress chart)               |
|  [Full-width chart with multiple metrics overlaid]                    |
|  Toggle: [x] val_bpb  [ ] VRAM  [ ] MFU  [ ] tokens  [ ] steps      |
|                                                                       |
+-----------------------------------------------------------------------+
|                                                                       |
|  IMPROVEMENT BREAKDOWN                                                |
|  +---------------------------------------------------------------+   |
|  |  Category       | Experiments | Kept | Avg Improvement | Best |   |
|  |  Architecture   |     12      |   3  |    -0.003       | -0.005|  |
|  |  Optimizer      |      8      |   2  |    -0.002       | -0.004|  |
|  |  Hyperparameters|     31      |   6  |    -0.001       | -0.003|  |
|  |  Training Loop  |      5      |   1  |    -0.001       | -0.002|  |
|  |  Other          |     27      |   3  |    -0.001       | -0.002|  |
|  +---------------------------------------------------------------+   |
|                                                                       |
+-----------------------------------------------------------------------+
|                                                                       |
|  AGENT STRATEGY OVER TIME                                             |
|  [Stacked area chart showing proportion of experiment categories      |
|   over time -- does the agent shift from exploration to exploitation?] |
|                                                                       |
+-----------------------------------------------------------------------+
|                                                                       |
|  CODE EVOLUTION                                                       |
|  A side-by-side diff viewer showing how the mutable file(s) evolved   |
|  from baseline to current best. Each kept experiment is a "layer"     |
|  that can be toggled on/off to see cumulative changes.                |
|                                                                       |
|  [Baseline]  [+exp 4]  [+exp 8]  [+exp 15]  ... [+exp 83] = Current |
|                                                                       |
|  +----------------------------+----------------------------+          |
|  | train.py (baseline)       | train.py (current best)    |          |
|  | ...                        | ...                        |          |
|  | DEPTH = 8                  | DEPTH = 9                  |          |
|  | ...                        | ...                        |          |
|  +----------------------------+----------------------------+          |
|                                                                       |
+-----------------------------------------------------------------------+
|                                                                       |
|  AGENT REASONING LOG                                                  |
|  Searchable, filterable view of all agent reasoning entries across    |
|  all experiments. Useful for understanding the agent's evolving       |
|  understanding of the problem.                                        |
|                                                                       |
+-----------------------------------------------------------------------+
```

### 7.3 Component Details

**Multi-Metric Trajectory**: An extended version of the progress chart that can overlay multiple metrics on shared or independent Y-axes. Useful for seeing correlations (e.g., does VRAM track with val_bpb improvement?). Each metric is a toggleable line with its own color and scale.

**Improvement Breakdown**: A table that categorizes experiments by the type of change attempted (auto-classified from the agent's descriptions using keyword analysis or LLM classification). Shows success rate, average improvement, and best improvement per category. This helps users understand which directions are most productive.

**Agent Strategy Over Time**: A stacked area chart showing what proportion of experiments fall into each category over time. This reveals the agent's evolving strategy -- early experiments might be broad architectural exploration, later ones might be fine-grained hyperparameter tuning. This is a unique insight that no human researcher typically has visibility into.

**Code Evolution**: A multi-version diff viewer. The left pane shows baseline code. The right pane shows the current best. Between them, a "timeline scrubber" lets the user step through each kept experiment to see the cumulative diff grow. Each kept experiment is a checkbox -- toggling one off shows what the code would look like without that change. This is essentially `git log --oneline` visualized as an interactive diff.

**Agent Reasoning Log**: A searchable feed of all agent reasoning entries. Each entry is tagged with the experiment number, outcome, and category. Users can search for specific concepts ("Did the agent ever consider mixture of experts?") to understand the agent's decision-making process.

### 7.4 Cross-Campaign Comparison

When accessed from the top-level History page, users can select multiple campaigns and compare:

- Normalized metric improvement curves (percentage improvement from baseline, overlaid)
- Keep rates over time
- Strategy distributions
- Time-to-best-result
- Resource usage profiles

This helps users learn which problem types benefit most from autonomous experimentation and which agent strategies work best.

---

## 8. Agent Configuration

### 8.1 Layout

A form-based settings page with sections, accessible from the campaign creation flow or the global settings. Uses a left sidebar for section navigation.

```
+-------------------+-------------------------------------------------------+
| SECTIONS          |  EXPLORATION STRATEGY                                 |
|                   |                                                       |
| > Strategy        |  Preset: [Balanced v]                                 |
|   Resources       |                                                       |
|   Behavior        |  Exploration vs. Exploitation                          |
|   Safety          |  [======|=========] 40% explore / 60% exploit          |
|   Advanced        |  How much should the agent try novel approaches vs.    |
|                   |  refine what's already working?                        |
|                   |                                                       |
|                   |  Risk Tolerance                                        |
|                   |  [===|=============] Low                               |
|                   |  How willing is the agent to try changes that might    |
|                   |  crash or significantly regress?                       |
|                   |                                                       |
|                   |  Simplicity Bias                                       |
|                   |  [==========|=====] High                               |
|                   |  Should the agent prefer simpler solutions? (High =    |
|                   |  reject marginal improvements that add complexity)     |
|                   |                                                       |
|                   |  Change Magnitude                                      |
|                   |  [=====|==========] Medium                             |
|                   |  Should the agent make small incremental tweaks or     |
|                   |  large structural changes?                             |
|                   |                                                       |
|                   |  Backtrack Willingness                                 |
|                   |  [==|==============] Low                               |
|                   |  How willing is the agent to revert multiple kept      |
|                   |  experiments and try a different path entirely?         |
|                   |                                                       |
+-------------------+-------------------------------------------------------+
```

### 8.2 Sections

**Strategy** (shown above): Controls the agent's research approach. Each slider has a plain-English description and shows its current position relative to the named presets. Presets:
- **Conservative**: Low risk, high simplicity bias, small changes, low backtracking. Good for polishing a nearly-optimal solution.
- **Balanced**: Default. Mix of exploration and exploitation.
- **Aggressive**: High risk, large changes, willing to backtrack. Good for early-stage exploration or when progress has stalled.
- **Exploratory**: Maximum exploration, low exploitation. Good for understanding the solution landscape without trying to converge.

**Resources**:
- Max VRAM per experiment (slider with numeric input, in GB)
- Max wall-clock time per experiment
- Max total experiments (or "unlimited")
- Max total compute time
- Concurrent experiment limit (for multi-GPU setups)
- GPU assignment (for multi-GPU: which GPUs to use)

**Behavior**:
- Auto-stop conditions: Stop on target metric, stop on N consecutive failures, stop on no improvement for N experiments
- Notification preferences: Notify on new best, notify on crash, notify on auto-stop, periodic summaries
- Log verbosity: Minimal (outcomes only), Normal (outcomes + reasoning), Verbose (everything including raw logs)

**Safety**:
- Mutable file whitelist (which files the agent can modify)
- Forbidden patterns (regex patterns the agent must not introduce into code, e.g., `os.system`, `subprocess`, network calls)
- VRAM hard limit (experiment is killed if exceeded, not just warned)
- Code review mode: Require human approval before each experiment runs (defeats the purpose of autonomy, but useful for initial trust-building)

**Advanced**:
- Custom system prompt additions (text that's appended to the agent's instructions)
- Environment variables to set during experiments
- Pre-experiment and post-experiment hooks (shell commands)
- Metric extraction override (custom regex or script)

### 8.3 Interactions

- All settings changes are saved immediately (no save button -- auto-save with a "saved" toast).
- Changes to strategy parameters take effect on the next experiment (not the currently running one).
- A "Reset to defaults" button per section.
- An "Export config" button that generates a JSON/YAML file for reproducibility.
- An "Import config" button to load a previously exported configuration.
- Settings can be scoped to a specific campaign or set as global defaults.

---

## 9. Notification System

### 9.1 In-App Notifications

A notification bell icon in the top-right corner. Shows a badge count. Clicking opens a dropdown:

```
+------------------------------------------+
| NOTIFICATIONS                    [Clear] |
|                                          |
| [*] New best! ML Training Alpha         |
|     val_bpb: 0.976 (exp #84)            |
|     2 minutes ago                        |
|                                          |
| [*] Campaign paused: Robotics Control   |
|     No improvement for 10 experiments    |
|     15 minutes ago                       |
|                                          |
| [ ] Crash: Portfolio Optimization       |
|     OOM in exp #23                       |
|     1 hour ago                           |
|                                          |
+------------------------------------------+
```

### 9.2 External Notifications

Configurable in Settings:
- Browser push notifications
- Email digest (hourly / daily / on-event)
- Webhook URL (for Slack/Discord integration)
- Desktop notifications (via Notification API)

---

## 10. Simulation Domain-Specific Considerations

Each simulation domain has unique visualization needs. The UI framework should support domain-specific "metric widgets" that plug into the standard experiment view.

### 10.1 ML Training
- Training loss curve (real-time streaming chart)
- Learning rate schedule visualization
- Model architecture diagram (auto-generated from code)
- Token throughput / MFU gauge

### 10.2 Systems / Infrastructure
- Latency distribution histograms
- Throughput over time
- Resource utilization heatmaps (CPU, memory, network, disk)
- Queue depth / backpressure visualizations

### 10.3 Control / Robotics
- Embedded simulation video/animation player (if the sim renders frames)
- State trajectory plots (position, velocity, angle over time)
- Control signal plots
- Reward decomposition (which components of the reward improved)

### 10.4 Physics / Engineering
- 2D/3D simulation visualization (Three.js or similar, embedded)
- Stress/strain field heatmaps
- Convergence curves for iterative solvers
- Parameter sensitivity tornado diagrams

### 10.5 Chemistry / Biology
- Molecular structure viewer (if applicable)
- Reaction rate / concentration curves
- Fitness landscape visualization
- Population dynamics plots

### 10.6 Economics / Markets
- Portfolio allocation pie/bar charts
- Returns distribution histograms
- Sharpe ratio / drawdown over time
- Correlation matrices

### 10.7 Game / Strategy
- Game board / state visualizer (domain-specific)
- Win rate over training time
- Strategy distribution heatmaps
- Elo/rating progression curves

### 10.8 Social / Agent-Based Models
- Network graph visualization
- Agent population state distributions
- Emergent behavior detection highlights
- Aggregate metric time series

### 10.9 Environment / Energy
- Grid/network topology visualization
- Load/generation balance curves
- Emission / cost Pareto frontiers
- Geographic heatmaps (if applicable)

### 10.10 Math / Combinatorial Optimization
- Solution quality over time (incumbent value curve)
- Feasibility rate tracking
- Solution visualization (graph coloring, route plots, bin packing diagrams)
- Gap-to-optimum tracking (if bounds are known)

---

## 11. Responsive Behavior & Accessibility

### 11.1 Layout Breakpoints

- **Wide (>1600px)**: Full three-column layout on Campaign view (table + chart + live monitor side by side).
- **Standard (1200-1600px)**: Two-column layout. Live monitor stacks below the chart. Table is full width.
- **Narrow (800-1200px)**: Single column. Tab-based navigation between chart, table, and monitor.
- **Mobile (<800px)**: Not a primary target, but the dashboard and notification views should be usable. Campaign detail is a simplified single-column feed.

### 11.2 Accessibility

- All charts have a table-based fallback accessible via screen reader.
- Color is never the sole indicator of state -- icons and text labels accompany all color signals.
- Keyboard navigation: Tab through all interactive elements, Enter to activate, Escape to close panels.
- High-contrast mode toggle in settings.
- All real-time updates are announced to screen readers via ARIA live regions (polite, not assertive -- the updates are frequent).

---

## 12. Real-Time Data Architecture

### 12.1 Data Flow

The UI receives data through two channels:

1. **REST API** for initial page loads and historical data. Paginated, with cursor-based pagination for the experiment table.
2. **WebSocket / Server-Sent Events** for real-time updates:
   - Experiment status changes (started, completed, kept, discarded, crashed)
   - Live training metrics (every 5-10 seconds during an experiment)
   - Agent reasoning updates (as the agent generates them)
   - Log lines (streaming)

### 12.2 State Management

Client-side state is organized around campaigns:

```
{
  campaigns: {
    [campaignId]: {
      metadata: { name, domain, status, createdAt, ... },
      experiments: [{ id, number, status, metrics, description, ... }],
      currentBest: { experimentId, metricValue },
      liveExperiment: {
        experimentId,
        elapsedTime,
        streamingMetrics: [{ timestamp, trainLoss, ... }],
        agentReasoning: string,
        logTail: string[],
      }
    }
  },
  agents: [{ id, status, currentCampaignId, currentExperimentId }],
  notifications: [...],
  globalMetrics: { experimentsToday, keepRate, ... }
}
```

### 12.3 Optimistic Updates

When the user pauses or stops a campaign, the UI updates immediately (optimistic) and reconciles if the server response differs. This prevents the UI from feeling sluggish.

### 12.4 Data Retention

All experiment data is persisted indefinitely. Raw logs are retained for 30 days by default (configurable). Agent reasoning is always retained. Code diffs are computed on-demand from git history and cached.

---

## 13. Key Interaction Patterns

### 13.1 The "Morning Review" Flow

The most common interaction for passive users:
1. Open the dashboard. See the global metrics ribbon: "47 experiments overnight, 8 kept, best improvement -2.3%".
2. Click the campaign card. See the progress chart with new green dots extending the running-best line.
3. Scan the experiment table, sorted by newest first. Expand a few kept experiments to read the agent's reasoning and see the diffs.
4. Open Analysis > Code Evolution to see the cumulative diff from baseline to current best.
5. Optionally adjust strategy sliders based on observations (e.g., "the agent is making too many small hyperparameter tweaks, increase Change Magnitude").
6. Resume or let it keep running.

### 13.2 The "Active Watching" Flow

For engaged users monitoring in real time:
1. Open the campaign view. The live monitor panel shows the current experiment.
2. Watch the training loss curve update in real time. Compare it mentally (or visually, with the reference line) to the previous best.
3. Read the agent's reasoning as it appears. Understand why this experiment was chosen.
4. When the experiment completes, see the outcome flash on screen (KEPT in green or DISCARDED in gray).
5. Watch the progress chart update with the new point.
6. If curious about a specific past experiment, click its dot on the chart or its row in the table.

### 13.3 The "Intervention" Flow

When the user wants to steer the agent:
1. Pause the campaign.
2. Modify the agent strategy (increase exploration, change risk tolerance).
3. Optionally, manually edit the mutable files (the agent will pick up from the new state).
4. Optionally, add a "hint" -- a text note that's injected into the agent's context for the next experiment ("Consider trying mixture of experts architecture").
5. Resume.

### 13.4 The "Hindsight" Flow

When the user wants to explore what-ifs:
1. Open Analysis > Code Evolution.
2. Toggle off a specific kept experiment to see what the code would look like without that change.
3. Optionally, "branch from here" -- create a new campaign starting from any historical experiment state.

---

## 14. Component Inventory

A summary of all UI components needed:

| Component | Type | Used In |
|-----------|------|---------|
| CampaignCard | Card | Dashboard |
| MetricsRibbon | Stat bar | Dashboard |
| ActivityFeed | List | Dashboard |
| AgentStatusBar | Progress bar | Dashboard |
| ProgressChart | Chart (custom) | Campaign, Analysis |
| ExperimentTable | Table | Campaign |
| LiveMonitorPanel | Panel | Campaign |
| TrainingLossChart | Streaming chart | Live Monitor |
| AgentReasoningFeed | Text stream | Live Monitor, Analysis |
| LogViewer | Terminal/monospace | Live Monitor, Experiment Detail |
| DiffViewer | Code diff | Experiment Detail, Analysis |
| CodeEvolutionViewer | Multi-diff | Analysis |
| MetricTrajectoryChart | Multi-line chart | Analysis |
| ImprovementBreakdownTable | Table | Analysis |
| StrategyDistributionChart | Stacked area | Analysis |
| ProblemInputWizard | Multi-step form | Problem Input |
| EnvironmentGrid | Card grid | Environment Browser |
| EnvironmentDetailPanel | Slide-over | Environment Browser |
| EnvironmentBuilder | Form + editor | Environment Browser |
| StrategySliders | Form with sliders | Agent Config |
| ResourceConfig | Form | Agent Config |
| NotificationDropdown | Dropdown | Global |
| CommandPalette | Modal | Global (Cmd+K) |
| DomainMetricWidget | Plugin | Campaign (varies by domain) |

---

## 15. Visual Identity Notes

### 15.1 The Progress Chart Is the Hero

The progress chart (Section 6.2) is the single most important visualization. It should be beautiful enough to screenshot and share. The autoresearch progress.png is already excellent -- our version should be a pixel-perfect, interactive reproduction. When users think of Automated Capacity, they should picture that chart with its green stepping-stone line descending toward better results, surrounded by a constellation of gray discarded attempts.

### 15.2 Information Density Over Whitespace

This is a tool for power users. Every pixel should earn its place. The default state should show more data, not less. Collapse/expand controls let users reduce density if desired, but the starting point is dense. Think: dark theme observability dashboard, not a marketing landing page.

### 15.3 The Agent as a Character

The agent's reasoning feed gives the system personality. The reasoning should be displayed prominently, not hidden in a collapsible section. When the agent makes a clever connection ("Exp #71 showed that activation function matters, and SwiGLU worked in the Llama paper, so let's try it") -- that's the moment of delight. The UI should make these moments discoverable and readable.

### 15.4 Sound Design (Optional Enhancement)

Subtle, optional audio cues:
- A gentle chime when an experiment is KEPT (positive feedback, like a quiet "ding")
- A muted thud when DISCARDED
- A brief alert tone for crashes
- These should default to OFF and be togglable in settings. They're useful when the user has the dashboard open in a background tab.

---

## 16. Technology Recommendations

This document is technology-agnostic, but the following would be strong choices:

- **Framework**: Next.js (React) or SvelteKit. The component model maps cleanly to React; Svelte would give smoother animations.
- **Charting**: D3.js for the Progress Chart (needs full custom control). A library like Recharts or Victory for simpler charts (metrics ribbon sparklines, etc.).
- **Code editor**: Monaco (VS Code's editor) for the environment builder's file editor.
- **Diff viewer**: `react-diff-viewer` or a Monaco-based diff view.
- **Real-time**: Socket.io or native WebSockets. SSE is simpler if bidirectional communication isn't needed from the client.
- **State**: Zustand (lightweight) or Jotai (atomic). Redux is overkill here.
- **Styling**: Tailwind CSS for rapid iteration, with CSS custom properties for theming.
- **Terminal/log viewer**: xterm.js for full ANSI support in the log viewer.

---

## 17. Open Questions for Further Design Iteration

1. **Multi-agent collaboration**: When multiple agents work on the same campaign (e.g., one exploring architecture, one tuning hyperparameters), how do we visualize their individual contributions and coordination? The progress chart could use different marker shapes per agent.

2. **Environment versioning**: When a user modifies a shared environment, should existing campaigns using it be affected? Probably not -- campaigns should pin an environment version. The UI needs to show "Environment v3 (v5 available, upgrade?)" somewhere.

3. **Collaborative use**: If multiple humans are watching/steering the same campaign, do we need real-time cursors, chat, or conflict resolution? Likely not for v1, but worth considering.

4. **Mobile companion app**: A read-only mobile view for checking campaign status from bed at 3 AM when you wonder if the agent found anything good. The notification system should carry enough context that you don't need to open the full UI.

5. **Plugin system for domain widgets**: The domain-specific visualizations (Section 10) should be pluggable. A well-defined interface for "here's a React component that receives experiment metrics and renders a domain-specific view" would allow the community to contribute new domain visualizations.

6. **Export and reproducibility**: Users will want to export their best experiment as a standalone, runnable artifact. The UI should have an "Export" action that packages the final code, configuration, and a reproducibility report (environment version, git commit, full experiment lineage).
