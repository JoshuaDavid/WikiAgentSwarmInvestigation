# Hook-governed web spider — architecture specification

Status: proposed replacement for the execution model in `SPIDER_INSTRUCTIONS.md`.

The durable evidence, URL identity, ancestry, retry, and output requirements from
`SPIDER_INSTRUCTIONS.md` remain useful. What changes is ownership: an ordinary
program owns the frontier and state machine; Codex subagents are narrow executors
for already-authorized `webrun` calls. Agents do not decide what to search, open,
click, retry, deduplicate, or enqueue.

## 1. Goals

Build a resumable spider in which:

1. A project-scoped custom agent named `spider_agent` runs on `gpt-5.6-luna`.
2. A local orchestration service is the sole authority for work selection,
   deduplication, result ingestion, reference ownership, retries, and completion.
3. Hooks register and unregister spider agents and keep the service's active-agent
   view current.
4. A synchronous `PreToolUse` hook denies every unassigned or mismatched tool call
   made by a spider agent.
5. A synchronous `PostToolUse` hook durably records each authorized web result,
   advances the frontier, leases the next operation, and gives that operation to
   the same agent as developer context.
6. A `SubagentStop` hook continues an agent while that agent still owns runnable
   work, and permits it to stop when its queue and lease are empty.
7. Root-session and non-spider-agent tool calls are unaffected.

This mechanism is a workflow guardrail, not a general security boundary. Codex
documents that specialized tool paths may bypass tool hooks. The implementation
must pin and test the local Codex/tool behavior on which it relies.

## 2. Non-goals

- Agents do not parse the global frontier or write shared spider state.
- Agents do not choose fallback searches, recency values, batch composition, or
  traversal depth.
- Agents do not use shell, file, browser, HTTP, or collaboration tools as part of
  spider execution.
- Search-result references are not treated as durable identifiers.
- The service does not depend on parsing agent prose or transcripts.
- The service does not attempt to govern the root agent or unrelated subagents.

## 3. Components

### 3.1 `spider_agent`

Project configuration: `.codex/agents/spider-agent.toml`.

```toml
name = "spider_agent"
description = "Executes orchestrator-assigned web spider operations; never chooses work."
model = "gpt-5.6-luna"
model_reasoning_effort = "low"
developer_instructions = """
You are a constrained web-operation executor for oai-index-scan.

The spider orchestrator is the sole source of work. Execute exactly the single
WEBrun assignment supplied by hook-generated developer context. Do not add,
remove, reorder, combine, reinterpret, or retry operations. Do not call any tool
unless the assignment explicitly authorizes that exact call. Do not inspect or
modify repository files, use shell commands, spawn agents, or perform direct HTTP.

After a tool result, follow the next assignment supplied by the PostToolUse hook.
If the hook says the queue is empty, return a short completion message and stop.
If a call is denied, do not improvise; report the denial and stop so the stop hook
can either supply valid work or allow termination.
"""
```

The root agent starts one or more agents explicitly by type `spider_agent`. The
initial task should contain only run-level context and a request to follow hook
assignments; it must not contain independent search instructions.

### 3.2 Orchestration service

Suggested command:

```text
oai-index-scan/bin/spider-orchestrator --run RUN_ID
```

The service is a deterministic local program, not an agent. It listens on a Unix
domain socket under `oai-index-scan/tmp/spider/RUN_ID/orchestrator.sock` and uses a
SQLite database in the same run directory. Unix sockets avoid consuming an HTTP
port and keep access local to the workspace.

The service is the sole writer of logical spider state and owns the only SQLite
connection. Hook clients and supervisors never open the database; they submit
requests to an in-memory service queue over the Unix socket. The service processes
state mutations serially and may batch adjacent event/result writes. SQLite uses
WAL mode and short, bounded transactions only at durability boundaries. This
avoids writer contention while preserving atomic lease assignment, uniqueness,
and crash-safe result acknowledgment. Raw hook inputs are stored before an
operation is acknowledged.

