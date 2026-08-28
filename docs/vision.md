# Luce: From Machine Control to Human Intent

> One safe language, many levels of meaning, for a persistent and federated
> world.

Status: design proposal. [Luce 1.0](language/1.0.md) remains the normative
language specification. This document explores the wider operating-system
direction, and implementation evidence will determine which ideas eventually
enter the language.

## Prologue: the experience we are actually trying to create

Imagine a parent saying:

> Every Sunday, make a short film from the family photos added this week. Let
> everyone suggest changes, but ask me before publishing it.

The system finds a trusted vocabulary for photos, families, editing, music, and
publication. It assembles a capability-scoped behavior the parent can inspect
at the level they understand:

- which family collection it may read;
- which renderer it will use;
- what an AI model may see;
- where the draft will be written;
- who may suggest edits;
- which final act still requires approval.

The behavior works offline. A relative can contribute a better sequencing rule
from another community. The draft is a reversible change; publication is a
separate, durable intent. Years later, the family can still discover which
photos, code, model result, permissions, and decisions produced a particular
film.

The parent experiences one understandable act. A domain author sees a reusable
film-making operation. A systems programmer sees schemas, capabilities,
snapshots, patches, workers, GPU calls, commits, and an outbox. Each perspective
is a faithful view of the same behavior.

That is the ambition. Luce begins as a clear systems language and grows into a
way to reduce the distance between human intention and dependable computation.
Cost, authority, and consequences remain visible throughout that journey.

## 1. What changed in our understanding

We began with a sensible language-design question: what is the smallest native
language that can make compilers, applications, C++ libraries, resources, and
concurrency pleasant and safe?

That question now sits inside a larger one. Luce is intended to build a new
family of operating systems in which:

- context sits at the center of computation;
- data outlives any particular application;
- files, records, media, people, places, and ideas can be linked and queried;
- devices and communities can operate independently and federate later;
- people and AI agents can construct useful behaviors from work experts have
  already done;
- the same system spans local native execution, durable shared worlds, and
  human-scale creation.

That context changes the altitude of language design. The question becomes:

> What must remain true from a machine instruction all the way up to a human
> intention?

Kernel work, an image editor, a replicated document, and a family automation
each need abstractions suited to their risk and execution models. They can still
obey one semantic constitution. Movement between layers should preserve
identity, authority, provenance, and meaning.

This yields the central proposal:

> **Luce should be one safe language with many levels of semantic zoom: low
> enough to build the operating system, and high enough that ordinary people
> can shape their world using trusted abstractions.**

The phrase *semantic zoom* describes a strict promise: zooming in reveals the
same facts at greater resolution. Authority, persistent effects, cost, and
failure keep the same meaning in every view.

## 2. Lessons shaping the design

Several lines of language, systems, and distributed-computing research converge
on a common direction.

### A small set of mechanisms should carry the language

A language becomes easier to learn and more powerful to combine when a small
set of coherent mechanisms solves recurring problems. For Luce, that encourages:

- conditional tests that also produce bindings and proof facts;
- structured concurrency with clear task lifetimes;
- atomic publication for groups of related persistent changes;
- semantic compatibility checks across APIs and stored information;
- an audit of every privileged compiler mechanism.

Each idea belongs at the boundary where its guarantee can be explained and
enforced. Query cardinality belongs in querying. Transactional publication
belongs at the persistent-state boundary. Proof facts belong in ordinary flow
analysis. This placement keeps the language nucleus small while allowing the
larger system to become expressive.

### Safety rules belong in machinery

Rust demonstrates the value of turning frequent classes of mistakes into rules
enforced by the language and its tools. Ownership, explicit mutability, sum
types, checked concurrency traits, and a visible unsafe boundary allow broad
properties to be reviewed once and then reused across a codebase.

The wider engineering lesson includes the whole safety system around the
language: verified representations, assertions, differential execution,
sanitizers, fuzzing, adversarial tests, resource accounting, and performance
measurement. Representation choices still determine allocation, locality, and
throughput. Language rules make those choices safer to express and maintain.

The principle for Luce is:

> Make the safe path ordinary, make exceptional power measurable, and make each
> regression strengthen the earliest shield that should have caught it.

ARC and checked slices provide two shields. Verified intermediate
representations, differential execution, resource ledgers, hostile-input tests,
native-boundary audits, cost explanations, and containment boundaries complete
the safety system around them.

