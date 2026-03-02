# Datacenter Tycoon v2 — Hacker Terminal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the tabbed TUI with a full-screen hacker terminal: BIOS-style boot animation, single terminal screen, pin panel, and view/open/close commands.

**Architecture:** Two new screens (`BootScreen`, `TerminalScreen`) replace all existing UI screens. Game backend (`game/`) is completely untouched. Layout uses Textual `RichLog` + `Input` + CSS-toggled panels. All 20 existing gameplay commands ported verbatim.

**Design doc:** `docs/plans/2026-03-02-hacker-terminal-design.md`

**Tech Stack:** Python 3.11, Textual 8.0+, Rich 13+

---

## Task 1: Rewrite app.tcss with hacker terminal theme

**Files:**
- Modify: `ui/app.tcss`

**Step 1: Replace the entire file**

```css
/* ── Global ─────────────────────────────────────────────── */
Screen {
    background: #0a0a0a;
    color: #00ff41;
    layout: vertical;
}

/* ── Boot screen ─────────────────────────────────────────── */
#boot-log {
    background: #0a0a0a;
    color: #00ff41;
    height: 1fr;
}

#boot-input-row {
    height: 3;
    background: #0a0a0a;
}

#boot-prompt {
    width: auto;
    color: #00ff41;
    background: #0a0a0a;
    padding: 0 0 0 1;
}

#boot-input {
    background: #0a0a0a;
    color: #00ff41;
    border: none;
    height: 1;
}

#boot-input:focus {
    border: none;
}

/* ── Terminal screen ─────────────────────────────────────── */
#top-area {
    height: 2fr;
    display: none;
}

#top-area.visible {
    display: block;
}

#pin-panel {
    width: 26;
    border-right: tall #9d4edd;
    background: #0a0a0a;
    color: #00ff41;
    padding: 0 1;
    display: none;
}

#pin-panel.visible {
    display: block;
}

#open-panel {
    background: #0a0a0a;
    color: #00ff41;
    padding: 0 1;
    height: 1fr;
}

#terminal {
    background: #0a0a0a;
    color: #00ff41;
    height: 1fr;
    scrollbar-color: #3a7a3a;
    scrollbar-background: #0a0a0a;
}

#input-row {
    height: 3;
    background: #0a0a0a;
}

#prompt-label {
    width: auto;
    color: #00ff41;
    background: #0a0a0a;
    padding: 0 0 0 1;
    content-align: left middle;
}

#cmd-input {
    background: #0a0a0a;
    color: #00ff41;
    border: none;
    height: 1;
}

#cmd-input:focus {
    border: none;
}
```

**Step 2: Verify syntax**

```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate
python -c "from ui.app import DatacenterApp; print('CSS OK')"
```

Expected: `CSS OK` (Textual validates CSS on import)

**Step 3: Commit**

```bash
cd /home/jacoby/datacenter-game
git add ui/app.tcss
git commit -m "style: hacker terminal CSS theme (green on black, purple accents)"
```

---

## Task 2: Create BootScreen

**Files:**
- Create: `ui/screens/boot_screen.py`

**Step 1: Create the file**

```python
import asyncio
from pathlib import Path
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import RichLog, Input, Static
from textual.containers import Horizontal


BOOT_LINES = [
    ("[bold #9d4edd]DATACENTER OS v2.0.0[/]", 0.06),
    ("[#3a7a3a]Copyright (C) 2026 Datacenter Tycoon Corp[/]", 0.06),
    ("", 0.04),
    ("[#00ff41]Initializing memory...            [/] [[bold #00ff41] OK [/]]", 0.07),
    ("[#00ff41]Loading kernel modules...         [/] [[bold #00ff41] OK [/]]", 0.07),
    ("[#00ff41]Mounting filesystems...           [/] [[bold #00ff41] OK [/]]", 0.07),
    ("[#00ff41]Starting network services...      [/] [[bold #00ff41] OK [/]]", 0.07),
    ("[#9d4edd]──────────────────────────────────────────[/]", 0.04),
    ("[bold #9d4edd] DATACENTER TYCOON TERMINAL[/]", 0.04),
    ("[#9d4edd]──────────────────────────────────────────[/]", 0.04),
    ("", 0.15),
]


class BootScreen(Screen):
    """BIOS-style boot animation → new or returning player flow."""

    _stage: str = "animating"   # "animating" | "name" | "difficulty" | "done"
    _company_name: str = ""

    def compose(self) -> ComposeResult:
        yield RichLog(id="boot-log", markup=True, highlight=False)
        with Horizontal(id="boot-input-row"):
            yield Static("", id="boot-prompt")
            yield Input(id="boot-input", placeholder="")

    def on_mount(self) -> None:
        self.query_one("#boot-input", Input).disabled = True
        self.run_worker(self._run_boot(), exclusive=True)

    def _log(self, text: str) -> None:
        self.query_one("#boot-log", RichLog).write(text)

    async def _run_boot(self) -> None:
        for line, delay in BOOT_LINES:
            self._log(line)
            await asyncio.sleep(delay)

        saves = sorted(
            Path("saves").glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if saves:
            await self._returning_player(saves[0].stem)
        else:
            await self._new_player()

    async def _new_player(self) -> None:
        self._log("[#3a7a3a]No existing session found.[/]")
        self._log("")
        self._stage = "name"
        self.query_one("#boot-prompt", Static).update("[#00ff41]Enter company name:[/] ")
        inp = self.query_one("#boot-input", Input)
        inp.disabled = False
        inp.focus()

    async def _returning_player(self, company_name: str) -> None:
        from game.save import load_game
        state = load_game(company_name)
        if state is None:
            await self._new_player()
            return
        self.app.state = state

        monthly_income = sum(
            (c.get("monthly_revenue", 0) if isinstance(c, dict) else c.monthly_revenue)
            for c in state.active_contracts
        )
        rack_rent = sum(
            (r.get("monthly_rent", 0) if isinstance(r, dict) else r.monthly_rent)
            for r in state.racks
        )
        loan_payments = sum(
            (l.get("monthly_payment", 0) if isinstance(l, dict) else l.monthly_payment)
            for l in state.loans
        )
        net = monthly_income - rack_rent - loan_payments
        net_color = "green" if net >= 0 else "red"
        sign = "+" if net >= 0 else ""

        self._log(f"[bold #00ff41]Welcome back, {state.company_name}.[/]  [#3a7a3a]Day {state.day}.[/]")
        self._log("")
        self._log(f"  [#3a7a3a]Cash:[/]             [#00ff41]${state.cash:,.2f}[/]")
        self._log(f"  [#3a7a3a]Active contracts:[/] {len(state.active_contracts)}  [#00ff41](+${monthly_income:,.0f}/mo)[/]")
        self._log(f"  [#3a7a3a]Rack rent:[/]        [red]-${rack_rent:,.0f}/mo[/]  ({len(state.racks)} racks)")
        if loan_payments > 0:
            self._log(f"  [#3a7a3a]Loan payments:[/]    [red]-${loan_payments:,.0f}/mo[/]")
        self._log(f"  [#3a7a3a]──────────────────────────[/]")
        self._log(f"  [#3a7a3a]Net monthly:[/]      [{net_color}]{sign}${net:,.0f}/mo[/]")
        self._log("")
        self._log("[#3a7a3a]Type 'help' for available commands.[/]")
        self._log("")
        await asyncio.sleep(0.6)
        from ui.screens.terminal_screen import TerminalScreen
        self.app.switch_screen(TerminalScreen())

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "boot-input":
            return
        raw = event.value.strip()
        event.input.value = ""
        if not raw:
            return

        if self._stage == "name":
            if len(raw) > 30:
                self._log("[red]Company name must be 30 chars or less[/]")
                return
            self._company_name = raw
            self._stage = "difficulty"
            self._log(f"[#3a7a3a]Enter company name:[/] [#00ff41]{raw}[/]")
            self.query_one("#boot-prompt", Static).update(
                "[#00ff41]Select difficulty [easy/normal/hard]:[/] "
            )

        elif self._stage == "difficulty":
            if raw.lower() not in ("easy", "normal", "hard"):
                self._log("[red]Choose: easy / normal / hard[/]")
                return
            self._log(f"[#3a7a3a]Select difficulty [easy/normal/hard]:[/] [#00ff41]{raw.lower()}[/]")
            self.query_one("#boot-input", Input).disabled = True
            self.query_one("#boot-prompt", Static).update("")
            self._stage = "done"
            self.run_worker(self._finish_new_game(raw.lower()), exclusive=True)

    async def _finish_new_game(self, difficulty: str) -> None:
        from game.engine import initialize_new_game
        self._log("")
        await asyncio.sleep(0.08)
        self._log("[#00ff41]Creating session...                [/] [[bold #00ff41] OK [/]]")
        await asyncio.sleep(0.08)
        self._log("[#00ff41]Initializing accounts...           [/] [[bold #00ff41] OK [/]]")
        await asyncio.sleep(0.08)
        self._log("[#00ff41]Provisioning first rack...         [/] [[bold #00ff41] OK [/]]")
        await asyncio.sleep(0.08)
        self._log("")
        self._log("[bold #9d4edd]Welcome to DATACENTER TYCOON.[/]")
        self._log("[#3a7a3a]You have been allocated $50,000 in seed funding.[/]")
        self._log("")
        self._log("[#3a7a3a]Type 'help' to begin.[/]")
        self._log("")
        self.app.state = initialize_new_game(self._company_name, difficulty)
        await asyncio.sleep(0.6)
        from ui.screens.terminal_screen import TerminalScreen
        self.app.switch_screen(TerminalScreen())
```

