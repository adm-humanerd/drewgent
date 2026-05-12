# Drewgent Changelog

All notable changes to Drewgent Agent are documented here.

---

## [0.7.1] — 2026-05-12

### Brain Upgrade — Karpathy Coding Principles

#### What changed

Drewgent's brain now enforces **Andrej Karpathy's 4 coding principles** at the P0 brainstem level — the highest priority layer, overriding all other rules.

#### Why

Drewgent was repeating common LLM coding mistakes: wrong assumptions as facts, overcomplicated code, surgical violations, and no verifiable success criteria. The brain needed enforcement teeth at the P0 level to catch these before they become user-visible bugs.

#### Files changed

| File | Change | Location |
|------|--------|----------|
| `~/.drewgent/SOUL.md` | Rewritten with Karpathy 4 principles (primary identity) | Drewgent home |
| `~/.drewgent/P1-limbic/persona/SOUL.md` | Same content (P1 fallback) | P1-limbic layer |
| `~/.drewgent/AGENTS.md` | Created from writing-style-guide.md + expanded with coding guidelines | Drewgent home project context |
| `~/.drewgent/brain/Drewgent-brain/P0-brainstem/禁karpathy_coding_principles.neuron` | **NEW** — P0 brainstem enforcement rule | Brain filesystem |

#### Cross-reference chain (organic brain system)

```
SOUL.md     → links: [P0-brainstem/禁, P1-limbic/persona/writing-style-guide.md]
AGENTS.md   → links: [SOUL.md, P0-brainstem/禁]
Neuron      → P0-brainstem/禁karpathy_coding_principles.neuron (located in P0-brainstem)
System prompt layers:
  Layer 1: load_soul_md()        → SOUL.md
  Layer 3: brain_load()          → P0-brainstem neurons (including neuron above)
  Layer 7: build_context_files_prompt() → AGENTS.md

Result: SOUL.md ↔ P0-brainstem ↔ AGENTS.md — circular organic reference chain
```

#### Verification (2026-05-12)

```
Active brain: Drewgent-brain
P0-brainstem neurons: 10 (禁karpathy_coding_principles included ✅)
brain_load(): returns brain content with neuron ✅
_load_agents_md(drew_home): returns AGENTS.md with Karpathy principles ✅
load_soul_md(): returns SOUL.md with 4 principles ✅
```

#### The 4 Karpathy Principles

1. **Think Before Coding** — State assumptions explicitly. Ask when uncertain. Stop when confused.
2. **Simplicity First** — Minimum code that solves the problem. Nothing speculative.
3. **Surgical Changes** — Touch only what you must. Don't refactor adjacent code.
4. **Goal-Driven Execution** — Define success criteria. Write tests first. Loop until verified.

#### Enforcement mechanism

```
User asks "fix the bug"
    → Agent must write test that reproduces it first
    → Then make it pass

User asks "add validation"
    → Agent must write tests for invalid inputs
    → Then make them pass

Multi-step task
    → State plan: "1. [step] → verify: [check]"
    → Each step verifiable independently
```

#### Brain scan verification

```
Active brain: Drewgent-brain
P0-brainstem neurons: 10 total
  - 禁tool_integration_3file
  - 禁rm_rf_root
  - 禁blind_write
  - 禁task_qa_gate
  - 禁secrets_in_code
  - 禁auto_validate
  - 禁console_log
  - 禁karpathy_coding_principles ✨ NEW
  - 禁subagent_verify
  - 禁filesystem_truth
```

#### Related components (unchanged, verified working)

- `agent/prompt_builder.py` — SOUL.md loading (primary: ~/.drewgent/SOUL.md, fallback: P1-limbic/persona/)
- `agent/prompt_builder.py` — AGENTS.md loading via `_load_agents_md(drew_home)`
- `drewgent_cli/brain_manager.py` — scan_brain/emit_brain for neuron filesystem
- `docs/DREWGENT_ARCHITECTURE.md` — brain system documentation (Version 1.0, 2026-04-15)

---

## [0.7.0] — 2026-04-03

### Initial release with NeuronFS brain governance

- 7-layer subsumption (P0-P6)
- Brain filesystem with `.neuron` files
- `禁` (forbidden) micro-opcode pattern
- `vorq` (value-or-lookup) harness for unknown governance tokens
- Discord gateway integration
- Skill/agent architecture