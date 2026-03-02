from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, RichLog, Static
from textual.containers import Horizontal


class TerminalScreen(Screen):
    """Hacker-terminal style main game screen."""

    def __init__(self) -> None:
        super().__init__()
        self._prompt_text: str = "[user@datacenter ~]$ "
        self._pinned_metrics: dict[str, bool] = {}   # metric name → True (just a set of names)
        self._open_target: str | None = None         # current open panel target, or None

    def compose(self) -> ComposeResult:
        with Horizontal(id="top-area"):
            yield Static("", id="pin-panel")
            yield Static("", id="open-panel")
        yield RichLog(id="terminal", markup=True, highlight=False, max_lines=500)
        with Horizontal(id="input-row"):
            yield Static(self._prompt_text, id="prompt-label")
            yield Input(id="cmd-input", placeholder="")

    def on_mount(self) -> None:
        self._prompt_text = self._prompt_str()
        self.query_one("#prompt-label", Static).update(self._prompt_text)
        self._log("Type [bold]'help'[/] to see available commands.")
        self.query_one("#cmd-input", Input).focus()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _prompt_str(self) -> str:
        name = self.app.state.company_name[:12].lower() if self.app.state else "user"
        return f"[{name}@datacenter ~]$ "

    def _log(self, text: str) -> None:
        self.query_one("#terminal", RichLog).write(text)

    @staticmethod
    def _ga(obj, attr: str, default=0):
        """Get attribute from a dataclass instance or a plain dict (after JSON load)."""
        return obj.get(attr, default) if isinstance(obj, dict) else getattr(obj, attr, default)

    def _refresh_pin_panel(self) -> None:
        if not self._pinned_metrics:
            return
        s = self.app.state
        if not s:
            return
        lines = []
        if "cash" in self._pinned_metrics:
            lines.append(f"Cash  [#00ff41]${s.cash:,.0f}[/]")
        if "day" in self._pinned_metrics:
            lines.append(f"Day   [#00ff41]{s.day}[/]")
        if "income" in self._pinned_metrics or "net" in self._pinned_metrics:
            income = sum(self._ga(c, "monthly_revenue") for c in s.active_contracts)
        if "income" in self._pinned_metrics:
            lines.append(f"Inc   [#00ff41]+${income:,.0f}/mo[/]")
        if "rep" in self._pinned_metrics:
            lines.append(f"Rep   [#00ff41]{s.reputation}[/]")
        if "credit" in self._pinned_metrics:
            lines.append(f"Cred  [#00ff41]{s.credit_score}[/]")
        if "net" in self._pinned_metrics:
            rent = sum(self._ga(r, "monthly_rent") for r in s.racks)
            loans = sum(self._ga(l, "monthly_payment") for l in s.loans)
            net = income - rent - loans
            color = "green" if net >= 0 else "red"
            sign = "+" if net >= 0 else ""
            lines.append(f"Net   [{color}]{sign}${net:,.0f}/mo[/]")
        self.query_one("#pin-panel", Static).update("\n".join(lines))

    def _update_visibility(self) -> None:
        top_area = self.query_one("#top-area", Horizontal)
        pin_panel = self.query_one("#pin-panel", Static)

        has_pin = bool(self._pinned_metrics)
        has_open = self._open_target is not None

        # Show/hide top-area
        if has_pin or has_open:
            top_area.add_class("visible")
        else:
            top_area.remove_class("visible")

        # Show/hide pin-panel
        if has_pin:
            pin_panel.add_class("visible")
        else:
            pin_panel.remove_class("visible")

    # ------------------------------------------------------------------ #
    # Input handling
    # ------------------------------------------------------------------ #

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        inp = self.query_one("#cmd-input", Input)
        inp.clear()
        if not raw:
            return
        self._log(f"[bold #00ff41]{self._prompt_text}[/] {raw}")
        self._run_command(raw)
        inp.focus()

    def _run_command(self, raw: str) -> None:
        parts = raw.split()
        cmd = parts[0].lower() if parts else ""
        args = parts[1:]
        dispatch = {
            "help": self._cmd_help,
            "day": self._cmd_day,
            "save": self._cmd_save,
            "view": self._cmd_view,
            "pin": self._cmd_pin,
            "unpin": self._cmd_unpin,
            "open": self._cmd_open,
            "close": self._cmd_close,
            "buy": self._cmd_buy,
            "sell": self._cmd_sell,
            "transfer": self._cmd_transfer,
            "loan": self._cmd_loan,
            "bond": self._cmd_bond,
            "sellbond": self._cmd_sellbond,
            "accept": self._cmd_accept,
            "decline": self._cmd_decline,
            "negotiate": self._cmd_negotiate,
            "assign": self._cmd_assign,
            "gig": self._cmd_gig,
            "buyhw": self._cmd_buyhw,
            "assemble": self._cmd_assemble,
            "install": self._cmd_install,
            "repair": self._cmd_repair,
            "rent": self._cmd_rent,
        }
        handler = dispatch.get(cmd)
        if handler:
            handler(args)
        else:
            self._log(f"[red]Unknown command: '{cmd}'. Type 'help' for available commands.[/]")

    # ------------------------------------------------------------------ #
    # Fully implemented commands
    # ------------------------------------------------------------------ #

    def _cmd_help(self, args: list[str]) -> None:
        self._log(
            "Available commands:\n"
            "  view <target>     — Print a report (cash, contracts, servers, market, loans, bonds, inventory, racks, gigs, all)\n"
            "  pin <metric>      — Pin a metric to the top panel (cash, day, income, rep, credit, net)\n"
            "  unpin <metric>    — Remove a pinned metric\n"
            "  pin clear         — Clear all pinned metrics\n"
            "  open <target>     — Open a panel (store, contracts, market, servers, racks, gigs, banking)\n"
            "  close             — Close the open panel\n"
            "\n"
            "  day               — Advance one day\n"
            "  save              — Save game\n"
            "  buy <qty> <ticker>   — Buy stocks\n"
            "  sell <qty> <ticker>  — Sell stocks\n"
            "  transfer <to|from> savings <amount>  — Move money between checking/savings\n"
            "  loan <amount> [term]  — Take out a loan (term: 6, 12, or 24 months)\n"
            "  bond <amount> [days]  — Buy a bond (30, 60, 90, or 180 days)\n"
            "  sellbond <id>         — Sell a bond early\n"
            "  accept <n>            — Accept contract #n from pending list\n"
            "  decline <n>           — Decline contract #n\n"
            "  negotiate <n> <pct>   — Counter-offer (e.g. negotiate 1 15 for +15%)\n"
            "  assign <server_id> <contract_id>  — Assign server to contract\n"
            "  gig <n>               — Accept gig #n from gig board\n"
            "  buyhw <hw_id>         — Buy hardware component (e.g. buyhw cpu_mid)\n"
            "  assemble <name> <cpu> <ram[,ram]> <storage[,storage]> <nic>  — Assemble server\n"
            "  install <server_id> <rack_id>  — Install server in rack\n"
            "  repair <server_id>    — Repair degraded server\n"
            "  rent                  — Rent another rack"
        )

    def _cmd_day(self, args: list[str]) -> None:
        from game.engine import advance_day
        from game.save import save_game
        if not self.app.state:
            self._log("[red]No active game session.[/]")
            return
        state = advance_day(self.app.state)
        self.app.state = state
        save_game(state)
        self._log(f"[#9d4edd]Day {state.day}[/]")
        for entry in state.event_log[-3:]:
            self._log(f"  [#3a7a3a]{entry}[/]")
        self._refresh_pin_panel()
        if state.cash == -1.0:
            self._log("[bold red]GAME OVER — BANKRUPTCY. Your company has collapsed.[/]")
            self._log("[dim]Save file preserved. Start a new game to try again.[/]")
            self.query_one("#cmd-input", Input).disabled = True

    def _cmd_save(self, args: list[str]) -> None:
        from game.save import save_game
        if not self.app.state:
            self._log("[red]No active game session.[/]")
            return
        save_game(self.app.state)
        self._log("Game saved.")

    # ------------------------------------------------------------------ #
    # Stub commands (implemented in later tasks)
    # ------------------------------------------------------------------ #

    def _cmd_view(self, args: list[str]) -> None:
        targets = {
            "cash": self._view_cash,
            "contracts": self._view_contracts,
            "servers": self._view_servers,
            "market": self._view_market,
            "loans": self._view_loans,
            "bonds": self._view_bonds,
            "inventory": self._view_inventory,
            "racks": self._view_racks,
            "gigs": self._view_gigs,
            "all": self._view_all,
        }
        if not args:
            self._log(f"[red]Usage: view <target>  Valid: {', '.join(sorted(targets))}[/]")
            return
        target = args[0].lower()
        fn = targets.get(target)
        if fn:
            fn()
        else:
            self._log(f"[red]Unknown view target '{target}'. Valid: {', '.join(sorted(targets))}[/]")

    def _view_cash(self) -> None:
        s = self.app.state
        self._log(f"[#9d4edd]── CASH ──[/]")
        self._log(f"  Checking:  [#00ff41]${s.cash:>12,.2f}[/]")
        self._log(f"  Savings:   [#00ff41]${s.savings:>12,.2f}[/]")
        self._log(f"  Total:     [#00ff41]${s.cash + s.savings:>12,.2f}[/]")

    def _view_contracts(self) -> None:
        s = self.app.state
        self._log("[#9d4edd]── CONTRACTS ──[/]")
        if not s.active_contracts and not s.pending_contracts:
            self._log("  [dim]No contracts.[/]")
            return
        if s.active_contracts:
            self._log("  [bold]Active:[/]")
            for i, c in enumerate(s.active_contracts):
                name = self._ga(c, "client_name", "?")
                rev = self._ga(c, "monthly_revenue", 0)
                days = self._ga(c, "days_remaining", 0)
                sla = self._ga(c, "sla_tier", "?")
                self._log(f"  {i+1}. {name}  ${rev:,.2f}/mo  {days}d left  SLA {sla}%")
        if s.pending_contracts:
            self._log("  [bold]Pending offers:[/]")
            for i, c in enumerate(s.pending_contracts):
                name = self._ga(c, "client_name", "?")
                rev = self._ga(c, "monthly_revenue", 0)
                cores = self._ga(c, "required_cores", 0)
                ram = self._ga(c, "required_ram_gb", 0)
                sla = self._ga(c, "sla_tier", "?")
                self._log(f"  {i+1}. {name}  ${rev:,.2f}/mo  {cores}c/{ram}GB  SLA {sla}%")

    def _view_servers(self) -> None:
        s = self.app.state
        self._log("[#9d4edd]── SERVERS ──[/]")
        if not s.servers:
            self._log("  [dim]No servers assembled.[/]")
            return
        for srv in s.servers:
            name = self._ga(srv, "name", "?")
            srv_id = self._ga(srv, "id", "?")[:8]
            cores = self._ga(srv, "total_cores", 0)
            ram = self._ga(srv, "total_ram_gb", 0)
            storage = self._ga(srv, "total_storage_gb", 0)
            health = self._ga(srv, "health", 1.0)
            rack_id = self._ga(srv, "rack_id", None)
            health_color = "green" if health > 0.7 else ("yellow" if health > 0.3 else "red")
            rack_str = f"rack:{rack_id[:6]}" if rack_id else "[dim]uninstalled[/]"
            self._log(f"  {name} [dim]({srv_id})[/]  {cores}c/{ram}GB/{storage}GB  [{health_color}]health:{health:.0%}[/]  {rack_str}")

    def _view_market(self) -> None:
        s = self.app.state
        self._log("[#9d4edd]── MARKET ──[/]")
        for ticker, price in sorted(s.market_prices.items()):
            hist = s.price_history.get(ticker, [price])
            prev = hist[-2] if len(hist) >= 2 else price
            chg = price - prev
            chg_pct = (chg / prev * 100) if prev else 0
            color = "green" if chg >= 0 else "red"
            owned = s.portfolio.get(ticker, {}).get("shares", 0)
            owned_str = f"  own:{owned}" if owned else ""
            self._log(f"  {ticker:<6} [#00ff41]${price:>8.2f}[/]  [{color}]{chg_pct:+.2f}%[/]{owned_str}")

    def _view_loans(self) -> None:
        s = self.app.state
        self._log("[#9d4edd]── LOANS ──[/]")
        if not s.loans:
            self._log("  [dim]No active loans.[/]")
            return
        for loan in s.loans:
            balance = self._ga(loan, "remaining_balance", 0)
            payment = self._ga(loan, "monthly_payment", 0)
            days = self._ga(loan, "days_remaining", 0)
            rate = self._ga(loan, "annual_rate", 0)
            self._log(f"  ${balance:,.2f} remaining  {rate*100:.1f}% APR  ${payment:,.2f}/mo  {days}d left")

    def _view_bonds(self) -> None:
        s = self.app.state
        self._log("[#9d4edd]── BONDS ──[/]")
        if not s.bonds:
            self._log("  [dim]No bonds held.[/]")
            return
        for bond in s.bonds:
            fv = self._ga(bond, "face_value", 0)
            yld = self._ga(bond, "annual_yield", 0)
            days = self._ga(bond, "days_remaining", 0)
            bid = self._ga(bond, "id", "?")[:8]
            self._log(f"  [dim]({bid})[/]  ${fv:,.2f} face  {yld*100:.0f}%/yr  {days}d to maturity")

    def _view_inventory(self) -> None:
        s = self.app.state
        self._log("[#9d4edd]── HARDWARE INVENTORY ──[/]")
        if not s.hardware_inventory:
            self._log("  [dim]No components in inventory.[/]")
            return
        for comp in s.hardware_inventory:
            ctype = self._ga(comp, "type", "?").upper()
            cname = self._ga(comp, "name", "?")
            price = self._ga(comp, "price", 0)
            cid = self._ga(comp, "id", "?")[:8]
            self._log(f"  [{ctype}] {cname}  ${price:,.2f}  [dim]id:{cid}[/]")

    def _view_racks(self) -> None:
        s = self.app.state
        self._log("[#9d4edd]── RACKS ──[/]")
        if not s.racks:
            self._log("  [dim]No racks rented.[/]")
            return
        for rack in s.racks:
            rid = self._ga(rack, "id", "?")[:8]
            rname = self._ga(rack, "name", "?")
            tier = self._ga(rack, "location_tier", "?")
            rent = self._ga(rack, "monthly_rent", 0)
            total_u = self._ga(rack, "total_u", 12)
            installed = [srv for srv in s.servers if self._ga(srv, "rack_id", None) == self._ga(rack, "id", None)]
            used_u = sum(self._ga(srv, "size_u", 1) for srv in installed)
            self._log(f"  {rname} [dim]({rid})[/]  {tier}  {used_u}/{total_u}U  ${rent:,.0f}/mo")

    def _view_gigs(self) -> None:
        s = self.app.state
        self._log("[#9d4edd]── GIG BOARD ──[/]")
        if not s.available_gigs:
            self._log("  [dim]No gigs available today.[/]")
            return
        for i, gig in enumerate(s.available_gigs):
            title = self._ga(gig, "title", "?")
            payout = self._ga(gig, "payout", 0)
            gid = self._ga(gig, "id", "?")[:6]
            self._log(f"  {i+1}. [#ffb703]${payout:,.2f}[/]  {title}  [dim](id:{gid})[/]")

    def _view_all(self) -> None:
        s = self.app.state
        monthly_revenue = sum(self._ga(c, "monthly_revenue") for c in s.active_contracts)
        monthly_rent = sum(self._ga(r, "monthly_rent") for r in s.racks)
        monthly_loans = sum(self._ga(l, "monthly_payment") for l in s.loans)
        net = monthly_revenue - monthly_rent - monthly_loans
        net_color = "green" if net >= 0 else "red"
        net_sign = "+" if net >= 0 else ""
        from game.market import portfolio_value
        port_val = portfolio_value(s.portfolio, s.market_prices)
        bond_val = sum(self._ga(b, "face_value") for b in s.bonds)
        loan_debt = sum(self._ga(l, "remaining_balance") for l in s.loans)
        net_worth = s.cash + s.savings + port_val + bond_val - loan_debt

        self._log(f"[#9d4edd]── FINANCIAL SUMMARY  Day {s.day} ──[/]")
        self._log(f"  Net Worth:       [#ffb703]${net_worth:>12,.2f}[/]")
        self._log(f"  Cash (checking): [#00ff41]${s.cash:>12,.2f}[/]")
        self._log(f"  Savings:         [#00ff41]${s.savings:>12,.2f}[/]")
        self._log(f"  Investments:     [#ffb703]${port_val + bond_val:>12,.2f}[/]")
        self._log(f"  Total Debt:      [red]${loan_debt:>12,.2f}[/]")
        self._log("")
        self._log(f"  Monthly Revenue: [#00ff41]${monthly_revenue:>10,.2f}[/]")
        self._log(f"  Monthly Costs:   [red]${monthly_rent + monthly_loans:>10,.2f}[/]")
        self._log(f"  Monthly Net:     [{net_color}]{net_sign}${abs(net):>10,.2f}[/]")
        self._log("")
        self._log(f"  Active Contracts: {len(s.active_contracts)}")
        self._log(f"  Servers Online:   {sum(1 for srv in s.servers if self._ga(srv, 'rack_id', None))}")
        self._log(f"  Racks Rented:     {len(s.racks)}")
        self._log(f"  Reputation:       {s.reputation}/100")
        self._log(f"  Credit Score:     {s.credit_score}")

    def _cmd_pin(self, args: list[str]) -> None:
        valid = {"cash", "day", "income", "rep", "credit", "net"}
        if not args:
            self._log("[red]Usage: pin <metric>  or  pin clear[/]")
            self._log(f"  Valid metrics: {', '.join(sorted(valid))}")
            return
        if args[0].lower() == "clear":
            self._pinned_metrics.clear()
            self._update_visibility()
            self._log("Pin panel cleared.")
            return
        metric = args[0].lower()
        if metric not in valid:
            self._log(f"[red]Unknown metric '{metric}'. Valid: {', '.join(sorted(valid))}[/]")
            return
        self._pinned_metrics[metric] = True
        self._update_visibility()
        self._refresh_pin_panel()
        self._log(f"Pinned [#9d4edd]{metric}[/].")

    def _cmd_unpin(self, args: list[str]) -> None:
        if not args:
            self._log("[red]Usage: unpin <metric>[/]")
            return
        metric = args[0].lower()
        if metric not in self._pinned_metrics:
            self._log(f"[yellow]{metric} is not pinned.[/]")
            return
        del self._pinned_metrics[metric]
        self._update_visibility()
        self._refresh_pin_panel()
        self._log(f"Unpinned {metric}.")

    def _cmd_open(self, args: list[str]) -> None:
        valid = {"store", "contracts", "market", "servers", "racks", "gigs", "banking"}
        if not args:
            self._log(f"[red]Usage: open <target>  Valid: {', '.join(sorted(valid))}[/]")
            return
        target = args[0].lower()
        if target not in valid:
            self._log(f"[red]Unknown target '{target}'. Valid: {', '.join(sorted(valid))}[/]")
            return
        self._open_target = target
        self._update_visibility()
        self._render_open_panel()
        self._log(f"Opened [#9d4edd]{target}[/]. Type 'close' to dismiss.")

    def _cmd_close(self, args: list[str]) -> None:
        if self._open_target is None:
            self._log("[yellow]No panel is open.[/]")
            return
        old = self._open_target
        self._open_target = None
        self.query_one("#open-panel", Static).update("")
        self._update_visibility()
        self._log(f"Closed {old} panel.")

    def _render_open_panel(self) -> None:
        """Dispatch to the appropriate panel renderer based on _open_target."""
        if self._open_target is None:
            return
        renderers = {
            "store":     self._panel_store,
            "contracts": self._panel_contracts,
            "market":    self._panel_market,
            "servers":   self._panel_servers,
            "racks":     self._panel_racks,
            "gigs":      self._panel_gigs,
            "banking":   self._panel_banking,
        }
        fn = renderers.get(self._open_target)
        if fn:
            self.query_one("#open-panel", Static).update(fn())
        else:
            self.query_one("#open-panel", Static).update(
                f"[#9d4edd]── {self._open_target.upper()} ──[/]\n[dim]No renderer for '{self._open_target}'[/]"
            )

    def _panel_store(self) -> str:
        import json
        from pathlib import Path
        hw_path = Path(__file__).resolve().parent.parent.parent / "data" / "hardware.json"
        hw = json.loads(hw_path.read_text())
        lines = ["[#9d4edd]── HARDWARE STORE ──[/]",
                 "[dim]Use: buyhw <id>[/]", ""]
        for category, items in hw.items():
            lines.append(f"[bold #9d4edd]{category.upper()}[/]")
            for item in items:
                lines.append(f"  {item['id']:<18} {item['name']:<28} [#00ff41]${item['price']:>6,.0f}[/]")
            lines.append("")
        return "\n".join(lines)

    def _panel_contracts(self) -> str:
        s = self.app.state
        lines = ["[#9d4edd]── PENDING CONTRACT OFFERS ──[/]",
                 "[dim]Use: accept <n>  decline <n>  negotiate <n> <pct>[/]", ""]
        if not s.pending_contracts:
            lines.append("  [dim]No pending offers.[/]")
        else:
            for i, c in enumerate(s.pending_contracts):
                name = self._ga(c, "client_name", "?")
                rev = self._ga(c, "monthly_revenue", 0)
                cores = self._ga(c, "required_cores", 0)
                ram = self._ga(c, "required_ram_gb", 0)
                storage = self._ga(c, "required_storage_gb", 0)
                sla = self._ga(c, "sla_tier", "?")
                dur = self._ga(c, "duration_days", 0)
                lines.append(f"  [bold]{i+1}.[/] {name}")
                lines.append(f"      [#00ff41]${rev:,.2f}/mo[/]  {dur}d  SLA {sla}%")
                lines.append(f"      Needs: {cores}c / {ram}GB RAM / {storage}GB storage")
                lines.append("")
        return "\n".join(lines)

    def _panel_market(self) -> str:
        s = self.app.state
        lines = ["[#9d4edd]── MARKET ──[/]",
                 "[dim]Use: buy <qty> <ticker>  sell <qty> <ticker>[/]", ""]
        for ticker, price in sorted(s.market_prices.items()):
            hist = s.price_history.get(ticker, [price])
            prev = hist[-2] if len(hist) >= 2 else price
            chg = price - prev
            chg_pct = (chg / prev * 100) if prev else 0
            color = "green" if chg >= 0 else "red"
            owned = s.portfolio.get(ticker, {}).get("shares", 0)
            owned_str = f"  [dim]own:{owned}[/]" if owned else ""
            lines.append(f"  {ticker:<6} [#00ff41]${price:>8.2f}[/]  [{color}]{chg_pct:+.2f}%[/]{owned_str}")
        return "\n".join(lines)

    def _panel_servers(self) -> str:
        s = self.app.state
        lines = ["[#9d4edd]── SERVERS ──[/]",
                 "[dim]Use: install <server_id> <rack_id>  repair <server_id>[/]", ""]
        if not s.servers:
            lines.append("  [dim]No servers assembled.[/]")
        else:
            for srv in s.servers:
                name = self._ga(srv, "name", "?")
                sid = self._ga(srv, "id", "?")[:8]
                cores = self._ga(srv, "total_cores", 0)
                ram = self._ga(srv, "total_ram_gb", 0)
                storage = self._ga(srv, "total_storage_gb", 0)
                health = self._ga(srv, "health", 1.0)
                rack_id = self._ga(srv, "rack_id", None)
                health_color = "green" if health > 0.7 else ("yellow" if health > 0.3 else "red")
                rack_str = f"rack:{rack_id[:6]}" if rack_id else "[dim]uninstalled[/]"
                lines.append(f"  {name} [dim]({sid})[/]")
                lines.append(f"    {cores}c/{ram}GB/{storage}GB  [{health_color}]{health:.0%}[/]  {rack_str}")
                lines.append("")
        return "\n".join(lines)

    def _panel_racks(self) -> str:
        s = self.app.state
        lines = ["[#9d4edd]── RACKS ──[/]",
                 "[dim]Use: install <server_id> <rack_id>  rent[/]", ""]
        if not s.racks:
            lines.append("  [dim]No racks rented. Use 'rent' to add one.[/]")
        else:
            for rack in s.racks:
                rid = self._ga(rack, "id", "?")
                rname = self._ga(rack, "name", "?")
                tier = self._ga(rack, "location_tier", "?")
                rent = self._ga(rack, "monthly_rent", 0)
                total_u = self._ga(rack, "total_u", 12)
                installed = [srv for srv in s.servers if self._ga(srv, "rack_id", None) == rid]
                lines.append(f"  [bold]{rname}[/] [dim]({rid[:8]})[/]  {tier}  ${rent:,.0f}/mo")
                # ASCII rack diagram
                lines.append("  ┌──────────────────────────┐")
                srv_map = {}
                slot = 0
                for srv in installed:
                    size = self._ga(srv, "size_u", 1)
                    start = self._ga(srv, "slot_start", None) or slot
                    for u in range(size):
                        srv_map[start + u] = (srv, u == 0)
                    slot = start + size
                for u in range(total_u):
                    if u in srv_map:
                        srv, is_top = srv_map[u]
                        health = self._ga(srv, "health", 1.0)
                        hc = "green" if health > 0.7 else ("yellow" if health > 0.3 else "red")
                        label = self._ga(srv, "name", "?")[:14] if is_top else "  └─────────────"
                        lines.append(f"  │ [{hc}]{u+1:02d}U {label:<14}[/] │")
                    else:
                        lines.append(f"  │ [dim]{u+1:02d}U  ── empty ──────[/] │")
                lines.append("  └──────────────────────────┘")
                lines.append("")
        return "\n".join(lines)

    def _panel_gigs(self) -> str:
        s = self.app.state
        lines = ["[#9d4edd]── GIG BOARD ──[/]",
                 "[dim]Use: gig <n>[/]", ""]
        if not s.available_gigs:
            lines.append("  [dim]No gigs available today.[/]")
        else:
            for i, gig in enumerate(s.available_gigs):
                title = self._ga(gig, "title", "?")
                payout = self._ga(gig, "payout", 0)
                gid = self._ga(gig, "id", "?")[:6]
                lines.append(f"  [bold]{i+1}.[/] [#ffb703]${payout:,.2f}[/]  {title}")
                lines.append(f"      [dim]id:{gid}[/]")
                lines.append("")
        return "\n".join(lines)

    def _panel_banking(self) -> str:
        s = self.app.state
        from game.finance import loan_interest_rate_for_credit_score
        rate = loan_interest_rate_for_credit_score(s.credit_score)
        lines = [
            "[#9d4edd]── BANKING ──[/]",
            "[dim]Use: transfer to|from savings <amt>  loan <amt> [term]  bond <amt> [days]  sellbond <id>[/]",
            "",
            f"  Checking:    [#00ff41]${s.cash:>12,.2f}[/]",
            f"  Savings:     [#00ff41]${s.savings:>12,.2f}[/]  (6%/yr)",
            f"  Credit:      {s.credit_score}  (loan rate: {rate*100:.1f}% APR)",
            "",
            "[bold]Loans:[/]",
        ]
        if not s.loans:
            lines.append("  [dim]No active loans.[/]")
        else:
            for loan in s.loans:
                balance = self._ga(loan, "remaining_balance", 0)
                payment = self._ga(loan, "monthly_payment", 0)
                days = self._ga(loan, "days_remaining", 0)
                lines.append(f"  ${balance:,.2f} remaining  ${payment:,.2f}/mo  {days}d left")
        lines.append("")
        lines.append("[bold]Bonds:[/]")
        if not s.bonds:
            lines.append("  [dim]No bonds held.[/]")
        else:
            for bond in s.bonds:
                fv = self._ga(bond, "face_value", 0)
                yld = self._ga(bond, "annual_yield", 0)
                days = self._ga(bond, "days_remaining", 0)
                bid = self._ga(bond, "id", "?")[:8]
                lines.append(f"  [dim]({bid})[/]  ${fv:,.2f}  {yld*100:.0f}%/yr  {days}d  [dim]sellbond {bid}[/]")
        lines.append("")
        lines.append("[bold]CDs:[/]")
        if not s.cds:
            lines.append("  [dim]No CDs.[/]")
        else:
            for cd in s.cds:
                balance = self._ga(cd, "balance", 0)
                rate_cd = self._ga(cd, "annual_rate", 0.15)
                days = self._ga(cd, "days_remaining", 0)
                lines.append(f"  ${balance:,.2f}  {rate_cd*100:.0f}%/yr  {days}d remaining")
        return "\n".join(lines)

    def _cmd_buy(self, args: list[str]) -> None:
        if len(args) != 2:
            self._log("[red]Usage: buy <qty> <ticker>[/]")
            return
        try:
            qty = int(args[0])
        except ValueError:
            self._log("[red]Usage: buy <qty> <ticker>  (qty must be a number)[/]")
            return
        ticker = args[1].upper()
        s = self.app.state
        price = s.market_prices.get(ticker)
        if price is None:
            self._log(f"[red]Unknown ticker '{ticker}'[/]")
            return
        if qty <= 0:
            self._log("[red]Quantity must be positive[/]")
            return
        cost = price * qty
        if s.cash < cost:
            self._log(f"[red]Insufficient funds: need ${cost:,.2f}, have ${s.cash:,.2f}[/]")
            return
        s.cash -= cost
        holding = s.portfolio.setdefault(ticker, {"shares": 0, "avg_cost": 0.0})
        total = holding["shares"] + qty
        holding["avg_cost"] = (holding["avg_cost"] * holding["shares"] + cost) / total
        holding["shares"] = total
        from game.save import save_game
        save_game(self.app.state)
        self._refresh_pin_panel()
        if self._open_target == "market":
            self._render_open_panel()
        self._log(f"[#00ff41]Bought {qty} {ticker} @ ${price:.2f}  (-${cost:,.2f})[/]")

    def _cmd_sell(self, args: list[str]) -> None:
        if len(args) != 2:
            self._log("[red]Usage: sell <qty> <ticker>[/]")
            return
        try:
            qty = int(args[0])
        except ValueError:
            self._log("[red]Usage: sell <qty> <ticker>  (qty must be a number)[/]")
            return
        ticker = args[1].upper()
        s = self.app.state
        price = s.market_prices.get(ticker)
        if price is None:
            self._log(f"[red]Unknown ticker '{ticker}'[/]")
            return
        holding = s.portfolio.get(ticker, {})
        owned = holding.get("shares", 0)
        if qty <= 0 or qty > owned:
            self._log(f"[red]You own {owned} shares of {ticker}[/]")
            return
        proceeds = price * qty
        s.cash += proceeds
        holding["shares"] -= qty
        if holding["shares"] == 0:
            del s.portfolio[ticker]
        from game.save import save_game
        save_game(self.app.state)
        self._refresh_pin_panel()
        if self._open_target == "market":
            self._render_open_panel()
        self._log(f"[#00ff41]Sold {qty} {ticker} @ ${price:.2f}  (+${proceeds:,.2f})[/]")

    def _cmd_transfer(self, args: list[str]) -> None:
        if len(args) != 3 or args[0] not in ("to", "from") or args[1] != "savings":
            self._log("[red]Usage: transfer to|from savings <amount>[/]")
            return
        direction = args[0]
        try:
            amt = float(args[2].replace(",", "").replace("$", ""))
        except ValueError:
            self._log("[red]Usage: transfer to|from savings <amount>[/]")
            return
        if amt <= 0:
            self._log("[red]Amount must be positive[/]")
            return
        s = self.app.state
        if direction == "to":
            if amt > s.cash:
                self._log(f"[red]Insufficient checking: have ${s.cash:,.2f}[/]")
                return
            s.cash -= amt
            s.savings += amt
            msg = f"[#00ff41]Moved ${amt:,.2f} → savings (savings: ${s.savings:,.2f})[/]"
        else:
            if amt > s.savings:
                self._log(f"[red]Insufficient savings: have ${s.savings:,.2f}[/]")
                return
            s.savings -= amt
            s.cash += amt
            msg = f"[#00ff41]Moved ${amt:,.2f} → checking (checking: ${s.cash:,.2f})[/]"
        from game.save import save_game
        save_game(self.app.state)
        self._refresh_pin_panel()
        if self._open_target == "banking":
            self._render_open_panel()
        self._log(msg)

    def _cmd_loan(self, args: list[str]) -> None:
        import uuid
        from game.finance import loan_interest_rate_for_credit_score, calculate_loan_payment
        if not args or len(args) > 2:
            self._log("[red]Usage: loan <amount> [term]  (term: 6, 12, or 24 months)[/]")
            return
        try:
            amt = float(args[0].replace(",", "").replace("$", ""))
            months = int(args[1]) if len(args) > 1 else 12
        except ValueError:
            self._log("[red]Usage: loan <amount> [term][/]")
            return
        if months not in (6, 12, 24):
            self._log("[red]Term must be 6, 12, or 24 months[/]")
            return
        if not (5000 <= amt <= 500000):
            self._log("[red]Loan amount must be $5,000–$500,000[/]")
            return
        s = self.app.state
        rate = loan_interest_rate_for_credit_score(s.credit_score)
        payment = calculate_loan_payment(amt, rate, months)
        loan = {
            "id": str(uuid.uuid4()),
            "principal": amt,
            "remaining_balance": amt,
            "annual_rate": rate,
            "term_days": months * 30,
            "days_remaining": months * 30,
            "monthly_payment": round(payment, 2),
        }
        s.loans.append(loan)
        s.cash += amt
        from game.save import save_game
        save_game(self.app.state)
        self._refresh_pin_panel()
        if self._open_target == "banking":
            self._render_open_panel()
        self._log(f"[#00ff41]Loan approved: ${amt:,.2f} at {rate*100:.1f}% APR, ${payment:,.2f}/mo for {months} months[/]")

    def _cmd_bond(self, args: list[str]) -> None:
        import uuid
        YIELDS = {30: 0.12, 60: 0.14, 90: 0.16, 180: 0.18}
        if not args or len(args) > 2:
            self._log("[red]Usage: bond <amount> [days]  (days: 30, 60, 90, or 180)[/]")
            return
        try:
            amt = float(args[0].replace(",", "").replace("$", ""))
            days = int(args[1]) if len(args) > 1 else 30
        except ValueError:
            self._log("[red]Usage: bond <amount> [days][/]")
            return
        if days not in YIELDS:
            self._log("[red]Term must be 30, 60, 90, or 180 days[/]")
            return
        if amt < 1000:
            self._log("[red]Minimum bond purchase is $1,000[/]")
            return
        s = self.app.state
        if amt > s.cash:
            self._log(f"[red]Insufficient funds: need ${amt:,.2f}, have ${s.cash:,.2f}[/]")
            return
        annual_yield = YIELDS[days]
        bond = {
            "id": str(uuid.uuid4()),
            "face_value": amt,
            "annual_yield": annual_yield,
            "maturity_days": days,
            "days_remaining": days,
            "purchase_price": amt,
        }
        s.bonds.append(bond)
        s.cash -= amt
        from game.save import save_game
        save_game(self.app.state)
        self._refresh_pin_panel()
        if self._open_target == "banking":
            self._render_open_panel()
        self._log(f"[#00ff41]Bond purchased: ${amt:,.2f} at {annual_yield*100:.0f}%/yr, matures in {days} days[/]")

    def _cmd_sellbond(self, args: list[str]) -> None:
        from game.finance import bond_current_value
        if len(args) != 1:
            self._log("[red]Usage: sellbond <id>[/]")
            return
        prefix = args[0]
        s = self.app.state
        idx = next(
            (i for i, b in enumerate(s.bonds)
             if (b.get("id", "") if isinstance(b, dict) else b.id).startswith(prefix)),
            None
        )
        if idx is None:
            self._log(f"[red]No bond with ID starting '{prefix}'[/]")
            return
        bond = s.bonds[idx]
        fv = self._ga(bond, "face_value")
        yld = self._ga(bond, "annual_yield")
        days_rem = self._ga(bond, "days_remaining")
        mat_days = self._ga(bond, "maturity_days")
        value = bond_current_value(fv, yld, days_rem, mat_days)
        s.cash += value
        s.bonds.pop(idx)
        diff = value - fv
        sign = "+" if diff >= 0 else ""
        from game.save import save_game
        save_game(self.app.state)
        self._refresh_pin_panel()
        if self._open_target == "banking":
            self._render_open_panel()
        self._log(f"[#00ff41]Sold bond for ${value:,.2f} (face ${fv:,.2f}, {sign}${diff:,.2f})[/]")

    def _cmd_accept(self, args: list[str]) -> None:
        if len(args) != 1:
            self._log("[red]Usage: accept <n>[/]")
            return
        try:
            idx = int(args[0]) - 1
        except ValueError:
            self._log("[red]Usage: accept <n>[/]")
            return
        s = self.app.state
        if idx < 0 or idx >= len(s.pending_contracts):
            self._log(f"[red]No offer #{idx+1}[/]")
            return
        contract = s.pending_contracts[idx]
        if isinstance(contract, dict):
            contract["status"] = "active"
        else:
            contract.status = "active"
        s.active_contracts.append(contract)
        s.pending_contracts.pop(idx)
        client = contract.get("client_name", "?") if isinstance(contract, dict) else contract.client_name
        from game.save import save_game
        save_game(self.app.state)
        self._refresh_pin_panel()
        if self._open_target == "contracts":
            self._render_open_panel()
        self._log(f"[#00ff41]Contract accepted from {client}! Assign a server with: assign <server_id> <contract_id>[/]")

    def _cmd_decline(self, args: list[str]) -> None:
        if len(args) != 1:
            self._log("[red]Usage: decline <n>[/]")
            return
        try:
            idx = int(args[0]) - 1
        except ValueError:
            self._log("[red]Usage: decline <n>[/]")
            return
        s = self.app.state
        if idx < 0 or idx >= len(s.pending_contracts):
            self._log(f"[red]No offer #{idx+1}[/]")
            return
        contract = s.pending_contracts.pop(idx)
        client = contract.get("client_name", "?") if isinstance(contract, dict) else contract.client_name
        from game.save import save_game
        save_game(self.app.state)
        self._refresh_pin_panel()
        if self._open_target == "contracts":
            self._render_open_panel()
        self._log(f"[#00ff41]Declined offer from {client}.[/]")

    def _cmd_negotiate(self, args: list[str]) -> None:
        from game.contracts import negotiate_contract
        from game.models import Contract as ContractModel
        # negotiate <n> [pct]  — counter-offer at +pct% (default 15%)
        if not args:
            self._log("[red]Usage: negotiate <n> [pct][/]")
            return
        try:
            idx = int(args[0]) - 1
            pct = float(args[1]) / 100 if len(args) > 1 else 0.15
        except ValueError:
            self._log("[red]Usage: negotiate <n> [pct][/]")
            return
        s = self.app.state
        if idx < 0 or idx >= len(s.pending_contracts):
            self._log(f"[red]No offer #{idx+1}[/]")
            return
        contract = s.pending_contracts[idx]
        c_obj = ContractModel(**contract) if isinstance(contract, dict) else contract
        new_contract = negotiate_contract(c_obj, counter_pct=pct)
        s.pending_contracts.pop(idx)
        if new_contract:
            new_contract.status = "active"
            s.active_contracts.append(new_contract)
            from game.save import save_game
            save_game(self.app.state)
            self._refresh_pin_panel()
            if self._open_target == "contracts":
                self._render_open_panel()
            self._log(f"[#00ff41]Negotiated! New rate: ${new_contract.monthly_revenue:,.2f}/mo[/]")
        else:
            from game.save import save_game
            save_game(self.app.state)
            self._refresh_pin_panel()
            if self._open_target == "contracts":
                self._render_open_panel()
            self._log("[red]Counter-offer rejected.[/]")

    def _cmd_assign(self, args: list[str]) -> None:
        if len(args) < 2:
            self._log("[red]Usage: assign <server_id> <contract_id>[/]")
            return
        server_id_prefix = args[0]
        contract_id_prefix = args[1]
        s = self.app.state
        server = next(
            (sv for sv in s.servers
             if (sv.get("id", "") if isinstance(sv, dict) else sv.id).startswith(server_id_prefix)),
            None
        )
        if server is None:
            self._log(f"[red]No server with ID starting '{server_id_prefix}'[/]")
            return
        contract = next(
            (c for c in s.active_contracts
             if (c.get("id", "") if isinstance(c, dict) else c.id).startswith(contract_id_prefix)),
            None
        )
        if contract is None:
            self._log(f"[red]No active contract with ID starting '{contract_id_prefix}'[/]")
            return
        srv_id = server.get("id") if isinstance(server, dict) else server.id
        ctr_id = contract.get("id") if isinstance(contract, dict) else contract.id
        if isinstance(contract, dict):
            contract["server_id"] = srv_id
        else:
            contract.server_id = srv_id
        if isinstance(server, dict):
            server["contract_id"] = ctr_id
        else:
            server.contract_id = ctr_id
        srv_name = server.get("name", srv_id[:8]) if isinstance(server, dict) else getattr(server, "name", srv_id[:8])
        cname = contract.get("client_name", "?") if isinstance(contract, dict) else contract.client_name
        from game.save import save_game
        save_game(self.app.state)
        self._refresh_pin_panel()
        if self._open_target == "contracts":
            self._render_open_panel()
        self._log(f"[#00ff41]Assigned {srv_name} to {cname}'s contract.[/]")

    def _cmd_gig(self, args: list[str]) -> None:
        from game.engine import accept_gig
        if len(args) != 1:
            self._log("[red]Usage: gig <n>[/]")
            return
        try:
            idx = int(args[0]) - 1
        except ValueError:
            self._log("[red]Usage: gig <n>[/]")
            return
        try:
            self.app.state = accept_gig(self.app.state, idx)
            from game.save import save_game
            save_game(self.app.state)
            self._refresh_pin_panel()
            if self._open_target == "gigs":
                self._render_open_panel()
            self._log("[#00ff41]Gig completed! Check event log for payout.[/]")
        except ValueError as e:
            self._log(f"[red]{e}[/]")

    def _cmd_buyhw(self, args: list[str]) -> None:
        from game.datacenter import buy_component
        if len(args) != 1:
            self._log("[red]Usage: buyhw <hw_id>  (see hw_id column in store panel)[/]")
            return
        try:
            self.app.state = buy_component(self.app.state, args[0])
            from game.save import save_game
            save_game(self.app.state)
            self._refresh_pin_panel()
            if self._open_target in ("store", "servers"):
                self._render_open_panel()
            self._log(f"[#00ff41]Purchased {args[0]}. Check inventory with: view inventory[/]")
        except ValueError as e:
            self._log(f"[red]{e}[/]")

    def _cmd_assemble(self, args: list[str]) -> None:
        from game.datacenter import assemble_server, _find_hardware
        if len(args) < 5:
            self._log("[red]Usage: assemble <name> <cpu_id> <ram_id> <storage_id> <nic_id>  (more ram/storage ok)[/]")
            return
        name = args[0]
        hw_ids = args[1:]
        cpu_ids, ram_ids, stor_ids, nic_ids = [], [], [], []
        for hw_id in hw_ids:
            if hw_id.startswith("cpu_"):
                cpu_ids.append(hw_id)
            elif hw_id.startswith("ram_"):
                ram_ids.append(hw_id)
            elif hw_id.startswith("hdd_") or hw_id.startswith("ssd_"):
                stor_ids.append(hw_id)
            elif hw_id.startswith("nic_"):
                nic_ids.append(hw_id)
            else:
                self._log(f"[red]Unknown component type for '{hw_id}'. IDs must start with cpu_/ram_/hdd_/ssd_/nic_[/]")
                return
        if len(cpu_ids) != 1:
            self._log("[red]Need exactly 1 CPU (cpu_budget / cpu_mid / cpu_pro / cpu_enterprise)[/]")
            return
        if not ram_ids:
            self._log("[red]Need at least 1 RAM stick[/]")
            return
        if not stor_ids:
            self._log("[red]Need at least 1 storage drive[/]")
            return
        if len(nic_ids) != 1:
            self._log("[red]Need exactly 1 NIC (nic_1g / nic_10g)[/]")
            return
        s = self.app.state
        used: set = set()
        def claim(hw_id):
            hw = _find_hardware(hw_id)
            for c in s.hardware_inventory:
                c_name = c.get("name") if isinstance(c, dict) else c.name
                c_id = c.get("id") if isinstance(c, dict) else c.id
                if c_name == hw["name"] and c_id not in used:
                    used.add(c_id)
                    return c_id
            return None
        try:
            cpu_inst = claim(cpu_ids[0])
            ram_insts = [claim(r) for r in ram_ids]
            stor_insts = [claim(r) for r in stor_ids]
            nic_inst = claim(nic_ids[0])
        except ValueError as e:
            self._log(f"[red]{e}[/]")
            return
        missing = []
        if cpu_inst is None:
            missing.append(cpu_ids[0])
        for i, r in enumerate(ram_insts):
            if r is None:
                missing.append(ram_ids[i])
        for i, r in enumerate(stor_insts):
            if r is None:
                missing.append(stor_ids[i])
        if nic_inst is None:
            missing.append(nic_ids[0])
        if missing:
            self._log(f"[red]Not in inventory: {', '.join(missing)}[/]")
            return
        try:
            self.app.state, server = assemble_server(s, name, cpu_inst, ram_insts, stor_insts, nic_inst)
            cores = server.total_cores if hasattr(server, "total_cores") else server.get("total_cores", 0)
            ram = server.total_ram_gb if hasattr(server, "total_ram_gb") else server.get("total_ram_gb", 0)
            stor = server.total_storage_gb if hasattr(server, "total_storage_gb") else server.get("total_storage_gb", 0)
            from game.save import save_game
            save_game(self.app.state)
            self._refresh_pin_panel()
            if self._open_target in ("store", "servers"):
                self._render_open_panel()
            self._log(f"[#00ff41]Built '{name}': {cores} cores / {ram}GB RAM / {stor}GB storage. Install with: install <server_id> <rack_id>[/]")
        except ValueError as e:
            self._log(f"[red]{e}[/]")

    def _cmd_install(self, args: list[str]) -> None:
        from game.datacenter import install_server_in_rack
        if len(args) < 2:
            self._log("[red]Usage: install <server_id> <rack_id>[/]")
            return
        server_id_prefix = args[0]
        rack_id_prefix = args[1]
        s = self.app.state
        server = next(
            (sv for sv in s.servers
             if (sv.get("id", "") if isinstance(sv, dict) else sv.id).startswith(server_id_prefix)),
            None
        )
        if server is None:
            self._log(f"[red]No server with ID starting '{server_id_prefix}'[/]")
            return
        rack = next(
            (r for r in s.racks
             if (r.get("id", "") if isinstance(r, dict) else r.id).startswith(rack_id_prefix)),
            None
        )
        if rack is None:
            self._log(f"[red]No rack with ID starting '{rack_id_prefix}'[/]")
            return
        server_name = server.get("name", server_id_prefix) if isinstance(server, dict) else getattr(server, "name", server_id_prefix)
        rack_name = rack.get("name", rack_id_prefix) if isinstance(rack, dict) else getattr(rack, "name", rack_id_prefix)
        rack_idx = s.racks.index(rack)
        try:
            self.app.state = install_server_in_rack(self.app.state, server_name, rack_idx)
            from game.save import save_game
            save_game(self.app.state)
            self._refresh_pin_panel()
            if self._open_target in ("servers", "racks"):
                self._render_open_panel()
            self._log(f"[#00ff41]Installed '{server_name}' in {rack_name}.[/]")
        except ValueError as e:
            self._log(f"[red]{e}[/]")

    def _cmd_repair(self, args: list[str]) -> None:
        from game.datacenter import repair_server
        if not args:
            self._log("[red]Usage: repair <server_id>[/]")
            return
        server_id_prefix = args[0]
        s = self.app.state
        server = next(
            (sv for sv in s.servers
             if (sv.get("id", "") if isinstance(sv, dict) else sv.id).startswith(server_id_prefix)),
            None
        )
        if server is None:
            self._log(f"[red]No server with ID starting '{server_id_prefix}'[/]")
            return
        server_name = server.get("name", server_id_prefix) if isinstance(server, dict) else getattr(server, "name", server_id_prefix)
        try:
            self.app.state = repair_server(self.app.state, server_name)
            from game.save import save_game
            save_game(self.app.state)
            self._refresh_pin_panel()
            if self._open_target in ("servers", "racks"):
                self._render_open_panel()
            self._log(f"[#00ff41]Repaired '{server_name}' to 100% health. (-$500)[/]")
        except ValueError as e:
            self._log(f"[red]{e}[/]")

    def _cmd_rent(self, args: list[str]) -> None:
        from game.datacenter import rent_rack
        try:
            self.app.state = rent_rack(self.app.state)
            rack = self.app.state.racks[-1]
            rent = rack.monthly_rent if hasattr(rack, "monthly_rent") else rack.get("monthly_rent", 800)
            from game.save import save_game
            save_game(self.app.state)
            self._refresh_pin_panel()
            if self._open_target == "racks":
                self._render_open_panel()
            self._log(f"[#00ff41]Rented a new rack (${rent:,.0f}/mo). You now have {len(self.app.state.racks)} racks.[/]")
        except ValueError as e:
            self._log(f"[red]{e}[/]")
