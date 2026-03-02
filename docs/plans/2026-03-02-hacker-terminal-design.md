# Datacenter Tycoon v2 — Hacker Terminal UI Design

**Date:** 2026-03-02
**Status:** Approved

---

## Goal

Replace the current tabbed TUI with a full-screen hacker terminal aesthetic. No menus, no visible panels by default — just a blank terminal with a BIOS-style boot sequence and a command-driven interface.

---

## Architecture

### Files Changed

| File | Change |
|------|--------|
| `ui/screens/boot_screen.py` | **New** — BIOS animation + new/returning player flow |
| `ui/screens/terminal_screen.py` | **New** — single full-screen terminal, replaces all tab panes |
| `ui/app.py` | **Modified** — push `BootScreen` instead of `NewGameScreen` |
| `ui/app.tcss` | **Modified** — full CSS rewrite for hacker theme |
| `ui/screens/main_screen.py` | **Deleted** (replaced by terminal_screen.py) |
| `ui/screens/new_game.py` | **Deleted** (replaced by boot_screen.py) |
| `ui/screens/*.py` (tab panes) | **Deleted** (datacenter_screen, market_screen, banking_screen, contracts_screen, glossary_screen, dashboard) |
| `game/**` | **Untouched** |
| `tests/**` | **Untouched** |
| `main.py` | **Untouched** |

---

## Layout

### State 1 — Default (nothing open, nothing pinned)

Terminal fills the entire screen. Clean black canvas.

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   [terminal output history — scrollable RichLog]           │
│                                                             │
│   [techcorp@datacenter ~]$ buy 10 AAPL                     │
│   Bought 10 AAPL @ $142.50  (-$1,425.00)                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│   [techcorp@datacenter ~]$ _                                │
└─────────────────────────────────────────────────────────────┘
```

### State 2 — Something pinned, nothing open

Pin panel floats top-left as an overlay. Terminal continues to fill the screen.

```
┌─────────────────────────────────────────────────────────────┐
│ ┌──────────────┐                                            │
│ │ Cash $82,400 │  [terminal history continues behind]       │
│ │ Day  47      │                                            │
│ └──────────────┘                                            │
├─────────────────────────────────────────────────────────────┤
│   [techcorp@datacenter ~]$ _                                │
└─────────────────────────────────────────────────────────────┘
```

### State 3 — Open panel active

Top 2/3 of screen splits into pin panel (left) + open panel (right). Terminal shrinks to bottom 1/3.

```
┌─────────────────────────────────────────────────────────────┐
│ ┌──────────────┐  ┌─────────────────────────────────────┐  │
│ │ [PINNED]     │  │  HARDWARE STORE                     │  │
│ │ Cash $82,400 │  │  ─────────────────────────────────  │  │  ← top 2/3
│ │ Day  47      │  │  cpu_budget   4 cores    $1,200     │  │
│ │ Inc  $4,200  │  │  cpu_mid      8 cores    $3,500     │  │
│ └──────────────┘  │  ram_8gb      8GB         $800      │  │
│                   │  hdd_500gb    500GB        $600      │  │
│                   └─────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  [techcorp@datacenter ~]$ open store                        │  ← bottom 1/3
│  Store opened. Type 'buyhw <hw_id>' to purchase.           │
│  Type 'close' to dismiss.                                   │
├─────────────────────────────────────────────────────────────┤
│  [techcorp@datacenter ~]$ _                                 │
└─────────────────────────────────────────────────────────────┘
```

### Textual Widget Structure

```
TerminalScreen (Screen)
├── Vertical (id="top-area", height=66%, display=none by default)
│   ├── Static (id="pin-panel", width=22, display=none by default)
│   └── Static (id="open-panel", expand=True)
├── RichLog (id="terminal", expand=True)
└── Input (id="cmd-input")
```

CSS controls visibility:
- `#top-area`: `display: none` → `display: block` when `open` is called
- `#pin-panel`: `display: none` → `display: block` when first `pin` is called
- When `close` is called and nothing is pinned: hide `#top-area` entirely

---

## Boot Sequence

### Flow

```
app.on_mount()
  └── push_screen(BootScreen)
        └── animate boot POST lines
              └── check: save file exists?
                    ├── NO  → new player prompts
                    └── YES → returning player snapshot
                          └── push_screen(TerminalScreen)
```

### BIOS Animation

Lines print one by one with ~60ms delay:

```
DATACENTER OS v1.0.0
Copyright (C) 2026 Datacenter Tycoon Corp

Initializing memory...             [ OK ]
Loading kernel modules...          [ OK ]
Mounting filesystems...            [ OK ]
Starting network services...       [ OK ]
──────────────────────────────────────────
 DATACENTER TYCOON TERMINAL
──────────────────────────────────────────
```