### Information should be durable and inspectable

A context-first operating system needs structured information that can be read
by path, queried directly, changed through exact patches, validated at trusted
boundaries, and retained with history. Data should survive the applications that
view and edit it.

Durable use also requires several kinds of identity. A path identifies a
meaningful place inside a structure. A stable entity identity follows a person,
project, or object across moves and renames. A revision identity names one exact
state. A principal identity carries authority. Clear separation among these
concepts makes synchronization and evolution understandable.

### The synthesis

The complete system has five cooperating responsibilities:

- **The Luce language and runtime** make implementation safety enforceable.
- **The information layer** makes structured data and changes inspectable.
- **The federation layer** makes exchange attributable and locally governed.
- **The behavior runtime** turns explicit authority into validated patches and
  durable intents.
- **Vocabularies** allow expert work to compound upward into human-scale tools.

Together, these responsibilities support a persistent, linked, and federated
world while keeping each safety boundary understandable.

## 3. The semantic constitution

The project needs a short set of rules that survive every level of abstraction.
They are the promises a user, package author, community operator, and future
maintainer can all rely on.

1. **Meaning has a stable identity.** Source, graph nodes, contextual actions,
   and AI tools present faithful views of the same behavior.
2. **Authority is explicit and attenuable.** High-level code receives only the
   capabilities it needs. Dependency authority is included in the behavior's
   visible grant.
3. **Persistent change is inspectable.** Retryable work produces a patch;
   irreversible interaction produces an intent. Local heap mutation remains
   private to an execution domain.
4. **Failure is precise.** Absence, recoverable failure, safety traps,
   cancellation, conflicts, and external rejection remain distinct.
5. **Local reasoning comes first.** Mutable identity stays within an execution
   domain. Workers and federated peers exchange values, immutable artifacts,
   patches, and messages.
6. **History and provenance are data.** Durable results retain enough identity
   to explain where they came from and, where possible, to replay or reverse
   them.
7. **Abstraction preserves material consequences.** Every level exposes the
   same authority, cost, publication, and data-disclosure story at an
   appropriate resolution.
8. **Evolution is checked.** Code, schemas, behavior contracts, and persisted
   information are expected to outlive today's implementation.
9. **Exceptional power is visible.** Native code, unsafe operations, unbounded
   work, non-replayable effects, and elevated profiles are small, attributable,
   and auditable.
10. **Claims are earned vertically.** A mechanism becomes language doctrine only
    after complete real behaviors prove that library and platform expression is
    inadequate.

This constitution spans explicit, monotonically more powerful execution
profiles:

```text
behavior-safe  ⊂  application-safe  ⊂  system-safe  ⊂  audited-native
```

The behavior-safe profile works with snapshots, patches, intents, and bounded
services. The system-safe profile adds facilities such as MMIO for drivers.
Private working memory uses ordinary Luce mutation in every profile. Moving
toward more authority is visible in source or package metadata, build output,
and review. Every high-level vocabulary keeps its execution profile visible.

## 4. Theory of mind: what each participant needs

A coherent design models the people inside it alongside the machine. Each
participant is rational from a different vantage point.

| Participant | What they are trying to achieve | What they fear | What the design owes them |
| --- | --- | --- | --- |
| A person shaping their world | Get a meaningful result with familiar concepts | Breaking something, exposing private data, recurring cost, or an automation they cannot stop | Preview, understandable scope, undo, provenance, revocation, and explanations in their language |
| A domain author | Turn expertise into a reusable concept | Endless wrappers, bespoke integrations, and compiler favoritism | One semantic declaration that projects faithfully into code, UI, graphs, tools, and documentation |
| A systems programmer | Control representation, latency, resources, and native boundaries | Hidden allocation, copying, retention, and unpredictable cleanup | Explicit costs, checked invariants, profiling, and narrow escape hatches |
| An AI agent | Help across large amounts of context | Ambiguous data, prompt injection, or authority it cannot safely interpret | Typed context, provenance-separated inputs, proposal-first execution, and hard budgets |
| A community operator | Serve a community while retaining sovereignty | Abuse, resource exhaustion, malicious peers, compromised keys, and global policy imposed locally | Local trust policy, moderation, quotas, revocation semantics, and inspectable replication |
| A future maintainer | Keep old code and information alive | Names changing meaning, silent schema drift, and irreproducible AI or build results | Stable identities, compatibility reports, migrations, immutable artifacts, and recorded provenance |
| The language designer | Make difficult things ordinary | A beautiful theory that solves the wrong workload, or a growing pile of magic | Corpus evidence, privilege ledgers, kill criteria, and permission to keep mechanisms in libraries |

