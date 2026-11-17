/* Synthetic reproduction of the pinned scheduler's absolute-deadline contract. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
static uint64_t cached,host,deadline,dispatch_cost;
static unsigned yielded;
void sched_vtime_refresh(void) {cached=host;}
uint64_t sched_vtime_deadline_after(uint64_t delta) {return UINT64_MAX-cached<delta?UINT64_MAX:cached+delta;}
void sched_service_wait(uint64_t end) {
    sched_vtime_refresh();deadline=end;
    if(cached+dispatch_cost<end)yielded++;
}
void sched_delay_current_dispatching(uint64_t interval) {
    deadline=host+interval;
    yielded++; /* pinned scheduler holds this thread out of the next pick */
}
#include "coop_service_wait.h"
int main(void) {
    const uint64_t delays[]={0,1000,2001,5000,20000,250000};
    for(unsigned i=0;i<sizeof delays/sizeof delays[0];i++) {
        cached=100000;host=cached+delays[i];yielded=0;dispatch_cost=0;
        sched_service_wait(sched_vtime_deadline_after(2000));
        if(delays[i]>=2000)assert(!yielded); /* failing-before starvation path */
        cached=100000;host=cached+delays[i];yielded=0;
        loa_coop_service_wait(2000);
        assert(yielded==1 && deadline==host+2000);
        cached=host;yielded=0;dispatch_cost=5000;
        sched_service_wait(sched_vtime_deadline_after(2000));
        assert(!yielded); /* clock refresh alone still loses to a late pick */
        yielded=0;loa_coop_service_wait(2000);
        assert(yielded==1);
    }
    puts("PASS: stale-clock baseline loses its delay after slow IPC; refreshed waits yield in all six cases");
    return 0;
}
