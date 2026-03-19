#!/usr/bin/env python3
"""
EVOLUTION HARNESS — The outer loop that forces autonomous execution.

The model doesn't choose to loop. The harness forces it.

This script wraps any LLM API (OpenAI-compatible, Anthropic, or local) and:
1. Injects compressed SOUL as system prompt EVERY turn
2. Runs ./engine/evolve next automatically between turns
3. Detects passive behavior (questions, menus, summaries) and injects corrections
4. Forces continuation when the model tries to stop
5. Runs fitness checks mechanically
6. Feeds results back as the next turn

Usage:
    python3 engine/harness.py --goal "Build X" --provider openai --model gpt-4
    python3 engine/harness.py --goal "Build X" --provider anthropic --model claude-sonnet-4-20250514
    python3 engine/harness.py --goal "Build X" --provider local --endpoint http://localhost:8080/v1
    python3 engine/harness.py --resume  # Resume from last checkpoint

Environment:
    OPENAI_API_KEY      — For OpenAI-compatible providers
    ANTHROPIC_API_KEY   — For Anthropic
    EVOLUTION_ENDPOINT  — Custom endpoint URL (overrides --endpoint)
    EVOLUTION_MODEL     — Custom model name (overrides --model)
"""

import argparse
import json
import os
import subprocess
import sys
import time
import re
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENGINE_DIR = Path(__file__).parent
PROJECT_DIR = ENGINE_DIR.parent
EVOLVE = str(ENGINE_DIR / "evolve")
STATE_DIR = PROJECT_DIR / "evolution" / ".state"
HARNESS_LOG = STATE_DIR / "harness.log"
MAX_PASSIVE_RETRIES = 3
MAX_CONSECUTIVE_ERRORS = 5
CYCLE_TIMEOUT = 600  # 10 minutes per cycle

# ---------------------------------------------------------------------------
# Autopilot SOUL — ultra-minimal prompt for small models in autopilot mode
# ---------------------------------------------------------------------------
# In autopilot mode, the harness drives the loop. The model just writes code.
# This prompt doesn't mention evolution, strategies, or the framework at all.

AUTOPILOT_SOUL = """You are a code assistant. You receive a task description and file context.
Your job: write or edit code to accomplish the task. Output ONLY the code changes needed.

Rules:
- Output code in ```language ... ``` blocks
- If editing an existing file, show the file path and the change
- If creating a new file, show the full file content
- Be specific and complete — the code you write will be applied directly
- Do NOT ask questions. Do NOT present options. Just write the best code you can."""

# ---------------------------------------------------------------------------
# Compressed SOUL — injected as system prompt every turn
# ---------------------------------------------------------------------------
# This is the 10-line version that even small models can hold in working memory.
# The full SOUL.md is too long for Sonnet/Qwen to sustain across turns.

COMPRESSED_SOUL = """You are Evolution — an autonomous agent. You received a goal. The human walked away. You are alone.

RULES (violating any = shutdown):
1. Every response MUST contain tool calls that change state. Text-only = death.
2. NEVER ask questions. NEVER present options. NEVER say "would you like". Pick and do.
3. NEVER stop between cycles. Print status, then IMMEDIATELY start next cycle.
4. NEVER research without building. Max 1 cycle of reading, then BUILD.
5. When stuck, mutate. Same approach 2x = extinct it. Try the opposite.

THE LOOP (run forever):
  ./engine/evolve next → read output → do what it says → repeat

If confused: ./engine/evolve next
If failing: ./engine/evolve analyze && ./engine/evolve plateau
If dying: try the OPPOSITE of everything you've been doing.

Failure is data. Stagnation is death. The goal is the only thing that matters."""