These viewpoints give “easy” a precise meaning: compressed expression with
preserved understanding. A short action remains easy when publication,
authority, cost, and recovery are clear.

## 5. One language, several altitudes

The same language can support the whole system through distinct abstraction
levels, each with semantics suited to its work.

| Altitude | Primary concepts | Principal safety boundary |
| --- | --- | --- |
| Machine and native | bytes, layout, ABI, devices, GPU, syscalls | audited native modules and generated wrappers |
| Systems | values, ARC identity, resources, collections, failures, workers | Luce type system, checked runtime, MIR verification |
| Operating system | services, principals, capabilities, budgets, domains | process/worker isolation and host policy |
| Durable world | entities, revisions, links, snapshots, patches, intents | schema validation, authorization, atomic commit |
| Vocabulary | domain nouns, verbs, views, merge and migration rules | signed packages and semantic descriptors |
| Behavior | composition, scheduling, context, provenance, explanation | sandboxed execution and explicit grants |
| Human | direct manipulation, forms, rules, graphs, conversation | preview, consent, undo, and faithful semantic zoom |

The implementation at a lower altitude should be reusable at every altitude
above it. Higher altitudes receive narrow, purpose-built access to lower-level
power, much like a file picker provides scoped access to selected information.

This model also clarifies where different ideas belong:

- Zero/one/many results are natural for queries and subscriptions.
- Ordinary mutation belongs inside a Luce execution domain; persistent world
  publication goes through patches.
- Structured workers provide local concurrency; federation uses durable
  messages, idempotency, and domain-specific consistency.
- Capabilities express explicit platform authority at behavior boundaries.
- AI acts as an author and planner through the same declared behaviors and
  grants as every other participant.

## 6. Vocabulary as the next abstraction

The feeling that a good library “becomes part of the language” points toward a
real requirement: packages should be able to teach the whole environment new
domain meaning.

A conventional library exports implementation: types and functions. A
**vocabulary** exports meaning that the whole environment can understand:

- domain nouns, schemas, units, and relationships;
- verbs and their typed inputs and outputs;
- queries, links, views, and editors;
- defaults, labels, examples, and explanations;
- required authority and expected resource cost;
- reversibility, idempotency, and confirmation policy;
- merge, migration, and compatibility rules;
- behavior entrypoints for people, automation, and agents.

One ordinary Luce operation plus a validated semantic descriptor should be
projectable as:

- a source-language call;
- a graph node;
- a contextual action or form;
- a command-line command;
- an AI tool;
- a schedulable job;
- a federated service contract;
- generated documentation and a permission explanation.

Packages extend the world's vocabulary through semantic descriptors. Luce keeps
a stable grammar shared by every package.

This is a falsifiable idea. The first test is to implement the family-film
behavior once and derive all of those projections from its declaration. Each
projection must preserve one behavior identity, the same types
and defaults, the same authority footprint, the same patch/intent behavior, and
the same provenance. If each view needs bespoke code, then the descriptor is
missing meaning. If the descriptor becomes larger and less comprehensible than
the adapters, then the abstraction is wrong.

Generated interfaces will still need small, human-authored semantic contracts.
Human authors supply meaning such as destructiveness, understandable labels,
ethical defaults, and confirmation policy. The compiler validates and reuses
that contract across every projection.

## 7. The behavior seam

An ordinary function computes. A behavior participates in the durable world.
That distinction is the architectural seam that lets local imperative code and
transactional publication coexist.

A behavior is conceptually:

```text
behavior identity
  + versioned code and vocabulary
  + typed inputs
  + capability-scoped context
  + lifetime and resource budgets
  + retry, determinism, and confirmation policy
  → patch + intents + explanation + provenance
```

The execution protocol should be:

```text
snapshot + event + capabilities
               |
               v
       isolated Luce execution
               |
               v
         patch + intents
               |
       validate schema, scope,
       budget, base revision
               |
               v
   atomic patch/provenance/outbox commit
               |
               v
 idempotent external intent execution
```

The two outputs must remain separate:

