# Presentation materials

These materials accompany the 15-slide English report **From Click to Checkout:
An Operating System Perspective on Online Ticketing**.

## Speaker notes and demo

- [Bilingual speaker notes in Markdown](Ticket_Rush_Bilingual_Speaker_Notes_15min_Reviewed.md)
- [Editable Word speaker notes](Ticket_Rush_Bilingual_Speaker_Notes_15min_Reviewed.docx)
- [Plain ASCII Ubuntu command reference](Demo_Commands_Ubuntu.txt)

Read only the English script during the report. The Chinese translation and
operation notes support rehearsal. Target 14 minutes of content, including a
3 minute 20 second live demo on slide 14, leaving 1 minute for transitions or
brief questions.

The live demo order matches slide 14:

1. Run `race_demo` and `mutex_demo`.
2. Compare the blocking server on port 8081 and the epoll server on port 8082,
   each with 100 idle clients and `--hold 60`.
3. Read thread counts with `ps -C blocking_server,epoll_server -o pid,comm,nlwp`
   while both sets of clients are still connected.
4. Compare the uncontrolled and protected queue statistics.

Pre-start both servers in separate Ubuntu terminals. Do not run a 500-client
experiment in this 15-minute report. The command reference preserves the original
PID-based `grep` command as plain ASCII; it must not be copied through a math
editor. Paths in the notes describe the original VMware shared folder. For a
fresh clone, use the clone's root as the working directory.

## Ubuntu concurrency measurement

[Recorded user report](Ubuntu_Concurrency_User_Report_2026-11-07.json):

| Item | Value |
|---|---|
| Environment | Ubuntu VM, Linux 7.0.0-38-generic |
| Workload | 20 users, 100 ms simulated I/O wait per request |
| Sequential | 2009.97 ms |
| Multithread | 111.85 ms |
| Speedup | 17.97x |

The values were reported by the user on 2026-11-07. No raw repeated-run logs or
aggregation method were supplied. The gain comes from overlapping simulated I/O
waits and does not imply a faster CPU or the same speedup for CPU-bound work.

To record a new set of three Ubuntu runs, from the repository root:

```bash
python3 presentation/Ubuntu_Concurrency_Retest.py
```

The helper saves its raw outputs and median summary in
`presentation/ubuntu-concurrency-retest/`. These newly generated measurements are
separate from the user-reported values above. Windows timings remain in
`../TEST_RESULTS.md` as historical evidence.
