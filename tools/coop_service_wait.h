/* SPDX-License-Identifier: GPL-3.0-or-later
 * Host IPC consumes wall time without a guest scheduling boundary. Anchor the
 * service delay after that work. A late dispatch must hand the CPU to another
 * ready thread before the high-priority poller is eligible again. These are
 * host polling workers, not the implementation of sceKernelDelayThread. */
#ifndef LOA_COOP_SERVICE_WAIT_H
#define LOA_COOP_SERVICE_WAIT_H
static inline void loa_coop_service_wait(uint64_t interval_us) {
    sched_vtime_refresh();
    sched_delay_current_dispatching(interval_us);
}
#endif