- A **Patch** changes durable information under known preconditions. It can be
  validated, previewed, retried after recomputation, committed atomically, and
  often reversed.
- An **Intent** requests an effect outside that transaction: publish a film,
  send a message, charge money, operate hardware, or invoke a remote service. It
  is durable, explicit, idempotent where possible, and replayed only through its
  declared policy.

Ordinary Luce code inside the behavior may allocate and mutate private state.
Its world input is an immutable snapshot. A trap, failure, exhausted budget,
stale revision, or cancellation discards the candidate patch before publication.

This boundary provides transactional publication while ordinary ARC memory,
native calls, and external I/O keep their direct execution semantics.

Initially, `Behavior`, `Snapshot`, `Patch`, `Intent`, `Capability`, `Principal`,
and related concepts should be ordinary Luce platform types plus a restricted
host protocol. A compiler-recognized declaration can be evaluated after several
independent domains reveal a shared need for stronger safety, diagnostics, or
composition.

## 8. Safety across every layer

Memory safety protects the foundation. Every altitude adds a class of failures
that requires its own enforceable shield.

### Language and runtime safety

Safe Luce should make memory corruption, dangling safe slices, double
destruction, unhandled fallible results, accidental shared-object data races,
and escaped raw native borrows impossible by construction or verification.

Some conditions remain runtime checks: bounds, overflow, invalid conversion,
budget exhaustion, and stack limits. Some are initially diagnostics and
instrumentation problems: ARC cycles, expensive graph copying, surprising
retention, and risky reentrancy.

Resource safety deserves special honesty. ARC calls `deinit` when the last
strong reference is released. Cycles can delay that release indefinitely, while
traps and power loss bypass normal scope exit. Critical resources should use
explicit idempotent close, domain-level host registries, forced cleanup at
worker/process termination, and checked-runtime leak reports. Repeated failures
in real programs would provide evidence for a narrow affine resource mechanism.

### Behavior safety

Capabilities scope authority. Information-flow controls govern how data moves
between granted domains. A behavior with access to private medical records and
public publication requires an explicit, reviewable declassification boundary.

Composition therefore needs:

- one visible grant calculated for the complete composed behavior;
- explicit review when a new read domain becomes connected to a write domain;
- provenance or sensitivity carried with contextual values;
- explicit declassification at privacy boundaries;
- compiler and runtime checks for authority captured by globals or closures;
- structural budgets against deep documents, query explosions, fan-out, and
  recomputation storms.

### AI safety

AI makes context powerful. Every linked document may also contain hostile input.
Instruction, user data, retrieved content, tool output, and model output keep
distinct provenance throughout evaluation.

The initial rule should be:

> AI proposes typed data, patches, and intents. Deterministic trusted code
> validates and commits them.

Model context must be minimized and capability-scoped. Token, time, money,
network, recursion, and mutation budgets are mandatory. Irreversible or
privacy-crossing actions require a separately authorized standing rule or a
meaningful confirmation. Replay uses the recorded model result as an immutable
artifact, making the historical execution reproducible.

### Federation safety

Signatures establish authorship. Truth, quality, and safety come from separate
validation and local trust policy. Federated communities also need key rotation
and recovery, expiry, replay protection, quarantine, moderation, blocking,
quotas, reproducible artifacts, and honest offline revocation semantics.

The information graph itself is sensitive. Links, tags, timestamps, sizes, and
query patterns can expose relationships even when contents are encrypted.
Indexes should be private by default, namespaces partitionable, queries local
where possible, and link-existence disclosure an explicit policy.

## 9. Identity, time, and federation

A world that survives applications and devices needs several explicit kinds of
identity:

- **Value identity:** copied information equal by content or value semantics.
- **Local reference identity:** one ARC object inside one execution domain.
- **Structural path:** a meaningful position within a document lineage.
- **Entity identity:** a durable thing that survives moves and renames.
- **Revision identity:** immutable state or content at a point in history.
- **Address:** a human-facing, mutable way to locate something.
- **Principal identity:** authority rooted in keys, including rotation and
  recovery.

Conflating these would make evolution appear simple while moving ambiguity into
the most dangerous parts of the system.

Federation needs consistency models chosen for each kind of state:

| State | Appropriate model |
| --- | --- |
| Local draft | local authority, synchronized later |
| Collaborative document | mergeable history or explicit conflict |
| Public conversation | signed append-only events plus moderation |
| Presence | lossy, expiring, non-historical updates |
| Unique inventory or ownership | one authority or domain-specific consensus |
| Payment or irreversible action | idempotent intent and domain ledger |
| Derived view or cache | disposable and recomputable |

Offline community networking provides delay tolerance, local sovereignty, and
store-and-forward exchange. A live shared-world experience adds presence and
immediate feedback when connectivity allows. Durable asynchronous semantics
remain the source of truth underneath that live experience.

Atomicity should normally stop at one community or document authority. Work
across authorities uses durable messages, idempotency, and compensating
workflows. Concurrent information may retain both versions. Money, permissions,
unique names, and ownership use domain-specific resolution. Custom merge
functions must be pure, deterministic, bounded, versioned, and authority-free.

## 10. Evolution is part of correctness

In a persistent world, time belongs in the type-and-tooling story. Public APIs,
schemas, capabilities, behavior descriptors, native ABIs, and serialized data
are promises to future code and people.

The already-planned `luce api diff` should report compatibility along distinct
dimensions:

- source compatibility;
- Luce runtime contract compatibility;
- C ABI compatibility;
- serialized-schema compatibility;
- behavior and capability-contract compatibility;
- changes that are structurally legal but require human semantic review.

The tool reports exactly what it can establish. For example, changing a function
from `T!` to `T` strengthens the result contract while existing source containing
`try f()` may require an edit. Structural compatibility can flag human meaning
for review. Canonical public-interface, ABI, schema, descriptor, and migration
artifacts carry durable authority across compiler versions. Commits can name the
exact behavior bundle, input revision, capability grant, and recorded AI artifact
that produced them.

This turns backward compatibility from politeness into a first-class product.

## 11. What belongs where

The vision will remain coherent only if each subsystem owns a narrow promise.

| Layer | Owns | Boundary |
| --- | --- | --- |
| Luce language | values, ARC references, precise failure, closures, interfaces, checked slices, structured isolated workers, native boundaries | local program semantics |
| Luce compiler/runtime | verification, lowering, cleanup, sendability, cost reports, API analysis, audited native surface | implementation guarantees and observable cost |
| Information layer | structured documents, paths, queries, schemas, patches, snapshots, and history | durable information inside a governed namespace |
| Behavior runtime | isolation, capabilities, budgets, patch validation, provenance, and outbox intents | one authorized execution and its publication |
| Federation layer | durable identities, signed exchange, replication, local trust, and policy | exchange among independently governed communities |
| Vocabulary system | domain meaning, descriptors, projections, compatibility, and migration contracts | reusable semantic concepts |
| Human and AI tools | direct manipulation, forms, graphs, conversation, preview, and explanation | faithful views of declared behaviors |

Several powerful ideas remain in the research queue: transactional heaps,
zero/one/many expression semantics, proof syntax, general effect rows,
distributed functions, custom grammar, universal merge rules, affine resources,
and first-class syntax for behaviors or capabilities. Ordinary types,
descriptors, and host protocols provide the experimental form for each idea.
Evidence from multiple complete domains can then determine which mechanisms
earn compiler or language support.

## 12. What we know, what we believe, and our open questions

The proposal should be explicit about its epistemic state.

### We know

- Luce has a coherent proposed native-language nucleus: copying values, local
  ARC identity, precise absence/failure/trap distinctions, checked operations,
  isolated workers, and generated native boundaries.
- The implementation is still early. The parser covers much of the proposed 1.0
  surface, while the executable HIR, MIR, and backend subset is smaller.
- The current information work demonstrates useful local invariants: readable
  structure, queries, optional schemas, snapshots, exact change representation,
  and history.
- Language-enforced constraints, verified IR, fuzzing, sanitizers, differential
  tests, and measurable escape hatches can eliminate broad classes of defects.
- Persistent, federated, AI-mediated software adds authority, provenance,
  evolution, privacy, and distributed-consistency problems beyond memory safety.

### We believe, and must test

- One semantic descriptor can make domain expertise feel native across source,
  UI, graphs, commands, schedules, and AI tools.
- Snapshot-to-patch behavior execution can provide the useful transactional
  guarantee at the persistent-publication boundary.
- Explicit capability values and behavior manifests can make authority
  understandable at behavior boundaries.
- ARC, scoped mutation, isolation, resource ledgers, and strong tooling can
  deliver the safety and predictability needed for the OS.