**Step 2: Verify import**

```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate
python -c "from ui.screens.boot_screen import BootScreen; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
cd /home/jacoby/datacenter-game
git add ui/screens/boot_screen.py
git commit -m "feat: add BootScreen with BIOS animation and new/returning player flows"
```

---

## Task 3: Create TerminalScreen — core layout, echo, help, day, save

**Files:**
- Create: `ui/screens/terminal_screen.py`

**Step 1: Create the file with core structure**

```python
import asyncio
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import RichLog, Input, Static
from textual.containers import Horizontal
from textual.binding import Binding
from game.engine import advance_day
from game.save import save_game


class TerminalScreen(Screen):
    """Full-screen hacker terminal. All gameplay via command bar."""

    BINDINGS = [
        Binding("space", "advance_day", "Advance Day"),
    ]

    # ── State ──────────────────────────────────────────────────────
    _pinned: dict = {}          # metric_name → True
    _open_target: str | None = None

    # ── Layout ─────────────────────────────────────────────────────
    def compose(self) -> ComposeResult:
        with Horizontal(id="top-area"):
            yield Static("", id="pin-panel")
            yield Static("", id="open-panel")
        yield RichLog(id="terminal", markup=True, highlight=False, max_lines=500)
        with Horizontal(id="input-row"):
            yield Static("", id="prompt-label")
            yield Input(id="cmd-input", placeholder="")

    def on_mount(self) -> None:
        self._pinned = {}
        self._open_target = None
        s = self.app.state
        slug = s.company_name[:12].lower().replace(" ", "")
        self.query_one("#prompt-label", Static).update(
            f"[#00ff41][{slug}@datacenter ~]$[/] "
        )
        self.query_one("#cmd-input", Input).focus()

    # ── Helpers ────────────────────────────────────────────────────
    def _write(self, text: str) -> None:
        """Append a line to the terminal log."""
        self.query_one("#terminal", RichLog).write(text)

    def _echo(self, raw: str) -> None:
        """Echo the command the user typed with prompt prefix."""
        s = self.app.state
        slug = s.company_name[:12].lower().replace(" ", "")
        self._write(f"[#3a7a3a][{slug}@datacenter ~]$[/] [#00ff41]{raw}[/]")

    def _update_visibility(self) -> None:
        """Show/hide top-area and pin-panel based on state."""
        top = self.query_one("#top-area", Horizontal)
        pin = self.query_one("#pin-panel", Static)
        has_pins = bool(self._pinned)
        has_open = self._open_target is not None
        if has_pins:
            pin.add_class("visible")
        else:
            pin.remove_class("visible")
        if has_pins or has_open:
            top.add_class("visible")
        else:
            top.remove_class("visible")

    def _refresh_pin_panel(self) -> None:
        """Rebuild pin panel content from current game state."""
        if not self._pinned:
            return
        s = self.app.state
        from game.market import portfolio_value
        monthly_income = sum(
            (c.get("monthly_revenue", 0) if isinstance(c, dict) else c.monthly_revenue)
            for c in s.active_contracts
        )
        rack_rent = sum(
            (r.get("monthly_rent", 0) if isinstance(r, dict) else r.monthly_rent)
            for r in s.racks
        )
        loan_payments = sum(
            (l.get("monthly_payment", 0) if isinstance(l, dict) else l.monthly_payment)
            for l in s.loans
        )
        net = monthly_income - rack_rent - loan_payments
        net_color = "#00ff41" if net >= 0 else "red"
        sign = "+" if net >= 0 else ""

        value_map = {
            "cash":   f"[#3a7a3a]Cash [/]  [#00ff41]${s.cash:,.0f}[/]",
            "day":    f"[#3a7a3a]Day  [/]  [#00ff41]{s.day}[/]",
            "income": f"[#3a7a3a]Inc  [/]  [#00ff41]${monthly_income:,.0f}/mo[/]",
            "rep":    f"[#3a7a3a]Rep  [/]  [#00ff41]{s.reputation}[/]",
            "credit": f"[#3a7a3a]Cred [/]  [#00ff41]{s.credit_score}[/]",
            "net":    f"[#3a7a3a]Net  [/]  [{net_color}]{sign}${net:,.0f}/mo[/]",
        }

        lines = ["[bold #9d4edd]── PINNED ──[/]"]
        for metric in self._pinned:
            if metric in value_map:
                lines.append(value_map[metric])
        self.query_one("#pin-panel", Static).update("\n".join(lines))

    # ── Input handling ─────────────────────────────────────────────
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "cmd-input":
            return
        raw = event.value.strip()
        event.input.value = ""
        if not raw:
            return
        self._echo(raw)
        parts = raw.split()
        cmd = parts[0].lower()
        args = parts[1:]
        self._run_command(cmd, args)

    def _run_command(self, cmd: str, args: list[str]) -> None:
        handlers = {
            "day":       self._cmd_day,
            "save":      self._cmd_save,
            "help":      self._cmd_help,
            "view":      self._cmd_view,
            "pin":       self._cmd_pin,
            "unpin":     self._cmd_unpin,
            "open":      self._cmd_open,
            "close":     self._cmd_close,
            "buy":       self._cmd_buy,
            "sell":      self._cmd_sell,
            "transfer":  self._cmd_transfer,
            "loan":      self._cmd_loan,
            "bond":      self._cmd_bond,
            "sellbond":  self._cmd_sellbond,
            "accept":    self._cmd_accept,
            "decline":   self._cmd_decline,
            "negotiate": self._cmd_negotiate,
            "assign":    self._cmd_assign,
            "gig":       self._cmd_gig,
            "buyhw":     self._cmd_buyhw,
            "assemble":  self._cmd_assemble,
            "install":   self._cmd_install,
            "repair":    self._cmd_repair,
            "rent":      self._cmd_rent,
        }
        handler = handlers.get(cmd)
        if handler is None:
            self._write(f"[red]command not found: {cmd}  (type 'help' for list)[/]")
            return
        try:
            success, msg = handler(args)
        except Exception as e:
            self._write(f"[red]error: {e}[/]")
            return
        if msg:
            color = "#00ff41" if success else "red"
            self._write(f"[{color}]{msg}[/]")
        if success:
            save_game(self.app.state)
            self._refresh_pin_panel()
            if self._open_target:
                self._refresh_open_panel()
            if self.app.state.cash < 0:
                self._write("[bold red]WARNING: NEGATIVE CASH — BANKRUPTCY RISK[/]")

    def _refresh_open_panel(self) -> None:
        if self._open_target:
            renderer = getattr(self, f"_render_{self._open_target}", None)
            if renderer:
                self.query_one("#open-panel", Static).update(renderer())

    def action_advance_day(self) -> None:
        self._echo("day")
        self._run_command("day", [])

    # ── Global commands ────────────────────────────────────────────
    def _cmd_day(self, args):
        self.app.state = advance_day(self.app.state)
        return True, f"Day {self.app.state.day} — market moved, billing processed."

    def _cmd_save(self, args):
        save_game(self.app.state)
        return True, "game saved."

    def _cmd_help(self, args):
        lines = [
            "[bold #9d4edd]── COMMANDS ──────────────────────────────────────────────────[/]",
            "",
            "[#9d4edd]SYSTEM[/]",
            "  [#00ff41]day[/]                              Advance one day",
            "  [#00ff41]save[/]                             Save game",
            "",
            "[#9d4edd]DISPLAY[/]",
            "  [#00ff41]view <target>[/]                    Print report to terminal",
            "    targets: cash contracts servers market loans bonds inventory racks gigs all",
            "  [#00ff41]pin <metric>[/]                     Add to top-left panel",
            "    metrics: cash day income rep credit net",
            "  [#00ff41]unpin <metric>[/]                   Remove from panel",
            "  [#00ff41]pin clear[/]                        Clear all pins",
            "  [#00ff41]open <target>[/]                    Open panel (top 2/3)",
            "    targets: store contracts market servers racks gigs banking",
            "  [#00ff41]close[/]                            Close open panel",
            "",
            "[#9d4edd]MARKET[/]",
            "  [#00ff41]buy <qty> <ticker>[/]               Buy stocks",
            "  [#00ff41]sell <qty> <ticker>[/]              Sell stocks",
            "",
            "[#9d4edd]BANKING[/]",
            "  [#00ff41]transfer <amt> savings|checking[/]  Move money between accounts",
            "  [#00ff41]loan <amt> <months>[/]              Take loan  (6/12/24 months)",
            "  [#00ff41]bond <amt>[/]                       Buy 30-day bond (15%/yr)",
            "  [#00ff41]sellbond <n>[/]                     Sell bond #n early",
            "",
            "[#9d4edd]CONTRACTS[/]",
            "  [#00ff41]accept <n>[/]                       Accept offer #n",
            "  [#00ff41]decline <n>[/]                      Decline offer #n",
            "  [#00ff41]negotiate <n>[/]                    Counter-offer +15%",
            "  [#00ff41]assign <n> <server>[/]              Assign server to active contract #n",
            "  [#00ff41]gig <n>[/]                          Collect gig #n payout",
            "",
            "[#9d4edd]DATACENTER[/]",
            "  [#00ff41]buyhw <hw_id>[/]                    Buy hardware  (see 'open store')",
            "  [#00ff41]assemble <name> <cpu> <ram> <hdd> <nic>[/]  Build server",
            "  [#00ff41]install <server> <rack_n>[/]         Install server in rack",
            "  [#00ff41]repair <server>[/]                  Repair server ($500)",
            "  [#00ff41]rent[/]                             Rent another rack",
            "",
            "[#9d4edd]──────────────────────────────────────────────────────────────[/]",
        ]
        for line in lines:
            self._write(line)
        return True, ""

    # ── Stubs for tasks 4-7 ────────────────────────────────────────
    def _cmd_view(self, args):      return False, "view: not yet implemented"
    def _cmd_pin(self, args):       return False, "pin: not yet implemented"
    def _cmd_unpin(self, args):     return False, "unpin: not yet implemented"
    def _cmd_open(self, args):      return False, "open: not yet implemented"
    def _cmd_close(self, args):     return False, "close: not yet implemented"
    def _cmd_buy(self, args):       return False, "not yet implemented"
    def _cmd_sell(self, args):      return False, "not yet implemented"
    def _cmd_transfer(self, args):  return False, "not yet implemented"
    def _cmd_loan(self, args):      return False, "not yet implemented"
    def _cmd_bond(self, args):      return False, "not yet implemented"
    def _cmd_sellbond(self, args):  return False, "not yet implemented"
    def _cmd_accept(self, args):    return False, "not yet implemented"
    def _cmd_decline(self, args):   return False, "not yet implemented"
    def _cmd_negotiate(self, args): return False, "not yet implemented"
    def _cmd_assign(self, args):    return False, "not yet implemented"
    def _cmd_gig(self, args):       return False, "not yet implemented"
    def _cmd_buyhw(self, args):     return False, "not yet implemented"
    def _cmd_assemble(self, args):  return False, "not yet implemented"
    def _cmd_install(self, args):   return False, "not yet implemented"
    def _cmd_repair(self, args):    return False, "not yet implemented"
    def _cmd_rent(self, args):      return False, "not yet implemented"
```

