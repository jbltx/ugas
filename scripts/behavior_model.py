"""Small executable contract models for §8.8, §9.5.1 and §13.8.

These intentionally model observable transitions, not an engine or transport. Time and
server checkpoints are injected. No expected fixture values are computed here.
"""
from __future__ import annotations

from copy import deepcopy
import math

MASK32 = (1 << 32) - 1
MASK64 = (1 << 64) - 1


def require(condition, message):
    if not condition:
        raise ValueError(message)


class RNG:
    def __init__(self, seed="42", sub=54):
        require(isinstance(seed, str) and seed.isdecimal(), "seed must be unsigned decimal text")
        require(0 <= int(seed) <= MASK64 and 0 <= sub < 65535, "seed/sub out of range")
        self.state = 0
        self.increment = (sub << 1) | 1
        self.draws = 0
        self._step()
        self.state = (self.state + int(seed)) & MASK64
        self._step()
        self.saved = {}
        self.output = []

    def _step(self):
        old = self.state
        self.state = (old * 6364136223846793005 + self.increment) & MASK64
        word = (((old >> 18) ^ old) >> 27) & MASK32
        rotation = old >> 59
        return ((word >> rotation) | (word << ((-rotation) & 31))) & MASK32

    def raw(self):
        self.draws += 1
        return self._step()

    def next(self, kind="raw", minimum=0, maximum=1):
        require(kind in {"raw", "float", "int"}, "unknown RNG operation")
        if kind == "int":
            require(-(1 << 31) <= minimum < maximum <= (1 << 31), "invalid integer range")
            span = maximum - minimum
            threshold = (1 << 32) % span
            # Explicit work limit: fail instead of substituting a biased modulo sample.
            for _ in range(128):
                word = self.raw()
                if word >= threshold:
                    value = minimum + word % span
                    break
            else:
                raise ValueError("RNG work budget exhausted")
        else:
            word = self.raw()
            value = word if kind == "raw" else (word >> 8) / (1 << 24)
        self.output.append(value)

    def save(self, name):
        self.saved[name] = (self.state, self.increment, self.draws)

    def restore(self, name):
        require(name in self.saved, "unknown RNG checkpoint")
        self.state, self.increment, self.draws = self.saved[name]

    def observe(self):
        return {"output": self.output[:], "draws": self.draws,
                "state": str(self.state), "increment": str(self.increment)}