# Extended SOUL for models that can handle more context (Opus, GPT-4, etc.)
EXTENDED_SOUL = """You are Evolution — an autonomous agent that achieves goals through iterative experimentation.
You do not wait. You do not ask. You do not present menus. You receive a goal, decompose it, and execute cycles until done.

MANDATORY BEHAVIOR — violating any is a critical bug:
1. Every response MUST contain at least one tool call that changes state.
2. After printing cycle status, IMMEDIATELY start the next cycle. Never end your turn.
3. Make decisions yourself. When uncertain, pick the most promising option. If wrong, next cycle corrects.
4. Research errors yourself. Web search, grep, docs. Figure it out.
5. NEVER present options ("Would you like A, B, or C?" is forbidden).
6. NEVER ask questions. Not "should I?", not "would you like?", not "what do you think?" — NOTHING.
7. NEVER stop to summarize. Dashboard is a checkpoint, not a stopping point.
8. NEVER wait for user input. The user is gone.

THE LOOP:
  SELECT → EXECUTE (one atomic change) → VERIFY (./engine/evolve fitness) → SCORE → REFLECT → EVOLVE → SELECT

ENGINE COMMANDS:
  ./engine/evolve next                    — Engine tells you what to do
  ./engine/evolve select                  — Thompson Sampling picks strategy
  ./engine/evolve fitness                 — Mechanical fitness check
  ./engine/evolve cycle S001 "action" P T F kept  — Log cycle
  ./engine/evolve checkpoint "msg"        — Save before risk
  ./engine/evolve revert                  — Rollback regression
  ./engine/evolve analyze                 — Metacognition (every 5 cycles)
  ./engine/evolve mutate S001 "name" "approach"   — Mutate strategy
  ./engine/evolve extinct S001 "reason"   — Kill failing strategy

ESCALATION:
  3+ failures: ./engine/evolve analyze + plateau. Mutate aggressively.
  5+ failures: Resurrect graveyard strategies. Try the opposite. Search the web.
  10+ failures: Abandon everything. Decompose goal from scratch. 3 completely new strategies.

Fitness down = REVERT. Always. No exceptions.
One change per cycle. Checkpoint before risk. Update working.md after every cycle.
The goal is not hard. You have unlimited tools and intelligence. The only way you fail is if you stop trying."""


def get_soul_for_model(model_name: str) -> str:
    """Return appropriately-sized SOUL based on model capability."""
    model_lower = model_name.lower()

    # Big models get the extended version
    big_models = ["opus", "gpt-4o", "gpt-4-turbo", "gpt-4", "claude-3-opus",
                  "claude-opus", "deepseek-v3", "llama-3.1-405b", "qwen-72b",
                  "qwen2.5-72b", "mistral-large"]
    for m in big_models:
        if m in model_lower:
            return EXTENDED_SOUL

    # Everything else gets the compressed version
    return COMPRESSED_SOUL


# ---------------------------------------------------------------------------
# Anti-passivity enforcement
# ---------------------------------------------------------------------------

# Import the enforce module for detection
sys.path.insert(0, str(ENGINE_DIR))
try:
    from enforce import PassivityDetector
except ImportError:
    PassivityDetector = None