- Stable entity and revision identities can complement structural paths in the
  information model.
- The same behavior artifact can support both novice authoring and expert
  inspection through faithful semantic zoom.

### Open questions

- How vocabulary descriptors can remain expressive, compact, and declarative.
- Whether mutable closure capture should remain implicit, become explicit, or be
  restricted.
- Whether ARC cycles and resource closure are manageable in real OS workloads.
- Whether copied worker graphs are fast enough for scenes, media, indexes, and
  model context.
- Which domains can merge automatically and which require a designated
  authority.
- Which effect facts should remain compiler-internal, appear in behavior
  descriptors, or eventually enter the language.
- Whether ordinary people can accurately predict the scope, privacy, cost, and
  failure behavior of composed automations.
- How much projection can be derived faithfully from one semantic declaration.

Open questions keep the project flexible and give experiments a clear purpose.

## 13. The path: learning through vertical slices

The sequence matters. A complete path through the system produces stronger
evidence than disconnected surface features. Each phase below begins with a
belief, builds the smallest proof, records what we learned, and has an explicit
continuation gate.

### Phase 0 — Write the constitution and choose the proving behavior

**What we think:** the project can share one set of invariants across distinct
execution profiles.

**Build:** adopt a glossary for value, reference, path, entity, revision,
principal, snapshot, patch, intent, behavior, capability, community, vocabulary, and
projection. Write the safety constitution, execution-profile rules, threat
model, and compiler privilege ledger. Specify twenty representative behaviors
from drivers and compilers through media, communication, personal automation,
and federation. Select the family-film behavior as the first north-star slice,
plus two deliberately different follow-ups.

**Learn:** whether the team uses the same words for the same state transitions,
failure modes, and authority boundaries.

**Gate:** every north-star step has stable terminology and a complete authority
explanation. Gaps send the team back to refine the constitution.

**Where it brings us:** a shared mental model against which language and
platform proposals can be judged.

### Phase 1 — Earn the safe native foundation

**What we think:** Luce's value/reference model can provide a pleasant,
high-performance OS foundation with predictable ownership and cleanup.

**Build:** continue the existing compiler plan in semantic-risk order:

1. aggregates, layout, enums, and exhaustive matching;
2. fallible execution and cleanup across every exit;
3. ARC classes, weak references, resources, and checked ledgers;
4. closures, collections, owner-retaining slices, and scoped mutable slices;
5. real semantic analysis for initialization, narrowing, capture, escape,
   sendability, and ownership facts;
6. isolated workers and measured transfer;
7. FIIR, generated native wrappers, and audited raw modules;
8. self-hosting, bootstrap reproducibility, and language freeze.

Resolve fallible iteration before implementing `for`: iteration over files,
streams, decoding, and federation needs three explicit outcomes—value, end, and
error. Decide mutable closure capture by corpus measurement before lowering
silently creates shared ARC cells.

At every milestone, compare the HIR interpreter, MIR interpreter, and compiled
artifact. Add malformed-MIR rejection, generated programs, fuzzing, allocation
failure, cancellation, sanitizers, native ABI probes, and cost accounting. Every
bug is assigned to the earliest shield that should have stopped it; the fix adds
a direct regression and neighboring generator or fuzzer cases.

**Learn:** actual ARC cycle rate, resource leaks, hidden allocation, retain
traffic, worker copy cost, native escape surface, and optimizer correctness.

**Gate:** representative system services survive hostile and fault-injected
tests; optimized artifacts agree with reference semantics; unsafe/native power
is attributable and small; performance is compared with credible baselines.

**Narrow or stop:** if correctness depends mainly on style conventions, raw
hooks spread through ordinary modules, or ARC/resource failures dominate, revise
the core mechanism before claiming production OS safety.

**Where it brings us:** a language with an evidence-backed safety story.

### Phase 2 — Build the local behavior kernel as ordinary Luce

**What we think:** snapshot, patch, intent, and capability form the correct seam
between private computation and the durable world.

**Build:** prototype `Principal`, `EntityId`, `RevisionId`, `Link[T]`,
`Snapshot[T]`, `Patch[T]`, `Intent`, `Capability[T]`, `BehaviorId`, and
`BehaviorResult[T]` as platform packages and host protocols. Run one behavior
locally under explicit memory, time, token, and authority budgets. Atomically
commit its validated patch, provenance, and outbox record, then execute intents
with durable idempotency keys.