**Step 2: Verify import**

```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate
python -c "from ui.screens.terminal_screen import TerminalScreen; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
cd /home/jacoby/datacenter-game
git add ui/screens/terminal_screen.py
git commit -m "feat: TerminalScreen core — layout, echo, help, day, save"
```

---

## Task 4: Implement pin/unpin/open/close commands

**Files:**
- Modify: `ui/screens/terminal_screen.py` — replace 5 stub methods

**Step 1: Replace `_cmd_pin`, `_cmd_unpin`, `_cmd_open`, `_cmd_close` stubs**

```python
VALID_PINS = ("cash", "day", "income", "rep", "credit", "net")
VALID_OPENS = ("store", "contracts", "market", "servers", "racks", "gigs", "banking")

def _cmd_pin(self, args):
    if not args:
        return False, f"Usage: pin <metric>  ({' | '.join(VALID_PINS)})  or  pin clear"
    if args[0] == "clear":
        self._pinned.clear()
        self.query_one("#pin-panel", Static).update("")
        self._update_visibility()
        return True, "pin panel cleared."
    metric = args[0].lower()
    if metric not in VALID_PINS:
        return False, f"Unknown metric '{metric}'. Choose: {' | '.join(VALID_PINS)}"
    self._pinned[metric] = True
    self._refresh_pin_panel()
    self._update_visibility()
    return True, f"Pinned {metric}."

def _cmd_unpin(self, args):
    if not args:
        return False, "Usage: unpin <metric>"
    metric = args[0].lower()
    if metric not in self._pinned:
        return False, f"'{metric}' is not pinned."
    del self._pinned[metric]
    self._refresh_pin_panel()
    self._update_visibility()
    return True, f"Unpinned {metric}."

def _cmd_open(self, args):
    if not args:
        return False, f"Usage: open <target>  ({' | '.join(VALID_OPENS)})"
    target = args[0].lower()
    if target not in VALID_OPENS:
        return False, f"Unknown target '{target}'. Choose: {' | '.join(VALID_OPENS)}"
    renderer = getattr(self, f"_render_{target}", None)
    if renderer is None:
        return False, f"Renderer for '{target}' not implemented yet."
    self._open_target = target
    self.query_one("#open-panel", Static).update(renderer())
    self._update_visibility()
    hint = {
        "store":     "buyhw <hw_id>",
        "contracts": "accept/decline/negotiate <n>  |  assign <n> <server>",
        "market":    "buy/sell <qty> <ticker>",
        "servers":   "install <server> <rack_n>  |  repair <server>",
        "racks":     "rent",
        "gigs":      "gig <n>",
        "banking":   "transfer/loan/bond/sellbond",
    }.get(target, "")
    return True, f"Opened {target}.  [{hint}]  Type 'close' to dismiss."

def _cmd_close(self, args):
    if self._open_target is None:
        return False, "Nothing is open."
    self._open_target = None
    self.query_one("#open-panel", Static).update("")
    self._update_visibility()
    return True, "Closed."
```