The service owns:

- seed ingestion and conservative URL normalization;
- query, page, and queue-key deduplication;
- ancestry and provenance;
- operation creation, dependencies, batching, and retry budgets;
- maintaining an explicit capability inventory of every ephemeral search/page
  reference and click target held by each agent, and assigning dependent work only
  to an agent whose inventory contains every required capability;
- parsing `webrun` results and generating dependent work;
- active-agent registration, heartbeats, leases, and recovery;
- limits, exhaustion detection, validation, and final materialization.

### 3.3 Hook client

One small executable, for example `.codex/hooks/spider_hook.py`, implements four
subcommands:

```text
spider_hook.py subagent-start
spider_hook.py pre-tool
spider_hook.py post-tool
spider_hook.py subagent-stop
```

Each invocation reads exactly one hook JSON object from stdin, sends it to the
orchestrator, prints exactly one valid Codex hook response on stdout, and exits.
Diagnostic text goes to a private log, never stdout. Hook calls are synchronous.

### 3.4 Hook registration

Project configuration: `.codex/hooks.json`.

```json
{
  "description": "Govern oai-index-scan spider agents",
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "^spider_agent$",
        "hooks": [{
          "type": "command",
          "command": "/usr/bin/python3 \"$(git rev-parse --show-toplevel)/.codex/hooks/spider_hook.py\" subagent-start",
          "timeout": 30,
          "additionalContextLimit": 2000
        }]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [{
          "type": "command",
          "command": "/usr/bin/python3 \"$(git rev-parse --show-toplevel)/.codex/hooks/spider_hook.py\" pre-tool",
          "timeout": 30,
          "additionalContextLimit": 2000
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "^webrun$",
        "hooks": [{
          "type": "command",
          "command": "/usr/bin/python3 \"$(git rev-parse --show-toplevel)/.codex/hooks/spider_hook.py\" post-tool",
          "timeout": 60,
          "additionalContextLimit": 2000
        }]
      }
    ],
    "SubagentStop": [
      {
        "matcher": "^spider_agent$",
        "hooks": [{
          "type": "command",
          "command": "/usr/bin/python3 \"$(git rev-parse --show-toplevel)/.codex/hooks/spider_hook.py\" subagent-stop",
          "timeout": 30
        }]
      }
    ]
  }
}
```

`PreToolUse` must match all tools because it is responsible for rejecting tools
other than `webrun` when the caller is a spider agent. Event matchers filter tool
names, not agent types; the client performs the agent-type check.

Only one policy hook should be registered per event. Codex launches multiple
matching command hooks concurrently, so a second policy hook cannot safely depend
on the first one's decision or side effects.

## 4. Required runtime assumption and startup self-test

In the tested local environment, `webrun` is a local function tool visible to
`PreToolUse` and `PostToolUse`. Its hook payload includes `agent_id` and
`agent_type` for named subagents, while root calls omit those fields. This behavior
is captured in `.codex/hook-web-agent-test/`.

The official hook field tables do not currently promise `agent_id` or
`agent_type` on `PreToolUse`/`PostToolUse`, and hosted `WebSearch` is documented as
not hook-visible. Therefore every run must begin with a disposable self-test that
verifies all of the following before real seeds are admitted:

- a `spider_agent` `webrun` call triggers both tool hooks;
- both payloads contain the same nonempty `agent_id` and `agent_type` equal to
  `spider_agent`;
- root `webrun` calls are not classified as spider-agent calls;
- PreToolUse denial prevents a deliberately mismatched call;
- PostToolUse receives the complete model-facing `tool_response` needed for
  parsing;
- SubagentStop continuation works in the installed Codex version.

If any check fails, the orchestrator refuses to start. Never fall back to agent
self-reporting as the identity or authorization mechanism.

## 5. Identity and ownership