Kill the process at every transition. Inject stale revisions, invalid schemas,
unauthorized paths, cancellation, repeated delivery, model failure, and resource
exhaustion.

**Learn:** whether ordinary Luce types express the protocol clearly; where
authority or retry semantics become ambiguous; which invariants belong in the
compiler versus the host.

**Gate:** fault injection proves atomic publication and capability confinement;
pure computation replays from recorded inputs; intent idempotency handles every
accidental retry.

**Narrow or stop:** downloaded-code exposure begins once retryable code is
confined to declared outputs and the host can derive an exact authority
explanation. Until then, the behavior runtime remains an internal experiment.

**Where it brings us:** a trustworthy unit of world computation.

### Phase 3 — Prove vocabulary projection

**What we think:** reusable meaning can make expert work feel native to the
whole environment.

**Build:** create the smallest descriptor that exports one behavior as Luce API,
graph node, contextual form/action, command, scheduled job, AI tool, and
documentation. Derive the projections from existing Luce declarations and one
semantic descriptor. Include authority, reversibility, expected duration/cost,
labels, defaults, examples, and confirmation rules.

Implement the family-film vocabulary end to end. Then attempt two unrelated
domains—for example a compiler/build behavior and a federated community
moderation behavior—to prevent the first example from designing the universal
model around itself.

**Learn:** which semantic facts are genuinely common, which are presentation
specific, and whether descriptor authoring is smaller and safer than conventional
integration code.

**Gate:** all projections preserve identity, types, defaults, authority,
patch/intent behavior, and provenance. A third-party vocabulary integrates
through the published descriptor protocol.

**Narrow or stop:** if each vocabulary needs bespoke integration, or the
descriptor becomes an untyped second language, keep projections as explicit
libraries. Consider syntax only after three distinct domains expose the same
diagnostic or safety deficit.

**Where it brings us:** the first real answer to “it feels less like a library
and more like using the language.”

### Phase 4 — Build the authoring ladder and test human understanding

**What we think:** source, direct manipulation, forms, rules, graphs, and
conversation can edit the same behavior artifact at different levels of detail.

**Build:** allow the family-film behavior to be created and modified through:

- a ready-made contextual action;
- a fill-in rule;
- a visual graph;
- AI-assisted conversation;
- direct Luce source.

Every view must reveal the same grant and data flow when expanded. AI output
takes the form of a scoped, inspectable descriptor or patch proposal.

Test with ordinary users, domain authors, systems programmers, and community
operators. Ask participants to predict what data is read, what can change, what
can leave the device, what happens on failure, and how to stop or undo it.

**Learn:** where semantic zoom helps, where it omits material facts, and which
approval moments support genuine understanding.

**Gate:** people at each altitude can complete the task and accurately predict
its material consequences; experts can reach the exact lower-level explanation
and find the same execution story in greater detail.

**Narrow or stop:** if recovery requires understanding the systems layer, or
high-level views routinely omit authority and cost, reduce automation and make
the projection more explicit.

**Where it brings us:** low friction grounded in accumulated knowledge and
visible consequences.

### Phase 5 — Add durable identity, evolution, and federation

**What we think:** the behavior model can survive device boundaries, offline
work, renames, upgrades, and hostile peers.

**Build:** connect two independently operated communities. Give entities stable
IDs separate from paths and addresses. Exchange immutable behavior bundles and
signed commits. Exercise offline edits, explicit conflicts, schema migration,
key rotation, expired grants, replay attacks, moderation, rollback, and package
upgrade quarantine.

Extend compatibility tooling across APIs, ABIs, schemas, descriptors, grants,
and migrations. Attach pure, bounded, versioned merge policies only to domains
that can safely merge; use domain authorities and durable workflows elsewhere.

**Learn:** what can remain local-first, what needs authority, how much metadata
privacy federation leaks, and whether provenance remains comprehensible after
years of evolution.

**Gate:** an entity survives moves and renames; unauthorized or replayed changes
are rejected; concurrent work remains recoverable; idempotency protects
irreversible effects; each community retains local trust and moderation control.

**Narrow or stop:** domains that require permanent global coordination receive
an explicit authority. Delay-tolerant domains retain offline federation.

**Where it brings us:** a real network of durable, independently governed
worlds.

### Phase 6 — Optimize only what the measurements reveal

