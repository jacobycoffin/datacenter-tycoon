# Datacenter Tycoon v1 — Command Interface Design

**Date:** 2026-02-28
**Goal:** Make the game fully playable by replacing button-based UI with a terminal command interface, and completing the missing gameplay features (server assembly, rack install, gig collection, server repair, early bond selling).

---

## Core Concept

Visual panels display game state as read-only dashboards. All actions are taken by typing commands into a persistent command bar at the bottom of the screen. Each panel shows a `cmd:` hint line so the player always knows what to type. Numbers in panels ([1], [2], etc.) are the references used in commands.

---

## Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Header: Company | Day | Cash | Net Worth | Rep | Credit        │
├─────────────────────────────────────────────────────────────────┤
│  [Tab 1] [Tab 2] [Tab 3] [Tab 4] [Tab 5] [Tab 6]               │
│                                                                  │
│  (active tab content — read-only visual panel)                  │
│  cmd: <available commands for this tab>                         │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Event log (last 3 entries)                                      │
├─────────────────────────────────────────────────────────────────┤
│  > _                                              [Enter]        │
│  Last: Bought 10 NVLT @ $145.20 (-$1,452.00)                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Command Language

### Global commands (work from any tab)
| Command | Action |
|---------|--------|
| `day` | Advance one day (SPACE also works) |
| `save` | Save game |
| `help` | Show all commands |
| `tab <n>` | Switch to tab n (1–6) |

### Market tab (Tab 3)
| Command | Action |
|---------|--------|
| `buy <qty> <ticker>` | Buy qty shares of ticker |
| `sell <qty> <ticker>` | Sell qty shares of ticker |

### Banking tab (Tab 4)
| Command | Action |
|---------|--------|
| `transfer <amount> savings` | Move amount from checking → savings |
| `transfer <amount> checking` | Move amount from savings → checking |
| `loan <amount> <months>` | Take a loan (6, 12, or 24 months) |
| `bond <amount>` | Buy a bond (30-day maturity, 15% yield) |
| `sellbond <n>` | Sell bond #n early (at discounted value) |

### Contracts tab (Tab 5)
| Command | Action |
|---------|--------|
| `accept <n>` | Accept contract offer #n |
| `decline <n>` | Decline contract offer #n |
| `negotiate <n>` | Negotiate offer #n (+15% counter) |
| `assign <contract_n> <server_name>` | Assign server to active contract #n |
| `gig <n>` | Collect gig #n (instant payout) |

### Datacenter tab (Tab 2)
| Command | Action |
|---------|--------|
| `buyhw <hw_id>` | Buy hardware component |
| `assemble <name> <cpu_id> <ram_id> [ram_id...] <storage_id> [storage_id...] <nic_id>` | Assemble server |
| `install <server_name> <rack_n>` | Install server into rack n |
| `repair <server_name>` | Repair degraded server (cost: $500) |
| `rent` | Rent another rack ($800/mo) |

---

## Panel Changes per Tab

### Tab 1 — Dashboard
- No commands. Pure read-only financial summary.
- Show: net worth, cash, savings, investments, debt, monthly P&L, market snapshot sparkline, business overview.

### Tab 2 — Datacenter
- **Rack view:** ASCII rack diagram, numbered racks. Servers show health color.
- **Hardware shop:** table of components with `[hw_id]` references shown.
- **Inventory:** list of unassembled components + assembled-but-unracked servers.
- **Cmd hint:** `buyhw <hw_id> | assemble <name> <cpu> <ram> <storage> <nic> | install <server> <rack_n> | repair <server> | rent`

### Tab 3 — Market
- Stock table with `[n]` row numbers. Columns: #, Ticker, Name, Price, Change, Chart, Owned.
- Portfolio summary below.
- **Cmd hint:** `buy <qty> <ticker> | sell <qty> <ticker>`

### Tab 4 — Banking
- Checking + savings balances.
- Loans table with `[n]` numbers showing balance, rate, days remaining.
- Bonds table with `[n]` numbers showing face value, yield, days remaining.
- **Cmd hint:** `transfer <amt> savings|checking | loan <amt> <months> | bond <amt> | sellbond <n>`