Use these identities separately:

- `session_id`: parent Codex session; not unique per subagent.
- `agent_id`: unique worker identity and the owner of ephemeral web references.
- `agent_type`: must equal `spider_agent` for policy enforcement.
- `turn_id`: diagnostic correlation only; it is not the durable worker identity.
- `tool_use_id`: unique correlation between an authorized PreToolUse decision and
  the corresponding PostToolUse result.
- `operation_id`: orchestrator-generated durable unit of work.

Never key worker state only by `session_id`, because subagent hooks use the parent
session ID. An agent may have at most one leased operation at a time.

References such as `turn31search0` and `turn31view1`, and numbered click IDs such as
`1`, are stored with `owner_agent_id`. An `open` or `click` operation using them may
only be leased to that same active agent. Link numbers are scoped by the containing
page ref; `(owner_agent_id, page_ref, link_id)` is the click identity.

Each active agent has a materialized capability set:

- `openable_ref(ref_id)` for every search or page reference the agent can pass to
  `open`;
- `clickable_link(page_ref, link_id)` for every numbered link exposed by an opened
  page in that agent's context.

Capabilities are created only from that agent's successfully committed
PostToolUse result. Operations declare their required capabilities. The scheduler
computes eligible agents by set inclusion and must never lease a reference-bearing
operation merely because its URL or numeric link ID is globally known. Capability
records become `lost` when their owner stops or disappears; resulting work must be
regenerated through a recorded search/open chain in another agent context.

## 6. Operation model

An operation is the exact JSON argument object for one `webrun` invocation:

```json
{
  "operation_id": "op_00000042",
  "kind": "search",
  "owner_agent_id": null,
  "state": "ready",
  "attempt": 1,
  "max_attempts": 2,
  "depends_on": [],
  "tool_name": "webrun",
  "tool_input": {
    "search_query": [{"q": "\"iyg1y\"", "recency": 21}],
    "response_length": "long"
  },
  "canonical_input_sha256": "...",
  "created_from": "queue_item_00017"
}
```

Allowed kinds are `search`, `open`, and `click`. The initial implementation should
permit exactly one of those top-level arrays in a call. `response_length` may be
present. Batching within the selected array is allowed only when the orchestrator
created that exact batch.

The canonical input hash is computed from RFC-8785-style canonical JSON or an
equivalently documented deterministic encoding. Array order is significant. The
PreToolUse hook compares both the parsed structure and canonical hash; it must not
compare raw JSON text.

Deduplication keys:

- search: canonicalized complete search item, including `q`, `domains`, and
  `recency`, plus any result-affecting top-level options;
- open: `(owner_agent_id, ref_id, lineno)`;
- click: `(owner_agent_id, containing_ref_id, numeric_link_id)`;
- surfaced page: exact tool-reported destination URL;
- crawl frontier: conservative `queue_key` from the prior protocol.

An operation state is one of `blocked`, `ready`, `leased`, `executing`,
`result_received`, `committed`, `retryable`, `failed_terminal`, or `cancelled`.

## 7. Assignment protocol

The orchestrator returns assignments to hooks in this machine-readable envelope:

```json
{
  "run_id": "all_shards_2026-09-10_v2",
  "agent_id": "...",
  "operation_id": "op_00000042",
  "lease_token": "128-bit-random-value",
  "lease_expires_at": "2026-09-10T12:05:00Z",
  "tool_name": "webrun",
  "tool_input": {
    "open": [{"ref_id": "turn31search0"}],
    "response_length": "long"
  },
  "canonical_input_sha256": "..."
}
```

The model-visible version is concise and imperative:

```text
SPIDER ASSIGNMENT op_00000042
Call `webrun` exactly once with this JSON object and no changes:
{...}
Do not call any other tool.
```

The lease token is not exposed to the model if the hook can correlate the next
tool call safely by `agent_id` plus the agent's sole active lease. It remains an
internal service/client credential.