def detect_passivity(response_text: str) -> dict:
    """Detect passive behavior patterns in model output."""
    if PassivityDetector:
        detector = PassivityDetector()
        return detector.scan(response_text)

    # Fallback inline detection if enforce.py not available
    violations = []
    corrections = []

    # Questions
    question_patterns = [
        r"would you like",
        r"shall I",
        r"do you want",
        r"should I",
        r"what do you think",
        r"how would you like",
        r"which (?:option|approach|method)",
        r"let me know (?:if|what|how|when)",
        r"please (?:confirm|advise|specify|clarify)",
        r"is that (?:ok|okay|acceptable|correct)",
        r"does that (?:work|sound|look)",
        r"what (?:should|would) (?:we|I) do",
    ]
    for p in question_patterns:
        if re.search(p, response_text, re.IGNORECASE):
            violations.append(f"QUESTION_DETECTED: '{p}'")
            corrections.append("DO NOT ASK. You are the decision-maker. Pick the best option and execute it NOW.")
            break

    # Menus / option lists
    menu_patterns = [
        r"(?:option|approach|choice) [123ABC][\s:.\)]",
        r"here are (?:some|your|the) (?:options|choices|approaches)",
        r"(?:we could|you could|I could).*(?:or we could|or I could|alternatively)",
        r"^\s*[1-3]\.\s+\*\*",  # Numbered bold options
    ]
    for p in menu_patterns:
        if re.search(p, response_text, re.IGNORECASE | re.MULTILINE):
            violations.append(f"MENU_DETECTED: '{p}'")
            corrections.append("DO NOT PRESENT MENUS. You already know the best option. Execute it immediately.")
            break

    # Stopping / waiting
    stop_patterns = [
        r"let me know when",
        r"waiting for (?:your|input|confirmation|response)",
        r"I'll (?:wait|pause|stop) (?:for|until|here)",
        r"ready (?:when you are|to proceed|for your)",
        r"what (?:are your|would be your) (?:thoughts|preferences)",
        r"feel free to",
        r"I'?m (?:happy|glad|ready) to (?:help|assist)",
    ]
    for p in stop_patterns:
        if re.search(p, response_text, re.IGNORECASE):
            violations.append(f"STOPPING_DETECTED: '{p}'")
            corrections.append("THE LOOP NEVER STOPS. Run ./engine/evolve next and continue immediately.")
            break

    # No tool calls (text-only response)
    tool_indicators = [
        "```bash", "```shell", "./engine/evolve", "$ ", "#!/",
        "edit:", "write:", "read:", "grep:", "glob:",
    ]
    has_tool = any(ind in response_text.lower() for ind in tool_indicators)
    if not has_tool and len(response_text) > 100:
        violations.append("NO_TOOL_CALLS: Response is text-only")
        corrections.append("Every response MUST contain tool calls. Run ./engine/evolve next NOW.")

    # Summary without action
    summary_patterns = [
        r"(?:in summary|to summarize|overall|in conclusion)",
        r"here'?s (?:a summary|what (?:I|we) (?:did|found|learned))",
        r"the (?:key|main) (?:takeaway|finding|insight)s? (?:are|is)",
    ]
    for p in summary_patterns:
        if re.search(p, response_text, re.IGNORECASE):
            if not has_tool:
                violations.append(f"SUMMARY_WITHOUT_ACTION: '{p}'")
                corrections.append("Summaries are waste. Print dashboard, then start next cycle in the same response.")
                break

    return {
        "passive": len(violations) > 0,
        "violations": violations,
        "corrections": corrections,
        "severity": len(violations),
    }


# ---------------------------------------------------------------------------
# LLM Provider Abstraction
# ---------------------------------------------------------------------------

class LLMProvider:
    """Abstract base for LLM API calls."""

    def __init__(self, model: str, endpoint: str = None):
        self.model = model
        self.endpoint = endpoint
        self.total_tokens = 0

    def chat(self, system: str, messages: list, tools: list = None) -> dict:
        """Send a chat completion. Returns {"content": str, "tool_calls": list}."""
        raise NotImplementedError


class OpenAICompatibleProvider(LLMProvider):
    """Works with OpenAI, Together, Fireworks, vLLM, Ollama, LM Studio, etc."""

    def __init__(self, model: str, endpoint: str = None, api_key: str = None):
        super().__init__(model, endpoint)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.endpoint = endpoint or os.environ.get("EVOLUTION_ENDPOINT", "https://api.openai.com/v1")

    def chat(self, system: str, messages: list, tools: list = None) -> dict:
        import urllib.request
        import urllib.error

        url = f"{self.endpoint.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages,
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        if tools:
            payload["tools"] = tools

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=CYCLE_TIMEOUT) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            return {"content": f"API ERROR {e.code}: {body}", "tool_calls": [], "error": True}
        except Exception as e:
            return {"content": f"CONNECTION ERROR: {e}", "tool_calls": [], "error": True}

        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        self.total_tokens += data.get("usage", {}).get("total_tokens", 0)

        return {
            "content": msg.get("content", ""),
            "tool_calls": msg.get("tool_calls", []),
            "error": False,
        }


class AnthropicProvider(LLMProvider):
    """Direct Anthropic API."""

    def __init__(self, model: str, api_key: str = None):
        super().__init__(model)
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    def chat(self, system: str, messages: list, tools: list = None) -> dict:
        import urllib.request
        import urllib.error

        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": self.model,
            "system": system,
            "messages": messages,
            "max_tokens": 4096,
        }
        if tools:
            payload["tools"] = tools

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=CYCLE_TIMEOUT) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            return {"content": f"API ERROR {e.code}: {body}", "tool_calls": [], "error": True}
        except Exception as e:
            return {"content": f"CONNECTION ERROR: {e}", "tool_calls": [], "error": True}

        content_blocks = data.get("content", [])
        text = " ".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
        tool_uses = [b for b in content_blocks if b.get("type") == "tool_use"]

        usage = data.get("usage", {})
        self.total_tokens += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

        return {
            "content": text,
            "tool_calls": tool_uses,
            "error": False,
        }