**Step 2: Add the class-level constants** — add these two lines near the top of the class body (just before `_pinned`):

```python
VALID_PINS = ("cash", "day", "income", "rep", "credit", "net")
VALID_OPENS = ("store", "contracts", "market", "servers", "racks", "gigs", "banking")
```

**Step 3: Verify import**

```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate
python -c "from ui.screens.terminal_screen import TerminalScreen; print('OK')"
```

**Step 4: Commit**

```bash
cd /home/jacoby/datacenter-game
git add ui/screens/terminal_screen.py
git commit -m "feat: pin/unpin/open/close commands with panel visibility"
```

---

## Task 5: Implement view commands (10 targets)

**Files:**
- Modify: `ui/screens/terminal_screen.py` — replace `_cmd_view` stub + add `_render_*` helpers

**Step 1: Replace `_cmd_view` stub**

```python
VIEW_TARGETS = ("cash", "contracts", "servers", "market", "loans", "bonds",
                "inventory", "racks", "gigs", "all")

def _cmd_view(self, args):
    if not args or args[0] not in VIEW_TARGETS:
        return False, f"Usage: view <target>  ({' | '.join(VIEW_TARGETS)})"
    target = args[0]
    if target == "all":
        for t in ("cash", "contracts", "servers", "market", "loans", "bonds",
                  "inventory", "racks", "gigs"):
            renderer = getattr(self, f"_view_{t}")
            for line in renderer():
                self._write(line)
            self._write("")
    else:
        renderer = getattr(self, f"_view_{target}")
        for line in renderer():
            self._write(line)
    return True, ""
```

**Step 2: Add the 9 view renderer methods**