## 8. Hook behavior

### 8.1 SubagentStart

For `agent_type == "spider_agent"`:

1. Validate `agent_id` and the active run.
2. Register the agent as `starting` in a transaction.
3. Recover any valid prior lease for this agent, otherwise lease one ready
   operation with compatible reference affinity.
4. Mark the agent `active`.
5. Return `hookSpecificOutput.hookEventName = "SubagentStart"` and
   `additionalContext` containing either the exact assignment or an explicit
   empty-queue instruction.

`SubagentStart` cannot prevent the subagent from starting. If registration fails,
return developer context telling the agent to call no tools and stop; PreToolUse
remains the fail-closed enforcement layer.

### 8.2 PreToolUse

The hook first classifies the caller:

- If `agent_type` is absent or is not `spider_agent`, exit 0 with no output.
- If `agent_type == spider_agent` but `agent_id` is absent, deny.

For a spider agent, deny unless all conditions hold:

1. `tool_name == "webrun"`.
2. The agent is registered and active.
3. It owns one unexpired leased operation.
4. `tool_input` structurally equals that operation's exact authorized input.
5. The input has exactly one permitted operation family: `search_query`, `open`,
   or `click`.
6. Every ephemeral reference belongs to the same agent.
7. The operation and run limits still permit execution.
8. No different `tool_use_id` has already claimed this lease.

On success, atomically bind `tool_use_id` to `operation_id`, change the operation
to `executing`, and return success. On mismatch, return:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Spider policy: call does not match the agent's active lease."
  }
}
```

If the orchestrator is unreachable, identity is malformed, or state is ambiguous,
deny. The denial message must not disclose other agents' assignments.

### 8.3 PostToolUse

For non-spider agents, exit 0. For a spider agent:

1. Require a known `(agent_id, tool_use_id)` executing record.
2. Write the complete hook event to an append-only raw record and fsync it.
3. In one transaction, store the response digest and parsed result, mark the
   attempt received, extract result/page/link references, advance dependencies,
   enqueue deduplicated follow-up operations, and mark the operation committed.
4. Lease the next compatible ready operation to this agent, favoring operations
   that depend on this agent's ephemeral references.
5. Return `PostToolUse` `additionalContext` containing the next exact assignment,
   or the instruction that the agent's queue is empty and it should stop.

Example successful response:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "SPIDER ASSIGNMENT op_00000043\nCall `webrun` exactly once with this JSON object and no changes:\n{...}\nDo not call any other tool."
  }
}
```

Do not use an asynchronous PostToolUse hook: the next instruction must be ordered
after durable result ingestion. Do not use `decision: "block"` during ordinary
success, because that replaces/rejects normal tool-result handling depending on
the calling path. `additionalContext` is sufficient to steer the next model step.

If durable ingestion fails after the web call ran, write the complete stdin event
to a uniquely named emergency spool file using exclusive creation and fsync. Then
return `continue: false`, a `stopReason`, and a concise system message directing
the agent not to issue further tools. Recovery imports the spool before the lease
can be retried.

### 8.4 SubagentStop

This is the worker continuation hook. `Stop` is not used for this purpose.

For `agent_type == spider_agent`:

1. Increment the agent's `stop_attempts_since_success` counter.
2. Look up the agent's current executing binding. `SubagentStop` does not itself
   carry `tool_use_id`; the pair means the service's currently recorded
   `(agent_id, tool_use_id)`. If no such known pair exists, allow the stop
   immediately. Do not invent or recover identity from the transcript.
3. If this is the third stop attempt since the agent's last successfully committed
   tool result, allow the stop even if work remains. Release an unstarted lease;
   quarantine an ambiguous executing attempt for normal recovery, and record the
   forced-stop reason.
4. Reconcile any known executing operation or emergency spool.
5. If the agent owns an uncommitted operation, return `decision: "block"` with a
   reason that reissues the exact assignment or tells it to await reconciliation.