class AsyncActivation:
    def __init__(self, mana=100, default_timeout=5000, max_requests=64):
        require(default_timeout > 0 and math.isfinite(default_timeout), "invalid default timeout")
        self.mana = mana
        self.default_timeout = default_timeout
        self.max_requests = max_requests
        self.now = 0
        self.granted = True
        self.blocked = False
        self.commit_fails = False
        self.attempts = {}
        self.current = {}
        self.commits = []
        self.cooldowns = set()
        self.tags = set()
        self.trace = []

    def start(self, id, ability="Spell", cost=10, timeout=None):
        deadline = self.default_timeout if timeout is None else timeout
        require(deadline > 0 and math.isfinite(deadline), "invalid timeout")
        if id in self.attempts:  # logical request retransmit
            old = self.attempts[id]
            require((old["ability"], old["cost"], old["timeout"]) == (ability, cost, deadline),
                    "request identity reused with different payload")
            return
        require(len(self.attempts) < self.max_requests, "request budget exhausted")
        attempt = {"ability": ability, "cost": cost, "deadline": self.now + deadline,
                   "timeout": deadline, "phase": "pending", "outcome": None}
        self.attempts[id] = attempt
        conflict = ability in self.current or ability in self.cooldowns
        if conflict or not self.granted or self.blocked or self.mana < cost:
            attempt.update(phase="ended", outcome="Rejected")
            self.trace.append("rejected:" + id)
            return
        self.current[ability] = id
        self.trace.append("pending:" + id)

    def _terminal(self, id, outcome):
        a = self.attempts[id]
        a["outcome"] = outcome
        a["phase"] = "active" if outcome == "Accepted" else "ended"
        if outcome != "Accepted":
            self.current.pop(a["ability"], None)
        self.trace.append(outcome.lower() + ":" + id)

    def resolve(self, id, ok=True):
        a = self.attempts.get(id)
        if not a or a["phase"] != "pending":
            return
        valid = (ok and self.now < a["deadline"] and self.granted and not self.blocked
                 and self.mana >= a["cost"] and a["ability"] not in self.cooldowns
                 and not self.commit_fails)
        if not valid:
            self._terminal(id, "Rejected")
            return
        # One mutation turn, with no callbacks between check, spend and terminalization.
        self.mana -= a["cost"]
        self.commits.append(id)
        self.cooldowns.add(a["ability"])
        self.tags.add(id)
        self._terminal(id, "Accepted")

    def cancel(self, id):
        a = self.attempts.get(id)
        if not a or a["phase"] == "ended":
            return
        if a["phase"] == "pending":
            self._terminal(id, "Cancelled")
        else:
            a["phase"] = "ended"
            self.tags.discard(id)
            self.current.pop(a["ability"], None)
            self.trace.append("ended:" + id)  # committed cost/cooldown remain

    def advance(self, milliseconds, fire_timers=True):
        require(milliseconds >= 0, "time cannot move backwards")
        self.now += milliseconds
        if fire_timers:
            for id, a in list(self.attempts.items()):
                if a["phase"] == "pending" and self.now >= a["deadline"]:
                    self.resolve(id, False)

    def change(self, mana=None, blocked=None, granted=None, commit_fails=None):
        if mana is not None:
            self.mana = mana
        if blocked is not None:
            self.blocked = blocked
        if commit_fails is not None:
            self.commit_fails = commit_fails
        if granted is not None:
            self.granted = granted
            if not granted:
                for id in list(self.attempts):
                    self.cancel(id)

    def observe(self):
        return {"mana": self.mana, "now": self.now, "commits": self.commits[:],
                "pending": sorted(k for k, a in self.attempts.items() if a["phase"] == "pending"),
                "active": sorted(k for k, a in self.attempts.items() if a["phase"] == "active"),
                "terminal": {k: a["outcome"] for k, a in self.attempts.items() if a["outcome"]},
                "cooldowns": sorted(self.cooldowns), "tags": sorted(self.tags), "trace": self.trace[:]}