```python
def _view_cash(self) -> list[str]:
    s = self.app.state
    from game.market import portfolio_value
    pv = portfolio_value(s.portfolio, s.market_prices)
    net = s.cash + s.savings + pv
    return [
        "[bold #9d4edd]── ACCOUNTS ──[/]",
        f"  Checking:  [#00ff41]${s.cash:>14,.2f}[/]",
        f"  Savings:   [#00ff41]${s.savings:>14,.2f}[/]  (6%/yr)",
        f"  Portfolio: [#00ff41]${pv:>14,.2f}[/]",
        f"  [#3a7a3a]──────────────────────────────[/]",
        f"  Net Worth: [bold #00ff41]${net:>14,.2f}[/]",
    ]

def _view_contracts(self) -> list[str]:
    s = self.app.state
    lines = ["[bold #9d4edd]── PENDING OFFERS ──[/]"]
    if not s.pending_contracts:
        lines.append("  [#3a7a3a]No incoming offers[/]")
    for i, c in enumerate(s.pending_contracts, 1):
        g = c if isinstance(c, dict) else vars(c)
        lines.append(
            f"  [[#00ff41]{i}[/]] {g.get('client_name',''):<20} "
            f"{g.get('required_cores',0)}c/{g.get('required_ram_gb',0)}GB  "
            f"[#00ff41]${g.get('monthly_revenue',0):,.0f}/mo[/]  {g.get('duration_days',0)}d"
        )
    lines += ["", "[bold #9d4edd]── ACTIVE CONTRACTS ──[/]"]
    if not s.active_contracts:
        lines.append("  [#3a7a3a]No active contracts[/]")
    for i, c in enumerate(s.active_contracts, 1):
        g = c if isinstance(c, dict) else vars(c)
        srv_id = g.get("server_id")
        srv_name = "—"
        if srv_id:
            srv = next((sv for sv in s.servers
                        if (sv.get("id") if isinstance(sv, dict) else sv.id) == srv_id), None)
            if srv:
                srv_name = sv.get("name") if isinstance(srv, dict) else srv.name
        lines.append(
            f"  [[#00ff41]{i}[/]] {g.get('client_name',''):<20} "
            f"[#00ff41]${g.get('monthly_revenue',0):,.0f}/mo[/]  "
            f"{g.get('days_remaining',0)}d  srv: {srv_name}"
        )
    return lines

def _view_servers(self) -> list[str]:
    s = self.app.state
    lines = ["[bold #9d4edd]── SERVERS ──[/]"]
    if not s.servers:
        lines.append("  [#3a7a3a]No servers assembled[/]")
    for i, srv in enumerate(s.servers, 1):
        g = srv if isinstance(srv, dict) else vars(srv)
        health = g.get("health", 1.0)
        h_color = "#00ff41" if health > 0.7 else ("#ffb703" if health > 0.3 else "red")
        rack_id = g.get("rack_id")
        rack_label = "unracked"
        if rack_id:
            rack = next((r for r in s.racks
                         if (r.get("id") if isinstance(r, dict) else r.id) == rack_id), None)
            if rack:
                rack_label = rack.get("name") if isinstance(rack, dict) else rack.name
        lines.append(
            f"  [[#00ff41]{i}[/]] {g.get('name',''):<16} "
            f"{g.get('total_cores',0)}c / {g.get('total_ram_gb',0)}GB / {g.get('total_storage_gb',0)}GB  "
            f"[{h_color}]health:{health*100:.0f}%[/]  {rack_label}"
        )
    return lines

def _view_market(self) -> list[str]:
    import json
    from pathlib import Path
    from game.market import portfolio_value
    companies = json.loads((Path(__file__).parent.parent.parent / "data" / "companies.json").read_text())
    s = self.app.state
    lines = [
        "[bold #9d4edd]── MARKET ──[/]",
        f"  [#3a7a3a]{'#':<3} {'Ticker':<7} {'Company':<22} {'Price':>9} {'Chg%':>7} {'Owned':>6}[/]",
        "  " + "─" * 56,
    ]
    for i, co in enumerate(companies, 1):
        t = co["ticker"]
        price = s.market_prices.get(t, co["base_price"])
        hist = s.price_history.get(t, [price])
        prev = hist[-2] if len(hist) >= 2 else price
        chg = (price - prev) / prev * 100 if prev else 0
        chg_color = "#00ff41" if chg >= 0 else "red"
        owned = s.portfolio.get(t, {}).get("shares", 0)
        lines.append(
            f"  [{i:<2}] [#00ff41]{t:<7}[/] {co['name']:<22} "
            f"${price:>8.2f} [{chg_color}]{chg:>+6.1f}%[/] {owned:>6}"
        )
    pv = portfolio_value(s.portfolio, s.market_prices)
    lines += ["", f"  Portfolio value: [#00ff41]${pv:,.2f}[/]"]
    return lines

def _view_loans(self) -> list[str]:
    s = self.app.state
    lines = ["[bold #9d4edd]── LOANS ──[/]"]
    if not s.loans:
        lines.append("  [#3a7a3a]No active loans[/]")
    for i, loan in enumerate(s.loans, 1):
        g = loan if isinstance(loan, dict) else vars(loan)
        lines.append(
            f"  [[#00ff41]{i}[/]] ${g.get('remaining_balance',0):>10,.2f} remaining  "
            f"${g.get('monthly_payment',0):,.2f}/mo  "
            f"{g.get('days_remaining',0)}d left"
        )
    return lines

def _view_bonds(self) -> list[str]:
    s = self.app.state
    lines = ["[bold #9d4edd]── BONDS ──[/]"]
    if not s.bonds:
        lines.append("  [#3a7a3a]No bonds held[/]")
    for i, bond in enumerate(s.bonds, 1):
        g = bond if isinstance(bond, dict) else vars(bond)
        yld = g.get("annual_yield", 0.15)
        lines.append(
            f"  [[#00ff41]{i}[/]] ${g.get('face_value',0):>10,.2f} face  "
            f"{yld*100:.0f}%/yr  "
            f"{g.get('days_remaining',0)}d to maturity"
        )
    return lines

def _view_inventory(self) -> list[str]:
    s = self.app.state
    lines = ["[bold #9d4edd]── HARDWARE INVENTORY ──[/]"]
    if not s.hardware_inventory:
        lines.append("  [#3a7a3a]No components in inventory[/]")
    for c in s.hardware_inventory:
        g = c if isinstance(c, dict) else vars(c)
        lines.append(
            f"  [[#9d4edd]{g.get('type','').upper()[:3]}[/]] "
            f"{g.get('name',''):<24} "
            f"id: [#3a7a3a]{g.get('id','')[:8]}[/]"
        )
    return lines

def _view_racks(self) -> list[str]:
    s = self.app.state
    lines = ["[bold #9d4edd]── RACKS ──[/]"]
    if not s.racks:
        lines.append("  [#3a7a3a]No racks rented[/]")
    for i, rack in enumerate(s.racks, 1):
        g = rack if isinstance(rack, dict) else vars(rack)
        rack_id = g.get("id", "")
        total_u = g.get("total_u", 12)
        used_u = sum(
            (sv.get("size_u", 1) if isinstance(sv, dict) else sv.size_u)
            for sv in s.servers
            if (sv.get("rack_id") if isinstance(sv, dict) else sv.rack_id) == rack_id
        )
        lines.append(
            f"  [[#00ff41]{i}[/]] {g.get('name',''):<12} "
            f"{g.get('location_tier',''):<10} "
            f"[#00ff41]{used_u}[/]/{total_u}U used  "
            f"${g.get('monthly_rent',0):,.0f}/mo"
        )
    return lines

def _view_gigs(self) -> list[str]:
    s = self.app.state
    lines = ["[bold #9d4edd]── GIG BOARD ──[/]"]
    if not s.available_gigs:
        lines.append("  [#3a7a3a]No gigs available[/]")
    for i, gig in enumerate(s.available_gigs, 1):
        g = gig if isinstance(gig, dict) else vars(gig)
        lines.append(
            f"  [[#00ff41]{i}[/]] [#9d4edd]${g.get('payout',0):,.2f}[/]  "
            f"{g.get('title','')}  —  [#3a7a3a]{g.get('description','')}[/]"
        )
    return lines
```