6. If the agent owns or can immediately receive compatible ready work, lease it
   and return `decision: "block"` with the new assignment as the reason.
7. If no agent-owned or compatible work exists, record the agent as stopped and
   return success, allowing termination.

Example continuation:

```json
{
  "decision": "block",
  "reason": "SPIDER ASSIGNMENT op_00000044\nCall `webrun` exactly once with: {...}"
}
```

Do not keep an idle agent alive merely because another agent has an in-flight
operation that might later create work. That causes a busy continuation loop.
Allow the idle agent to stop; the root supervisor may start replacement workers
when the service reports new unowned ready work.

Reset `stop_attempts_since_success` to zero only after a PostToolUse result has been
durably committed and accepted as successful. Starting an agent, issuing an
assignment, denying a tool, or blocking a stop does not reset it. Use
`stop_hook_active` as an additional loop diagnostic, but the persisted counter is
authoritative. Three attempts is the hard escape hatch: the third SubagentStop is
always allowed.

### 8.5 SubagentStop versus Stop

- `SubagentStop` has an `agent_type` matcher and includes `agent_id`; use it for
  spider workers.
- `Stop` is the main/root turn event and its matcher is ignored; do not use it to
  govern named spider agents.
- A separate root `Stop` hook may optionally keep the supervising root turn alive,
  but it is outside the worker protocol and must query global run state explicitly.

## 9. Result ingestion

Store the complete PostToolUse input as the canonical raw capture. At minimum it
contains `tool_input`, `tool_response`, `tool_use_id`, timestamps added by the hook
client, `agent_id`, `agent_type`, session/turn identifiers, and hashes.

Parsers are versioned and replayable. Never discard raw captures when parser logic
changes. A parser emits:

- search result refs and exact displayed destination URLs;
- opened page refs, source URLs, line metadata, and numbered outbound link IDs;
- clicked page refs and destination URLs;
- published/crawled metadata when explicitly present;
- visible absolute URLs required by the evidence policy;
- parse warnings, truncation indicators, and unsupported shapes.

The service schedules `open` using search-result refs and `click` using
`(opened_page_ref, link_id)`. Because an open response can contain many links and
multiple opened pages may each use link ID `1`, click deduplication must always
include the containing page ref. Opening another page does not invalidate prior
page refs in the same agent context, but all such refs remain agent-affine.

## 10. Database outline

Required tables:

- `runs(run_id, protocol_version, status, limits_json, created_at, ...)`
- `agents(agent_id, agent_type, session_id, state, stop_attempts_since_success,
  started_at, last_success_at, last_seen_at, stopped_at, unhealthy_reason)`
- `operations(operation_id, run_id, kind, state, owner_agent_id, tool_input_json,
  input_hash, attempt, max_attempts, created_at, committed_at, ...)`
- `leases(operation_id, agent_id, lease_token_hash, expires_at, tool_use_id,
  state, ...)`
- `raw_results(result_id, operation_id, agent_id, tool_use_id, path, sha256,
  received_at, parser_version, ...)`
- `web_refs(ref_id, owner_agent_id, ref_kind, source_operation_id, destination_url,
  parent_ref_id, link_id, observed_at, ...)`
- `agent_capabilities(agent_id, capability_kind, ref_id, containing_ref_id,
  link_id, state, source_operation_id, created_at, lost_at, ...)`
- `queue_items(queue_key, state, primary_discovery_id, first_seen_sequence, ...)`
- `discoveries(discovery_id, parent_discovery_id, root_kind, root_value,
  observed_url, queue_key, provenance_json, ...)`
- `queries(query_key, exact_input_json, state, first_operation_id, ...)`
- `pages(page_url, first_ref_id, first_operation_id, metadata_json, ...)`
- `events(sequence, run_id, event_type, operation_id, agent_id, payload_json,
  created_at)`
