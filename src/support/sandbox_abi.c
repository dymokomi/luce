/* Platform ABI isolation only; sandbox policy and execution live in sandbox.lucb. */
#include <stdint.h>

#if !defined(_WIN32)
#include <sys/resource.h>
#include <unistd.h>

int luce_sandbox_set_limit(int resource, uint64_t value) {
    struct rlimit limit = {(rlim_t)value, (rlim_t)value};
    return setrlimit(resource, &limit);
}

int luce_sandbox_close(int descriptor) {
    return close(descriptor);
}
#else
int luce_sandbox_set_limit(int resource, uint64_t value) {
    (void)resource;
    (void)value;
    return -1;
}

int luce_sandbox_close(int descriptor) {
    (void)descriptor;
    return -1;
}
#endif

#if defined(__APPLE__)
/* Present in libSystem but no longer declared without deprecated SDK annotations. */
extern int sandbox_init_with_parameters(const char *, uint64_t,
                                        const char *const[], char **);
extern void sandbox_free_error(char *);

int luce_sandbox_init_with_parameters(const char *profile, unsigned long long flags,
                                      const char *const parameters[], char **error_buffer) {
    return sandbox_init_with_parameters(profile, flags, parameters, error_buffer);
}

void luce_sandbox_free_error(char *message) {
    sandbox_free_error(message);
}
#else
int luce_sandbox_init_with_parameters(const char *profile, unsigned long long flags,
                                      const char *const parameters[], char **error_buffer) {
    (void)profile;
    (void)flags;
    (void)parameters;
    (void)error_buffer;
    return -1;
}

void luce_sandbox_free_error(char *message) {
    (void)message;
}
#endif

#if defined(__linux__)
#include <fcntl.h>
#include <linux/filter.h>
#include <linux/landlock.h>
#include <linux/seccomp.h>
#include <sys/prctl.h>
#include <sys/syscall.h>

int64_t luce_sandbox_landlock_version(void) {
    return syscall(__NR_landlock_create_ruleset, 0, 0, LANDLOCK_CREATE_RULESET_VERSION);
}

int luce_sandbox_landlock_create(uint64_t rights) {
    struct landlock_ruleset_attr ruleset = {.handled_access_fs = rights};
    return (int)syscall(__NR_landlock_create_ruleset, &ruleset, sizeof(ruleset), 0);
}

int luce_sandbox_open_root(const char *root) {
    /* Linux O_PATH | O_CLOEXEC; numeric ABI avoids requiring _GNU_SOURCE. */
    return open(root, 0x280000);
}

int luce_sandbox_landlock_add(int ruleset, uint64_t rights, int root) {
    struct landlock_path_beneath_attr below = {
        .allowed_access = rights,
        .parent_fd = root,
    };
    return (int)syscall(__NR_landlock_add_rule, ruleset, LANDLOCK_RULE_PATH_BENEATH,
                        &below, 0);
}

int luce_sandbox_landlock_restrict(int ruleset) {
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0) return -1;
    return (int)syscall(__NR_landlock_restrict_self, ruleset, 0);
}

int luce_sandbox_seccomp(const struct sock_fprog *program) {
    return prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, program);
}
#else
int64_t luce_sandbox_landlock_version(void) { return -1; }
int luce_sandbox_landlock_create(uint64_t rights) { (void)rights; return -1; }
int luce_sandbox_open_root(const char *root) { (void)root; return -1; }
int luce_sandbox_landlock_add(int ruleset, uint64_t rights, int root) {
    (void)ruleset; (void)rights; (void)root; return -1;
}
int luce_sandbox_landlock_restrict(int ruleset) { (void)ruleset; return -1; }
int luce_sandbox_seccomp(const void *program) { (void)program; return -1; }
#endif