**Step 3: Also add the `VIEW_TARGETS` constant** near the top of the class body:

```python
VIEW_TARGETS = ("cash", "contracts", "servers", "market", "loans", "bonds",
                "inventory", "racks", "gigs", "all")
```

**Step 4: Verify import**

```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate
python -c "from ui.screens.terminal_screen import TerminalScreen; print('OK')"
```

**Step 5: Commit**

```bash
cd /home/jacoby/datacenter-game
git add ui/screens/terminal_screen.py
git commit -m "feat: view command with 10 targets (cash, contracts, servers, market, loans, bonds, inventory, racks, gigs, all)"
```

---

## Task 6: Implement open panel renderers (_render_* methods)

**Files:**
- Modify: `ui/screens/terminal_screen.py` — add 7 `_render_*` methods

**Step 1: Add 7 render methods to TerminalScreen**

These render the content of `#open-panel` when `open <target>` is called. Each returns a single string (Rich markup, multi-line).

```python
def _render_store(self) -> str:
    from game.datacenter import HARDWARE
    lines = ["[bold #9d4edd]── HARDWARE STORE ──────────────────────────────────────────────[/]", ""]
    for cat, items in HARDWARE.items():
        lines.append(f"  [bold #9d4edd]{cat.upper()}[/]")
        for item in items:
            specs = "  ".join(f"{v}" for v in item["specs"].values())
            lines.append(
                f"    [#00ff41]{item['id']:<18}[/] {item['name']:<22} "
                f"[#3a7a3a]{specs:<14}[/]  [#9d4edd]${item['price']:,.0f}[/]"
            )
        lines.append("")
    lines.append("[#3a7a3a]buyhw <hw_id> to purchase[/]")
    return "\n".join(lines)

def _render_contracts(self) -> str:
    s = self.app.state
    lines = ["[bold #9d4edd]── CONTRACT OFFERS ──────────────────────────────────────────────[/]", ""]
    if not s.pending_contracts:
        lines.append("  [#3a7a3a]No pending offers[/]")
    for i, c in enumerate(s.pending_contracts, 1):
        g = c if isinstance(c, dict) else vars(c)
        lines.append(
            f"  [[#00ff41]{i}[/]] {g.get('client_name',''):<20} "
            f"{g.get('required_cores',0)}c/{g.get('required_ram_gb',0)}GB  "
            f"[#9d4edd]${g.get('monthly_revenue',0):,.0f}/mo[/]  {g.get('duration_days',0)}d"
        )
    lines += ["", "[bold #9d4edd]── ACTIVE ──────────────────────────────────────────────────────[/]", ""]
    if not s.active_contracts:
        lines.append("  [#3a7a3a]No active contracts[/]")
    for i, c in enumerate(s.active_contracts, 1):
        g = c if isinstance(c, dict) else vars(c)
        lines.append(
            f"  [[#00ff41]{i}[/]] {g.get('client_name',''):<20} "
            f"[#00ff41]${g.get('monthly_revenue',0):,.0f}/mo[/]  {g.get('days_remaining',0)}d left"
        )
    lines += ["", "[#3a7a3a]accept/decline/negotiate <n>  |  assign <n> <server>[/]"]
    return "\n".join(lines)

def _render_market(self) -> str:
    import json
    from pathlib import Path
    from game.market import portfolio_value
    companies = json.loads((Path(__file__).parent.parent.parent / "data" / "companies.json").read_text())
    s = self.app.state
    lines = [
        "[bold #9d4edd]── MARKET ──────────────────────────────────────────────────────[/]",
        f"  [#3a7a3a]{'#':<3} {'Ticker':<7} {'Company':<20} {'Price':>9} {'Chg%':>7} {'Owned':>5}[/]",
        "  " + "─" * 54,
    ]
    for i, co in enumerate(companies, 1):
        t = co["ticker"]
        price = s.market_prices.get(t, co["base_price"])
        hist = s.price_history.get(t, [price])
        prev = hist[-2] if len(hist) >= 2 else price
        chg = (price - prev) / prev * 100 if prev else 0
        chg_color = "#00ff41" if chg >= 0 else "red"
        owned = s.portfolio.get(t, {}).get("shares", 0)
        lines.append(
            f"  [{i:<2}] [#00ff41]{t:<7}[/] {co['name']:<20} "
            f"${price:>8.2f} [{chg_color}]{chg:>+6.1f}%[/] {owned:>5}"
        )
    pv = portfolio_value(s.portfolio, s.market_prices)
    lines += ["", f"  Portfolio: [#00ff41]${pv:,.2f}[/]", "", "[#3a7a3a]buy/sell <qty> <ticker>[/]"]
    return "\n".join(lines)

def _render_servers(self) -> str:
    s = self.app.state
    lines = ["[bold #9d4edd]── SERVERS ──────────────────────────────────────────────────────[/]", ""]
    if not s.servers:
        lines.append("  [#3a7a3a]No servers assembled. Use: buyhw → assemble → install[/]")
    for i, srv in enumerate(s.servers, 1):
        g = srv if isinstance(srv, dict) else vars(srv)
        health = g.get("health", 1.0)
        h_color = "#00ff41" if health > 0.7 else ("#ffb703" if health > 0.3 else "red")
        rack_id = g.get("rack_id")
        rack_label = "[#3a7a3a]unracked[/]"
        if rack_id:
            rack = next((r for r in s.racks
                         if (r.get("id") if isinstance(r, dict) else r.id) == rack_id), None)
            if rack:
                rack_label = rack.get("name") if isinstance(rack, dict) else rack.name
        lines.append(
            f"  [[#00ff41]{i}[/]] [#9d4edd]{g.get('name',''):<14}[/] "
            f"{g.get('total_cores',0)}c/{g.get('total_ram_gb',0)}GB/{g.get('total_storage_gb',0)}GB  "
            f"[{h_color}]{health*100:.0f}%[/]  {rack_label}"
        )
    lines += ["", "[#3a7a3a]install <server> <rack_n>  |  repair <server>[/]"]
    return "\n".join(lines)

def _render_racks(self) -> str:
    s = self.app.state
    lines = ["[bold #9d4edd]── RACKS ─────────────────────────────────────────────────────────[/]", ""]
    if not s.racks:
        lines.append("  [#3a7a3a]No racks. Use: rent[/]")
    for i, rack in enumerate(s.racks, 1):
        g = rack if isinstance(rack, dict) else vars(rack)
        rack_id = g.get("id", "")
        total_u = g.get("total_u", 12)
        rack_servers = [
            sv for sv in s.servers
            if (sv.get("rack_id") if isinstance(sv, dict) else sv.rack_id) == rack_id
        ]
        used_u = sum(sv.get("size_u", 1) if isinstance(sv, dict) else sv.size_u
                     for sv in rack_servers)
        lines.append(
            f"  [[#00ff41]{i}[/]] [#9d4edd]{g.get('name',''):<12}[/] "
            f"{g.get('location_tier',''):<10}  "
            f"[#00ff41]{used_u}[/]/{total_u}U  "
            f"${g.get('monthly_rent',0):,.0f}/mo"
        )
        for srv in rack_servers:
            sg = srv if isinstance(srv, dict) else vars(srv)
            lines.append(f"       └ {sg.get('name','')}")
    lines += ["", "[#3a7a3a]rent — adds a new rack[/]"]
    return "\n".join(lines)

def _render_gigs(self) -> str:
    s = self.app.state
    lines = ["[bold #9d4edd]── GIG BOARD ─────────────────────────────────────────────────────[/]", ""]
    if not s.available_gigs:
        lines.append("  [#3a7a3a]No gigs available. Advance days to refresh.[/]")
    for i, gig in enumerate(s.available_gigs, 1):
        g = gig if isinstance(gig, dict) else vars(gig)
        lines.append(
            f"  [[#00ff41]{i}[/]] [#9d4edd]${g.get('payout',0):,.2f}[/]  "
            f"[#00ff41]{g.get('title','')}[/]"
        )
        lines.append(f"       [#3a7a3a]{g.get('description','')}[/]")
        lines.append("")
    lines.append("[#3a7a3a]gig <n> — collect payout[/]")
    return "\n".join(lines)

def _render_banking(self) -> str:
    from game.finance import loan_interest_rate_for_credit_score
    s = self.app.state
    rate = loan_interest_rate_for_credit_score(s.credit_score)
    monthly_income = sum(
        (c.get("monthly_revenue", 0) if isinstance(c, dict) else c.monthly_revenue)
        for c in s.active_contracts
    )
    rack_rent = sum(
        (r.get("monthly_rent", 0) if isinstance(r, dict) else r.monthly_rent)
        for r in s.racks
    )
    loan_payments = sum(
        (l.get("monthly_payment", 0) if isinstance(l, dict) else l.monthly_payment)
        for l in s.loans
    )
    net = monthly_income - rack_rent - loan_payments
    net_color = "#00ff41" if net >= 0 else "red"
    sign = "+" if net >= 0 else ""
    lines = [
        "[bold #9d4edd]── BANKING ──────────────────────────────────────────────────────[/]",
        "",
        "[#9d4edd]ACCOUNTS[/]",
        f"  Checking:  [#00ff41]${s.cash:>14,.2f}[/]",
        f"  Savings:   [#00ff41]${s.savings:>14,.2f}[/]  (6%/yr)",
        "",
        f"[#9d4edd]CREDIT SCORE: [#00ff41]{s.credit_score}[/]  (loan rate: {rate*100:.1f}% APR)[/]",
        "",
        "[#9d4edd]MONTHLY FLOW[/]",
        f"  Income:    [#00ff41]+${monthly_income:,.0f}/mo[/]",
        f"  Rent:      [red]-${rack_rent:,.0f}/mo[/]",
    ]
    if loan_payments:
        lines.append(f"  Loans:     [red]-${loan_payments:,.0f}/mo[/]")
    lines += [
        f"  [#3a7a3a]──────────────────────────[/]",
        f"  Net:       [{net_color}]{sign}${net:,.0f}/mo[/]",
        "",
        "[#9d4edd]ACTIVE LOANS[/]",
    ]
    if not s.loans:
        lines.append("  [#3a7a3a]None[/]")
    for i, loan in enumerate(s.loans, 1):
        g = loan if isinstance(loan, dict) else vars(loan)
        lines.append(
            f"  [[#00ff41]{i}[/]] ${g.get('remaining_balance',0):>10,.2f} rem  "
            f"${g.get('monthly_payment',0):,.2f}/mo  {g.get('days_remaining',0)}d"
        )
    lines += ["", "[#9d4edd]BONDS[/]"]
    if not s.bonds:
        lines.append("  [#3a7a3a]None[/]")
    for i, bond in enumerate(s.bonds, 1):
        g = bond if isinstance(bond, dict) else vars(bond)
        lines.append(
            f"  [[#00ff41]{i}[/]] ${g.get('face_value',0):>10,.2f}  "
            f"{g.get('annual_yield',0)*100:.0f}%/yr  {g.get('days_remaining',0)}d"
        )
    lines += ["", "[#3a7a3a]transfer/loan/bond/sellbond[/]"]
    return "\n".join(lines)
```