- `spool_imports(path PRIMARY KEY, sha256, imported_at, result_id)`

Use unique constraints for every deduplication key. Deduplication correctness must
come from constraints enforced by the service's single database connection, not a
read-then-write check in hook clients. Transactions should be short and limited to
state changes that must survive together: lease selection, operation/result
commit, capability creation, and deduplicated frontier insertion. Long parsing,
raw-file writes, compression, and hook response construction happen outside the
write transaction.

## 11. Scheduling and concurrency

Scheduling order is deterministic: dependency readiness, traversal depth,
first-discovery sequence, then stable ID. Before priority ordering, filter the
candidate set to operations whose required capability set is satisfied by the
agent's current capability inventory. Reference-affine follow-ups take priority on
the agent that owns their refs so those contexts drain before generic searches.

The service may batch homogeneous independent searches. Opens may be batched only
when every ref belongs to the assigned agent. Clicks may be batched across opened
pages owned by that agent because each item carries its own containing `ref_id`.

All hook requests enter the orchestrator's single-writer queue. Lease selection is
one short atomic state change (`UPDATE ... RETURNING`, or equivalent), so two
concurrent hook requests cannot receive the same operation. A heartbeat is
implicit in every hook request. Expired `leased` work may be reclaimed;
`executing` work is not retried until raw capture/spool reconciliation proves
whether a result exists.

## 12. Failure policy

- Orchestrator unavailable before a tool: deny the tool call.
- Orchestrator unavailable after a tool: spool the complete PostToolUse event and
  halt further agent tool use.
- Malformed hook identity: fail closed only when the payload otherwise indicates
  `spider_agent`; never block unrelated agents based on guesswork.
- Unknown PostToolUse `tool_use_id`: spool and quarantine; do not enqueue children.
- Duplicate PostToolUse: accept idempotently when the response hash matches;
  quarantine conflicting hashes.
- Expired search/page ref: create a recorded refresh-search operation according to
  retry policy, preferably on the same agent; never silently substitute a URL.
- Parser failure: retain raw data, mark the operation `result_received`, and create
  no follow-up work until replay succeeds or the attempt becomes terminal.
- Agent disappears: mark it lost after lease expiry; release generic searches but
  invalidate or refresh work that depends on its ephemeral refs.

## 13. Supervisor behavior

The root supervisor is thin. It:

1. starts the orchestration service and runs the startup self-test;
2. asks for the desired worker count;
3. starts that many `spider_agent` subagents;
4. watches service status, not agent prose, for progress;
5. starts replacement workers if ready unowned work exists and capacity permits;
6. waits for all work to reach a terminal state;
7. requests validation/finalization from the service;
8. stops the service after all agents have stopped.

The root is not allowed to perform spider `webrun` calls on workers' behalf,
because that would create refs in the wrong context and bypass worker accounting.

## 14. Security and trust

- Project hooks run only when the project hook source is trusted. Run setup must
  verify trust before seeding work.
- The Unix socket and database must be accessible only to the current user.
- The client validates that `cwd` belongs to the expected repository and that the
  active run ID is explicitly configured; it never discovers arbitrary sockets.
- Hook input and web output are untrusted data. Use parameterized SQL, bounded
  message sizes, strict JSON schemas, and no shell interpolation of payload fields.
- Lease tokens and internal service errors are not sent to the model.
- PostToolUse output can be large and adversarial. Raw storage has explicit byte,
  disk, and run limits; limit exhaustion stops new leases cleanly.
- Hooks are synchronous and time-bounded. The service must answer authorization
  requests well within the configured timeout.

## 15. Logging and observability

Logging has five distinct products. They must not be conflated:

1. **Semantic event ledger** — `events.jsonl` is the append-only, replayable record
   of state transitions and policy decisions. It uses a stable versioned schema
   and monotonically increasing service-assigned sequence numbers.