### Tab 5 — Contracts
- Incoming offers table numbered `[1]`, `[2]`, etc.
- Active contracts table numbered `[1]`, `[2]`, etc. with server assignment shown.
- Gig board numbered `[1]`, `[2]`, etc.
- **Cmd hint:** `accept <n> | decline <n> | negotiate <n> | assign <n> <server> | gig <n>`

### Tab 6 — Glossary
- Live search still via typing in a dedicated search input (switched to with `?` key).
- No commands needed.

---

## New Gameplay Features

### Server Assembly (`assemble` command)
- Takes: server name, 1 CPU id, 1-4 RAM ids, 1-4 storage ids, 1 NIC id
- All component ids must be in `hardware_inventory`
- On success: components removed from inventory, server added to `state.servers` (unracked)
- On failure: show error (e.g. "cpu_budget not in inventory")
- Uses existing `assemble_server()` in `game/datacenter.py`

### Rack Installation (`install` command)
- Takes: server name (or partial match), rack number (1-based index into `state.racks`)
- Sets `server.rack_id` to the rack's id
- Validates rack has enough free U space
- Fix `render_rack()` bug: `used_u` must track cumulative slot usage across servers

### Gig Collection (`gig <n>` command)
- Takes: gig number (1-based index into `state.available_gigs`)
- Immediately adds `gig.payout` to `state.cash`, logs the event
- Removes gig from available list (or marks accepted)
- No server required — gigs are one-off freelance tasks

### Server Repair (`repair <server_name>` command)
- Finds server by name (partial match OK)
- Cost: $500 flat
- Sets `server.health = 1.0`
- Logs the repair event

### Early Bond Selling (`sellbond <n>` command)
- Takes: bond index (1-based)
- Calls `bond_current_value()` to compute discounted value
- Adds value to cash, removes bond from `state.bonds`
- Shows gain/loss vs. face value

### Game Over Screen
- When bankruptcy detected in `advance_day()`, show a modal/screen: "GAME OVER — BANKRUPT"
- Option to start new game (clears state, goes to NewGameScreen)

---

## Command Bar Implementation

- Persistent `Input` widget with id `#cmd-input` always visible at bottom of MainScreen
- A `Static` with id `#cmd-feedback` shows result of last command
- `on_input_submitted` in MainScreen parses the command string and routes to handlers
- Command parser: split on spaces, first token = command name, rest = args
- Each command handler returns a `(success: bool, message: str)` tuple
- On success: update state, save, refresh UI, show green feedback
- On error: show red feedback, no state change

---

## Files to Modify/Create

| File | Change |
|------|--------|
| `ui/screens/main_screen.py` | Add command bar Input + feedback Static, `on_input_submitted` router |
| `ui/screens/datacenter_screen.py` | Remove buttons, add cmd hint, fix render_rack bug |
| `ui/screens/market_screen.py` | Remove buttons, add row numbers, add cmd hint |
| `ui/screens/banking_screen.py` | Remove buttons, add row numbers, add cmd hint |
| `ui/screens/contracts_screen.py` | Remove buttons, add row numbers to all tables, add cmd hint |
| `ui/screens/dashboard.py` | No change (already read-only) |
| `ui/screens/glossary_screen.py` | No change |
| `game/datacenter.py` | Add `install_server_in_rack()`, `repair_server()` functions |
| `game/engine.py` | Add `accept_gig()`, add game-over flag or cash=-1 detection |
| `tests/` | New tests for install_server_in_rack, repair_server, accept_gig |

---

## Error Handling

- Unknown command → `[red]Unknown command. Type 'help' for a list.[/]`
- Wrong arg count → `[red]Usage: buy <qty> <ticker>[/]`
- Insufficient funds → `[red]Insufficient funds: need $X, have $Y[/]`
- Component not in inventory → `[red]<hw_id> not in inventory[/]`
- Server not found → `[red]No server named '<name>'[/]`
- Rack full → `[red]Rack <n> is full (<used>/<total> U used)[/]`