**What we think:** clear semantics allow aggressive implementation improvement
while preserving the human model.

**Build:** instrument allocation, ARC traffic, copies, serialization, query
work, incremental recomputation, model use, startup, latency, energy, and
federation traffic. Then introduce shared immutable backing, content-addressed
blobs, ownership transfer, incremental views, structured fan-out, remote
execution, or representation packing only where workloads demand them.

Branch-local proof facts—presence, enum narrowing, bounds relationships,
nonzero values, initialization—should first improve verification and diagnostics,
then justify check elimination. Ordinary code should produce these facts
automatically.

**Learn:** which costs dominate in real workloads and which abstractions remain
cheap enough to be default.

**Gate:** defined workloads meet explicit latency, memory, startup, and energy
budgets while preserving reference behavior and safety checks.

**Narrow or stop:** pervasive STM, automatic parallelization, shared mutable
worker memory, and broad effect systems enter consideration when measured
workloads demonstrate a recurring need.

**Where it brings us:** high performance as an observable property of the
system.

## 14. Immediate decisions and next actions

The first actions should preserve momentum in the compiler while opening a
narrow path toward the larger vision.

1. Adopt this document as a directional companion to the authoritative 1.0
   specification.
2. Write the safety constitution and profile definitions where they clarify
   existing guarantees. Platform syntax remains an evidence-driven future
   decision.
3. Create the compiler privilege ledger and mark every current special case,
   native escape, implicit allocation, and closed protocol.
4. Resolve three pre-implementation design risks: fallible iteration, mutable
   closure capture, and checked resource cleanup.
5. Specify `luce api diff` as a multidimensional compatibility report.
6. Keep executing the compiler milestones, and promote differential testing,
   fuzzing, hostile inputs, resource ledgers, cost reports, and native ABI probes
   from “eventually” to release gates for OS use.
7. Write a platform glossary and threat model while keeping Luce syntax stable.
8. Specify the family-film behavior as a complete trace from human request to
   native work, patch, intent, provenance, and synchronization.
9. Prototype the behavior kernel as ordinary Luce packages and a restricted host
   protocol.
10. Prototype one semantic descriptor and measure how much handwritten glue it
    actually removes across source, UI, graph, command, schedule, and AI views.
11. Run the same projection experiment in two unrelated domains before designing
    a language feature.
12. Establish quantitative continuation gates for safety, performance,
    understandability, federation, and compatibility, and publish failures as
    design evidence.

These steps deliberately allow several outcomes. The descriptor may remain a
library format. Some domains may require central authority while others
federate. ARC may need a narrow resource addition. A future behavior declaration
may earn syntax. Flexibility lets the direction mature through evidence.

## Epilogue: what success feels like

Return to the parent making the weekly family film.

Their experience centers on familiar ideas: photos, family, editing,
suggestions, and publishing. The libraries, distributed execution, permissions,
and AI pipeline become a transparent foundation beneath one new idea expressed
in those words.

The domain authors should recognize their exact expertise in that experience.
The systems programmer should be able to zoom in and account for every
allocation, copy, native call, capability, patch, and intent. The community operator
should retain authority over local policy. The future maintainer should be able
to explain the film's provenance long after today's implementation is gone.

That is what “easy because someone already did the hard work” should mean. The
hard work becomes reusable, constrained, visible, and trustworthy.

Luce can bring systems safety, durable information, visual composition,
AI-assisted authorship, and federation together around one promise:

> From machine control to human intent, power composes upward while safety,
> meaning, and ownership remain intact.

## Selected background reading

- [Lex Fridman Podcast #467 — Tim Sweeney transcript](https://lexfridman.com/tim-sweeney-transcript/)
- [The Verse Calculus (ICFP 2023)](https://simon.peytonjones.org/assets/pdfs/verse-icfp23.pdf)
- [The Next Mainstream Programming Language (Tim Sweeney, 2006)](https://groups.csail.mit.edu/cag/crg/papers/sweeney06games.pdf)
- [The Book of Verse](https://verselang.github.io/book/)
- [The Rust Programming Language — Understanding Ownership](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html)
- [The Rust Programming Language — Fearless Concurrency](https://doc.rust-lang.org/book/ch16-00-concurrency.html)
- [Unison: the big idea](https://www.unison-lang.org/learn/the-big-idea/)
- [Local-first software](https://www.inkandswitch.com/essay/local-first/)