`[ OK ]` is rendered in green. Headers in purple. Body in green.

### New Player Path

```
No existing session found.

Enter company name: _
```

After name entered:

```
Enter company name: TechCorp
Select difficulty [easy/normal/hard]: _
```

After difficulty:

```
Creating session...                [ OK ]
Initializing accounts...           [ OK ]
Provisioning first rack...         [ OK ]

Welcome to DATACENTER TYCOON.
You have been allocated $50,000 in seed funding.

Type 'help' to begin.

[techcorp@datacenter ~]$ _
```

### Returning Player Path

```
Welcome back, TechCorp.  Day 47.

  Cash:             $82,400.00
  Active contracts: 3  (+$4,200/mo)
  Rack rent:        -$1,600/mo  (2 racks)
  Loan payments:    -$400/mo
  ──────────────────────────
  Net monthly:      +$2,200/mo

Type 'help' for available commands.

[techcorp@datacenter ~]$ _
```

### Multi-Step Input Handling

`BootScreen` tracks `_stage: str` with values `"name"` → `"difficulty"` → `"done"`. `on_input_submitted` dispatches based on stage. Input is blocked (disabled) during animation, enabled once animation completes.

---

## Commands

### New Commands

| Command | Description |
|---------|-------------|
| `view <target>` | Print formatted report to terminal |
| `pin <metric>` | Add metric to top-left panel |
| `unpin <metric>` | Remove metric from panel |
| `pin clear` | Wipe pin panel |
| `open <target>` | Show panel in top 2/3 |
| `close` | Dismiss open panel |

### `view` Targets

| Target | Shows |
|--------|-------|
| `view cash` | Checking + savings balances |
| `view contracts` | Active + pending contracts table |
| `view servers` | Servers, health, rack assignment |
| `view market` | Stock prices + portfolio |
| `view loans` | Active loans + monthly payments |
| `view bonds` | Bonds held + days to maturity |
| `view inventory` | Hardware components in stock |
| `view racks` | Rack list + capacity |
| `view gigs` | Available gig board |
| `view all` | Full financial summary (welcome screen re-printed) |

### `pin` Metrics

| Metric | Displays |
|--------|----------|
| `pin cash` | Cash  $82,400 |
| `pin day` | Day   47 |
| `pin income` | Inc   $4,200/mo |
| `pin rep` | Rep   72 |
| `pin credit` | Cred  650 |
| `pin net` | Net   +$2,200/mo |

### `open` Targets

| Target | Panel Shows |
|--------|-------------|
| `open store` | Hardware catalog — IDs, specs, prices |
| `open contracts` | Pending offers table |
| `open market` | Stock prices + portfolio |
| `open servers` | Server list with health + rack |
| `open racks` | Rack diagram |
| `open gigs` | Gig board |
| `open banking` | Accounts, loans, bonds |

### Existing Commands (unchanged)

All 20 v1 commands work identically: `day`, `save`, `help`, `tab` (repurposed as `open`), `buy`, `sell`, `transfer`, `loan`, `bond`, `sellbond`, `accept`, `decline`, `negotiate`, `assign`, `gig`, `buyhw`, `assemble`, `install`, `repair`, `rent`.

---

## Color Scheme

| Element | Color | Hex |
|---------|-------|-----|
| Background | Near-black | `#0a0a0a` |
| Primary text | Matrix green | `#00ff41` |
| Headers / accents | Purple | `#9d4edd` |
| Dim text | Dark green | `#3a7a3a` |
| Warnings | Amber | `#ffb703` |
| Errors | Red | `#ff4444` |
| `[ OK ]` | Green | `#00ff41` |
| Prompt | Green | `#00ff41` |

---

## Command Echo Format

Every command submission echoes to the RichLog before output:

```
[techcorp@datacenter ~]$ buy 10 AAPL
Bought 10 AAPL @ $142.50  (-$1,425.00)
```

The prompt prefix uses the company name in lowercase, truncated to 12 chars.

---

## Implementation Notes

- Boot animation: `async def _animate()` with `await asyncio.sleep(0.06)` per line, writes to a `RichLog` inside `BootScreen`
- `TerminalScreen` keeps the same `_run_command` / `_cmd_*` dispatch pattern from v1
- `#top-area` height is set via CSS; toggle `display: none` → `display: block` via `add_class` / `remove_class`
- Pin panel content is rebuilt from a `dict[str, callable]` that maps metric name → current value getter
- Open panel content is a `Static` widget updated by calling the appropriate `_render_<target>()` method
- `close` command hides `#top-area` if nothing is pinned, or hides only `#open-panel` if something is still pinned