**Step 2: Verify import**

```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate
python -c "from ui.screens.terminal_screen import TerminalScreen; print('OK')"
```

**Step 3: Commit**

```bash
cd /home/jacoby/datacenter-game
git add ui/screens/terminal_screen.py
git commit -m "feat: open panel renderers for store, contracts, market, servers, racks, gigs, banking"
```

---

## Task 7: Port all 20 gameplay commands from main_screen.py

**Files:**
- Modify: `ui/screens/terminal_screen.py` — replace 20 stub methods with implementations

**Step 1: Read `ui/screens/main_screen.py`** to confirm the exact implementations (lines 201–572), then copy each `_cmd_*` method into `terminal_screen.py`, replacing the stubs.

The methods to copy verbatim (they work identically — same `self.app.state` access):
- `_cmd_buy` (line 202)
- `_cmd_sell` (line 227)
- `_cmd_transfer` (line 252)
- `_cmd_loan` (line 276)
- `_cmd_bond` (line 307)
- `_cmd_sellbond` (line 333)
- `_cmd_accept` (line 358)
- `_cmd_decline` (line 379)
- `_cmd_negotiate` (line 394)
- `_cmd_assign` (line 417)
- `_cmd_gig` (line 446)
- `_cmd_buyhw` (line 462)
- `_cmd_assemble` (line 473)
- `_cmd_install` (line 534)
- `_cmd_repair` (line 550)
- `_cmd_rent` (line 562)

