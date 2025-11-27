#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/kthread.h>
#include <linux/delay.h>
#include <linux/spinlock.h>
#include <linux/debugfs.h>
#include <linux/seq_file.h>
#include <linux/slab.h>
#include <linux/timekeeping.h>
#include <linux/smp.h>
#include <linux/cpumask.h>
#include <linux/atomic.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("ChatGPT");
MODULE_DESCRIPTION("Kernel microbenchmark for spinlock strategies (TSP-friendly) - safe unload version");

static int threads = 16;
module_param(threads, int, 0444);
MODULE_PARM_DESC(threads, "Number of kernel worker threads to create");

static unsigned long iterations = 1000;
module_param(iterations, ulong, 0444);
MODULE_PARM_DESC(iterations, "Iterations per worker thread");

static int work_size = 256; /* number of counters accessed inside critical section */
module_param(work_size, int, 0444);
MODULE_PARM_DESC(work_size, "Number of shared counters touched in critical section");

static bool bind_cpus = false;
module_param(bind_cpus, bool, 0444);
MODULE_PARM_DESC(bind_cpus, "Bind each thread to a CPU round-robin");

/* Global spinlock to benchmark - this will use kernel's spinlock implementation */
static spinlock_t global_lock;

struct worker_stats {
    int id;
    struct task_struct *task;
    u64 acquires;
    u64 total_wait_ns;
    u64 max_wait_ns;
    u64 total_hold_ns;
    u64 max_hold_ns;
    int last_cpu;
    spinlock_t stats_lock; /* protect per-worker aggregates */
};

static struct worker_stats *wstats;
static u64 *shared_counters;
static struct dentry *dbg_dir;
static struct dentry *dbg_stats_file;
static int created_threads = 0;

static inline u64 now_ns(void)
{
    return ktime_get_ns();
}

static int worker_fn(void *data)
{
    struct worker_stats *st = data;
    if (bind_cpus) {
        int cpu = st->id % num_online_cpus();

        if (!cpu_online(cpu)) {
            pr_warn("tspk/%d: target cpu %d not online, skip bind\n", st->id, cpu);
        } else {
            /* bind current kthread to CPU 'cpu' safely */
            set_cpus_allowed_ptr(current, cpumask_of(cpu));
            /* 或用: sched_setaffinity(current, cpumask_of_cpu(cpu)); */
            pr_info("tspk/%d: bound to cpu %d\n", st->id, cpu);
        }
    }

    allow_signal(SIGKILL);
    unsigned long i;
    for (i = 0; i < iterations && !kthread_should_stop(); ++i) {

        u64 t0 = now_ns();
        spin_lock(&global_lock);
        u64 t1 = now_ns();
        u64 wait_ns = t1 - t0;

        /* critical section */
        u64 hold0 = now_ns();
        int j;
        for (j = 0; j < work_size; ++j)
            shared_counters[j]++;
        u64 hold1 = now_ns();
        u64 hold_ns = hold1 - hold0;

        spin_unlock(&global_lock);

        /* update stats */
        spin_lock(&st->stats_lock);
        st->acquires++;
        st->total_wait_ns += wait_ns;
        if (wait_ns > st->max_wait_ns)
            st->max_wait_ns = wait_ns;
        st->total_hold_ns += hold_ns;
        if (hold_ns > st->max_hold_ns)
            st->max_hold_ns = hold_ns;
        st->last_cpu = smp_processor_id();
        spin_unlock(&st->stats_lock);

        if (signal_pending(current))
            break;
        cond_resched();
    }

    while (!kthread_should_stop())
        schedule();

    pr_info("tsp_kbench: worker_fn over id=%d\n", st->id);
    return 0;
}

