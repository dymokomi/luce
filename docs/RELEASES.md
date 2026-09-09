# Releases

## 0.1.1

- Declared Base handle destroy functions use Luce's close-once bookkeeping, so direct
  destruction, aliases, repeated calls, and `with` cleanup cannot destroy a handle twice.
- Pin Base 0.11.26, including directory allocation and process capture failure cleanup.
- Full gate verified on arm64 macOS.
