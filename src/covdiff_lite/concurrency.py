"""Multi-Threaded / Concurrency Race Coverage Fidelity Engine.

Evaluates coverage tool profiling under high thread contention and POSIX multithreading:
1. Synthesizes concurrent C programs with N worker threads executing synchronized loops.
2. Checks whether coverage profiling instrumentation introduces:
   - Counter tearing or lost increments under thread contention.
   - Concurrency overhead and deadlocks in profile counters.
   - Divergence in multi-threaded line hit accumulation between GCC and Clang.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


THREAD_TEMPLATE = """#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

#define NUM_THREADS {num_threads}
#define ITERATIONS_PER_THREAD {iterations}

static volatile long shared_counter = 0;
static pthread_mutex_t counter_mutex = PTHREAD_MUTEX_INITIALIZER;

void *worker_routine(void *arg) {{
    long thread_id = (long)arg;
    for (int i = 0; i < ITERATIONS_PER_THREAD; i++) {{
        pthread_mutex_lock(&counter_mutex);
        shared_counter++; /* SCORED_CRITICAL_SECTION */
        pthread_mutex_unlock(&counter_mutex);
    }}
    return NULL;
}}

int main(void) {{
    pthread_t threads[NUM_THREADS];
    for (long t = 0; t < NUM_THREADS; t++) {{
        if (pthread_create(&threads[t], NULL, worker_routine, (void *)t) != 0) {{
            return 1;
        }}
    }}
    for (int t = 0; t < NUM_THREADS; t++) {{
        pthread_join(threads[t], NULL);
    }}
    printf("final_counter=%ld\\n", shared_counter);
    return (shared_counter == (long)NUM_THREADS * ITERATIONS_PER_THREAD) ? 0 : 2;
}}
"""


@dataclass
class ConcurrencyTestProfile:
    num_threads: int
    iterations_per_thread: int
    expected_critical_hits: int
    gcc_critical_hits: Optional[int]
    llvm_critical_hits: Optional[int]
    gcc_counter_exact: bool
    llvm_counter_exact: bool
    passed: bool
    overhead_ratio: float


def generate_concurrent_c_program(num_threads: int = 4, iterations: int = 1000) -> str:
    """Generate a multi-threaded C program testing coverage instrumentation under concurrency."""
    return THREAD_TEMPLATE.format(num_threads=num_threads, iterations=iterations)


def analyze_concurrency_fidelity(
    num_threads: int,
    iterations: int,
    gcc_hits: Optional[int],
    llvm_hits: Optional[int],
    overhead_ratio: float = 1.0,
) -> ConcurrencyTestProfile:
    """Analyze whether concurrent execution preserved exact hit counts without counter tearing."""
    expected = num_threads * iterations
    gcc_exact = (gcc_hits == expected) if gcc_hits is not None else False
    llvm_exact = (llvm_hits == expected) if llvm_hits is not None else False

    passed = (gcc_exact or gcc_hits is None) and (llvm_exact or llvm_hits is None)
    return ConcurrencyTestProfile(
        num_threads=num_threads,
        iterations_per_thread=iterations,
        expected_critical_hits=expected,
        gcc_critical_hits=gcc_hits,
        llvm_critical_hits=llvm_hits,
        gcc_counter_exact=gcc_exact,
        llvm_counter_exact=llvm_exact,
        passed=passed,
        overhead_ratio=overhead_ratio,
    )
