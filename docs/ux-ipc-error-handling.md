# UX and IPC error handling

This document explains the daemon/client IPC used by CEDR and recommends UX best practices for error messages and exit behavior.

## How daemon/client IPC works

CEDR uses **POSIX named semaphores** and **shared memory** for communication:

- **Server (daemon):** The CEDR runtime (`cedr` / `runtime`) creates the semaphore `sem_submission_queue` and shared memory `mem1` at startup.
- **Client:** `sub_dag` and `kill_daemon` connect to those objects to submit work or shut down the daemon.

You must **start the daemon first**; then run `sub_dag` or `kill_daemon` from another shell (or script).

### Common errors you may see

| Message | Who | Meaning |
|--------|-----|--------|
| `sem_open failed in client initialization: No such file or directory` | Client (`sub_dag` or `kill_daemon`) | The daemon is not running (or the semaphore does not exist). **Start the daemon first.** |
| `sem_unlink failed in server initialization: No such file or directory` | Server (daemon) | No previous semaphore to remove (e.g. first run). **Usually harmless.** |
| `shm_unlink in server initializtion: No such file or directory` | Server (daemon) | No previous shared memory to remove. **Usually harmless.** |

In Docker, ensure the container has a proper `/dev/shm` and that client and daemon run in the same container (or share IPC) so the semaphore and shared memory are visible to both.

---

## UX best practices (recommendations)

These recommendations apply to the code that reports IPC errors (e.g. in `src-dag/ipc.cpp` and `src-api/ipc.cpp`).

### 1. Actionable, user-facing messages

- **Avoid:** Relying only on raw `perror()` (e.g. “sem_open failed in client initialization: No such file or directory”).
- **Prefer:** A single, clear sentence plus what to do next.

**Example for client (e.g. `sub_dag`):**  
*“Cannot connect to CEDR daemon. Is the daemon running? Start it first (e.g. `./cedr` or `./runtime`), then run this command again.”*

So: explain what failed in user terms and give the next step.

### 2. Don’t treat “expected” failures as errors

- **Avoid:** Printing an error for every “failure” when some are normal (e.g. first run).
- **Prefer:** For **unlink** calls, treat **ENOENT** as “nothing to clean up”:
  - Either **don’t print** for ENOENT, or
  - Log only at **debug/verbose**, or
  - One line like “Cleaning up previous run…” and only **warn** if the error is **not** ENOENT.

That keeps real problems visible and reduces noise.

### 3. Use correct exit codes

- **Avoid:** `exit(0)` on failure (scripts and CI cannot distinguish success from failure).
- **Prefer:** `exit(EXIT_FAILURE)` or `exit(1)` on real errors so `echo $?` and scripts behave correctly.

### 4. Consistent wording and spelling

- Use one term for the other process (e.g. “daemon” in user-facing messages).
- Fix spelling (e.g. “initializtion” → “initialization”) so messages look intentional and are searchable.

### 5. Identify which program failed

- **Prefer:** Prefix with the program name (e.g. `sub_dag: …` or `argv[0]`) so in multi-tool workflows it is clear which binary failed.

### 6. Optional: use log levels

- The codebase already uses **plog**. Use it to separate:
  - **Real errors:** error level, stderr, user-facing message and remediation.
  - **Benign unlink ENOENT:** debug/verbose only (or no message).
  - **Internal/low-level detail:** debug only; keep default output minimal and calm.

---

## Summary table

| Situation | Current UX | Recommended UX |
|-----------|-------------|-----------------|
| Client can’t connect (daemon not running) | `perror("sem_open failed...")` then `exit(0)` | One clear line: “Cannot connect to CEDR daemon. Start the daemon first.” + `exit(EXIT_FAILURE)` |
| Server cleanup (unlink, first run) | `perror("sem_unlink failed...")` etc. | No message for ENOENT, or debug-only; optionally warn only for non-ENOENT |
| Any real IPC failure | `perror()` only | Short user message; optionally append “(…: &lt;strerror&gt;)” for technical detail |
| Exit on error | `exit(0)` | `exit(EXIT_FAILURE)` |

Implementing these in the IPC initialization paths will make daemon/client errors easier to understand and to script around.