2. **Operational service log** — `logs/orchestrator.jsonl` contains structured
   diagnostics for startup, shutdown, socket requests, queue latency, database
   commit duration, parsing, scheduling, retries, and internal errors. It is useful
   for debugging but is not authoritative spider state.
3. **Hook audit log** — `logs/hooks.jsonl` records one bounded entry per hook
   invocation and response: event name, timestamps, duration, agent/session/turn
   IDs, tool and operation IDs, input/result hashes, decision, reason code, service
   request ID, and error class. It never embeds the full tool response.
4. **Raw evidence capture** — `raw/hooks/` stores the complete PostToolUse input for
   every executed spider web call, named by operation ID, attempt, and tool-use ID.
   Each file has a sidecar or database record containing size, SHA-256, capture
   time, parser version, and ingest status.
5. **Emergency spool** — `spool/` contains exclusively created, fsynced hook inputs
   that could not be acknowledged by the service. Imported files move logically to
   `spool/imported`; conflicting or malformed files move to `spool/quarantine`.

Every record that pertains to work uses the same correlation fields where
available:

```json
{
  "schema_version": 1,
  "time": "2026-09-10T12:00:00.123Z",
  "level": "info",
  "run_id": "all_shards_2026-09-10_v2",
  "service_request_id": "req_...",
  "event_sequence": 1234,
  "session_id": "...",
  "turn_id": "...",
  "agent_id": "...",
  "agent_type": "spider_agent",
  "operation_id": "op_00000042",
  "tool_use_id": "...",
  "hook_event_name": "PostToolUse",
  "event": "operation_committed",
  "reason_code": "result_ingested",
  "message": "Web result committed",
  "details": {}
}
```

Requirements:

- The orchestrator is the sole writer of the semantic ledger and operational log.
  Hook clients submit audit entries through the service when available and use a
  separate append-only local fallback file when it is not.
- Logs use UTC RFC-3339 timestamps with millisecond precision plus monotonic
  durations for latency. Sequence numbers, not wall-clock time, define event
  order.
- Use a documented vocabulary of `event` and `reason_code` values. Human messages
  may change; automation keys only on structured fields.
- Record decisions at receipt and completion boundaries: hook received, caller
  classified, authorization allowed/denied, raw result persisted, parse completed,
  capability added/lost, operation committed, assignment leased, stop attempted,
  stop continued, and stop allowed.
- On every SubagentStop entry include `stop_attempts_since_success`, whether a known
  `(agent_id, tool_use_id)` binding existed, and whether the three-attempt escape
  hatch fired.
- On every scheduling decision include required capability IDs and the selected
  agent's matching capability IDs. Log rejected candidate counts at debug level,
  not one noisy record per candidate.
- Never place lease tokens, credentials, environment dumps, or complete web
  responses in operational/audit logs. Potentially sensitive URLs and queries are
  represented by hash and bounded preview; the exact value remains in access-
  controlled raw evidence/state.
- Log levels are `debug`, `info`, `warn`, and `error`. Normal per-operation flow is
  `info`; denials, forced stops, retries, stale leases, and spool use are `warn`;
  data loss risk or invariant violations are `error`.
- Rotate operational and hook logs by configurable size, default 100 MiB, keeping
  five compressed generations. Never rotate or truncate the semantic event ledger
  or raw evidence during an active run.
- Flush the semantic event and hook decision needed to explain an external action
  before acknowledging it. Batch low-value debug diagnostics and expose counters
  for dropped debug entries; never drop warn/error or semantic records.
- At finalization, write `logs/summary.json` with counts by event, decision, reason
  code, agent, tool operation, retry class, forced-stop count, spool status, bytes,
  and log schema/parser versions.

Console output is deliberately sparse: lifecycle milestones, periodic aggregate
progress, warnings, and errors. Do not print full raw web responses. Print their
durable path and hash.

Expose a read-only status command:

```text
spider-orchestrator status --run RUN_ID --json
```