static int stats_show(struct seq_file *m, void *v)
{
    int i;
    seq_puts(m, "id,last_cpu,acquires,avg_wait_ns,max_wait_ns,avg_hold_ns,max_hold_ns\n");
    for (i = 0; i < threads; ++i) {
        u64 acquires, tw, th, mw, mh;
        spin_lock(&wstats[i].stats_lock);
        acquires = wstats[i].acquires;
        tw = wstats[i].total_wait_ns;
        th = wstats[i].total_hold_ns;
        mw = wstats[i].max_wait_ns;
        mh = wstats[i].max_hold_ns;
        spin_unlock(&wstats[i].stats_lock);

        if (acquires > 0)
            seq_printf(m, "%d,%d,%llu,%llu,%llu,%llu,%llu\n",
                       wstats[i].id, wstats[i].last_cpu,
                       (unsigned long long)acquires,
                       (unsigned long long)(tw / acquires),
                       (unsigned long long)mw,
                       (unsigned long long)(th / acquires),
                       (unsigned long long)mh);
        else
            seq_printf(m, "%d,%d,0,0,0,0,0\n", wstats[i].id, wstats[i].last_cpu);
    }
    return 0;
}

static int stats_open(struct inode *inode, struct file *file)
{
    return single_open(file, stats_show, NULL);
}

static const struct file_operations stats_fops = {
    .owner = THIS_MODULE,
    .open = stats_open,
    .read = seq_read,
    .llseek = seq_lseek,
    .release = single_release,
};

static void cleanup_all(void)
{
    int i;

    if (dbg_dir) {
        debugfs_remove_recursive(dbg_dir);
        dbg_dir = NULL;
        dbg_stats_file = NULL;
    }

    /* stop threads that were created */
    for (i = 0; i < created_threads; ++i) {
        pr_info("tsp_kbench: stopping thread %d task=%p\n", i, wstats[i].task);
        if (wstats[i].task) {
            kthread_stop(wstats[i].task);
            put_task_struct(wstats[i].task);
            wstats[i].task = NULL;
        }
    }
    /* give threads a moment to exit */
    msleep(50);

    kfree(shared_counters);
    shared_counters = NULL;
    kfree(wstats);
    wstats = NULL;
}

static int __init tsp_kbench_init(void)
{
    int i;
    pr_info("tsp_kbench: init threads=%d iterations=%lu work_size=%d bind=%d\n",
            threads, iterations, work_size, bind_cpus);

    if (threads <= 0) return -EINVAL;

    wstats = kcalloc(threads, sizeof(struct worker_stats), GFP_KERNEL);
    if (!wstats) return -ENOMEM;

    shared_counters = kcalloc(max(1, work_size), sizeof(u64), GFP_KERNEL);
    if (!shared_counters) {
        kfree(wstats);
        return -ENOMEM;
    }

    spin_lock_init(&global_lock);

    /* create debugfs first so that readers can access stats even if threads are starting */
    dbg_dir = debugfs_create_dir("tsp_kbench", NULL);
    if (!dbg_dir) {
        pr_warn("tsp_kbench: debugfs not available\n");
        /* continue without debugfs but still allow benchmark */
    } else {
        dbg_stats_file = debugfs_create_file("stats", 0444, dbg_dir, NULL, &stats_fops);
        if (!dbg_stats_file) {
            pr_warn("tsp_kbench: failed to create stats file\n");
            debugfs_remove_recursive(dbg_dir);
            dbg_dir = NULL;
        }
    }

    /* create threads */
    for (i = 0; i < threads; ++i) {
        char name[32];
        wstats[i].id = i;
        wstats[i].acquires = 0;
        wstats[i].total_wait_ns = 0;
        wstats[i].max_wait_ns = 0;
        wstats[i].total_hold_ns = 0;
        wstats[i].max_hold_ns = 0;
        wstats[i].last_cpu = -1;
        spin_lock_init(&wstats[i].stats_lock);
        snprintf(name, sizeof(name), "tspk/%d", i);
        wstats[i].task = kthread_run(worker_fn, &wstats[i], name);
        if (IS_ERR(wstats[i].task)) {
            pr_err("tsp_kbench: failed to create thread %d\n", i);
            wstats[i].task = NULL;
            break;
        }
        get_task_struct(wstats[i].task);
        created_threads++;
    }

    if (created_threads == 0) {
        pr_err("tsp_kbench: no threads created, aborting\n");
        cleanup_all();
        return -ENOMEM;
    }

    return 0;
}

static void __exit tsp_kbench_exit(void)
{
    pr_info("tsp_kbench: exit\n");

    cleanup_all();
}

module_init(tsp_kbench_init);
module_exit(tsp_kbench_exit);