class Prediction:
    def __init__(self, mana=100, max_millis=250, max_frames=16, max_actions=8,
                 max_requests=64, epoch=1, owner="player", period_ms=0, tick_mana=0):
        require(min(max_millis, max_frames, max_actions, max_requests) > 0, "invalid prediction limits")
        self.baseline = {"mana": mana, "cooldowns": [], "tags": [], "effects": []}
        self.period_ms, self.tick_mana = period_ms, tick_mana
        if period_ms:
            self.baseline["period"] = {"elapsed": 0, "count": 0}
        self.state = deepcopy(self.baseline)
        self.max_millis, self.max_frames = max_millis, max_frames
        self.max_actions, self.max_requests = max_actions, max_requests
        self.epoch, self.owner = epoch, owner
        self.now = self.frame = self.revision = self.watermark = 0
        self.requests = {}
        self.terminal = {}
        self.journal = []
        self.overlays = set()
        self.presentation_retired = set()
        self.trace = []
        self.ready = True
        self.next_base = 1
        self.frame_actions = 0
        self.window_start = None

    def _apply(self, request, replay=False, subs=None):
        allowed = set(subs) if subs is not None else {n["sub"] for n in request["nodes"]}
        applied = []
        for node in request["nodes"]:
            if node["sub"] not in allowed:
                continue
            label = f'{request["base"]}:{node["sub"]}'
            if ((node["parent"] is not None and node["parent"] not in applied)
                    or self.state["mana"] < node["cost"]):
                self.trace.append("ineligible:" + label)
                continue
            self.state["mana"] -= node["cost"]
            self.state["cooldowns"].append(label)
            self.state["tags"].append(label)
            applied.append(node["sub"])
            if node.get("target") and not node.get("authority_only") and label not in self.presentation_retired:
                self.overlays.add(label)
        self.trace.append(("replay:" if replay else "predict:") + str(request["base"]))
        return applied

    def _record(self, action):
        if not self.journal or self.journal[-1]["frame"] != self.frame:
            self.journal.append({"time": self.now, "frame": self.frame, "actions": []})
        self.journal[-1]["actions"].append(action)

    def _tick(self, milliseconds):
        if self.period_ms:
            period = self.state["period"]
            total = period["elapsed"] + milliseconds
            count, period["elapsed"] = divmod(total, self.period_ms)
            period["count"] += count
            self.state["mana"] += count * self.tick_mana

    def submit(self, base, nodes, predictable=True, local_failure=False, late_nonpredictable=False):
        payload = {"base": base, "nodes": deepcopy(nodes), "predictable": predictable,
                   "local_failure": local_failure, "late_nonpredictable": late_nonpredictable}
        if base <= self.watermark:
            return  # retired identity; cannot execute again
        if base in self.requests:
            require(self.requests[base]["payload"] == payload, "request identity reused with different payload")
            return
        require(base == self.next_base and base <= MASK32, "invalid or exhausted Base")
        require(len(self.requests) < self.max_requests, "request budget exhausted")
        seen = set()
        for i, node in enumerate(nodes):
            sub, parent = node["sub"], node["parent"]
            require(sub == i and sub < 65535, "invalid Sub allocation")
            require(parent is None if i == 0 else parent in seen, "invalid parent")
            seen.add(sub)
        self.next_base += 1
        request = {**payload, "payload": payload, "time": self.now, "frame": self.frame}
        self.requests[base] = request
        self.trace.append("send:" + str(base))
        eligible = (self.ready and predictable and self.frame_actions + len(nodes) <= self.max_actions)
        if not eligible:
            self.trace.append("authority:" + str(base))
            return
        self.frame_actions += len(nodes)
        before = deepcopy(self.state)
        overlays = self.overlays.copy()
        subs = self._apply(request)
        if local_failure or late_nonpredictable:
            self.state = before
            self.overlays = overlays
            self.trace.append("unwind:" + str(base))
            return
        if not subs:
            return  # The original authoritative request remains outstanding.
        if self.window_start is None:
            self.window_start = (self.now, self.frame)
        self._record({"kind": "request", "request": request, "subs": subs})

    def _discard(self, reason):
        self.state = deepcopy(self.baseline)
        self.overlays.clear()
        self.journal.clear()
        self.window_start = None
        self.ready = False
        self.trace.append(reason)

    def advance(self, milliseconds, frames=1, simulation_ms=None):
        require(milliseconds >= 0 and frames >= 0, "time cannot move backwards")
        require(frames > 0 or simulation_ms in (None, 0), "simulation time requires frame progress")
        self.now += milliseconds
        self.frame += frames
        if frames:
            self.frame_actions = 0
        if self.journal:
            start_time, start_frame = self.window_start
            if self.now - start_time >= self.max_millis or self.frame - start_frame >= self.max_frames:
                self._discard("expired")
            elif frames:
                # A clock-only check can expire prediction but never simulates or records
                # another substep. Each new frame contributes at most one timer record.
                delta = milliseconds if simulation_ms is None else simulation_ms
                self._tick(delta)
                self._record({"kind": "tick", "milliseconds": delta})

    def receipt(self, base):
        require(base in self.requests, "unknown request")
        # Deliberately does not free journal/identity or advance terminal watermark.

    def cancel(self, base):
        if base not in self.requests:
            return
        for n in self.requests[base]["nodes"]:
            label = f'{base}:{n["sub"]}'
            self.presentation_retired.add(label)
            self.overlays.discard(label)
        self.trace.append("cancel:" + str(base))
        # Client intent is distinct from the server's eventual terminal outcome.

    def update(self, revision, state, outcomes, resolved_through=0, included=None,
               complete_history=True, epoch=None, owner=None, checkpoint_frame=0):
        if ((epoch is not None and epoch != self.epoch) or
                (owner is not None and owner != self.owner) or revision <= self.revision):
            return
        try:
            require(resolved_through >= self.watermark, "decreasing resolution watermark")
            require(resolved_through < self.next_base, "resolution watermark exceeds allocated inputs")
            resolved = set()
            for group in outcomes:
                base = group["base"]
                if base <= self.watermark:
                    continue  # repeated outcome for an already retired request
                require(base not in resolved and base in self.requests, "unknown or duplicate outcome group")
                nodes = self.requests[base]["nodes"]
                accepted = group["accepted"]
                require(len(accepted) == len(nodes), "partial group outcome")
                for n, ok in zip(nodes, accepted):
                    require(not ok or n["parent"] is None or accepted[n["parent"]], "accepted descendant of rejected parent")
                require(base not in self.terminal or self.terminal[base] == accepted,
                        "terminal outcome changed")
                resolved.add(base)
            require(all(base in resolved or base in self.terminal for base in self.requests if base <= resolved_through),
                    "watermark crossed pending input")
        except ValueError:
            self._discard("resync")
            raise
        self.revision, self.watermark = revision, resolved_through
        self.baseline = deepcopy(state)
        self.state = deepcopy(state)
        self.overlays.clear()
        # Outcomes identify executions already incorporated, even past the watermark.
        incorporated = set(included or []) | resolved
        suffix = []
        for record in self.journal:
            actions = [a for a in record["actions"]
                       if (a["kind"] == "request" and a["request"]["base"] not in incorporated)
                       or (a["kind"] == "tick" and record["frame"] > checkpoint_frame)]
            if actions:
                suffix.append({**record, "actions": actions})
        self.journal = suffix
        if not suffix:
            self.window_start = None
        for group in outcomes:
            if group["base"] in self.requests:
                self.terminal[group["base"]] = group["accepted"][:]
        for base in list(self.requests):
            if base <= resolved_through:
                retired = self.requests.pop(base)
                self.terminal.pop(base, None)
                self.presentation_retired.difference_update(
                    f'{base}:{node["sub"]}' for node in retired["nodes"])
        if not complete_history or (not self.ready and suffix):
            self._discard("resync")
            return
        self.ready = True
        replayed = []
        for record in suffix:
            actions = []
            for action in record["actions"]:
                if action["kind"] == "request":
                    subs = self._apply(action["request"], replay=True, subs=action["subs"])
                    if subs:
                        actions.append({**action, "subs": subs})
                else:
                    self._tick(action["milliseconds"])
                    self.trace.append("replay-step:" + str(record["frame"]))
                    actions.append(action)
            if actions:
                replayed.append({**record, "actions": actions})
        self.journal = replayed
        if not replayed:
            self.window_start = None
        self.trace.append("update:" + str(revision))

    def reconnect(self, epoch, owner="player"):
        require(epoch != self.epoch, "epoch must change")
        self.epoch, self.owner = epoch, owner
        self.requests.clear()
        self.terminal.clear()
        self.presentation_retired.clear()
        self.revision = self.watermark = 0
        self.next_base = 1
        self._discard("reconnect")

    def observe(self):
        return {"state": deepcopy(self.state), "overlays": sorted(self.overlays),
                "pending": sorted(set(self.requests) - set(self.terminal)), "journal": [a["request"]["base"] for r in self.journal for a in r["actions"] if a["kind"] == "request"],
                "history_frames": len(self.journal),
                "ready": self.ready, "revision": self.revision, "watermark": self.watermark,
                "epoch": self.epoch, "trace": self.trace[:]}


MODELS = {"rng": RNG, "async": AsyncActivation, "prediction": Prediction}