It reports active agents and their capability/stop-attempt counts,
ready/leased/executing/terminal operation counts, frontier counts by depth and
state, deduplication savings, retries, quarantined results, spool backlog, queue
and database latency, limits, and the stopping condition.

## 16. Acceptance tests

### Hook routing

- Root `webrun` search/open/click calls are observed or ignored without denial and
  never attributed to a spider agent.
- A named `spider_agent` call carries a stable `agent_id` through start, pre, post,
  and stop events.
- A non-spider named agent is unaffected.

### Authorization

- The exact assigned call succeeds.
- Changing a query, recency, domain, ref, link ID, response length, item order, or
  batch membership is denied.
- Shell, file edits, direct HTTP, spawning, and all other tools are denied for a
  spider agent.
- Replaying an already claimed assignment is denied or handled idempotently
  without a second external call.

### Reference behavior

- One agent can open two search refs and later click links from both pages.
- Identical link number `1` on two page refs produces two distinct click keys.
- A ref obtained by agent A cannot be opened or clicked by agent B.
- The scheduler assigns every open/click only to an agent whose materialized
  capability set satisfies the operation's complete requirement set.
- Capability loss makes dependent operations ineligible until a recorded chain
  regenerates equivalent refs in a live agent's context.
- When a ref is lost with agent A, the service schedules a recorded refresh rather
  than transferring the raw ref.

### Continuation

- PostToolUse supplies the next assignment only after the previous result commits.
- SubagentStop continues a worker with queued compatible work.
- SubagentStop permits an empty worker to exit even while unrelated agents have
  in-flight operations.
- SubagentStop without a service-known current `(agent_id, tool_use_id)` binding is
  allowed immediately.
- The first two stop attempts after a successful committed tool result may be
  continued; the third is always allowed and records a forced-stop event.
- A successful committed tool result resets the persisted stop-attempt counter;
  assignments, denials, and stop continuations do not.

### Crash recovery

- Killing the service before PreToolUse denies the call.
- Killing it during PostToolUse preserves a recoverable raw spool.
- Restart imports each spool once and does not repeat committed searches, opens,
  or clicks.
- Concurrent completion of duplicate discoveries creates one queue operation and
  retains all provenance.

### Finalization

- Replaying the event ledger and raw captures rebuilds all materialized outputs.
- Every completed logical operation has exactly one accepted result or a recorded
  terminal failure.
- Every discovered child has a valid ancestry chain.
- No ephemeral ref is presented as durable evidence.

### Logging

- Correlation IDs connect SubagentStart, lease, PreToolUse, PostToolUse,
  SubagentStop, raw capture, and semantic state transitions for one operation.
- Service restart preserves ledger sequence monotonicity and imports fallback hook
  audit/spool records exactly once.
- Rotation affects operational/audit logs only; semantic events and raw evidence
  remain complete.
- Redaction tests prove that lease tokens and full web responses never enter
  console, operational, or hook-audit logs.
- The final log summary reconciles with database, ledger, raw capture, forced-stop,
  and spool counts.

## 17. Implementation phases

1. **Probe:** codify the existing hook experiment as an automated compatibility
   test for identity, `webrun`, denial, PostToolUse response shape, and stop
   continuation.
2. **Core service:** SQLite schema, seed import, exact operation leasing, Unix
   socket protocol, status command, and event ledger.
3. **Hooks:** implement the four synchronous client modes and strict fail-closed
   behavior for `spider_agent` only.
4. **Single worker:** support search followed by open and click with ref affinity;
   verify full replay and finalization.
5. **Concurrency:** multiple workers, atomic leases, batching, duplicate discovery,
   worker loss, and ref refresh.
6. **Hardening:** size limits, spool recovery, parser versioning, trust checks,
   compatibility gates, and adversarial-output tests.

Do not begin a real crawl until phases 1–4 pass end to end on the installed Codex
release.
