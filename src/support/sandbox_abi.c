/* Platform ABI isolation only; sandbox policy and execution live in sandbox.lucb. */
#if defined(__APPLE__)
#include <stdint.h>

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