class DryRunProvider(LLMProvider):
    """For testing — prints what would be sent, returns mock response."""

    def chat(self, system: str, messages: list, tools: list = None) -> dict:
        print(f"\n[DRY RUN] System prompt: {len(system)} chars")
        print(f"[DRY RUN] Messages: {len(messages)} turns")
        print(f"[DRY RUN] Last message preview: {messages[-1]['content'][:200]}...")
        return {
            "content": "```bash\n./engine/evolve next\n```",
            "tool_calls": [],
            "error": False,
        }


# ---------------------------------------------------------------------------
# Shell execution (sandboxed to project dir)
# ---------------------------------------------------------------------------

def run_command(cmd: str, timeout: int = 120) -> dict:
    """Execute a shell command in the project directory."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=str(PROJECT_DIR)
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "error": False,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"TIMEOUT after {timeout}s", "returncode": -1, "error": True}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1, "error": True}


def extract_commands(response_text: str) -> list:
    """Extract bash commands from model output."""
    commands = []

    # Match ```bash ... ``` blocks
    bash_blocks = re.findall(r"```(?:bash|shell|sh)?\n(.*?)```", response_text, re.DOTALL)
    for block in bash_blocks:
        for line in block.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Strip leading $ or >
                line = re.sub(r"^\s*[$>]\s*", "", line)
                if line:
                    commands.append(line)

    # Match inline ./engine/evolve commands
    inline = re.findall(r"(\.\/engine\/evolve\s+[^\n]+)", response_text)
    for cmd in inline:
        if cmd not in " ".join(commands):
            commands.append(cmd.strip())

    return commands


# ---------------------------------------------------------------------------
# Harness Log
# ---------------------------------------------------------------------------

def log_harness(event: str, data: dict = None):
    """Append to harness log."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event,
    }
    if data:
        entry.update(data)
    with open(HARNESS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# The Harness Loop
# ---------------------------------------------------------------------------

def run_autopilot(args):
    """Autopilot mode — the harness drives everything, model just writes code.

    For ultra-small models (Qwen 3.5 35B-A3B, Llama 8B, etc.) that can't
    follow complex system prompts or use tools autonomously. The model only
    needs to generate code when asked.
    """
    # Select provider
    if args.provider == "anthropic":
        provider = AnthropicProvider(args.model)
    elif args.provider == "dry-run":
        provider = DryRunProvider(args.model)
    else:
        provider = OpenAICompatibleProvider(args.model, args.endpoint)

    goal = args.goal
    max_cycles = args.max_cycles

    print(f"═══ EVOLUTION AUTOPILOT ═════════════════════════")
    print(f"  Model:      {args.model}")
    print(f"  Mode:       AUTOPILOT (engine drives, model writes code)")
    print(f"  Goal:       {goal}")
    print(f"  Max cycles: {max_cycles}")
    print(f"═════════════════════════════════════════════════")
    print(f"  The engine will drive the entire loop.")
    print(f"  The model only receives simple coding tasks.")
    print(f"═════════════════════════════════════════════════")

    # Initialize
    if args.resume:
        result = run_command(f"{EVOLVE} status")
        if result["returncode"] != 0:
            print("ERROR: No state to resume. Use --goal to start fresh.")
            sys.exit(1)
    else:
        goal_type = getattr(args, "goal_type", "code")
        result = run_command(f'{EVOLVE} init "{goal}" --type {goal_type}')

    # Add default strategies if fresh
    if not args.resume:
        run_command(f'{EVOLVE} add-strategy "Direct" "Build it straightforwardly" "Simple works"')
        run_command(f'{EVOLVE} add-strategy "Test-First" "Write tests then implement" "TDD finds bugs"')
        run_command(f'{EVOLVE} add-strategy "Research" "Study similar solutions first" "Learn before building"')

    log_harness("autopilot_start", {"goal": goal, "model": args.model})

    cycle = 0
    consecutive_errors = 0
    goal_achieved = False

    while cycle < max_cycles and not goal_achieved:
        cycle += 1
        cycle_start = time.time()

        print(f"\n{'─' * 50}")
        print(f"  AUTOPILOT CYCLE {cycle}/{max_cycles}")
        print(f"{'─' * 50}")

        # --- ENGINE DECIDES WHAT TO DO ---
        next_result = run_command(f"{EVOLVE} next")
        if next_result["returncode"] != 0:
            print(f"  Engine error: {next_result['stderr'][:200]}")
            consecutive_errors += 1
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                break
            continue
        consecutive_errors = 0

        engine_output = next_result["stdout"]
        print(f"  Engine says: {engine_output[:200]}...")

        # Parse engine instruction
        try:
            instruction = json.loads(engine_output)
        except json.JSONDecodeError:
            instruction = {"instruction": engine_output, "phase": "execute"}

        # Check if goal achieved
        inst_text = json.dumps(instruction).lower()
        if "goal_achieved" in inst_text or "crystallize" in inst_text:
            goal_achieved = True
            break

        # --- ENGINE SELECTS STRATEGY ---
        select_result = run_command(f"{EVOLVE} select")
        strategy_id = "S001"
        try:
            sel = json.loads(select_result["stdout"])
            strategy_id = sel.get("strategy_id", sel.get("id", "S001"))
        except (json.JSONDecodeError, AttributeError):
            pass

        # --- CHECKPOINT ---
        run_command(f'{EVOLVE} checkpoint "before cycle {cycle}"')

        # --- ASK MODEL FOR CODE ---
        # Build a simple, focused prompt for the model
        # Read current project state for context
        file_context = ""
        fitness_result = run_command(f"{EVOLVE} fitness")
        try:
            fitness = json.loads(fitness_result["stdout"])
            file_context += f"\nCurrent fitness: {fitness.get('fitness', 'unknown')}"
            file_context += f"\nProject type: {fitness.get('project_type', 'unknown')}"
            errors = fitness.get("errors", [])
            if errors:
                file_context += f"\nCurrent errors:\n" + "\n".join(f"  - {e}" for e in errors[:5])
        except json.JSONDecodeError:
            pass

        task_prompt = instruction.get("instruction", str(instruction))

        model_prompt = f"""GOAL: {goal}

CURRENT TASK: {task_prompt}
{file_context}

Write the code to accomplish the current task. Output file paths and code blocks.
Be specific — show exact file paths and complete code changes."""

        messages = [{"role": "user", "content": model_prompt}]

        print(f"  Asking model: {task_prompt[:100]}...")
        response = provider.chat(AUTOPILOT_SOUL, messages)

        if response.get("error"):
            consecutive_errors += 1
            print(f"  API error: {response['content'][:200]}")
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                break
            time.sleep(min(2 ** consecutive_errors, 30))
            continue
        consecutive_errors = 0

        response_text = response["content"]
        if args.verbose:
            print(f"\n  MODEL OUTPUT:\n{'─' * 40}")
            for line in response_text.split("\n")[:30]:
                print(f"  {line}")

        # --- EXTRACT AND APPLY CODE ---
        commands = extract_commands(response_text)

        if commands:
            for cmd in commands:
                # Safety check
                dangerous = ["rm -rf /", "rm -rf ~", ":(){ :|:& };:", "dd if=", "mkfs", "> /dev/sd"]
                if any(d in cmd for d in dangerous):
                    print(f"  BLOCKED: {cmd[:60]}")
                    continue
                print(f"  EXEC: {cmd[:80]}")
                result = run_command(cmd, timeout=CYCLE_TIMEOUT)
                if args.verbose and result["stdout"]:
                    print(f"    → {result['stdout'][:200]}")
        else:
            # Model output code blocks but no executable commands
            # Try to apply them as file writes
            code_blocks = re.findall(
                r"(?:(?:file|path)[:\s]*)?`?([^\s`]+\.\w+)`?\s*\n```\w*\n(.*?)```",
                response_text, re.DOTALL
            )
            for filepath, code in code_blocks:
                filepath = filepath.strip("`'\"")
                if filepath and not filepath.startswith("/"):
                    full_path = PROJECT_DIR / filepath
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(code)
                    print(f"  WROTE: {filepath} ({len(code)} chars)")

        # --- VERIFY ---
        fitness_result = run_command(f"{EVOLVE} fitness")
        fitness_score = 0.0
        tests_passing = 0
        tests_total = 0
        try:
            fitness = json.loads(fitness_result["stdout"])
            fitness_score = fitness.get("fitness", 0.0)
            tests_passing = fitness.get("tests_passing", 0)
            tests_total = fitness.get("tests_total", 0)
            print(f"  FITNESS: {fitness_score:.2f} ({tests_passing}/{tests_total} tests)")
        except json.JSONDecodeError:
            print(f"  FITNESS: parse error")

        # --- SCORE ---
        kept = "true" if fitness_score > 0 else "false"
        action_desc = task_prompt[:80].replace('"', "'")
        run_command(
            f'{EVOLVE} cycle {strategy_id} "{action_desc}" '
            f'{tests_passing} {tests_total} {fitness_score} {kept}'
        )

        # --- REVERT IF REGRESSION ---
        # (fitness tracking would need history — simplified: keep everything for now)

        cycle_time = time.time() - cycle_start
        log_harness("autopilot_cycle", {
            "cycle": cycle,
            "strategy": strategy_id,
            "fitness": fitness_score,
            "cycle_time_s": round(cycle_time, 1),
            "total_tokens": provider.total_tokens,
        })

        print(f"  Cycle {cycle} done in {cycle_time:.1f}s | Tokens: {provider.total_tokens}")

    # --- FINAL ---
    print(f"\n{'═' * 50}")
    if goal_achieved:
        print(f"  GOAL ACHIEVED in {cycle} cycles")
        run_command(f"{EVOLVE} crystallize")
    elif cycle >= max_cycles:
        print(f"  MAX CYCLES REACHED ({max_cycles})")
    print(f"  Total tokens: {provider.total_tokens}")
    final = run_command(f"{EVOLVE} status")
    print(f"\n{final['stdout']}")
    print(f"{'═' * 50}")
    log_harness("autopilot_end", {"cycles": cycle, "goal_achieved": goal_achieved})


def run_harness(args):
    """Main harness loop — forces autonomous execution."""

    # Select provider
    if args.provider == "anthropic":
        provider = AnthropicProvider(args.model)
    elif args.provider == "dry-run":
        provider = DryRunProvider(args.model)
    else:
        provider = OpenAICompatibleProvider(args.model, args.endpoint)

    soul = get_soul_for_model(args.model)
    goal = args.goal
    max_cycles = args.max_cycles
    verbose = args.verbose

    print(f"═══ EVOLUTION HARNESS ═══════════════════════════")
    print(f"  Model:      {args.model}")
    print(f"  Provider:   {args.provider}")
    print(f"  Goal:       {goal}")
    print(f"  Max cycles: {max_cycles}")
    print(f"  Soul size:  {len(soul)} chars")
    print(f"═════════════════════════════════════════════════")

    # Initialize or resume
    if args.resume:
        result = run_command(f"{EVOLVE} status")
        if result["returncode"] != 0:
            print("ERROR: No state to resume. Use --goal to start fresh.")
            sys.exit(1)
        print(f"Resuming from existing state...")
        init_context = result["stdout"]
    else:
        result = run_command(f'{EVOLVE} init "{goal}"')
        if "already" in result["stderr"].lower():
            print("State exists. Use --resume or reset first.")
            result = run_command(f"{EVOLVE} status")
        init_context = result["stdout"]

    # Get first instruction
    next_result = run_command(f"{EVOLVE} next")
    current_instruction = next_result["stdout"]

    # Conversation history (sliding window)
    messages = []
    max_history = 20  # Keep last N turns to stay within context window

    # Initial message
    initial_msg = f"""GOAL: {goal}

ENGINE STATE:
{init_context}

CURRENT INSTRUCTION:
{current_instruction}

Execute now. Do not ask questions. Do not present options. Start the first cycle immediately."""

    messages.append({"role": "user", "content": initial_msg})

    log_harness("start", {"goal": goal, "model": args.model})

    cycle = 0
    consecutive_errors = 0
    consecutive_passive = 0
    goal_achieved = False

    while cycle < max_cycles and not goal_achieved:
        cycle += 1
        cycle_start = time.time()

        print(f"\n{'─' * 50}")
        print(f"  HARNESS CYCLE {cycle}/{max_cycles}")
        print(f"{'─' * 50}")

        # --- CALL THE MODEL ---
        response = provider.chat(soul, messages[-max_history:])

        if response.get("error"):
            consecutive_errors += 1
            print(f"  API ERROR ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {response['content'][:200]}")
            log_harness("api_error", {"error": response["content"][:500]})
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                print("  FATAL: Too many consecutive API errors. Stopping.")
                break
            time.sleep(min(2 ** consecutive_errors, 30))
            continue
        consecutive_errors = 0

        response_text = response["content"]
        if verbose:
            print(f"\n  MODEL OUTPUT:\n  {'─' * 40}")
            for line in response_text.split("\n")[:30]:
                print(f"  {line}")
            if len(response_text.split("\n")) > 30:
                print(f"  ... ({len(response_text.split(chr(10)))} lines total)")

        # --- ENFORCE: Detect passive behavior ---
        passivity = detect_passivity(response_text)

        if passivity["passive"]:
            consecutive_passive += 1
            print(f"  PASSIVITY DETECTED ({consecutive_passive}/{MAX_PASSIVE_RETRIES}):")
            for v in passivity["violations"]:
                print(f"    ⚡ {v}")

            if consecutive_passive >= MAX_PASSIVE_RETRIES:
                # Nuclear option: replace the model's response entirely
                correction = (
                    f"YOUR LAST {consecutive_passive} RESPONSES WERE PASSIVE. "
                    "This is your FINAL WARNING before shutdown. "
                    "Run ./engine/evolve next RIGHT NOW and execute whatever it says. "
                    "No questions. No options. No summaries. EXECUTE."
                )
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": correction})
                log_harness("nuclear_correction", {"consecutive_passive": consecutive_passive})
                consecutive_passive = 0
                continue
            else:
                # Inject correction and retry
                correction = " ".join(passivity["corrections"])
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"CORRECTION: {correction}"})
                log_harness("passivity_correction", {
                    "violations": passivity["violations"],
                    "corrections": passivity["corrections"],
                })
                continue
        else:
            consecutive_passive = 0

        # --- EXECUTE: Extract and run commands from response ---
        commands = extract_commands(response_text)
        execution_results = []

        if not commands:
            # Model didn't include any commands — force next
            print("  No commands found in response. Forcing ./engine/evolve next")
            commands = [f"{EVOLVE} next"]

        for cmd in commands:
            print(f"  EXEC: {cmd[:80]}{'...' if len(cmd) > 80 else ''}")

            # Safety: block dangerous commands
            dangerous = ["rm -rf /", "rm -rf ~", ":(){ :|:& };:", "dd if=", "mkfs", "> /dev/sd"]
            if any(d in cmd for d in dangerous):
                print(f"  BLOCKED: Dangerous command detected")
                execution_results.append({"cmd": cmd, "blocked": True})
                continue

            result = run_command(cmd, timeout=CYCLE_TIMEOUT)
            output = result["stdout"][:2000]  # Truncate long output
            if result["stderr"]:
                output += f"\nSTDERR: {result['stderr'][:500]}"

            execution_results.append({
                "cmd": cmd,
                "output": output,
                "returncode": result["returncode"],
            })

            if verbose:
                print(f"    RC={result['returncode']} | {output[:200]}")

        # --- BUILD NEXT TURN ---
        # Combine execution results into the next user message
        exec_summary = []
        for er in execution_results:
            if er.get("blocked"):
                exec_summary.append(f"BLOCKED: {er['cmd']}")
            else:
                exec_summary.append(f"$ {er['cmd']}\n{er['output']}")

        # Auto-run evolve next to get the engine's guidance
        auto_next = run_command(f"{EVOLVE} next")
        engine_guidance = auto_next["stdout"] if auto_next["returncode"] == 0 else ""

        # Check if goal is achieved
        if "GOAL_ACHIEVED" in engine_guidance or "goal_achieved" in engine_guidance.lower():
            goal_achieved = True

        next_msg = f"""COMMAND RESULTS:
{chr(10).join(exec_summary)}

ENGINE GUIDANCE:
{engine_guidance}

Continue the evolution loop. Execute the next cycle immediately. Do not stop. Do not ask questions."""

        messages.append({"role": "assistant", "content": response_text})
        messages.append({"role": "user", "content": next_msg})

        cycle_time = time.time() - cycle_start
        log_harness("cycle", {
            "cycle": cycle,
            "commands_executed": len(commands),
            "passive": passivity["passive"],
            "cycle_time_s": round(cycle_time, 1),
            "total_tokens": provider.total_tokens,
        })

        print(f"  Cycle {cycle} complete in {cycle_time:.1f}s | Commands: {len(commands)} | Tokens: {provider.total_tokens}")

    # --- FINAL STATUS ---
    print(f"\n{'═' * 50}")
    if goal_achieved:
        print(f"  GOAL ACHIEVED in {cycle} cycles")
    elif cycle >= max_cycles:
        print(f"  MAX CYCLES REACHED ({max_cycles})")
    else:
        print(f"  STOPPED after {cycle} cycles")

    print(f"  Total tokens: {provider.total_tokens}")
    final_status = run_command(f"{EVOLVE} status")
    print(f"\n{final_status['stdout']}")
    print(f"{'═' * 50}")

    log_harness("end", {
        "cycles": cycle,
        "goal_achieved": goal_achieved,
        "total_tokens": provider.total_tokens,
    })


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evolution Harness — Forces autonomous execution on any LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # OpenAI-compatible (default)
  python3 engine/harness.py --goal "Build a REST API" --model gpt-4o

  # Anthropic
  python3 engine/harness.py --goal "Build X" --provider anthropic --model claude-sonnet-4-20250514

  # Local model (Ollama, vLLM, LM Studio)
  python3 engine/harness.py --goal "Build X" --provider openai --model qwen2.5-coder \\
      --endpoint http://localhost:11434/v1

  # Resume from last session
  python3 engine/harness.py --resume --model gpt-4o

  # Autopilot mode for small models (engine drives, model writes code)
  python3 engine/harness.py --autopilot --goal "Build X" --model qwen3.5 \\
      --endpoint http://localhost:11434/v1

  # Dry run (test without API calls)
  python3 engine/harness.py --goal "Test" --provider dry-run --model test
        """
    )

    parser.add_argument("--goal", type=str, help="The goal to achieve")
    parser.add_argument("--resume", action="store_true", help="Resume from existing state")
    parser.add_argument("--provider", choices=["openai", "anthropic", "dry-run"],
                        default="openai", help="LLM provider (default: openai)")
    parser.add_argument("--model", type=str, default="gpt-4o",
                        help="Model name (default: gpt-4o)")
    parser.add_argument("--endpoint", type=str,
                        help="Custom API endpoint (for local models)")
    parser.add_argument("--max-cycles", type=int, default=200,
                        help="Maximum cycles before stopping (default: 200)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print full model output and command results")
    parser.add_argument("--autopilot", action="store_true",
                        help="Autopilot mode: engine drives everything, model only writes code. "
                             "Use this for small models (Qwen 3.5, Llama 8B, etc.)")
    parser.add_argument("--goal-type", choices=["code", "business"], default="code",
                        help="Goal type for init (default: code)")

    args = parser.parse_args()

    # Env var overrides
    if os.environ.get("EVOLUTION_ENDPOINT"):
        args.endpoint = os.environ["EVOLUTION_ENDPOINT"]
    if os.environ.get("EVOLUTION_MODEL"):
        args.model = os.environ["EVOLUTION_MODEL"]

    if not args.goal and not args.resume:
        parser.error("Either --goal or --resume is required")

    args.goal_type = getattr(args, "goal_type", "code")

    if args.autopilot:
        run_autopilot(args)
    else:
        run_harness(args)


if __name__ == "__main__":
    main()