**NOTE:** The old `_cmd_help` and `_cmd_tab` are NOT copied — TerminalScreen has its own implementations.

**Step 2: Remove the `buyhw` hint** in `_cmd_buyhw` — change the error message from `"see hw_id column in Datacenter tab"` to `"see 'open store' for hw_ids"`.

**Step 3: Verify import**

```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate
python -c "from ui.screens.terminal_screen import TerminalScreen; print('OK')"
```

**Step 4: Run tests** (backend tests must still pass — no game logic changed)

```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate
pytest tests/ -q 2>&1 | tail -5
```

Expected: 58 passed

**Step 5: Commit**

```bash
cd /home/jacoby/datacenter-game
git add ui/screens/terminal_screen.py
git commit -m "feat: port all 20 gameplay commands to TerminalScreen"
```

---

## Task 8: Wire app.py + delete old screens + smoke test + tag v2.0.0

**Files:**
- Modify: `ui/app.py`
- Delete: `ui/screens/main_screen.py`, `ui/screens/new_game.py`, `ui/screens/dashboard.py`, `ui/screens/market_screen.py`, `ui/screens/banking_screen.py`, `ui/screens/contracts_screen.py`, `ui/screens/datacenter_screen.py`, `ui/screens/glossary_screen.py`

**Step 1: Replace `ui/app.py`**

```python
from textual.app import App
from textual.binding import Binding
from game.models import GameState
from game.save import save_game


class DatacenterApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "DATACENTER TYCOON"
    BINDINGS = [
        Binding("ctrl+q", "quit_and_save", "Save & Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.state: GameState | None = None

    def on_mount(self) -> None:
        from ui.screens.boot_screen import BootScreen
        self.push_screen(BootScreen())

    def action_quit_and_save(self) -> None:
        if self.state:
            save_game(self.state)
        self.exit()
```

**Step 2: Delete the old UI screens**

```bash
cd /home/jacoby/datacenter-game
rm ui/screens/main_screen.py
rm ui/screens/new_game.py
rm ui/screens/dashboard.py
rm ui/screens/market_screen.py
rm ui/screens/banking_screen.py
rm ui/screens/contracts_screen.py
rm ui/screens/datacenter_screen.py
rm ui/screens/glossary_screen.py
```

**Step 3: Verify no broken imports**

```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate
python -c "
from ui.app import DatacenterApp
from ui.screens.boot_screen import BootScreen
from ui.screens.terminal_screen import TerminalScreen
print('All imports OK')
"
```

**Step 4: Run backend tests** (should all still pass)

```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate
pytest tests/ -q 2>&1 | tail -5
```

Expected: 58 passed

**Step 5: Smoke test the full game loop**

```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate
python -c "
from game.engine import initialize_new_game, advance_day, accept_gig
from game.datacenter import buy_component, assemble_server, install_server_in_rack
from game.save import save_game, load_game
import tempfile

s = initialize_new_game('HackerCorp', 'normal')
s = buy_component(s, 'cpu_budget')
s = buy_component(s, 'ram_8gb')
s = buy_component(s, 'hdd_500gb')
s = buy_component(s, 'nic_1g')
cpu = s.hardware_inventory[0].id
ram = s.hardware_inventory[1].id
stor = s.hardware_inventory[2].id
nic = s.hardware_inventory[3].id
s, srv = assemble_server(s, 'srv1', cpu, [ram], [stor], nic)
s = install_server_in_rack(s, 'srv1', 0)
gig_count = len(s.available_gigs)
s = accept_gig(s, 0)
assert len(s.available_gigs) == gig_count - 1
for _ in range(3):
    s = advance_day(s)
print('Smoke test passed. Day:', s.day, 'Cash:', round(s.cash, 2))
"
```

**Step 6: Commit, tag, push**

```bash
cd /home/jacoby/datacenter-game
git add ui/app.py ui/screens/
git commit -m "feat: wire BootScreen + TerminalScreen, remove old tab-based UI"

git tag v2.0.0 -m "Datacenter Tycoon v2.0.0 — hacker terminal UI"

TOKEN=$(gh auth token)
git remote set-url origin "https://jacobycoffin:${TOKEN}@github.com/jacobycoffin/datacenter-tycoon.git"
git push origin master
git push origin v2.0.0
git remote set-url origin "https://github.com/jacobycoffin/datacenter-tycoon.git"
```

---

## Summary

| Task | What it does |
|------|-------------|
| 1 | CSS — green on black, purple accents |
| 2 | BootScreen — BIOS animation + new/returning player |
| 3 | TerminalScreen core — layout, echo, help, day, save |
| 4 | pin/unpin/open/close commands + panel visibility |
| 5 | view command — 10 targets print to terminal |
| 6 | open panel renderers — 7 formatted panels |
| 7 | Port all 20 gameplay commands verbatim |
| 8 | Wire app.py, delete old screens, tag v2.0.0 |
